/* SPDX-License-Identifier: GPL-2.0 */
/* Backlight Lowlevel Control Abstraction
 * Copyright (C) 2003,2004 Hewlett-Packard Company
 * Exact extracts from Linux v7.2.7 (f42acb367842); unchanged since v7.1.4.
 * Registration, event notification and DSI transport remain host boundaries. */

static inline int backlight_update_status(struct backlight_device *bd)
{
	int ret = -ENOENT;

	mutex_lock(&bd->update_lock);
	if (bd->ops && bd->ops->update_status)
		ret = bd->ops->update_status(bd);
	mutex_unlock(&bd->update_lock);

	return ret;
}

static inline int backlight_enable(struct backlight_device *bd)
{
	if (!bd)
		return 0;

	bd->props.power = BACKLIGHT_POWER_ON;
	bd->props.state &= ~BL_CORE_FBBLANK;

	return backlight_update_status(bd);
}

static inline int backlight_disable(struct backlight_device *bd)
{
	if (!bd)
		return 0;

	bd->props.power = BACKLIGHT_POWER_OFF;
	bd->props.state |= BL_CORE_FBBLANK;

	return backlight_update_status(bd);
}

static inline bool backlight_is_blank(const struct backlight_device *bd)
{
	return bd->props.power != BACKLIGHT_POWER_ON ||
	       bd->props.state & (BL_CORE_SUSPENDED | BL_CORE_FBBLANK);
}

static inline int backlight_get_brightness(const struct backlight_device *bd)
{
	if (backlight_is_blank(bd))
		return 0;
	else
		return bd->props.brightness;
}

/* Keep the kernel's signed max_brightness field and unsigned API argument;
 * local suppression matches kernel builds without weakening other host checks. */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wsign-compare"
int backlight_device_set_brightness(struct backlight_device *bd,
				    unsigned long brightness)
{
	int rc = -ENXIO;

	mutex_lock(&bd->ops_lock);
	if (bd->ops) {
		if (brightness > bd->props.max_brightness)
			rc = -EINVAL;
		else {
			pr_debug("set brightness to %lu\n", brightness);
			bd->props.brightness = brightness;
			rc = backlight_update_status(bd);
		}
	}
	mutex_unlock(&bd->ops_lock);

	backlight_generate_event(bd, BACKLIGHT_UPDATE_SYSFS);

	return rc;
}

#pragma GCC diagnostic pop
