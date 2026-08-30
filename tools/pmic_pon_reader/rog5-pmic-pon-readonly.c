// SPDX-License-Identifier: GPL-2.0-only
/* Snapshot the ASUS PON FIFO only; no address parameter and no write API. */
#include <linux/debugfs.h>
#include <linux/device.h>
#include <linux/err.h>
#include <linux/module.h>
#include <linux/nvmem-consumer.h>
#include <linux/of.h>
#include <linux/string.h>

#define PON_NODE "/soc@0/spmi@c440000/pmic@0/nvram@7400"
#define PON_START 0x4b
#define PON_END 0xbf
#define PON_BYTES (PON_END - PON_START + 1)

struct pon_lookup {
	unsigned int *count;
	struct device_node *node;
	bool select;
};

static u8 snapshot[8 + PON_BYTES] = { 'R', 'P', 'O', 'N', 1, 0, 0, PON_BYTES };
static struct debugfs_blob_wrapper blob = {
	.data = snapshot,
	.size = sizeof(snapshot),
};
static struct dentry *directory;

static int pon_match(struct device *dev, const void *data)
{
	const struct pon_lookup *lookup = data;
	struct device_node *np = dev_of_node(dev);
	u32 base;

	if (!np || np != lookup->node ||
	    !of_device_is_compatible(np, "qcom,spmi-sdam") ||
	    of_property_read_u32(np, "reg", &base) || base != 0x7400)
		return 0;
	(*lookup->count)++;
	return lookup->select;
}

static int __init pon_init(void)
{
	struct nvmem_device *nvmem;
	struct dentry *entry;
	unsigned int count = 0;
	struct pon_lookup lookup = { .count = &count };
	int ret;

	if (!of_machine_is_compatible("asus,rog-phone5"))
		return -ENODEV;
	/* full_name contains the local FDT node name, not its absolute path. */
	lookup.node = of_find_node_by_path(PON_NODE);
	if (!lookup.node)
		return -ENODEV;
	nvmem = nvmem_device_find(&lookup, pon_match);
	if (!IS_ERR_OR_NULL(nvmem))
		nvmem_device_put(nvmem);
	if (count != 1) {
		of_node_put(lookup.node);
		return -ENODEV;
	}
	lookup.select = true;
	count = 0;
	nvmem = nvmem_device_find(&lookup, pon_match);
	of_node_put(lookup.node);
	if (IS_ERR_OR_NULL(nvmem))
		return -ENODEV;

	ret = nvmem_device_read(nvmem, 0x46, 1, &snapshot[5]);
	if (ret != 1)
		goto out;
	ret = nvmem_device_read(nvmem, PON_START, PON_BYTES, &snapshot[8]);
	if (ret != PON_BYTES)
		goto out;
	ret = nvmem_device_read(nvmem, 0x46, 1, &snapshot[6]);
	if (ret != 1)
		goto out;
	if (snapshot[5] != snapshot[6] || snapshot[5] < PON_START ||
	    snapshot[5] > PON_END) {
		ret = -EAGAIN;
		goto out;
	}
	nvmem_device_put(nvmem);
	directory = debugfs_create_dir("rog5-pmic-pon-readonly", NULL);
	if (IS_ERR_OR_NULL(directory))
		return -ENODEV;
	entry = debugfs_create_blob("snapshot", 0400, directory, &blob);
	if (IS_ERR_OR_NULL(entry)) {
		debugfs_remove_recursive(directory);
		return -ENODEV;
	}
	pr_info("ROG5_PON_READONLY snapshot ready; fixed bank 0x7400\n");
	return 0;
out:
	nvmem_device_put(nvmem);
	return ret < 0 ? ret : -EIO;
}

static void __exit pon_exit(void)
{
	debugfs_remove_recursive(directory);
}
module_init(pon_init);
module_exit(pon_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("ROG5 fixed-bank read-only PMIC PON history snapshot");
