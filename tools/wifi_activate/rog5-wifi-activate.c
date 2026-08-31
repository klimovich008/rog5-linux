// SPDX-License-Identifier: GPL-2.0-only
/* One fixed, RAM-only status changeset after the protected S12 handoff. */
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>

extern int rog5_s12_validate_hold(void);

static const struct {
	const char *path;
	const char *compatible;
} targets[] = {
	{ "/wcn6855-pmu", "qcom,wcn6855-pmu" },
	{ "/soc@0/phy@1c06000", "qcom,sm8350-qmp-gen3x1-pcie-phy" },
	{ "/soc@0/pcie@1c00000", "qcom,pcie-sm8350" },
};
static struct of_changeset activation;
static int result = -EINPROGRESS;
module_param(result, int, 0400);
MODULE_PARM_DESC(result, "Status changeset result, not radio qualification");

static int __init wifi_activate_init(void)
{
	struct device_node *nodes[ARRAY_SIZE(targets)] = {};
	struct device_node *supply, *rail;
	struct platform_device *pdev;
	const char *status;
	unsigned int i;
	int ret = -ENODEV;

	if (!of_machine_is_compatible("asus,rog-phone5"))
		return -ENODEV;
	/* No arbitrary paths, parameters, regulator properties, or removal. */
	for (i = 0; i < ARRAY_SIZE(targets); i++) {
		nodes[i] = of_find_node_by_path(targets[i].path);
		if (!nodes[i] ||
		    !of_device_is_compatible(nodes[i], targets[i].compatible) ||
		    of_property_read_string(nodes[i], "status", &status) ||
		    strcmp(status, "disabled"))
			goto put_nodes;
		pdev = of_find_device_by_node(nodes[i]);
		if (pdev) {
			platform_device_put(pdev);
			ret = -EBUSY;
			goto put_nodes;
		}
	}
	rail = of_find_node_by_path(
		"/soc@0/rsc@18200000/regulators-0/smps12");
	supply = of_parse_phandle(nodes[0], "vddpmu-supply", 0);
	ret = rail && supply == rail ? 0 : -ENODEV;
	of_node_put(supply);
	of_node_put(rail);
	if (ret)
		goto put_nodes;
	ret = rog5_s12_validate_hold();
	if (ret)
		goto put_nodes;

	of_changeset_init(&activation);
	for (i = 0; i < ARRAY_SIZE(targets); i++) {
		ret = of_changeset_update_prop_string(&activation, nodes[i],
						      "status", "okay");
		if (ret) {
			of_changeset_destroy(&activation);
			goto put_nodes;
		}
	}
	/* Applying can notify/probe hardware even when a later notifier fails.
	 * Retain this changeset and module for either outcome; reboot, never retry
	 * or revert a partially executed power sequence. Check result, not insmod.
	 */
	__module_get(THIS_MODULE);
	pr_info("ROG5_WIFI_ACTIVATE enter\n");
	result = of_changeset_apply(&activation);
	pr_info("ROG5_WIFI_ACTIVATE return result=%d\n", result);
	ret = 0;
put_nodes:
	for (i = 0; i < ARRAY_SIZE(nodes); i++)
		of_node_put(nodes[i]);
	return ret;
}

module_init(wifi_activate_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("ROG5 one-shot late Wi-Fi node activation after S12 hold");
