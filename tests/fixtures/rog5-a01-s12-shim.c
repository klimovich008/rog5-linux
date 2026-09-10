// SPDX-License-Identifier: GPL-2.0-only
/* QEMU-only link fixture. Never package this in a phone target or recovery.
 * The real provider is checked separately. This cannot report a valid hold.
 */
#include <linux/atomic.h>
#include <linux/errno.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/notifier.h>
#include <linux/of.h>

static atomic_t calls = ATOMIC_INIT(0);
static atomic_t coming = ATOMIC_INIT(0);
static atomic_t live = ATOMIC_INIT(0);

int rog5_s12_validate_hold(void);
int rog5_s12_validate_hold(void)
{
	atomic_inc(&calls);
	return -EPERM;
}
EXPORT_SYMBOL_GPL(rog5_s12_validate_hold);

static int get_count(char *buffer, const struct kernel_param *parameter)
{
	return scnprintf(buffer, 32, "%d", atomic_read(parameter->arg));
}

static const struct kernel_param_ops count_ops = { .get = get_count };
module_param_cb(validator_calls, &count_ops, &calls, 0444);
module_param_cb(btf_coming, &count_ops, &coming, 0444);
module_param_cb(consumer_live, &count_ops, &live, 0444);

static int observe_consumer(struct notifier_block *block,
			    unsigned long action, void *data)
{
	struct module *module = data;

	if (strcmp(module->name, "rog5_wifi_activate"))
		return NOTIFY_DONE;
	if (action == MODULE_STATE_COMING) {
		/* Runs after the accepted kernel's priority-zero BTF notifier. */
#ifdef CONFIG_DEBUG_INFO_BTF_MODULES
		if (!module->btf_data || !module->btf_data_size ||
		    !module->btf_base_data || !module->btf_base_data_size)
			return notifier_from_errno(-EINVAL);
		atomic_inc(&coming);
#else
		return notifier_from_errno(-EOPNOTSUPP);
#endif
	} else if (action == MODULE_STATE_LIVE) {
		atomic_inc(&live);
	}
	return NOTIFY_OK;
}

static struct notifier_block observer = {
	.notifier_call = observe_consumer,
	.priority = -128,
};

static int __init fixture_init(void)
{
	if (!of_machine_is_compatible("linux,dummy-virt") ||
	    of_machine_is_compatible("asus,rog-phone5") ||
	    !IS_ENABLED(CONFIG_DEBUG_INFO_BTF_MODULES) ||
	    IS_ENABLED(CONFIG_MODULE_ALLOW_BTF_MISMATCH))
		return -ENODEV;
	return register_module_notifier(&observer);
}

static void __exit fixture_exit(void)
{
	unregister_module_notifier(&observer);
}

module_init(fixture_init);
module_exit(fixture_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("QEMU A01 link/BTF observer; never a real S12 provider");
