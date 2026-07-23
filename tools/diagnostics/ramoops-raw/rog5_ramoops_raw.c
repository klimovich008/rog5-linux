// SPDX-License-Identifier: GPL-2.0-only
#include <linux/io.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/proc_fs.h>
#include <linux/uaccess.h>

#ifndef ROG5_RAMOOPS_PHYS
#error "ROG5_RAMOOPS_PHYS must be provided by the private build"
#endif

#define ROG5_RAMOOPS_SIZE (4 * 1024 * 1024)

static void __iomem *ramoops;
static struct proc_dir_entry *ramoops_proc;
static char bounce[PAGE_SIZE];
static char *expected_compatible;
module_param(expected_compatible, charp, 0000);
MODULE_PARM_DESC(expected_compatible,
		 "Required exact root compatible string for the target phone");

static ssize_t rog5_ramoops_read(struct file *file, char __user *buffer,
				 size_t count, loff_t *offset)
{
	size_t available;

	if (*offset < 0 || *offset >= ROG5_RAMOOPS_SIZE)
		return 0;

	available = ROG5_RAMOOPS_SIZE - *offset;
	count = min(count, min(available, sizeof(bounce)));
	memcpy_fromio(bounce, (u8 __iomem *)ramoops + *offset, count);
	if (copy_to_user(buffer, bounce, count))
		return -EFAULT;

	*offset += count;
	return count;
}

static const struct file_operations rog5_ramoops_fops = {
	.owner = THIS_MODULE,
	.read = rog5_ramoops_read,
};

static int __init rog5_ramoops_init(void)
{
	if (!expected_compatible || !*expected_compatible)
		return -EPERM;
	if (!of_machine_is_compatible(expected_compatible))
		return -ENODEV;
	if (!IS_ALIGNED((phys_addr_t)ROG5_RAMOOPS_PHYS, PAGE_SIZE))
		return -EINVAL;

	ramoops = ioremap(ROG5_RAMOOPS_PHYS, ROG5_RAMOOPS_SIZE);
	if (!ramoops)
		return -ENOMEM;

	ramoops_proc = proc_create("rog5_ramoops_raw", 0400, NULL,
				   &rog5_ramoops_fops);
	if (!ramoops_proc) {
		iounmap(ramoops);
		return -ENOMEM;
	}

	return 0;
}

static void __exit rog5_ramoops_exit(void)
{
	proc_remove(ramoops_proc);
	iounmap(ramoops);
}

module_init(rog5_ramoops_init);
module_exit(rog5_ramoops_exit);

MODULE_DESCRIPTION("Read-only ASUS ROG Phone 5 ramoops reservation");
MODULE_LICENSE("GPL");
