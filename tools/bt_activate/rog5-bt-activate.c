// SPDX-License-Identifier: GPL-2.0
/* One fixed, RAM-only status change: enable QUP wrapper 2 (the Bluetooth
 * UART's parent) only after Wi-Fi is bound.
 *
 * Enabling the wrapper at boot gives it an SMMU context bank ahead of the
 * PCIe Wi-Fi function; the WCN6855 hw1.1 then fails its MHI/BHI firmware
 * load every time (RAM trials t16, t18 and t20 on 2026-09-24, the last with
 * only the wrapper enabled). Once ath11k owns 17cb:1103 the wrapper can
 * probe, and its uart18 child and the qcom,wcn6855-bt device come up with it.
 */
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/pci.h>
#include <linux/platform_device.h>

static const char wrapper_path[] = "/soc@0/geniqup@8c0000";
static struct of_changeset activation;
static int result = -EINPROGRESS;
module_param(result, int, 0400);
MODULE_PARM_DESC(result, "Status changeset result");

static bool wifi_bound(void)
{
	struct pci_dev *wifi = pci_get_device(0x17cb, 0x1103, NULL);
	bool bound = wifi && wifi->dev.driver &&
		     !strcmp(wifi->dev.driver->name, "ath11k_pci");

	pci_dev_put(wifi);
	return bound;
}

static int __init bt_activate_init(void)
{
	struct platform_device *pdev;
	struct device_node *node;
	const char *status;
	int ret = -ENODEV;

	if (!of_machine_is_compatible("asus,rog-phone5"))
		return -ENODEV;
	if (!wifi_bound())
		return -EAGAIN;
	node = of_find_node_by_path(wrapper_path);
	if (!node || !of_device_is_compatible(node, "qcom,geni-se-qup") ||
	    of_property_read_string(node, "status", &status) ||
	    strcmp(status, "disabled"))
		goto put;
	pdev = of_find_device_by_node(node);
	if (pdev) {
		platform_device_put(pdev);
		ret = -EBUSY;
		goto put;
	}
	of_changeset_init(&activation);
	ret = of_changeset_update_prop_string(&activation, node, "status", "okay");
	if (ret) {
		of_changeset_destroy(&activation);
		goto put;
	}
	/* Keep the module and changeset whatever the outcome; never revert. */
	__module_get(THIS_MODULE);
	result = of_changeset_apply(&activation);
	pr_info("ROG5_BT_ACTIVATE wrapper result=%d\n", result);
	ret = 0;
put:
	of_node_put(node);
	return ret;
}

module_init(bt_activate_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("ROG5 one-shot late QUP wrapper 2 (Bluetooth UART) activation after Wi-Fi");
