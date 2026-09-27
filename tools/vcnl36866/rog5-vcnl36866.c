// SPDX-License-Identifier: GPL-2.0
/* Vishay VCNL36866 ambient light and proximity sensor (IIO).
 *
 * The ROG Phone 5's front light/proximity sensor sits on QUP SE0 I2C at 0x60
 * (ID register 0xf6 reads 0x62). Registers are 16-bit, low byte first. The
 * configuration follows the stock ASUS driver defaults (ASH vcnl36866):
 * proximity 10 ms period, 2T integration, 14 mA VCSEL, 2 pulses, high gain;
 * light 50 ms integration with high dynamic range.
 *
 * Both functions are switched on at the first read and off again 2 s after
 * the last one, so an idle phone does not pulse the VCSEL.
 * in_illuminance_raw * in_illuminance_scale is lux with the stock default
 * calibration (846 counts at 1000 lux: the ROG5 builds the stock driver
 * with ONE_PL_CHIP, vcnl36866.h; the 1658 two-chip default read 2x low);
 * in_proximity_raw rises as an object
 * approaches.
 */
#include <linux/delay.h>
#include <linux/i2c.h>
#include <linux/iio/iio.h>
#include <linux/module.h>
#include <linux/mod_devicetable.h>
#include <linux/regulator/consumer.h>
#include <linux/workqueue.h>

#define CS_CONF1	0x00	/* CS_CONF2 is its high byte */
#define PS_CONF1	0x03	/* PS_CONF2 is its high byte */
#define PS_CONF3	0x04	/* PS_CONF4 is its high byte */
#define ALS_DATA	0xf1
#define PS_DATA		0xf4
#define ID_REG		0xf6
#define CHIP_ID		0x62

#define CAL_1000LUX	846
#define IDLE_OFF_MS	2000

struct vcnl {
	struct i2c_client *i2c;
	struct mutex lock;
	struct delayed_work off;
	bool on;
};

/* read-modify-write of one byte (hi = high byte) of a 16-bit register */
static int rmw(struct vcnl *v, u8 reg, bool hi, u8 keep, u8 set)
{
	int val = i2c_smbus_read_word_data(v->i2c, reg);
	u8 b;

	if (val < 0)
		return val;
	b = hi ? val >> 8 : val & 0xff;
	b = (b & keep) | set;
	val = hi ? (val & 0x00ff) | (b << 8) : (val & 0xff00) | b;
	return i2c_smbus_write_word_data(v->i2c, reg, val);
}

static int configure(struct vcnl *v)
{
	int ret = 0;

	/* proximity (vcnl36866_proximity_hw_set_config) */
	ret |= rmw(v, CS_CONF1, false, 0xfd, 1 << 1);	/* CS standby config */
	ret |= rmw(v, CS_CONF1, false, 0x7f, 1 << 7);	/* CS start */
	ret |= rmw(v, PS_CONF1, false, 0xf3, 1 << 0);	/* PS off, PS int off */
	ret |= rmw(v, PS_CONF1, true, 0xf7, 1 << 3);	/* PS start */
	ret |= rmw(v, PS_CONF3, false, 0xf7, 1 << 3);	/* PS start2 */
	ret |= rmw(v, PS_CONF1, false, 0x3f, 0 << 6);	/* 10 ms period */
	ret |= rmw(v, PS_CONF1, false, 0xcf, 0 << 4);	/* persistence 1 */
	ret |= rmw(v, PS_CONF1, true, 0x3f, 1 << 6);	/* integration 2T */
	ret |= rmw(v, PS_CONF3, true, 0xfc, 2);		/* VCSEL 14 mA */
	ret |= rmw(v, PS_CONF1, true, 0xcf, 1 << 4);	/* 2 pulses */
	ret |= rmw(v, PS_CONF1, true, 0xfb, 1 << 2);	/* high gain */
	/* light (vcnl36866_light_hw_set_config) */
	ret |= rmw(v, CS_CONF1, true, 0xfd, 1 << 1);	/* CS start2 */
	ret |= rmw(v, CS_CONF1, true, 0xf3, 0 << 2);	/* persistence 1 */
	ret |= rmw(v, CS_CONF1, false, 0xf3, 0 << 2);	/* 50 ms */
	ret |= rmw(v, CS_CONF1, true, 0xff, 1 << 6);	/* high dynamic range */
	ret |= rmw(v, CS_CONF1, false, 0xff, 0xc0);	/* ALS start */
	return ret ? -EIO : 0;
}

static int power(struct vcnl *v, bool on)
{
	int ret;

	/* SD bits: 1 = shut down */
	ret = rmw(v, CS_CONF1, false, 0xfe, on ? 0 : 1);
	if (!ret)
		ret = rmw(v, PS_CONF1, false, 0xfe, on ? 0 : 1);
	if (!ret)
		v->on = on;
	return ret;
}

static void off_work(struct work_struct *work)
{
	struct vcnl *v = container_of(to_delayed_work(work), struct vcnl, off);

	mutex_lock(&v->lock);
	if (v->on)
		power(v, false);
	mutex_unlock(&v->lock);
}

static int vcnl_read_raw(struct iio_dev *indio, struct iio_chan_spec const *chan,
			 int *val, int *val2, long mask)
{
	struct vcnl *v = iio_priv(indio);
	int ret;

	switch (mask) {
	case IIO_CHAN_INFO_RAW:
		mutex_lock(&v->lock);
		if (!v->on) {
			ret = power(v, true);
			if (ret) {
				mutex_unlock(&v->lock);
				return ret;
			}
			msleep(80);	/* one 50 ms ALS cycle plus margin */
		}
		ret = i2c_smbus_read_word_data(v->i2c,
					       chan->type == IIO_LIGHT ? ALS_DATA : PS_DATA);
		mod_delayed_work(system_dfl_wq, &v->off, msecs_to_jiffies(IDLE_OFF_MS));
		mutex_unlock(&v->lock);
		if (ret < 0)
			return ret;
		*val = ret;
		return IIO_VAL_INT;
	case IIO_CHAN_INFO_SCALE:
		if (chan->type != IIO_LIGHT)
			return -EINVAL;
		*val = 1000;
		*val2 = CAL_1000LUX;
		return IIO_VAL_FRACTIONAL;
	}
	return -EINVAL;
}

static const struct iio_chan_spec vcnl_channels[] = {
	{
		.type = IIO_LIGHT,
		.info_mask_separate = BIT(IIO_CHAN_INFO_RAW) | BIT(IIO_CHAN_INFO_SCALE),
	}, {
		.type = IIO_PROXIMITY,
		.info_mask_separate = BIT(IIO_CHAN_INFO_RAW),
	},
};

static const struct iio_info vcnl_info = {
	.read_raw = vcnl_read_raw,
};

static void vcnl_shutdown_action(void *data)
{
	struct vcnl *v = data;

	cancel_delayed_work_sync(&v->off);
	mutex_lock(&v->lock);
	power(v, false);
	mutex_unlock(&v->lock);
}

static int vcnl_probe(struct i2c_client *i2c)
{
	struct device *dev = &i2c->dev;
	struct iio_dev *indio;
	struct vcnl *v;
	int id, ret;

	ret = devm_regulator_get_enable_optional(dev, "vdd");
	if (ret && ret != -ENODEV)
		return dev_err_probe(dev, ret, "vdd supply\n");
	if (!ret)
		msleep(5);
	id = i2c_smbus_read_word_data(i2c, ID_REG);
	if (id < 0)
		return dev_err_probe(dev, id, "no response\n");
	if ((id & 0xff) != CHIP_ID)
		return dev_err_probe(dev, -ENODEV, "ID %#x, not a VCNL36866\n", id);

	indio = devm_iio_device_alloc(dev, sizeof(*v));
	if (!indio)
		return -ENOMEM;
	v = iio_priv(indio);
	v->i2c = i2c;
	mutex_init(&v->lock);
	INIT_DELAYED_WORK(&v->off, off_work);
	ret = configure(v);
	if (!ret)
		ret = power(v, false);
	if (ret)
		return dev_err_probe(dev, ret, "configuration failed\n");
	ret = devm_add_action_or_reset(dev, vcnl_shutdown_action, v);
	if (ret)
		return ret;

	indio->name = "vcnl36866";
	indio->info = &vcnl_info;
	indio->channels = vcnl_channels;
	indio->num_channels = ARRAY_SIZE(vcnl_channels);
	indio->modes = INDIO_DIRECT_MODE;
	return devm_iio_device_register(dev, indio);
}

static const struct of_device_id vcnl_of_match[] = {
	{ .compatible = "vishay,vcnl36866" },
	{ }
};
MODULE_DEVICE_TABLE(of, vcnl_of_match);

static const struct i2c_device_id vcnl_id[] = {
	{ "vcnl36866" },
	{ }
};
MODULE_DEVICE_TABLE(i2c, vcnl_id);

static struct i2c_driver vcnl_driver = {
	.driver = {
		.name = "rog5-vcnl36866",
		.of_match_table = vcnl_of_match,
	},
	.probe = vcnl_probe,
	.id_table = vcnl_id,
};
module_i2c_driver(vcnl_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Vishay VCNL36866 light and proximity sensor for the ROG Phone 5");
