// SPDX-License-Identifier: GPL-2.0-only
#include <linux/init.h>
#include <linux/module.h>
#include <linux/nvmem-consumer.h>
#include <linux/of.h>
#include <linux/slab.h>

static char *expected_compatible;
module_param(expected_compatible, charp, 0000);
MODULE_PARM_DESC(expected_compatible,
		 "Required exact root compatible string for the target phone");

static int __init rog5_bootloader_reason_init(void)
{
	struct device_node *node;
	struct nvmem_cell *cell;
	const char *cell_name = "restart_reason";
	unsigned int reason = 0x02;
	size_t length;
	void *cell_data;
	int ret;

	if (!expected_compatible || !*expected_compatible)
		return -EPERM;
	if (!of_machine_is_compatible(expected_compatible))
		return -ENODEV;

	node = of_find_compatible_node(NULL, NULL, "qcom,reboot-reason");
	if (!node) {
		node = of_find_compatible_node(NULL, NULL, "nvmem-reboot-mode");
		cell_name = "reboot-mode";
	}
	if (!node)
		return -ENODEV;

	cell = of_nvmem_cell_get(node, cell_name);
	of_node_put(node);
	if (IS_ERR(cell))
		return PTR_ERR(cell);

	cell_data = nvmem_cell_read(cell, &length);
	if (IS_ERR(cell_data)) {
		ret = PTR_ERR(cell_data);
		goto out;
	}
	kfree(cell_data);
	if (!length || length > sizeof(reason)) {
		ret = -EINVAL;
		goto out;
	}

	ret = nvmem_cell_write(cell, &reason, length);
	if (!ret)
		pr_info("rog5: next reset armed for bootloader\n");

out:
	nvmem_cell_put(cell);
	return ret;
}

static void __exit rog5_bootloader_reason_exit(void)
{
}

module_init(rog5_bootloader_reason_init);
module_exit(rog5_bootloader_reason_exit);

MODULE_DESCRIPTION("Arm the ROG Phone 5 next-reset bootloader reason");
MODULE_LICENSE("GPL");
