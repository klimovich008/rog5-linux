// SPDX-License-Identifier: GPL-2.0
/* Hold the CPU memory path at its top level while the user interacts.
 *
 * The bandwidth monitors (icc-bwmon) raise LLCC and DDR only after they have
 * measured traffic, a few milliseconds per step. The first frames of a gesture
 * are latency-bound, so with DDR scaling on they started on 451 MHz DDR and
 * the input-to-first-frame time grew from ~26 to ~38 ms (bench, r31). Stock
 * Android covers this with memory-latency governors and input boost.
 *
 * Any touchscreen, keyboard or power-key event raises peak votes on the
 * CPU->LLCC and LLCC->DDR paths of this node; they are dropped boost_ms after
 * the last event. Idle behaviour is unchanged.
 */
#include <linux/input.h>
#include <linux/interconnect.h>
#include <linux/module.h>
#include <linux/mod_devicetable.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/workqueue.h>

static unsigned int boost_ms = 250;
module_param(boost_ms, uint, 0644);
MODULE_PARM_DESC(boost_ms, "Hold time after the last input event");

struct input_boost {
	struct icc_path *llcc, *ddr;
	u32 llcc_kbps, ddr_kbps;
	struct work_struct on;
	struct delayed_work off;
	struct workqueue_struct *wq;	/* ordered: on and off never overlap */
	struct input_handler handler;
	bool boosted;		/* only touched from the work items */
};

static void boost_on(struct work_struct *work)
{
	struct input_boost *b = container_of(work, struct input_boost, on);

	if (b->boosted)
		return;
	b->boosted = true;
	icc_set_bw(b->llcc, 0, b->llcc_kbps);
	icc_set_bw(b->ddr, 0, b->ddr_kbps);
}

static void boost_off(struct work_struct *work)
{
	struct input_boost *b = container_of(to_delayed_work(work), struct input_boost, off);

	if (!b->boosted)
		return;
	b->boosted = false;
	icc_set_bw(b->ddr, 0, 0);
	icc_set_bw(b->llcc, 0, 0);
}

static void boost_event(struct input_handle *handle, unsigned int type,
			unsigned int code, int value)
{
	struct input_boost *b = handle->handler->private;

	if (type == EV_SYN)
		return;
	queue_work(b->wq, &b->on);
	mod_delayed_work(b->wq, &b->off, msecs_to_jiffies(boost_ms));
}

static int boost_connect(struct input_handler *handler, struct input_dev *dev,
			 const struct input_device_id *id)
{
	struct input_handle *handle;
	int ret;

	handle = kzalloc(sizeof(*handle), GFP_KERNEL);
	if (!handle)
		return -ENOMEM;
	handle->dev = dev;
	handle->handler = handler;
	handle->name = "rog5-input-boost";
	ret = input_register_handle(handle);
	if (ret)
		goto free;
	ret = input_open_device(handle);
	if (ret)
		goto unregister;
	return 0;
unregister:
	input_unregister_handle(handle);
free:
	kfree(handle);
	return ret;
}

static void boost_disconnect(struct input_handle *handle)
{
	input_close_device(handle);
	input_unregister_handle(handle);
	kfree(handle);
}

static const struct input_device_id boost_ids[] = {
	{	/* touchscreens (the panel's and the bench's virtual one) */
		.flags = INPUT_DEVICE_ID_MATCH_EVBIT | INPUT_DEVICE_ID_MATCH_ABSBIT,
		.evbit = { BIT_MASK(EV_ABS) },
		.absbit = { [BIT_WORD(ABS_MT_POSITION_X)] = BIT_MASK(ABS_MT_POSITION_X) },
	},
	{	/* keyboards */
		.flags = INPUT_DEVICE_ID_MATCH_EVBIT | INPUT_DEVICE_ID_MATCH_KEYBIT,
		.evbit = { BIT_MASK(EV_KEY) },
		.keybit = { [BIT_WORD(KEY_SPACE)] = BIT_MASK(KEY_SPACE) },
	},
	{	/* power key: the display wake */
		.flags = INPUT_DEVICE_ID_MATCH_EVBIT | INPUT_DEVICE_ID_MATCH_KEYBIT,
		.evbit = { BIT_MASK(EV_KEY) },
		.keybit = { [BIT_WORD(KEY_POWER)] = BIT_MASK(KEY_POWER) },
	},
	{ }
};

static int boost_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct input_boost *b;
	int ret;

	b = devm_kzalloc(dev, sizeof(*b), GFP_KERNEL);
	if (!b)
		return -ENOMEM;
	b->llcc = devm_of_icc_get(dev, "cpu-llcc");
	if (IS_ERR(b->llcc))
		return dev_err_probe(dev, PTR_ERR(b->llcc), "cpu-llcc path\n");
	b->ddr = devm_of_icc_get(dev, "llcc-ddr");
	if (IS_ERR(b->ddr))
		return dev_err_probe(dev, PTR_ERR(b->ddr), "llcc-ddr path\n");
	if (of_property_read_u32(dev->of_node, "asus,cpu-llcc-kBps", &b->llcc_kbps) ||
	    of_property_read_u32(dev->of_node, "asus,llcc-ddr-kBps", &b->ddr_kbps))
		return dev_err_probe(dev, -EINVAL, "boost bandwidths missing\n");
	b->wq = alloc_ordered_workqueue("rog5-input-boost", WQ_HIGHPRI);
	if (!b->wq)
		return -ENOMEM;
	INIT_WORK(&b->on, boost_on);
	INIT_DELAYED_WORK(&b->off, boost_off);
	b->handler.event = boost_event;
	b->handler.connect = boost_connect;
	b->handler.disconnect = boost_disconnect;
	b->handler.name = "rog5-input-boost";
	b->handler.id_table = boost_ids;
	b->handler.private = b;
	ret = input_register_handler(&b->handler);
	if (ret) {
		destroy_workqueue(b->wq);
		return ret;
	}
	platform_set_drvdata(pdev, b);
	dev_info(dev, "cpu-llcc %u kBps, llcc-ddr %u kBps for %u ms after input\n",
		 b->llcc_kbps, b->ddr_kbps, boost_ms);
	return 0;
}

static void boost_remove(struct platform_device *pdev)
{
	struct input_boost *b = platform_get_drvdata(pdev);

	input_unregister_handler(&b->handler);
	cancel_delayed_work_sync(&b->off);
	cancel_work_sync(&b->on);
	destroy_workqueue(b->wq);
	icc_set_bw(b->ddr, 0, 0);
	icc_set_bw(b->llcc, 0, 0);
}

static const struct of_device_id boost_match[] = {
	{ .compatible = "asus,rog5-input-boost" },
	{ }
};
MODULE_DEVICE_TABLE(of, boost_match);

static struct platform_driver boost_driver = {
	.probe = boost_probe,
	.remove = boost_remove,
	.driver = {
		.name = "rog5-input-boost",
		.of_match_table = boost_match,
	},
};
module_platform_driver(boost_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("ROG5 input boost for the CPU memory path (LLCC/DDR)");
