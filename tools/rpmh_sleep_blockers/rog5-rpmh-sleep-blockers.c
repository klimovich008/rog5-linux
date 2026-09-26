// SPDX-License-Identifier: GPL-2.0-only
/*
 * ROG5: read-only view of what keeps the SoC out of RPMh sleep.
 *
 * debugfs rog5-sleep-blockers/
 *   votes  APPS-DRV votes read back with rpmh_read() (patch 0035) for the
 *          resources upstream never writes (QUP BCMs, clock buffers, the
 *          ddr/qphy ARCs) plus a few it does, for comparison. A vote the
 *          ASUS 5.4 wrapper kernel left before kexec stays in the DRV vote
 *          register, and is what the DRV holds during sleep too, because the
 *          sleep TCS only carries resources this kernel caches.
 *   vx     AOP "system PM violators" log at 0xc320000 (stock sys_pm_vx.c,
 *          qcom,sys-pm-lahaina): per-DRV votes that blocked CXPC/AOSS/DDR.
 *   vx_raw the same region as hex words.
 *
 * Nothing is written: no RPMh write, no QMP message, no MMIO store. Reads stop
 * at the first failed rpmh_read (never queue behind a timed-out read).
 */
#include <linux/debugfs.h>
#include <linux/delay.h>
#include <linux/err.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/seq_file.h>
#include <linux/slab.h>
#include <soc/qcom/cmd-db.h>
#include <soc/qcom/rpmh.h>

#define RSC_CHILD	"/soc@0/rsc@18200000/power-controller"
#define VX_BASE		0x0c320000
#define VX_SIZE		0x400
#define VRM_EN		0x4	/* clk-rpmh CLK_RPMH_VRM_EN_OFFSET */

static const struct {
	const char *res;
	u32 offset;
	const char *note;
} fields[] = {
	/* ARC levels (index into the cmd-db level table, 0 = off). */
	{ "xo.lvl", 0, "arc: 0 lets XO shut down (aosd)" },
	{ "cx.lvl", 0, "arc: managed by rpmhpd" },
	{ "mx.lvl", 0, "arc: managed by rpmhpd" },
	{ "mmcx.lvl", 0, "arc: managed by rpmhpd" },
	{ "ebi.lvl", 0, "arc: managed by rpmhpd" },
	{ "lcx.lvl", 0, "arc: managed by rpmhpd" },
	{ "lmx.lvl", 0, "arc: managed by rpmhpd" },
	{ "mxc.lvl", 0, "arc: managed by rpmhpd" },
	{ "ddr.lvl", 0, "arc: NOT managed upstream" },
	{ "qphy.lvl", 0, "arc: NOT managed upstream" },
	/* PMIC clock buffers: enable bit; they keep XO running. */
	{ "lnbclka1", VRM_EN, "clk: ln_bb_clk1, no DT consumer" },
	{ "lnbclka2", VRM_EN, "clk: ln_bb_clk2, no DT consumer" },
	{ "lnbclka3", VRM_EN, "clk: ln_bb_clk3, no DT consumer" },
	{ "rfclka1", VRM_EN, "clk: rf_clk1 (stock: usb3803 hub)" },
	{ "rfclka2", VRM_EN, "clk: rf_clk2" },
	{ "rfclka3", VRM_EN, "clk: rf_clk3" },
	{ "rfclka4", VRM_EN, "clk: rf_clk4" },
	{ "rfclka5", VRM_EN, "clk: rf_clk5" },
	{ "divclka1", VRM_EN, "clk: div_clk1" },
	/* BCMs last: bit 30 commit, 29 valid, x = 27:14, y = 13:0. */
	{ "QUP0", 0, "bcm: NOT in upstream sm8350 icc" },
	{ "QUP1", 0, "bcm: NOT in upstream sm8350 icc" },
	{ "QUP2", 0, "bcm: NOT in upstream sm8350 icc" },
	{ "IP0", 0, "bcm: NOT in upstream sm8350 icc" },
	{ "MC0", 0, "bcm: DDR, managed by icc" },
	{ "SH0", 0, "bcm: gem noc, managed by icc" },
	{ "ACV", 0, "bcm: DDR ACV, managed by icc" },
	{ "CN0", 0, "bcm: config noc, managed by icc" },
};

/* Stock drv_names_lahaina[] order (sys_pm_vx.c). */
static const char * const vx_drv[] = {
	"TZ", "HYP", "HLOS", "L3", "SECPROC", "AUDIO", "SENSOR", "AOP",
	"DEBUG", "GPU", "DISPLAY", "COMPUTE", "MDM_SW", "MDM_HW", "WLAN_RF",
	"WLAN_BB", "DDR_AUX", "ARC_CPRF",
};

static struct dentry *dir;
static struct device *rsc_child;
static void __iomem *vx;
static DEFINE_MUTEX(read_lock);

static int read_one(struct tcs_cmd *cmd)
{
	int attempt, ret = -EAGAIN;

	for (attempt = 0; attempt < 5 && ret == -EAGAIN; attempt++) {
		ret = rpmh_read(rsc_child, cmd);
		if (ret == -EAGAIN)
			msleep(20);
	}
	return ret;
}

static int votes_show(struct seq_file *s, void *unused)
{
	unsigned int i;
	int ret;

	seq_puts(s, "scope=APPS-DRV-votes-readback\n");
	mutex_lock(&read_lock);
	for (i = 0; i < ARRAY_SIZE(fields); i++) {
		struct tcs_cmd cmd = { 0 };
		u32 addr = cmd_db_read_addr(fields[i].res);

		if (!addr) {
			seq_printf(s, "%-9s absent-from-cmd-db\n", fields[i].res);
			continue;
		}
		cmd.addr = addr + fields[i].offset;
		ret = read_one(&cmd);
		if (ret) {
			seq_printf(s, "%-9s addr=%#07x result=%d (stopping)\n",
				   fields[i].res, cmd.addr, ret);
			break;
		}
		seq_printf(s, "%-9s addr=%#07x raw=%#010x  %s\n",
			   fields[i].res, cmd.addr, cmd.data, fields[i].note);
	}
	mutex_unlock(&read_lock);
	return 0;
}
DEFINE_SHOW_ATTRIBUTE(votes);

static const char *vx_mode(u8 type)
{
	switch (type) {
	case 0xaa: return "AOSS";
	case 0xcc: return "CXPC";
	case 0xdd: return "DDR";
	default: return "?";
	}
}

static int vx_show(struct seq_file *s, void *unused)
{
	u32 off = 0, w, ts_shift, logsize, i, j, k;
	u8 v[ARRAY_SIZE(vx_drv) + 4];

	w = readl_relaxed(vx + off); off += 4;
	if (!w) {
		seq_puts(s, "empty (AOP has not written a violators log)\n");
		return 0;
	}
	logsize = (w >> 8) & 0xff;
	seq_printf(s, "Mode: %s (%#x)  log entries: %u\n", vx_mode(w & 0xff),
		   w & 0xff, logsize);
	w = readl_relaxed(vx + off); off += 4;
	ts_shift = (w >> 16) & 0xff;
	seq_printf(s, "Duration ms: %u  ts shift: %u  flush threshold: %u\n",
		   w & 0xffff, ts_shift, w >> 24);
	seq_puts(s, "timestamp");
	for (j = 0; j < ARRAY_SIZE(vx_drv); j++)
		seq_printf(s, " %s", vx_drv[j]);
	seq_puts(s, "\n");
	for (i = 0; i < logsize; i++) {
		u32 ts, any = 0;

		if (off + 4 > VX_SIZE)
			break;
		ts = readl_relaxed(vx + off); off += 4;
		if (!ts)
			break;
		for (j = 0; j < ARRAY_SIZE(vx_drv);) {
			if (off + 4 > VX_SIZE)
				return 0;
			w = readl_relaxed(vx + off); off += 4;
			for (k = 0; k < 4; k++)
				v[j++] = (w >> (8 * k)) & 0xff;
		}
		seq_printf(s, "%#x", ts << ts_shift);
		for (j = 0; j < ARRAY_SIZE(vx_drv); j++) {
			any |= v[j];
			if (v[j])
				seq_printf(s, " %s=%u", vx_drv[j], v[j]);
		}
		seq_puts(s, any ? "\n" : " (all clear: mode entered/exited)\n");
	}
	return 0;
}
DEFINE_SHOW_ATTRIBUTE(vx);

static int vx_raw_show(struct seq_file *s, void *unused)
{
	u32 off;

	for (off = 0; off < VX_SIZE; off += 4)
		seq_printf(s, "%08x%c", readl_relaxed(vx + off),
			   (off & 0x1c) == 0x1c ? '\n' : ' ');
	return 0;
}
DEFINE_SHOW_ATTRIBUTE(vx_raw);

static int __init blockers_init(void)
{
	struct device_node *np;
	struct platform_device *pdev;

	if (!of_machine_is_compatible("asus,rog-phone5"))
		return -ENODEV;
	np = of_find_node_by_path(RSC_CHILD);
	if (!np)
		return -ENODEV;
	pdev = of_find_device_by_node(np);
	of_node_put(np);
	if (!pdev)
		return -ENODEV;
	if (!pdev->dev.driver || !pdev->dev.parent ||
	    !dev_get_drvdata(pdev->dev.parent)) {
		put_device(&pdev->dev);
		return -EPROBE_DEFER;
	}
	rsc_child = &pdev->dev;

	vx = ioremap(VX_BASE, VX_SIZE);
	if (!vx) {
		put_device(rsc_child);
		return -ENOMEM;
	}

	dir = debugfs_create_dir("rog5-sleep-blockers", NULL);
	debugfs_create_file("votes", 0400, dir, NULL, &votes_fops);
	debugfs_create_file("vx", 0400, dir, NULL, &vx_fops);
	debugfs_create_file("vx_raw", 0400, dir, NULL, &vx_raw_fops);
	return 0;
}

static void __exit blockers_exit(void)
{
	debugfs_remove_recursive(dir);
	iounmap(vx);
	put_device(rsc_child);
}
module_init(blockers_init);
module_exit(blockers_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("ROG5 read-only RPMh sleep blocker snapshot");
