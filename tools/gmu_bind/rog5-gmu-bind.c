// SPDX-License-Identifier: GPL-2.0
/* Bind the A660 GMU platform device to an empty driver so its clock
 * suppliers can finish boot.
 *
 * msm drives the GMU through of_find_device_by_node() from the GPU's bind and
 * never probes a driver for it. fw_devlink still records the GMU as a
 * consumer of GCC and GPUCC, so both providers wait for it forever
 * ("sync_state() pending due to 3d6a000.gmu") and their unused boot-time
 * clocks are never switched off. Binding here marks those links active and
 * changes nothing else: no clocks, power domains or registers are touched.
 *
 * It must load before msm: msm puts devm resources on the GMU device, and the
 * driver core refuses to probe a device that already has some.
 */
#include <linux/module.h>
#include <linux/mod_devicetable.h>
#include <linux/of.h>
#include <linux/platform_device.h>

static int gmu_bind_probe(struct platform_device *pdev)
{
	dev_info(&pdev->dev, "ROG5_GMU_BIND bound for fw_devlink\n");
	return 0;
}

static const struct of_device_id gmu_bind_match[] = {
	{ .compatible = "qcom,adreno-gmu-660.1" },
	{ }
};

static struct platform_driver gmu_bind_driver = {
	.probe = gmu_bind_probe,
	.driver = {
		.name = "rog5-gmu-bind",
		.of_match_table = gmu_bind_match,
		.suppress_bind_attrs = true,
	},
	/* msm owns the GMU's IOMMU domain; leave the default domain alone. */
	.driver_managed_dma = true,
};

static int __init gmu_bind_init(void)
{
	if (!of_machine_is_compatible("asus,rog-phone5"))
		return -ENODEV;
	return platform_driver_register(&gmu_bind_driver);
}

module_init(gmu_bind_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("ROG5 empty driver for the A660 GMU so GCC/GPUCC reach sync_state");
