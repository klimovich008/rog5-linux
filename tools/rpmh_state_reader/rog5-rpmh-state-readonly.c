// SPDX-License-Identifier: GPL-2.0-only
/* Fixed-resource APPS vote snapshot; no regulator initialization or writes. */
#include <linux/debugfs.h>
#include <linux/delay.h>
#include <linux/err.h>
#include <linux/fs.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/string.h>
#include <generated/utsrelease.h>
#include <soc/qcom/cmd-db.h>
#include <soc/qcom/rpmh.h>

#define PMIC_NODE "/soc@0/rsc@18200000/regulators-0"
#define RSC_NODE "/soc@0/rsc@18200000"

static char snapshot[1024];
static size_t snapshot_length;
static struct dentry *directory;

static ssize_t snapshot_read(struct file *file, char __user *buffer,
			     size_t size, loff_t *offset)
{
	return simple_read_from_buffer(buffer, size, offset, snapshot,
				      snapshot_length);
}

static const struct file_operations snapshot_ops = {
	.owner = THIS_MODULE,
	.open = simple_open,
	.read = snapshot_read,
	.llseek = default_llseek,
};

static int read_one(const struct device *dev, struct tcs_cmd *cmd)
{
	unsigned int attempt;
	int ret;

	for (attempt = 0; attempt < 5; attempt++) {
		ret = rpmh_read(dev, cmd);
		/* EAGAIN proves nothing was queued. Never retry a timed-out read. */
		if (ret != -EAGAIN)
			return ret;
		if (attempt < 4)
			msleep(20);
	}
	return ret;
}

static int __init state_reader_init(void)
{
	static const struct {
		const char *name;
		u32 address;
	} fields[] = {
		/* S12 has no Linux consumer in the required baseline DT. Query it
		 * before the optional, actively used L6 sanity reference.
		 */
		{ "s12-voltage", 0x40100 },
		{ "s12-enable", 0x40104 },
		{ "s12-mode", 0x40108 },
		{ "reference-l6-voltage", 0x41a00 },
		{ "reference-l6-enable", 0x41a04 },
		{ "reference-l6-mode", 0x41a08 },
	};
	struct device_node *pmic, *rsc, *s12, *pcie;
	struct platform_device *pdev;
	struct dentry *entry;
	const char *id;
	u32 drv_id;
	unsigned int i;
	int ret = -ENODEV;

	if (!of_machine_is_compatible("asus,rog-phone5"))
		return -ENODEV;
	pmic = of_find_node_by_path(PMIC_NODE);
	rsc = of_find_node_by_path(RSC_NODE);
	s12 = of_find_node_by_path(PMIC_NODE "/smps12");
	pcie = of_find_node_by_path("/soc@0/pcie@1c00000");
	/* Use the working baseline DT, not the opt-in voltage-voting Wi-Fi DT. */
	if (!pmic || !rsc || s12 || !pcie || of_device_is_available(pcie) ||
	    !of_device_is_compatible(pmic, "qcom,pm8350-rpmh-regulators") ||
	    !of_device_is_compatible(rsc, "qcom,rpmh-rsc") ||
	    of_property_read_string(pmic, "qcom,pmic-id", &id) ||
	    strcmp(id, "b") ||
	    of_property_read_u32(rsc, "qcom,drv-id", &drv_id) || drv_id != 2 ||
	    cmd_db_read_addr("smpb12") != 0x40100 ||
	    cmd_db_read_addr("ldob6") != 0x41a00)
		goto put_nodes;
	pdev = of_find_device_by_node(pmic);
	if (!pdev)
		goto put_nodes;
	if (!pdev->dev.driver || !pdev->dev.parent ||
	    dev_of_node(pdev->dev.parent) != rsc ||
	    !dev_get_drvdata(pdev->dev.parent))
		goto put_device;

	snapshot_length = scnprintf(snapshot, sizeof(snapshot),
		"format=rog5-rpmh-readonly-v1\nkernel=%s\n"
		"scope=APPS-votes-not-physical-measurements\n", UTS_RELEASE);
	for (i = 0; i < ARRAY_SIZE(fields); i++) {
		struct tcs_cmd cmd = { .addr = fields[i].address };

		pr_info("ROG5_RPMH_READ enter field=%s address=%#x\n",
			fields[i].name, cmd.addr);
		ret = read_one(&pdev->dev, &cmd);
		if (ret)
			snapshot_length += scnprintf(snapshot + snapshot_length,
				sizeof(snapshot) - snapshot_length,
				"%s result=%d raw=unavailable\n", fields[i].name, ret);
		else
			snapshot_length += scnprintf(snapshot + snapshot_length,
				sizeof(snapshot) - snapshot_length,
				"%s result=0 raw=%#x\n", fields[i].name, cmd.data);
		pr_info("ROG5_RPMH_READ return field=%s result=%d raw=%#x\n",
			fields[i].name, ret, cmd.data);
		/* Do not queue further work behind a failed/timed-out read. */
		if (ret)
			break;
	}
	put_device(&pdev->dev);
	directory = debugfs_create_dir("rog5-rpmh-readonly", NULL);
	if (IS_ERR_OR_NULL(directory)) {
		ret = -ENODEV;
		goto put_nodes;
	}
	entry = debugfs_create_file("snapshot", 0400, directory, NULL,
				   &snapshot_ops);
	if (IS_ERR_OR_NULL(entry)) {
		debugfs_remove_recursive(directory);
		ret = -ENODEV;
		goto put_nodes;
	}
	ret = 0; /* The snapshot reports errors; never reinterpret them as OFF. */
	goto put_nodes;
put_device:
	put_device(&pdev->dev);
put_nodes:
	of_node_put(pcie);
	of_node_put(s12);
	of_node_put(rsc);
	of_node_put(pmic);
	return ret;
}

static void __exit state_reader_exit(void)
{
	debugfs_remove_recursive(directory);
}
module_init(state_reader_init);
module_exit(state_reader_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("ROG5 fixed-resource read-only RPMh APPS vote snapshot");
