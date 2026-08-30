// SPDX-License-Identifier: GPL-2.0-only
/* QEMU-only PCI power-control reproduction, with dummy supplies and no GPIOs. */
#include <linux/module.h>
#include <linux/of.h>
#include <linux/pci-pwrctrl.h>
#include <linux/platform_device.h>

static int rog5_pwrctrl_probe(struct platform_device *pdev)
{
	int ret;

	if (!of_machine_is_compatible("linux,dummy-virt"))
		return -EPERM;

	dev_info(&pdev->dev, "ROG5_PWRCTRL_CREATE_ENTER\n");
	ret = pci_pwrctrl_create_devices(&pdev->dev);
	dev_info(&pdev->dev, "ROG5_PWRCTRL_CREATE_RETURN=%d\n", ret);
	if (ret)
		return ret;

	dev_info(&pdev->dev, "ROG5_PWRCTRL_DUMMY_POWER_ON_ENTER\n");
	ret = pci_pwrctrl_power_on_devices(&pdev->dev);
	dev_info(&pdev->dev, "ROG5_PWRCTRL_DUMMY_POWER_ON_RETURN=%d\n", ret);
	if (!ret) {
		pci_pwrctrl_power_off_devices(&pdev->dev);
		dev_info(&pdev->dev, "ROG5_PWRCTRL_DUMMY_POWER_OFF_RETURN\n");
	} else
		pci_pwrctrl_destroy_devices(&pdev->dev);
	return ret;
}

static void rog5_pwrctrl_remove(struct platform_device *pdev)
{
	pci_pwrctrl_destroy_devices(&pdev->dev);
}

static const struct of_device_id rog5_pwrctrl_match[] = {
	{ .compatible = "rog5,qemu-pcie-pwrctrl-test" },
	{ }
};
MODULE_DEVICE_TABLE(of, rog5_pwrctrl_match);

static struct platform_driver rog5_pwrctrl_driver = {
	.probe = rog5_pwrctrl_probe,
	.remove = rog5_pwrctrl_remove,
	.driver = {
		.name = "rog5-qemu-pwrctrl-test",
		.of_match_table = rog5_pwrctrl_match,
	},
};
module_platform_driver(rog5_pwrctrl_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("QEMU-only PCI power-control creation regression probe");
