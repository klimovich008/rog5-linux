// SPDX-License-Identifier: GPL-2.0-only
/*
 * ROG5 debug: hold an ACTIVE_ONLY (AMC+WAKE, sleep 0) DDR bandwidth vote
 * through the rog5-input-boost node's "llcc-ddr" path until unload.
 * If the APPS RSC really sends its sleep set in s2idle, DDR drops during
 * suspend; if it does not, DDR stays at the held frequency.
 */
#include <linux/interconnect.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <dt-bindings/interconnect/qcom,icc.h>

static unsigned int peak_kbps = 10000000;
module_param(peak_kbps, uint, 0444);
static char *path_name = "llcc-ddr";
module_param(path_name, charp, 0444);
static struct icc_path *path;
static struct platform_device *pdev;

static int __init holdbw_init(void)
{
	struct device_node *np = of_find_node_by_path("/rog5-input-boost");
	int ret;

	if (!np)
		return -ENODEV;
	pdev = of_find_device_by_node(np);
	of_node_put(np);
	if (!pdev)
		return -ENODEV;
	path = of_icc_get(&pdev->dev, path_name);
	if (IS_ERR_OR_NULL(path)) {
		put_device(&pdev->dev);
		return path ? PTR_ERR(path) : -ENODEV;
	}
	icc_set_tag(path, QCOM_ICC_TAG_ACTIVE_ONLY);
	ret = icc_set_bw(path, 0, peak_kbps);
	pr_info("rog5-holdbw: %s peak %u kBps active-only: %d\n", path_name, peak_kbps, ret);
	if (ret) {
		icc_put(path);
		put_device(&pdev->dev);
	}
	return ret;
}

static void __exit holdbw_exit(void)
{
	icc_set_bw(path, 0, 0);
	icc_put(path);
	put_device(&pdev->dev);
	pr_info("rog5-holdbw: released\n");
}
module_init(holdbw_init);
module_exit(holdbw_exit);
MODULE_DESCRIPTION("ROG5 debug: hold an active-only DDR vote across suspend");
MODULE_LICENSE("GPL");
