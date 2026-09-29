// SPDX-License-Identifier: GPL-2.0-only
/*
 * ROG5 debug: send one AOP QMP text message per write to
 * debugfs rog5-aop-qmp/send, through the qcom_aoss driver's qmp_send().
 * Used to enable the AOP sleep-violator log ({class: lpm_mon, ...}) and for
 * the CXSD experiments. No RPMh or MMIO writes of its own.
 */
#include <linux/debugfs.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/soc/qcom/qcom_aoss.h>
#include <linux/io.h>
#include <linux/delay.h>
#include <linux/seq_file.h>
#include <linux/uaccess.h>

/* AOP message RAM: DDR stats base = 0xc300000 + readl(0xc3f001c) (lahaina-pm.dtsi) */
#define AOP_MSGRAM	0x0c300000
#define AOP_DDR_OFFSET	0x0c3f001c
static const char * const drv_names[18] = {
	"TZ", "HYP", "HLOS", "L3", "SECPROC", "AUDIO", "SENSOR", "AOP", "DEBUG",
	"GPU", "DISPLAY", "COMPUTE", "MDM_SW", "MDM_HW", "WLAN_RF", "WLAN_BB",
	"DDR_AUX", "ARC_CPRF",
};

static struct qmp *qmp;
static struct device *aoss_dev;
static struct dentry *dir;

static ssize_t send_write(struct file *f, const char __user *ubuf, size_t len, loff_t *pos)
{
	char buf[96];
	int ret;

	if (len >= sizeof(buf) || len == 0)
		return -EINVAL;
	if (copy_from_user(buf, ubuf, len))
		return -EFAULT;
	buf[len] = 0;
	strim(buf);
	ret = qmp_send(qmp, "%s", buf);
	pr_info("rog5-aop-qmp: sent \"%s\": %d\n", buf, ret);
	return ret ? ret : len;
}

/* Per-DRV DDR votes as the AOP reports them ({class: ddr, res: drvs_ddr_votes}). */
static int ddr_votes_show(struct seq_file *m, void *unused)
{
	void __iomem *off, *base;
	u32 offset, count, v;
	int ret, i;

	off = ioremap(AOP_DDR_OFFSET, 4);
	if (!off)
		return -ENOMEM;
	offset = readl(off);
	iounmap(off);
	if (!offset || offset > 0xffc00)
		return -ENODEV;
	base = ioremap(AOP_MSGRAM + offset, 0x400);
	if (!base)
		return -ENOMEM;
	count = readl(base + 4);
	if (count > 20) {
		iounmap(base);
		return -EINVAL;
	}
	ret = qmp_send(qmp, "{class: ddr, res: drvs_ddr_votes}");
	seq_printf(m, "send rc=%d entry_count=%u\n", ret, count);
	for (i = 0; i < 18; i++) {
		v = readl(base + 8 + count * 16 + i * 4);
		if (v == 0xdeaddead)
			seq_printf(m, "%-9s absent\n", drv_names[i]);
		else if (v == 0xffffdead)
			seq_printf(m, "%-9s invalid\n", drv_names[i]);
		else
			seq_printf(m, "%-9s ab=%u ib=%u raw=%#010x\n", drv_names[i],
				   (v >> 14) & 0x3fff, v & 0x3fff, v);
	}
	iounmap(base);
	return 0;
}
DEFINE_SHOW_ATTRIBUTE(ddr_votes);

/* Raw dump of the DDR stats region before and after the drvs_ddr_votes QMP message. */
static int ddr_raw_show(struct seq_file *m, void *unused)
{
	void __iomem *off, *base;
	u32 offset, before[128];
	int ret, i;

	off = ioremap(AOP_DDR_OFFSET, 4);
	if (!off)
		return -ENOMEM;
	offset = readl(off);
	iounmap(off);
	if (!offset || offset > 0xffc00)
		return -ENODEV;
	base = ioremap(AOP_MSGRAM + offset, 0x200);
	if (!base)
		return -ENOMEM;
	for (i = 0; i < 128; i++)
		before[i] = readl(base + i * 4);
	ret = qmp_send(qmp, "{class: ddr, res: drvs_ddr_votes}");
	msleep(50);
	seq_printf(m, "offset=%#x send rc=%d\n", offset, ret);
	for (i = 0; i < 128; i++) {
		u32 v = readl(base + i * 4);
		seq_printf(m, "%03x: %08x%s%08x%s", i * 4, before[i], v != before[i] ? " -> " : "    ", v, (i % 4 == 3) ? "\n" : "  ");
	}
	iounmap(base);
	return 0;
}
DEFINE_SHOW_ATTRIBUTE(ddr_raw);

static const struct file_operations send_fops = {
	.owner = THIS_MODULE,
	.write = send_write,
	.open = simple_open,
};

static int __init aop_qmp_init(void)
{
	struct device_node *np = of_find_node_by_path("/soc@0/power-management@c300000");
	struct platform_device *pdev;

	if (!np)
		return -ENODEV;
	pdev = of_find_device_by_node(np);
	of_node_put(np);
	if (!pdev)
		return -ENODEV;
	qmp = platform_get_drvdata(pdev);
	if (!qmp) {
		put_device(&pdev->dev);
		return -EPROBE_DEFER;
	}
	aoss_dev = &pdev->dev;
	dir = debugfs_create_dir("rog5-aop-qmp", NULL);
	debugfs_create_file("send", 0200, dir, NULL, &send_fops);
	debugfs_create_file("ddr_votes", 0400, dir, NULL, &ddr_votes_fops);
	debugfs_create_file("ddr_raw", 0400, dir, NULL, &ddr_raw_fops);
	return 0;
}

static void __exit aop_qmp_exit(void)
{
	debugfs_remove_recursive(dir);
	put_device(aoss_dev);
}

module_init(aop_qmp_init);
module_exit(aop_qmp_exit);
MODULE_DESCRIPTION("ROG5 AOP QMP message sender (debug)");
MODULE_LICENSE("GPL");
