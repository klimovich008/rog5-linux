// SPDX-License-Identifier: GPL-2.0
/* Awinic AW8697 LRA haptic driver, continuous (CONT) mode only.
 *
 * The ROG Phone 5 vibration motor is an LRA behind an AW8697 on QUP SE6 I2C
 * (0x5a, chip ID 0x97). The chip drives the motor at its resonance by itself
 * in CONT mode (zero-cross F0 tracking from a 150 Hz preset), so no waveform
 * RAM or firmware is needed. It is exposed as an input force-feedback device
 * (FF_RUMBLE): each effect runs CONT mode for the effect length, with the
 * strongest requested magnitude scaling the drive level.
 *
 * Register values and the init/CONT sequence follow the stock ASUS driver
 * (drivers/motor/aw8697_haptic, ZS673KS DT: vib_* properties).
 */
#include <linux/delay.h>
#include <linux/i2c.h>
#include <linux/input.h>
#include <linux/module.h>
#include <linux/mod_devicetable.h>
#include <linux/of.h>
#include <linux/workqueue.h>

#define REG_ID		0x00
#define REG_SYSINT	0x02
#define REG_SYSINTM	0x03
#define REG_SYSCTRL	0x04
#define REG_GO		0x05
#define REG_DATCTRL	0x2b
#define REG_PWMPRC	0x2d
#define REG_PWMDBG	0x2e
#define REG_BSTDBG1	0x31
#define REG_BSTDBG2	0x32
#define REG_BSTDBG3	0x33
#define REG_BSTCFG	0x34
#define REG_ANADBG	0x35
#define REG_PRLVL	0x3e
#define REG_GLB_STATE	0x46
#define REG_BST_AUTO	0x47
#define REG_CONT_CTRL	0x48
#define REG_F_PRE_H	0x49
#define REG_F_PRE_L	0x4a
#define REG_TD_H	0x4b
#define REG_TD_L	0x4c
#define REG_TSET	0x4d
#define REG_R_SPARE	0x5d
#define REG_DETCTRL	0x5f
#define REG_ADCTEST	0x66
#define REG_ZC_THRSH_H	0x72
#define REG_ZC_THRSH_L	0x73
#define REG_BEMF_VTHH_H	0x74
#define REG_BEMF_VTHH_L	0x75
#define REG_BEMF_VTHL_H	0x76
#define REG_BEMF_VTHL_L	0x77
#define REG_BEMF_NUM	0x78
#define REG_TIME_NZC	0x7a
#define REG_DRV_LVL	0x7b
#define REG_DRV_LVL_OV	0x7c

#define CHIP_ID		0x97

/* ZS673KS DT values (vib_* properties) */
#define F0_PRE		1500	/* 150.0 Hz */
#define F0_COEFF	260
#define CONT_DRV_LVL	100
#define CONT_DRV_LVL_OV	100
#define CONT_TD		0x006c
#define CONT_ZC_THR	0x0ff1
#define CONT_NUM_BRK	3
#define TSET		0x12
#define R_SPARE		0x68
static const u8 bstdbg[3] = { 0x30, 0xeb, 0xd4 };
static const u8 bemf[4] = { 0x10, 0x08, 0x03, 0xf8 };

struct aw8697 {
	struct i2c_client *i2c;
	struct input_dev *input;
	struct work_struct work;
	struct mutex lock;
	u16 magnitude;		/* latest requested strength, 0 = stop */
	bool playing;
};

static int wr(struct aw8697 *aw, u8 reg, u8 val)
{
	return i2c_smbus_write_byte_data(aw->i2c, reg, val);
}

/* the stock driver's write_bits: keep the bits in mask, OR in val */
static int wr_bits(struct aw8697 *aw, u8 reg, u8 mask, u8 val)
{
	int old = i2c_smbus_read_byte_data(aw->i2c, reg);

	if (old < 0)
		return old;
	return wr(aw, reg, (old & mask) | val);
}

static void standby(struct aw8697 *aw)
{
	wr_bits(aw, REG_SYSINTM, (u8)~(1 << 5), 1 << 5);	/* UVLO irq off */
	wr_bits(aw, REG_SYSCTRL, (u8)~(1 << 0), 1 << 0);	/* standby */
}

static void active(struct aw8697 *aw)
{
	wr_bits(aw, REG_SYSCTRL, (u8)~(1 << 0), 0);		/* active */
	i2c_smbus_read_byte_data(aw->i2c, REG_SYSINT);		/* clear */
	wr_bits(aw, REG_SYSINTM, (u8)~(1 << 5), 0);		/* UVLO irq on */
}

static void stop(struct aw8697 *aw)
{
	int i, st;

	wr_bits(aw, REG_GO, (u8)~(1 << 0), 0);
	for (i = 0; i < 100; i++) {
		st = i2c_smbus_read_byte_data(aw->i2c, REG_GLB_STATE);
		if (st < 0 || (st & 0x0f) == 0)
			break;
		usleep_range(2000, 2500);
	}
	standby(aw);
	wr_bits(aw, REG_SYSCTRL, (u8)~(1 << 1), 1 << 1);	/* boost mode */
}

static void play_cont(struct aw8697 *aw, u8 drv_lvl)
{
	u32 f0_reg = 1000000000 / (F0_PRE * F0_COEFF);

	/* CONT play mode, boost bypass, active */
	wr_bits(aw, REG_SYSCTRL, (u8)~(3 << 2), 2 << 2);
	wr_bits(aw, REG_SYSCTRL, (u8)~(1 << 1), 0);
	active(aw);
	wr(aw, REG_F_PRE_H, f0_reg >> 8);
	wr(aw, REG_F_PRE_L, f0_reg & 0xff);
	/* 1 kHz low-pass on */
	wr_bits(aw, REG_DATCTRL, (u8)~(1 << 6), 3 << 6);
	wr_bits(aw, REG_DATCTRL, (u8)~(1 << 5), 1 << 5);
	/* zero-cross detect, 1-period wait, run until GO clears, closed loop,
	 * no F0 detect, no open-to-closed switch, auto brake */
	wr_bits(aw, REG_CONT_CTRL, (u8)~(1 << 7), 1 << 7);
	wr_bits(aw, REG_CONT_CTRL, (u8)~(3 << 5), 0);
	wr_bits(aw, REG_CONT_CTRL, (u8)~(1 << 4), 0);
	wr_bits(aw, REG_CONT_CTRL, (u8)~(1 << 3), 1 << 3);
	wr_bits(aw, REG_CONT_CTRL, (u8)~(1 << 2), 0);
	wr_bits(aw, REG_CONT_CTRL, (u8)~(1 << 1), 0);
	wr_bits(aw, REG_CONT_CTRL, (u8)~(1 << 0), 1 << 0);
	wr(aw, REG_TD_H, CONT_TD >> 8);
	wr(aw, REG_TD_L, CONT_TD & 0xff);
	wr(aw, REG_TSET, TSET);
	wr(aw, REG_ZC_THRSH_H, CONT_ZC_THR >> 8);
	wr(aw, REG_ZC_THRSH_L, CONT_ZC_THR & 0xff);
	wr_bits(aw, REG_BEMF_NUM, (u8)~15, CONT_NUM_BRK);
	wr(aw, REG_TIME_NZC, 0x23);
	wr(aw, REG_DRV_LVL, drv_lvl);
	wr(aw, REG_DRV_LVL_OV, CONT_DRV_LVL_OV);
	wr_bits(aw, REG_GO, (u8)~(1 << 0), 1 << 0);
}

static void play_work(struct work_struct *work)
{
	struct aw8697 *aw = container_of(work, struct aw8697, work);
	u16 magnitude;

	mutex_lock(&aw->lock);
	magnitude = READ_ONCE(aw->magnitude);
	if (aw->playing)
		stop(aw);
	aw->playing = false;
	if (magnitude) {
		/* scale the stock drive level; weak requests still move the mass */
		u8 lvl = max_t(u32, 30, CONT_DRV_LVL * magnitude / 0xffff);

		play_cont(aw, lvl);
		aw->playing = true;
	}
	mutex_unlock(&aw->lock);
}

static int aw8697_play(struct input_dev *dev, void *data, struct ff_effect *effect)
{
	struct aw8697 *aw = input_get_drvdata(dev);

	WRITE_ONCE(aw->magnitude, max(effect->u.rumble.strong_magnitude,
				      effect->u.rumble.weak_magnitude));
	schedule_work(&aw->work);
	return 0;
}

static void aw8697_close(struct input_dev *dev)
{
	struct aw8697 *aw = input_get_drvdata(dev);

	WRITE_ONCE(aw->magnitude, 0);
	cancel_work_sync(&aw->work);
	play_work(&aw->work);
}

static void hw_init(struct aw8697 *aw)
{
	int i;

	standby(aw);
	wr_bits(aw, REG_PWMDBG, (u8)~(3 << 5), 2 << 5);		/* 24 kHz PWM */
	wr(aw, REG_BSTDBG1, bstdbg[0]);
	wr(aw, REG_BSTDBG2, bstdbg[1]);
	wr(aw, REG_BSTDBG3, bstdbg[2]);
	wr(aw, REG_TSET, TSET);
	wr(aw, REG_R_SPARE, R_SPARE);
	wr_bits(aw, REG_ANADBG, (u8)~(3 << 2), 3 << 2);		/* 4.65 A IOC */
	wr_bits(aw, REG_BSTCFG, (u8)~7, 5);			/* 3.5 A peak */
	/* motor protection off */
	wr_bits(aw, REG_DETCTRL, (u8)~(1 << 5), 1 << 5);
	wr_bits(aw, REG_PWMPRC, (u8)~(1 << 7), 0);
	wr_bits(aw, REG_PRLVL, (u8)~(1 << 7), 0);
	wr_bits(aw, REG_BST_AUTO, (u8)~(1 << 2), 0);		/* manual boost */
	/* offset calibration */
	wr_bits(aw, REG_SYSCTRL, (u8)~(1 << 5), 1 << 5);
	wr_bits(aw, REG_DETCTRL, (u8)~(1 << 0), 1 << 0);
	for (i = 0; i < 2000; i++) {
		int v = i2c_smbus_read_byte_data(aw->i2c, REG_DETCTRL);

		if (v < 0 || !(v & 1))
			break;
	}
	wr_bits(aw, REG_SYSCTRL, (u8)~(1 << 5), 0);
	wr_bits(aw, REG_ADCTEST, (u8)~(1 << 6), 1 << 6);	/* HW VBAT comp */
	wr(aw, REG_BEMF_VTHH_H, bemf[0]);
	wr(aw, REG_BEMF_VTHH_L, bemf[1]);
	wr(aw, REG_BEMF_VTHL_H, bemf[2]);
	wr(aw, REG_BEMF_VTHL_L, bemf[3]);
}

static int aw8697_probe(struct i2c_client *i2c)
{
	struct device *dev = &i2c->dev;
	struct aw8697 *aw;
	int id, ret;

	id = i2c_smbus_read_byte_data(i2c, REG_ID);
	if (id < 0)
		return dev_err_probe(dev, id, "no response\n");
	if (id != CHIP_ID)
		return dev_err_probe(dev, -ENODEV, "chip id %#x, not an AW8697\n", id);

	aw = devm_kzalloc(dev, sizeof(*aw), GFP_KERNEL);
	if (!aw)
		return -ENOMEM;
	aw->i2c = i2c;
	mutex_init(&aw->lock);
	INIT_WORK(&aw->work, play_work);
	hw_init(aw);

	aw->input = devm_input_allocate_device(dev);
	if (!aw->input)
		return -ENOMEM;
	aw->input->name = "aw8697-haptics";
	aw->input->id.bustype = BUS_I2C;
	aw->input->close = aw8697_close;
	input_set_drvdata(aw->input, aw);
	input_set_capability(aw->input, EV_FF, FF_RUMBLE);
	ret = input_ff_create_memless(aw->input, NULL, aw8697_play);
	if (ret)
		return ret;
	ret = input_register_device(aw->input);
	if (ret)
		return ret;
	i2c_set_clientdata(i2c, aw);
	dev_info(dev, "AW8697 haptics (CONT mode, F0 preset %u.%u Hz)\n", F0_PRE / 10, F0_PRE % 10);
	return 0;
}

static void aw8697_remove(struct i2c_client *i2c)
{
	struct aw8697 *aw = i2c_get_clientdata(i2c);

	cancel_work_sync(&aw->work);
	mutex_lock(&aw->lock);
	if (aw->playing)
		stop(aw);
	mutex_unlock(&aw->lock);
}

static const struct of_device_id aw8697_of_match[] = {
	{ .compatible = "awinic,aw8697" },
	{ }
};
MODULE_DEVICE_TABLE(of, aw8697_of_match);

static const struct i2c_device_id aw8697_id[] = {
	{ "aw8697" },
	{ }
};
MODULE_DEVICE_TABLE(i2c, aw8697_id);

static struct i2c_driver aw8697_driver = {
	.id_table = aw8697_id,
	.driver = {
		.name = "rog5-aw8697",
		.of_match_table = aw8697_of_match,
	},
	.probe = aw8697_probe,
	.remove = aw8697_remove,
};
module_i2c_driver(aw8697_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Awinic AW8697 LRA haptics (CONT mode) for the ROG Phone 5");
