/* SPDX-License-Identifier: GPL-2.0-only */
/* Hardware/devres boundaries for the actual driver and extracted kernel code. */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <pthread.h>
#include "rog5_fts_protocol.h"
#define CHECK(x)                                                      \
	do {                                                          \
		if (!(x)) {                                           \
			fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, \
				__LINE__, #x);                        \
			exit(1);                                      \
		}                                                     \
	} while (0)
typedef uint32_t u32;
typedef int irqreturn_t;
#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))
#define BIT(x) (1U << (x))
#define I2C_M_RD 1
#define I2C_CLIENT_TEN 16
#define I2C_FUNC_I2C 1
#define IRQ_TYPE_EDGE_FALLING 2
#define IRQF_ONESHOT 4
#define IRQF_TRIGGER_FALLING 8
#define IRQ_HANDLED 1
#define GFP_KERNEL 0
#define GPIOD_OUT_HIGH 1
#define GPIOD_OUT_LOW 0
#define BUS_I2C 1
#define INPUT_MT_DIRECT 1
#define INPUT_MT_DROP_UNUSED 2
#define INPUT_MT_POINTER 4
#define INPUT_MT_SEMI_MT 8
#define MT_TOOL_FINGER 0
#define ABS_MT_POSITION_X 0
#define ABS_MT_POSITION_Y 1
#define ABS_MT_TOUCH_MAJOR 2
#define ABS_MT_TRACKING_ID 3
#define ABS_MT_TOOL_TYPE 4
#define ABS_MT_SLOT 5
#define EV_ABS 3
#define IS_ERR(p) ((intptr_t)(p) < 0 && (intptr_t)(p) > -4096)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define dev_err(dev, ...) ((void)(dev))
#define dev_info(dev, ...) ((void)(dev))
#define dev_warn_ratelimited(dev, ...) ((void)(dev))
#define dev_dbg(...) ((void)0)
#define dev_err_probe(dev, err, ...) (err)
#define might_sleep() ((void)0)
#define guard(type) fixture_guard
#define lockdep_assert_held(lock) ((void)(lock))
struct device {
	void *of_node;
};
struct i2c_client {
	struct device dev;
	int addr, flags, irq;
	void *adapter, *data;
};
struct i2c_msg {
	int addr, flags, len;
	u8 *buf;
};
struct gpio_desc {
	const char *name;
	int level;
};
struct regulator {
	const char *name;
	int votes;
	unsigned enable_calls, disable_calls;
};
struct input_mt_slot {
	int id, x, y, area;
	unsigned frame;
};
struct input_mt {
	unsigned frame, flags, slot;
	int num_slots;
	int trkid;
	struct input_mt_slot slots[10];
};
struct input_dev {
	const char *name;
	struct {
		int bustype;
	} id;
	struct input_mt *mt;
	int event_lock;
	bool valid, registered;
	unsigned syncs;
};
struct action {
	void (*fn)(void *);
	void *data;
};
static struct action resources[12];
static unsigned resource_count;
static struct input_dev input;
static struct input_mt mt;
static struct gpio_desc reset = { "reset", 1 }, io_enable = { "io", 0 };
static struct regulator vdd = { .name = "vdd" }, io = { .name = "io" };
static void *allocated;
static const char *fault, *second_fault;
static int faults_left, second_faults_left, short_transfer, reads,
	identity_reads, disables;
static unsigned long jiffies;
static bool irq_during_request;
static bool normal_id = true, irq_available, irq_disabled, irq_inflight,
	    block_read, read_entered, read_continue;
static irqreturn_t (*irq_handler)(int, void *);
static void *irq_data;
static u8 frame_bytes[ROG5_FTS_FRAME_BYTES];
static pthread_mutex_t irq_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t irq_cond = PTHREAD_COND_INITIALIZER;
static int fail(const char *name)
{
	if (fault && !strcmp(name, fault) && faults_left) {
		faults_left--;
		return -EIO;
	}
	if (second_fault && !strcmp(name, second_fault) && second_faults_left) {
		second_faults_left--;
		return -EIO;
	}
	return 0;
}
static int operation(const char *prefix, const char *name, int value)
{
	char key[100];
	snprintf(key, sizeof(key), "%s:%s:%d", prefix, name, value);
	return fail(key);
}
static void push(void (*fn)(void *), void *data)
{
	CHECK(resource_count < ARRAY_SIZE(resources));
	resources[resource_count++] = (struct action){ fn, data };
}
static void unwind(void)
{
	while (resource_count) {
		struct action a = resources[--resource_count];
		a.fn(a.data);
	}
}
static void fixture_guard(void *lock)
{
	(void)lock;
}
static void msleep(unsigned ms)
{
	jiffies += ms;
}
static void usleep_range(unsigned min, unsigned max)
{
	CHECK(min <= max);
	jiffies += min / 1000;
}
#define msecs_to_jiffies(ms) (ms)
#define time_after_eq(a, b) ((long)((a) - (b)) >= 0)
static int gpiod_set_value_cansleep(struct gpio_desc *gpio, int level)
{
	CHECK(!irq_inflight);
	int ret = operation("gpio", gpio->name, level);
	if (!ret)
		gpio->level = level;
	return ret;
}
static int regulator_enable(struct regulator *reg)
{
	/* This boundary fixture preserves votes on error; it is not regulator core. */
	reg->enable_calls++;
	int ret = operation("enable", reg->name, 1);
	if (!ret)
		reg->votes++;
	return ret;
}
static int regulator_disable(struct regulator *reg)
{
	reg->disable_calls++;
	CHECK(!irq_inflight);
	CHECK(reg->votes == 1);
	int ret = operation("disable", reg->name, 0);
	if (!ret)
		reg->votes--;
	return ret;
}
static int i2c_transfer(void *adapter, struct i2c_msg *messages, unsigned count)
{
	(void)adapter;
	CHECK(count == 2);
	CHECK(messages[0].addr == 0x38 && messages[1].addr == 0x38);
	CHECK(messages[0].len == 1 && !messages[0].flags &&
	      messages[1].flags == I2C_M_RD);
	u8 reg = messages[0].buf[0];
	CHECK(reg == 0xa3 || reg == 0x9f || reg == 0x01);
	CHECK(vdd.votes == 1 && io.votes == 1 && reset.level == 0 &&
	      io_enable.level == 1);
	reads++;
	if (reg == 0x01) {
		pthread_mutex_lock(&irq_lock);
		if (block_read) {
			read_entered = true;
			pthread_cond_broadcast(&irq_cond);
			while (!read_continue)
				pthread_cond_wait(&irq_cond, &irq_lock);
		}
		pthread_mutex_unlock(&irq_lock);
		CHECK(messages[1].len == ROG5_FTS_FRAME_BYTES);
		if (short_transfer)
			return short_transfer;
		memcpy(messages[1].buf, frame_bytes, sizeof(frame_bytes));
	} else {
		identity_reads++;
		CHECK(messages[1].len == 1);
		if (fail(reg == 0xa3 ? "read:high" : "read:low"))
			return -EIO;
		messages[1].buf[0] = normal_id ? (reg == 0xa3 ? 0x56 : 0x52) :
						 0;
	}
	return 2;
}
static int __disable_irq_nosync(unsigned irq)
{
	CHECK(irq == 23);
	pthread_mutex_lock(&irq_lock);
	irq_disabled = true;
	disables++;
	pthread_cond_broadcast(&irq_cond);
	pthread_mutex_unlock(&irq_lock);
	return 0;
}
static void synchronize_irq(unsigned irq)
{
	CHECK(irq == 23);
	pthread_mutex_lock(&irq_lock);
	while (irq_inflight)
		pthread_cond_wait(&irq_cond, &irq_lock);
	pthread_mutex_unlock(&irq_lock);
}
static void input_mt_slot(struct input_dev *dev, unsigned slot)
{
	CHECK(dev->valid && dev->registered && slot < 10);
	dev->mt->slot = slot;
}
static int input_mt_get_value(struct input_mt_slot *slot, int axis)
{
	CHECK(axis == ABS_MT_TRACKING_ID);
	return slot->id;
}
static int input_mt_new_trkid(struct input_mt *m)
{
	return ++m->trkid;
}
static bool input_mt_is_active(struct input_mt_slot *slot)
{
	return slot->id >= 0;
}
static bool input_mt_is_used(struct input_mt *m, struct input_mt_slot *slot)
{
	return slot->frame == m->frame;
}
static void input_event(struct input_dev *dev, int type, int axis, int value)
{
	CHECK(dev->valid && dev->registered && type == EV_ABS);
	if (axis == ABS_MT_SLOT) {
		input_mt_slot(dev, value);
		return;
	}
	struct input_mt_slot *slot = &dev->mt->slots[dev->mt->slot];
	if (axis == ABS_MT_TRACKING_ID)
		slot->id = value;
	else if (axis == ABS_MT_POSITION_X)
		slot->x = value;
	else if (axis == ABS_MT_POSITION_Y)
		slot->y = value;
	else if (axis == ABS_MT_TOUCH_MAJOR)
		slot->area = value;
	else
		CHECK(axis == ABS_MT_TOOL_TYPE);
}
#define input_handle_event input_event
static void input_report_abs(struct input_dev *dev, int axis, int value)
{
	input_event(dev, EV_ABS, axis, value);
}
static void input_mt_report_pointer_emulation(struct input_dev *dev, bool count)
{
	(void)dev;
	(void)count;
}
static void input_sync(struct input_dev *dev)
{
	CHECK(dev->valid && dev->registered);
	dev->syncs++;
}
static int device_property_read_u32(struct device *dev, const char *key,
				    u32 *value)
{
	(void)dev;
	*value = strstr(key, "size-x") ? ROG5_FTS_SIZE_X : ROG5_FTS_SIZE_Y;
	return 0;
}
static int irq_get_trigger_type(int irq)
{
	CHECK(irq == 23);
	return IRQ_TYPE_EDGE_FALLING;
}
static int i2c_check_functionality(void *adapter, int function)
{
	(void)adapter;
	return function == I2C_FUNC_I2C;
}
static void i2c_set_clientdata(struct i2c_client *client, void *data)
{
	client->data = data;
}
static void *i2c_get_clientdata(struct i2c_client *client)
{
	return client->data;
}
static void *devm_kzalloc(struct device *dev, size_t bytes, int flags)
{
	(void)dev;
	(void)flags;
	allocated = calloc(1, bytes);
	CHECK(allocated);
	return allocated;
}
static struct regulator *devm_regulator_get_optional(struct device *dev,
						     const char *name)
{
	(void)dev;
	return !strcmp(name, "vdd") ? &vdd : &io;
}
static struct gpio_desc *devm_gpiod_get(struct device *dev, const char *name,
					int flags)
{
	(void)dev;
	(void)flags;
	return !strcmp(name, "reset") ? &reset : &io_enable;
}
static const char *dev_name(struct device *dev)
{
	(void)dev;
	return "fixture";
}
static int devm_add_action_or_reset(struct device *dev, void (*action)(void *),
				    void *data)
{
	(void)dev;
	int ret = fail(resource_count ? "stop-action" : "power-action");
	if (ret) {
		action(data);
		return ret;
	}
	push(action, data);
	return 0;
}
static void input_free(void *data)
{
	struct input_dev *dev = data;
	CHECK(!irq_available && !dev->registered);
	dev->valid = false;
}
static void input_unregister(void *data)
{
	struct input_dev *dev = data;
	CHECK(!irq_available);
	dev->registered = false;
}
static struct input_dev *devm_input_allocate_device(struct device *dev)
{
	(void)dev;
	if (fail("input-allocate"))
		return NULL;
	input.valid = true;
	push(input_free, &input);
	return &input;
}
static void input_set_abs_params(struct input_dev *dev, int axis, int min,
				 int max, int fuzz, int flat)
{
	(void)dev;
	CHECK(min == 0 && fuzz == 0 && flat == 0);
	CHECK(max == (axis == ABS_MT_POSITION_X ? ROG5_FTS_SIZE_X - 1 :
		      axis == ABS_MT_POSITION_Y ? ROG5_FTS_SIZE_Y - 1 :
						  15));
}
static int input_mt_init_slots(struct input_dev *dev, unsigned count,
			       unsigned flags)
{
	CHECK(count == 10 && flags == (INPUT_MT_DIRECT | INPUT_MT_DROP_UNUSED));
	if (fail("input-slots"))
		return -ENOMEM;
	dev->mt = &mt;
	mt.num_slots = count;
	mt.flags = flags;
	mt.frame = 1;
	for (unsigned i = 0; i < count; i++)
		mt.slots[i].id = -1;
	return 0;
}
static int input_register_device(struct input_dev *dev)
{
	if (fail("input-register"))
		return -EIO;
	dev->registered = true;
	push(input_unregister, dev);
	return 0;
}
static void irq_free(void *data)
{
	(void)data;
	CHECK(irq_disabled && !irq_inflight);
	irq_available = false;
}
static int devm_request_threaded_irq(struct device *dev, int irq, void *primary,
				     irqreturn_t (*handler)(int, void *),
				     int flags, const char *name, void *data)
{
	(void)dev;
	(void)name;
	CHECK(irq == 23 && !primary &&
	      flags == (IRQF_ONESHOT | IRQF_TRIGGER_FALLING));
	if (fail("irq-request"))
		return -EIO;
	irq_available = true;
	irq_handler = handler;
	irq_data = data;
	push(irq_free, data);
	if (irq_during_request)
		CHECK(handler(irq, data) == IRQ_HANDLED);
	return 0;
}
