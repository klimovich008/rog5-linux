// SPDX-License-Identifier: GPL-2.0
/* ROG Phone 5 back logo (Aura) RGB LED.
 *
 * A Nuvoton MS51 microcontroller on QUP SE0 I2C (0x16) drives the logo. Its
 * supply is switched by PM8350C GPIO 2 (stock DT "logo_5p0_en", hw_stage 5 and
 * later); the MCU answers about 300 ms after power-up. Registers have 16-bit
 * addresses (stock ASUS ms51_phone.c): 0x8010-0x8012 and 0x8013-0x8015 are
 * the red/green/blue levels of the two logo zones, 0x8021 the effect mode
 * (0 off, 1 static), 0x802f = 1 applies the settings, 0xcb01 the firmware
 * version.
 *
 * Exposed as one multicolor LED class device (rgb:logo). The MCU is powered
 * only while the LED is lit.
 */
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/i2c.h>
#include <linux/led-class-multicolor.h>
#include <linux/module.h>
#include <linux/mod_devicetable.h>

#define REG_RED		0x8010
#define REG_MODE	0x8021
#define REG_APPLY	0x802f
#define REG_FW		0xcb01
#define POWER_UP_MS	300

struct aura {
	struct i2c_client *i2c;
	struct gpio_desc *enable;
	struct led_classdev_mc mc;
	struct mc_subled sub[3];
	struct mutex lock;
	bool powered;
};

static int aura_write(struct aura *a, u16 reg, u8 val)
{
	u8 buf[3] = { reg >> 8, reg & 0xff, val };
	int ret = i2c_master_send(a->i2c, buf, sizeof(buf));

	return ret == sizeof(buf) ? 0 : (ret < 0 ? ret : -EIO);
}

static int aura_read(struct aura *a, u16 reg, u8 *data, int len)
{
	u8 addr[2] = { reg >> 8, reg & 0xff };
	int ret = i2c_master_send(a->i2c, addr, sizeof(addr));

	if (ret != sizeof(addr))
		return ret < 0 ? ret : -EIO;
	usleep_range(1000, 1500);
	ret = i2c_master_recv(a->i2c, data, len);
	return ret == len ? 0 : (ret < 0 ? ret : -EIO);
}

static void power(struct aura *a, bool on)
{
	if (a->powered == on)
		return;
	gpiod_set_value_cansleep(a->enable, on);
	if (on)
		msleep(POWER_UP_MS);
	a->powered = on;
}

static int aura_set(struct led_classdev *cdev, enum led_brightness brightness)
{
	struct led_classdev_mc *mc = lcdev_to_mccdev(cdev);
	struct aura *a = container_of(mc, struct aura, mc);
	int ret = 0, i;

	mutex_lock(&a->lock);
	if (!brightness) {
		if (a->powered) {
			aura_write(a, REG_MODE, 0);
			aura_write(a, REG_APPLY, 1);
		}
		power(a, false);
		goto out;
	}
	power(a, true);
	led_mc_calc_color_components(mc, brightness);
	for (i = 0; i < 3 && !ret; i++) {
		ret = aura_write(a, REG_RED + i, a->sub[i].brightness);
		if (!ret)
			ret = aura_write(a, REG_RED + 3 + i, a->sub[i].brightness);
	}
	if (!ret)
		ret = aura_write(a, REG_MODE, 1);
	if (!ret)
		ret = aura_write(a, REG_APPLY, 1);
out:
	mutex_unlock(&a->lock);
	return ret;
}

static int aura_probe(struct i2c_client *i2c)
{
	struct device *dev = &i2c->dev;
	struct led_init_data init = { };
	struct aura *a;
	u8 fw[2];
	int ret, i;

	a = devm_kzalloc(dev, sizeof(*a), GFP_KERNEL);
	if (!a)
		return -ENOMEM;
	a->i2c = i2c;
	mutex_init(&a->lock);
	a->enable = devm_gpiod_get(dev, "enable", GPIOD_OUT_LOW);
	if (IS_ERR(a->enable))
		return dev_err_probe(dev, PTR_ERR(a->enable), "enable GPIO\n");

	/* Check the MCU once, then leave it unpowered until the LED is used. */
	power(a, true);
	ret = aura_read(a, REG_FW, fw, sizeof(fw));
	power(a, false);
	if (ret)
		return dev_err_probe(dev, ret, "MCU does not answer\n");

	for (i = 0; i < 3; i++)
		a->sub[i].color_index = LED_COLOR_ID_RED + i;
	a->mc.subled_info = a->sub;
	a->mc.num_colors = 3;
	a->mc.led_cdev.max_brightness = 255;
	a->mc.led_cdev.brightness_set_blocking = aura_set;
	init.default_label = "rgb:logo";
	init.devicename = "rog5-aura";
	init.fwnode = dev_fwnode(dev);
	ret = devm_led_classdev_multicolor_register_ext(dev, &a->mc, &init);
	if (ret)
		return ret;
	dev_info(dev, "Aura logo MCU firmware %02x%02x\n", fw[0], fw[1]);
	return 0;
}

static const struct of_device_id aura_of_match[] = {
	{ .compatible = "asus,rog5-aura" },
	{ }
};
MODULE_DEVICE_TABLE(of, aura_of_match);

static struct i2c_driver aura_driver = {
	.driver = {
		.name = "rog5-aura",
		.of_match_table = aura_of_match,
	},
	.probe = aura_probe,
};
module_i2c_driver(aura_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("ROG Phone 5 back logo (Aura MS51) RGB LED");
