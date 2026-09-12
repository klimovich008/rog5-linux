// SPDX-License-Identifier: GPL-2.0-only
/* ASUS MP2 front touch: normal firmware protocol only. */
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/i2c.h>
#include <linux/input.h>
#include <linux/input/mt.h>
#include <linux/interrupt.h>
#include <linux/irq.h>
#include <linux/jiffies.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/pm.h>
#include <linux/property.h>
#include <linux/regulator/consumer.h>
#include <linux/slab.h>

#include "rog5_fts_protocol.h"

/* A regulator error can occur after child or parent bookkeeping changed. */
enum rog5_fts_vote {
	ROG5_FTS_VOTE_NONE,
	ROG5_FTS_VOTE_HELD,
	ROG5_FTS_VOTE_UNKNOWN,
};

struct rog5_fts {
	struct i2c_client *client;
	struct input_dev *input;
	struct gpio_desc *reset;
	struct gpio_desc *io_enable;
	struct regulator *vdd;
	struct regulator *vcc_i2c;
	enum rog5_fts_vote vdd_vote;
	enum rog5_fts_vote io_vote;
	bool irq_running;
};

static int rog5_fts_read(struct rog5_fts *ts, u8 reg, u8 *data, u16 size)
{
	struct i2c_msg messages[] = {
		{ .addr = ts->client->addr, .len = 1, .buf = &reg },
		{ .addr = ts->client->addr, .flags = I2C_M_RD,
		  .len = size, .buf = data },
	};

	return rog5_fts_transfer_result(i2c_transfer(ts->client->adapter,
						 messages, ARRAY_SIZE(messages)));
}

static int rog5_fts_identify(struct rog5_fts *ts)
{
	unsigned long deadline = jiffies + msecs_to_jiffies(1000);
	int attempt, ret;
	u8 high, low;

	/* At most twenty pairs, with no HID/bootloader/firmware writes. */
	for (attempt = 0; attempt < 20; attempt++) {
		ret = rog5_fts_read(ts, 0xa3, &high, 1);
		if (ret)
			return ret;
		ret = rog5_fts_read(ts, 0x9f, &low, 1);
		if (ret)
			return ret;
		if (rog5_fts_normal_id(high, low)) {
			dev_info(&ts->client->dev, "normal firmware ID %02x%02x\n",
				 high, low);
			return 0;
		}
		if (time_after_eq(jiffies, deadline))
			break;
		if (attempt != 19)
			msleep(50);
	}
	return -ENODEV;
}

/* Drop only our votes. In particular, never force-disable shared L8C. */
static int rog5_fts_power_off(struct rog5_fts *ts)
{
	struct device *dev = &ts->client->dev;
	int ret, first = 0;

	ret = gpiod_set_value_cansleep(ts->reset, 1);
	if (ret) {
		dev_err(dev, "reset assert failed: %d\n", ret);
		first = ret;
	}
	usleep_range(10000, 12000);
	ret = gpiod_set_value_cansleep(ts->io_enable, 0);
	if (ret) {
		dev_err(dev, "IO enable low failed: %d\n", ret);
		if (!first)
			first = ret;
	}
	usleep_range(1000, 1500);
	if (ts->vdd_vote == ROG5_FTS_VOTE_UNKNOWN) {
		dev_err(dev, "VDD ownership unknown; recovery required\n");
		if (!first)
			first = -EUCLEAN;
	} else if (ts->vdd_vote == ROG5_FTS_VOTE_HELD) {
		ret = regulator_disable(ts->vdd);
		if (ret) {
			ts->vdd_vote = ROG5_FTS_VOTE_UNKNOWN;
			dev_err(dev, "VDD vote release failed: %d\n", ret);
			if (!first)
				first = ret;
		} else {
			ts->vdd_vote = ROG5_FTS_VOTE_NONE;
		}
	}
	if (ts->io_vote == ROG5_FTS_VOTE_UNKNOWN) {
		dev_err(dev, "IO supply ownership unknown; recovery required\n");
		if (!first)
			first = -EUCLEAN;
	} else if (ts->io_vote == ROG5_FTS_VOTE_HELD) {
		ret = regulator_disable(ts->vcc_i2c);
		if (ret) {
			ts->io_vote = ROG5_FTS_VOTE_UNKNOWN;
			dev_err(dev, "IO supply vote release failed: %d\n", ret);
			if (!first)
				first = ret;
		} else {
			ts->io_vote = ROG5_FTS_VOTE_NONE;
		}
	}
	return first;
}

static void rog5_fts_power_cleanup(void *data)
{
	/* Every failure is logged by the helper; devres cannot return it. */
	rog5_fts_power_off(data);
}

static int rog5_fts_power_on(struct rog5_fts *ts)
{
	int ret;

	if (ts->vdd_vote != ROG5_FTS_VOTE_NONE ||
	    ts->io_vote != ROG5_FTS_VOTE_NONE)
		return -EBUSY;
	ret = gpiod_set_value_cansleep(ts->reset, 1);
	if (ret)
		return ret;
	usleep_range(1000, 1500);
	ret = regulator_enable(ts->vcc_i2c);
	if (ret) {
		ts->io_vote = ROG5_FTS_VOTE_UNKNOWN;
		return ret;
	}
	ts->io_vote = ROG5_FTS_VOTE_HELD;
	ret = gpiod_set_value_cansleep(ts->io_enable, 1);
	if (ret)
		goto fail;
	usleep_range(1000, 1500);
	ret = regulator_enable(ts->vdd);
	if (ret) {
		ts->vdd_vote = ROG5_FTS_VOTE_UNKNOWN;
		goto fail;
	}
	ts->vdd_vote = ROG5_FTS_VOTE_HELD;
	usleep_range(5000, 6000);
	ret = gpiod_set_value_cansleep(ts->reset, 0);
	if (ret)
		goto fail;
	msleep(200);
	return 0;
fail:
	rog5_fts_power_off(ts);
	return ret;
}

static void rog5_fts_release(struct rog5_fts *ts)
{
	unsigned int slot;

	for (slot = 0; slot < ROG5_FTS_POINTS; slot++) {
		input_mt_slot(ts->input, slot);
		input_mt_report_slot_state(ts->input, MT_TOOL_FINGER, false);
	}
	input_mt_sync_frame(ts->input);
	input_sync(ts->input);
}

static irqreturn_t rog5_fts_irq(int irq, void *data)
{
	struct rog5_fts *ts = data;
	struct rog5_fts_frame frame;
	u8 bytes[ROG5_FTS_FRAME_BYTES];
	unsigned int i;
	int ret;

	ret = rog5_fts_read(ts, 0x01, bytes, sizeof(bytes));
	if (!ret)
		ret = rog5_fts_decode(bytes, sizeof(bytes), &frame);
	if (ret) {
		/* A bad transfer/frame cannot leave a stale active contact. */
		rog5_fts_release(ts);
		dev_warn_ratelimited(&ts->client->dev, "touch frame refused: %d\n",
				     ret);
		return IRQ_HANDLED;
	}

	for (i = 0; i < frame.records; i++) {
		const struct rog5_fts_point *point = &frame.points[i];
		bool active = frame.active & BIT(point->slot);

		input_mt_slot(ts->input, point->slot);
		input_mt_report_slot_state(ts->input, MT_TOOL_FINGER, active);
		if (active) {
			input_report_abs(ts->input, ABS_MT_POSITION_X, point->x);
			input_report_abs(ts->input, ABS_MT_POSITION_Y, point->y);
			input_report_abs(ts->input, ABS_MT_TOUCH_MAJOR, point->area);
		}
	}
	input_mt_sync_frame(ts->input);
	input_sync(ts->input);
	return IRQ_HANDLED;
}

/* Runs before managed IRQ/input/power resources are released. */
static void rog5_fts_stop(void *data)
{
	struct rog5_fts *ts = data;

	if (ts->irq_running) {
		disable_irq(ts->client->irq);
		ts->irq_running = false;
	}
	rog5_fts_release(ts);
}

static int rog5_fts_probe(struct i2c_client *client)
{
	struct device *dev = &client->dev;
	struct rog5_fts *ts;
	u32 x, y;
	int ret;

	if (!dev->of_node || client->addr != 0x38 ||
	    (client->flags & I2C_CLIENT_TEN) || client->irq <= 0)
		return -EINVAL;
	if (!i2c_check_functionality(client->adapter, I2C_FUNC_I2C))
		return -EOPNOTSUPP;
	if (irq_get_trigger_type(client->irq) != IRQ_TYPE_EDGE_FALLING)
		return dev_err_probe(dev, -EINVAL, "require falling-edge IRQ\n");
	ret = device_property_read_u32(dev, "touchscreen-size-x", &x);
	if (ret)
		return ret;
	ret = device_property_read_u32(dev, "touchscreen-size-y", &y);
	if (ret)
		return ret;
	if (x != ROG5_FTS_SIZE_X || y != ROG5_FTS_SIZE_Y)
		return dev_err_probe(dev, -EINVAL, "require native MP2 axes\n");

	ts = devm_kzalloc(dev, sizeof(*ts), GFP_KERNEL);
	if (!ts)
		return -ENOMEM;
	ts->client = client;
	i2c_set_clientdata(client, ts);
	/* Optional-get semantics prevent silently substituting dummy supplies. */
	ts->vdd = devm_regulator_get_optional(dev, "vdd");
	if (IS_ERR(ts->vdd))
		return dev_err_probe(dev, PTR_ERR(ts->vdd), "require real VDD\n");
	ts->vcc_i2c = devm_regulator_get_optional(dev, "vcc_i2c");
	if (IS_ERR(ts->vcc_i2c))
		return dev_err_probe(dev, PTR_ERR(ts->vcc_i2c), "require real IO\n");
	ts->reset = devm_gpiod_get(dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(ts->reset))
		return dev_err_probe(dev, PTR_ERR(ts->reset), "get reset\n");
	ts->io_enable = devm_gpiod_get(dev, "io-enable", GPIOD_OUT_LOW);
	if (IS_ERR(ts->io_enable))
		return dev_err_probe(dev, PTR_ERR(ts->io_enable), "get IO enable\n");
	ret = devm_add_action_or_reset(dev, rog5_fts_power_cleanup, ts);
	if (ret)
		return ret;
	ret = rog5_fts_power_on(ts);
	if (ret)
		return dev_err_probe(dev, ret, "power on\n");
	ret = rog5_fts_identify(ts);
	if (ret)
		return dev_err_probe(dev, ret, "normal firmware ID refused\n");

	ts->input = devm_input_allocate_device(dev);
	if (!ts->input)
		return -ENOMEM;
	ts->input->name = "ASUS ROG5 MP2 front FTS3658U";
	ts->input->id.bustype = BUS_I2C;
	input_set_abs_params(ts->input, ABS_MT_POSITION_X, 0, x - 1, 0, 0);
	input_set_abs_params(ts->input, ABS_MT_POSITION_Y, 0, y - 1, 0, 0);
	input_set_abs_params(ts->input, ABS_MT_TOUCH_MAJOR, 0, 15, 0, 0);
	ret = input_mt_init_slots(ts->input, ROG5_FTS_POINTS,
				  INPUT_MT_DIRECT | INPUT_MT_DROP_UNUSED);
	if (ret)
		return ret;
	ret = input_register_device(ts->input);
	if (ret)
		return ret;
	ret = devm_request_threaded_irq(dev, client->irq, NULL, rog5_fts_irq,
					IRQF_ONESHOT | IRQF_TRIGGER_FALLING,
					dev_name(dev), ts);
	if (ret)
		return dev_err_probe(dev, ret, "request IRQ\n");
	ts->irq_running = true;
	return devm_add_action_or_reset(dev, rog5_fts_stop, ts);
}

static void rog5_fts_shutdown(struct i2c_client *client)
{
	struct rog5_fts *ts = i2c_get_clientdata(client);

	rog5_fts_stop(ts);
	rog5_fts_power_off(ts);
}

/* Initial component probe does not qualify suspend/resume or wake gestures. */
static int rog5_fts_suspend(struct device *dev)
{
	return -EBUSY;
}
static DEFINE_SIMPLE_DEV_PM_OPS(rog5_fts_pm, rog5_fts_suspend, NULL);

static const struct of_device_id rog5_fts_match[] = {
	{ .compatible = "asus,rog5-mp2-fts3658u" },
	{ }
};
MODULE_DEVICE_TABLE(of, rog5_fts_match);

static struct i2c_driver rog5_fts_driver = {
	.driver = {
		.name = "rog5-fts3658u",
		.of_match_table = rog5_fts_match,
		.pm = pm_sleep_ptr(&rog5_fts_pm),
	},
	.probe = rog5_fts_probe,
	.shutdown = rog5_fts_shutdown,
};
module_i2c_driver(rog5_fts_driver);

MODULE_DESCRIPTION("ASUS ROG5 MP2 front normal-mode FocalTech touch");
MODULE_LICENSE("GPL");
