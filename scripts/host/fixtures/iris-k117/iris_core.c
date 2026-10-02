// SPDX-License-Identifier: GPL-2.0-only
/*
 * Copyright (c) 2022-2024 Qualcomm Innovation Center, Inc. All rights reserved.
 */

#include <linux/ctype.h>
#include <linux/module.h>
#include <linux/pm_runtime.h>
#include <linux/timekeeping.h>

#include <linux/delay.h>

#include "iris_core.h"
#include "iris_firmware.h"
#include "iris_instance.h"
#include "iris_state.h"
#include "iris_vpu_common.h"

bool iris_markers;
module_param_named(markers, iris_markers, bool, 0644);
MODULE_PARM_DESC(markers, "print a line before/after each risky step (for netconsole)");

/*
 * ROG5, encoder bring-up: after each marker wait this long, so that
 * netconsole, a `dmesg -w` reader and the persistent ramoops console have
 * the line before the next step touches the hardware.
 */
unsigned int iris_marker_delay_ms;
module_param_named(marker_delay_ms, iris_marker_delay_ms, uint, 0644);
MODULE_PARM_DESC(marker_delay_ms, "wait after each marker line (ms, max 1000)");

void iris_mark_settle(void)
{
	unsigned int ms = min(READ_ONCE(iris_marker_delay_ms), 1000U);

	if (!ms)
		return;
	if (preemptible())
		msleep(ms);
	else
		mdelay(ms);
}

/* ROG5: called with core->lock held; @pkt starts with the HFI size word */
void iris_core_trace(struct iris_core *core, u32 dir, const void *pkt)
{
	struct iris_trace_entry *e = &core->trace[core->trace_next++ % IRIS_TRACE_ENTRIES];
	u32 size = *(const u32 *)pkt;

	e->ns = ktime_get_ns();
	e->dir = dir;
	memset(e->w, 0, sizeof(e->w));
	memcpy(e->w, pkt, min_t(u32, size, sizeof(e->w)));
}

/* ROG5: one firmware debug-queue message (not NUL-terminated) */
void iris_core_fw_log(struct iris_core *core, const u8 *msg, size_t len)
{
	char *line = core->fw_log[core->fw_log_next++ % IRIS_FW_LOG_LINES];
	size_t i, n = 0;

	for (i = 0; i < len && msg[i] && n < IRIS_FW_LOG_LEN - 1; i++)
		line[n++] = isprint(msg[i]) ? msg[i] : ' ';
	while (n && line[n - 1] == ' ')
		n--;
	line[n] = '\0';
	dev_err_ratelimited(core->dev, "fw: %s\n", line);
}

/*
 * ROG5: print what the firmware left in the SFR (Subsystem Failure Reason)
 * buffer, the last HFI packets in both directions and the last firmware
 * messages. Called with core->lock held, before teardown frees the SFR and
 * queue memory. Rate limited to one dump per 10 s unless @force.
 */
void iris_core_dump_diag_locked(struct iris_core *core, const char *reason, bool force)
{
	u64 now = ktime_get_ns();
	char sfr[256];
	u32 i, n;

	if (!force && core->diag_jiffies &&
	    time_before(jiffies, core->diag_jiffies + 10 * HZ))
		return;
	core->diag_jiffies = jiffies ?: 1;

	dev_err(core->dev, "diagnostics (%s): state %d, attempt %u\n",
		reason, core->state, core->init_attempt);

	if (core->sfr_vaddr) {
		const u8 *p = (const u8 *)core->sfr_vaddr + sizeof(u32);
		u32 size = READ_ONCE(*(u32 *)core->sfr_vaddr);

		for (n = 0; n < sizeof(sfr) - 1 && n < SFR_SIZE - sizeof(u32) && p[n]; n++)
			sfr[n] = isprint(p[n]) ? p[n] : '.';
		sfr[n] = '\0';
		dev_err(core->dev, "SFR (size word %#x): %s\n", size, n ? sfr : "<empty>");
	} else {
		dev_err(core->dev, "SFR: not allocated\n");
	}

	for (i = 0; i < IRIS_TRACE_ENTRIES; i++) {
		const struct iris_trace_entry *e =
			&core->trace[(core->trace_next + i) % IRIS_TRACE_ENTRIES];

		if (!e->dir)
			continue;
		dev_err(core->dev,
			"hfi %c -%llu us: %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x\n",
			e->dir, div_u64(now - e->ns, NSEC_PER_USEC), e->w[0], e->w[1],
			e->w[2], e->w[3], e->w[4], e->w[5], e->w[6], e->w[7], e->w[8],
			e->w[9], e->w[10], e->w[11], e->w[12], e->w[13], e->w[14], e->w[15]);
	}

	for (i = 0; i < IRIS_FW_LOG_LINES; i++) {
		const char *line = core->fw_log[(core->fw_log_next + i) % IRIS_FW_LOG_LINES];

		if (line[0])
			dev_err(core->dev, "fw log: %s\n", line);
	}
}

/*
 * ROG5: drop the module pin taken in iris_fw_load() once the firmware is
 * shut down and the core powered off without a hold. Called with
 * core->lock held from a context that keeps the module alive (an open
 * file, the sysfs attribute, the containment work that removal cancels).
 */
static void iris_core_unpin(struct iris_core *core)
{
	if (core->fw_pinned && !core->fw_held) {
		core->fw_pinned = false;
		module_put(THIS_MODULE);
	}
}

/* called with core->lock held and the core not in IRIS_CORE_DEINIT */
static void iris_core_teardown(struct iris_core *core, bool powered)
{
	int ret;

	ret = iris_fw_unload(core);
	if (ret) {
		/*
		 * ROG5: the firmware may still run and access the queues and
		 * buffers: keep clocks, votes and memory instead of pulling them
		 * from under it, and never reuse this core.
		 */
		dev_err(core->dev,
			"firmware shutdown (PAS) failed: %d; keeping the video core powered and its memory mapped\n",
			ret);
		core->fatal = true;
		iris_core_mark_held(core);
		core->state = IRIS_CORE_ERROR;
		return;
	}

	if (powered)
		iris_vpu_power_off(core);
	/* ROG5: power off kept the hardware (iris_core_hold_locked()) */
	if (core->fw_held) {
		core->state = IRIS_CORE_ERROR;
		return;
	}

	iris_hfi_queues_deinit(core);
	core->state = IRIS_CORE_DEINIT;
	iris_core_unpin(core);
}

/*
 * Unload the firmware and power the core off. The interrupt is quiesced
 * first and outside core->lock: the threaded handler takes that lock, and
 * iris_vpu_power_off() waits for it in disable_irq(), so a pending handler
 * would deadlock a teardown that only disabled it under the lock. The extra
 * disable is undone afterwards, which leaves the depth power off/on expect
 * (also after a watchdog interrupt, which keeps the line disabled). With
 * @attempt, only that core init attempt is torn down: sys error recovery may
 * have started a newer one meanwhile.
 */
static void __iris_core_deinit(struct iris_core *core, bool any, u32 attempt, int err)
{
	int ret;

	ret = pm_runtime_resume_and_get(core->dev);
	disable_irq(core->irq);

	mutex_lock(&core->lock);
	if (core->state != IRIS_CORE_DEINIT && !core->fw_held &&
	    (any || core->init_attempt == attempt)) {
		if (!any) {
			dev_err(core->dev, "firmware did not complete system init (%d), powering the core off\n",
				err);
			iris_core_dump_diag_locked(core, "core init", true);
		}
		iris_core_teardown(core, core->powered);
	}
	mutex_unlock(&core->lock);

	enable_irq(core->irq);
	if (!ret)
		pm_runtime_put_sync(core->dev);
}

/*
 * ROG5: the firmware reported a fatal system error or its watchdog fired.
 * Called from the interrupt thread (no core lock held). Upstream reloaded
 * the firmware right away; the instances kept their old session ids, and the
 * reloaded firmware answered every later command with "invalid session id"
 * (0x1004) until it failed again (ROG Phone 5 trial, k114). Latch the error
 * for the rest of this binding instead and contain it from a work item.
 */
void iris_core_fatal(struct iris_core *core, const char *reason)
{
	mutex_lock(&core->lock);
	if (!core->fatal)
		dev_err(core->dev,
			"fatal firmware error (%s): no reload; video stays unavailable until qcom_iris is reloaded\n",
			reason);
	core->fatal = true;
	if (core->state == IRIS_CORE_INIT)
		core->state = IRIS_CORE_ERROR;
	/* under the lock, so iris_remove() can stop new work reliably */
	if (!core->removing)
		schedule_delayed_work(&core->sys_error_handler, 0);
	mutex_unlock(&core->lock);
}

/*
 * ROG5: the core keeps resources the firmware may still use (fw_held). Pin
 * the module so that rmmod cannot run the managed cleanup (supplier links,
 * power domains, interconnect votes) under it; sysfs unbind is disabled for
 * this driver. Only a reboot clears a held core.
 */
void iris_core_mark_held(struct iris_core *core)
{
	if (!core->fw_held && try_module_get(THIS_MODULE))
		dev_err(core->dev, "video core held: qcom_iris stays loaded until reboot\n");
	core->fw_held = true;
}

/*
 * ROG5: the hardware could not be released safely (MVS0 stuck under hardware
 * control, or the firmware not confirmed suspended): keep every resource,
 * latch the core and fail its instances. Called with core->lock held. The
 * runtime PM callbacks refuse to suspend while core->fw_held, so the device
 * and its MX/MMCX suppliers stay active (system sleep is refused too).
 */
void iris_core_hold_locked(struct iris_core *core, const char *reason)
{
	dev_err(core->dev,
		"%s: keeping the video core powered; video unavailable until reboot\n",
		reason);
	core->fatal = true;
	iris_core_mark_held(core);
	if (core->state == IRIS_CORE_INIT)
		core->state = IRIS_CORE_ERROR;
	if (!core->removing)
		schedule_delayed_work(&core->sys_error_handler, 0);
}

static void iris_core_fail_instance(struct iris_inst *inst)
{
	mutex_lock(&inst->lock);
	iris_inst_change_state(inst, IRIS_INST_ERROR);
	/* wake poll() and every buffer wait; the context is gone once closing */
	if (!inst->closing)
		iris_vb2_queue_error(inst);
	complete_all(&inst->completion);
	complete_all(&inst->flush_completion);
	mutex_unlock(&inst->lock);
}

/*
 * ROG5: work item after a fatal error. First every instance is failed and
 * woken (each under its own lock, never under core->lock, which the command
 * paths take inside inst->lock). Then the interrupt is quiesced outside
 * core->lock and the firmware shut down; only if TrustZone accepted the
 * shutdown is the core powered off and the shared memory freed.
 */
void iris_core_contain_fatal(struct iris_core *core)
{
	struct iris_inst *inst;
	bool powered;
	int ret;

	mutex_lock(&core->lock);
	core->fatal = true;
	if (core->state == IRIS_CORE_INIT)
		core->state = IRIS_CORE_ERROR;
	mutex_unlock(&core->lock);

	for (;;) {
		struct iris_inst *found = NULL;

		mutex_lock(&core->lock);
		list_for_each_entry(inst, &core->instances, list) {
			if (!inst->fatal_notified) {
				inst->fatal_notified = true;
				kref_get(&inst->ref);
				found = inst;
				break;
			}
		}
		mutex_unlock(&core->lock);
		if (!found)
			break;
		iris_core_fail_instance(found);
		iris_put_instance(found);
	}

	ret = pm_runtime_resume_and_get(core->dev);
	disable_irq(core->irq);

	mutex_lock(&core->lock);
	complete_all(&core->core_init_done);
	if (core->state != IRIS_CORE_DEINIT && !core->fw_held) {
		powered = core->powered;
		iris_core_dump_diag_locked(core, "fatal", false);
		iris_core_teardown(core, powered);
		if (core->state == IRIS_CORE_DEINIT)
			dev_err(core->dev, "video core shut down after the fatal error\n");
	}
	mutex_unlock(&core->lock);

	enable_irq(core->irq);
	if (ret >= 0)
		pm_runtime_put_sync(core->dev);
}

void iris_core_deinit(struct iris_core *core)
{
	__iris_core_deinit(core, true, 0, 0);
}

/*
 * ROG5: shut an idle core down (firmware_unload attribute), so that the
 * module pin of iris_fw_load() is dropped and qcom_iris can be removed.
 * Refused while any instance exists or an open is in progress; a later
 * open loads the firmware again.
 */
int iris_core_unload_idle(struct iris_core *core)
{
	int ret, pm;

	pm = pm_runtime_resume_and_get(core->dev);
	disable_irq(core->irq);

	mutex_lock(&core->lock);
	if (!list_empty(&core->instances) || atomic_read(&core->openers)) {
		ret = -EBUSY;
	} else if (core->fw_held || core->fatal) {
		ret = -EIO;
	} else {
		ret = 0;
		if (core->state != IRIS_CORE_DEINIT) {
			iris_mark(core, "firmware unload");
			iris_core_teardown(core, core->powered);
			if (core->state != IRIS_CORE_DEINIT || core->fw_held)
				ret = -EIO;
		}
	}
	mutex_unlock(&core->lock);

	enable_irq(core->irq);
	if (pm >= 0)
		pm_runtime_put_sync(core->dev);

	return ret;
}

/*
 * The firmware was loaded and the core powered, but it did not complete the
 * system init of this attempt (no answer, or an error answer): tear the core
 * down like every earlier failure in iris_core_init() does, instead of
 * leaving the core, its clocks, OPP and bandwidth votes on in
 * IRIS_CORE_ERROR. The result is taken under core->lock and only counts for
 * this attempt.
 */
static int iris_wait_for_system_response(struct iris_core *core, u32 attempt)
{
	bool answered;
	int ret = 0;

	answered = core->state != IRIS_CORE_ERROR &&
		   wait_for_completion_timeout(&core->core_init_done,
					       msecs_to_jiffies(HW_RESPONSE_TIMEOUT_VALUE));

	mutex_lock(&core->lock);
	if (core->init_attempt != attempt)
		ret = -EIO;	/* superseded by sys error recovery */
	else if (!answered)
		ret = core->state == IRIS_CORE_ERROR ? -EIO : -ETIMEDOUT;
	else if (core->state != IRIS_CORE_INIT)
		ret = -EIO;
	mutex_unlock(&core->lock);

	if (ret)
		__iris_core_deinit(core, false, attempt, ret);

	return ret;
}

int iris_core_init(struct iris_core *core)
{
	bool unload = false;
	u32 attempt;
	int ret;

	mutex_lock(&core->lock);
	if (core->fatal) {
		/* ROG5: latched until the driver is rebound */
		ret = -EIO;
		goto exit;
	}
	if (core->state == IRIS_CORE_INIT) {
		ret = 0;
		goto exit;
	} else if (core->state == IRIS_CORE_ERROR) {
		/*
		 * Leave the state alone: the failed core still holds its
		 * firmware and power, and its waiter or the sys error
		 * recovery tears it down.
		 */
		ret = -EINVAL;
		goto exit;
	}

	core->state = IRIS_CORE_INIT;
	attempt = ++core->init_attempt;
	/* drop a completion left over from an earlier attempt */
	reinit_completion(&core->core_init_done);

	ret = iris_hfi_queues_init(core);
	if (ret)
		goto error;

	/* ROG5: before power on enables the IRQ (the thread uses the ops) */
	core->iris_firmware_data->init_hfi_ops(core);

	iris_mark(core, "core init %u: power on", attempt);
	ret = iris_vpu_power_on(core);
	if (ret)
		goto error_queue_deinit;

	iris_mark(core, "core init %u: firmware load", attempt);
	ret = iris_fw_load(core);
	if (ret)
		goto error_power_off;

	iris_mark(core, "core init %u: firmware boot", attempt);
	ret = iris_vpu_boot_firmware(core);
	if (ret)
		goto error_unload_fw;
	iris_mark(core, "core init %u: firmware booted", attempt);

	ret = iris_vpu_switch_to_hwmode(core);
	if (ret)
		goto error_unload_fw;

	ret = iris_hfi_core_init(core);
	if (ret)
		goto error_unload_fw;

	mutex_unlock(&core->lock);

	return iris_wait_for_system_response(core, attempt);

error_unload_fw:
	unload = true;
error_power_off:
	/*
	 * The IRQ is live since power on and its threaded handler takes
	 * core->lock, while iris_vpu_power_off() waits for it in
	 * disable_irq(): quiesce it with the lock dropped. Other openers see
	 * IRIS_CORE_ERROR meanwhile; if sys error recovery tore the core down
	 * or started a new attempt in that window, it owns the core now.
	 */
	core->state = IRIS_CORE_ERROR;
	mutex_unlock(&core->lock);
	disable_irq(core->irq);
	mutex_lock(&core->lock);
	if (core->init_attempt != attempt || core->state != IRIS_CORE_ERROR ||
	    core->fw_held) {
		enable_irq(core->irq);
		goto exit;
	}
	/* ROG5: same policy as iris_core_teardown(): keep all if PAS shutdown fails */
	if (unload && iris_fw_unload(core)) {
		dev_err(core->dev,
			"firmware shutdown (PAS) failed after a failed boot; keeping the video core powered and its memory mapped\n");
		core->fatal = true;
		iris_core_mark_held(core);
		enable_irq(core->irq);
		goto exit;
	}
	iris_vpu_power_off(core);
	enable_irq(core->irq);
	if (core->fw_held) {
		core->state = IRIS_CORE_ERROR;
		goto exit;
	}
	iris_core_unpin(core);
error_queue_deinit:
	iris_hfi_queues_deinit(core);
error:
	core->state = IRIS_CORE_DEINIT;
exit:
	mutex_unlock(&core->lock);

	return ret;
}
