// SPDX-License-Identifier: GPL-2.0
/* Development probe: send whitelisted brightness DCS commands to the AMS678.
 *
 * Writes to /sys/kernel/debug/rog5-panel-dcs, one command per write:
 *   "53 XX lp|hs"      Write CTRL Display, exactly one parameter byte
 *   "51 HH LL lp|hs"   Write Display Brightness, exactly two parameter bytes
 *   "r 0a|52|54 lp|hs" read power mode, brightness or CTRL display; reading
 *                      the file returns the last result as hex bytes
 * Nothing else is accepted: a padded 0x51 (four bytes) hard-hung the phone,
 * so lengths are fixed. Not for production; the panel driver owns the link.
 */
#include <drm/drm_mipi_dsi.h>
#include <linux/debugfs.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/uaccess.h>

static const char panel_path[] = "/soc@0/display-subsystem@ae00000/dsi@ae94000/panel@0";
static struct mipi_dsi_device *dsi;
static struct dentry *file;
static DEFINE_MUTEX(lock);
static char last[64] = "none\n";

static ssize_t dcs_write(struct file *f, const char __user *ubuf, size_t len, loff_t *off)
{
	char buf[32] = {}, mode[3] = {};
	unsigned int cmd, a, b;
	unsigned long saved;
	u8 params[2];
	int n, count, ret;

	if (len >= sizeof(buf) || copy_from_user(buf, ubuf, len))
		return -EINVAL;
	if (buf[0] == 'r') {
		u8 data[4] = {};

		if (sscanf(buf, "r %x %2s", &cmd, mode) != 2 ||
		    (cmd != 0x0a && cmd != 0x52 && cmd != 0x54) ||
		    (strcmp(mode, "lp") && strcmp(mode, "hs")))
			return -EINVAL;
		mutex_lock(&lock);
		saved = dsi->mode_flags;
		if (!strcmp(mode, "lp"))
			dsi->mode_flags |= MIPI_DSI_MODE_LPM;
		else
			dsi->mode_flags &= ~MIPI_DSI_MODE_LPM;
		ret = mipi_dsi_dcs_read(dsi, cmd, data, cmd == 0x52 ? 2 : 1);
		dsi->mode_flags = saved;
		snprintf(last, sizeof(last), "%02x ret=%d: %02x %02x\n", cmd, ret, data[0], data[1]);
		mutex_unlock(&lock);
		pr_info("rog5-panel-dcs: read %s", last);
		return ret < 0 ? ret : len;
	}
	if (sscanf(buf, "%x", &cmd) != 1)
		return -EINVAL;
	if (cmd == 0x53) {
		n = sscanf(buf, "%x %x %2s", &cmd, &a, mode);
		if (n != 3 || a > 0xff)
			return -EINVAL;
		params[0] = a;
		count = 1;
	} else if (cmd == 0x51) {
		n = sscanf(buf, "%x %x %x %2s", &cmd, &a, &b, mode);
		if (n != 4 || a > 0xff || b > 0xff)
			return -EINVAL;
		params[0] = a;
		params[1] = b;
		count = 2;
	} else {
		return -EINVAL;
	}
	if (strcmp(mode, "lp") && strcmp(mode, "hs"))
		return -EINVAL;

	mutex_lock(&lock);
	saved = dsi->mode_flags;
	if (!strcmp(mode, "lp"))
		dsi->mode_flags |= MIPI_DSI_MODE_LPM;
	else
		dsi->mode_flags &= ~MIPI_DSI_MODE_LPM;
	ret = mipi_dsi_dcs_write(dsi, cmd, params, count);
	dsi->mode_flags = saved;
	mutex_unlock(&lock);
	pr_info("rog5-panel-dcs: %02x len=%d %s ret=%d\n", cmd, count, mode, ret);
	return ret < 0 ? ret : len;
}

static ssize_t dcs_read(struct file *f, char __user *ubuf, size_t len, loff_t *off)
{
	return simple_read_from_buffer(ubuf, len, off, last, strlen(last));
}

static const struct file_operations fops = {
	.owner = THIS_MODULE,
	.write = dcs_write,
	.read = dcs_read,
};

static int __init probe_init(void)
{
	struct device_node *np = of_find_node_by_path(panel_path);

	if (!np || !of_device_is_compatible(np, "asus,rog5-ams678-er2")) {
		of_node_put(np);
		return -ENODEV;
	}
	dsi = of_find_mipi_dsi_device_by_node(np);
	of_node_put(np);
	if (!dsi)
		return -ENODEV;
	file = debugfs_create_file("rog5-panel-dcs", 0600, NULL, NULL, &fops);
	return 0;
}

static void __exit probe_exit(void)
{
	debugfs_remove(file);
	put_device(&dsi->dev);
}

module_init(probe_init);
module_exit(probe_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("ROG5 development probe for whitelisted AMS678 brightness DCS writes");
