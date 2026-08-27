// SPDX-License-Identifier: GPL-2.0-only
#include <linux/clk.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>

#define WDT_EN		0x08
#define WDT_STS		0x0c
#define WDT_BARK_TIME	0x10
#define WDT_BITE_TIME	0x14

static int rog5_wdt_observer_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct resource *res;
	void __iomem *base;
	struct clk *clk;
	unsigned long rate = 0;

	res = platform_get_resource_byname(pdev, IORESOURCE_MEM, "wdt-base");
	if (!res)
		return dev_err_probe(dev, -ENODEV,
				     "missing exact wdt-base resource\n");

	base = devm_ioremap_resource(dev, res);
	if (IS_ERR(base))
		return PTR_ERR(base);

	clk = devm_clk_get_optional(dev, NULL);
	if (IS_ERR(clk))
		return dev_err_probe(dev, PTR_ERR(clk),
				     "cannot inspect watchdog clock\n");
	if (clk)
		rate = clk_get_rate(clk);

	dev_info(dev,
		 "ROG5_WDT_OBSERVER_V1 rate=%lu en=%08x sts=%08x bark=%08x bite=%08x\n",
		 rate, readl_relaxed(base + WDT_EN),
		 readl_relaxed(base + WDT_STS),
		 readl_relaxed(base + WDT_BARK_TIME),
		 readl_relaxed(base + WDT_BITE_TIME));

	return 0;
}

static const struct of_device_id rog5_wdt_observer_of_match[] = {
	{ .compatible = "rog5,sm8350-wdt-observer" },
	{ }
};
MODULE_DEVICE_TABLE(of, rog5_wdt_observer_of_match);

static struct platform_driver rog5_wdt_observer_driver = {
	.probe = rog5_wdt_observer_probe,
	.driver = {
		.name = "rog5-qcom-wdt-observer",
		.of_match_table = rog5_wdt_observer_of_match,
	},
};
module_platform_driver(rog5_wdt_observer_driver);

MODULE_DESCRIPTION("Read-only ROG Phone 5 APSS watchdog register observer");
MODULE_LICENSE("GPL");
