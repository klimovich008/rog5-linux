// SPDX-License-Identifier: GPL-2.0
/*
 * ROG5: suspend without the PM console VT switch.
 *
 * kernel/power/console.c switches to the suspend VT unless some device has
 * registered pm_vt_switch_required(dev, false). Normally fbdev does that from
 * register_framebuffer(); the ROG5 boots without an fbdev client, so every
 * suspend switched VTs. The switch deactivates the seat session: seatd
 * disabled Denial (which then never re-added its libinput devices) and logind
 * paused phoc (which re-created DSI-1 on resume and crashed phosh).
 * The compositors restore the display themselves, so the switch is not needed.
 */
#include <linux/err.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/pm.h>

static struct platform_device *rog5_no_vt_switch_dev;

static int __init rog5_no_vt_switch_init(void)
{
	int ret;

	rog5_no_vt_switch_dev = platform_device_register_simple("rog5-no-vt-switch",
								 PLATFORM_DEVID_NONE, NULL, 0);
	if (IS_ERR(rog5_no_vt_switch_dev))
		return PTR_ERR(rog5_no_vt_switch_dev);

	ret = pm_vt_switch_required(&rog5_no_vt_switch_dev->dev, false);
	if (ret) {
		platform_device_unregister(rog5_no_vt_switch_dev);
		return ret;
	}
	return 0;
}

static void __exit rog5_no_vt_switch_exit(void)
{
	pm_vt_switch_unregister(&rog5_no_vt_switch_dev->dev);
	platform_device_unregister(rog5_no_vt_switch_dev);
}

module_init(rog5_no_vt_switch_init);
module_exit(rog5_no_vt_switch_exit);
MODULE_DESCRIPTION("ROG5: suspend without the PM console VT switch");
MODULE_LICENSE("GPL");
