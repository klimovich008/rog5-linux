// SPDX-License-Identifier: GPL-2.0
/* Exact extracts from Linux7.1.4, pinned base7a5cef0db4795d9d453a12e0f61b5b7634fc4d40. */
/*
 * Copyright (C) 1992, 1998-2006 Linus Torvalds, Ingo Molnar
 * Copyright (C) 2005-2006 Thomas Gleixner
 *
 * This file contains driver APIs to the irq subsystem.
 */
/*
 * Input Multitouch Library
 *
 * Copyright (c) 2008-2010 Henrik Rydberg
 */
static inline void input_mt_set_value(struct input_mt_slot *slot,
				      unsigned code, int value)
{
	slot->abs[code - ABS_MT_FIRST] = value;
}

static inline int input_mt_get_value(const struct input_mt_slot *slot,
				     unsigned code)
{
	return slot->abs[code - ABS_MT_FIRST];
}

static inline bool input_mt_is_active(const struct input_mt_slot *slot)
{
	return input_mt_get_value(slot, ABS_MT_TRACKING_ID) >= 0;
}

static inline bool input_mt_is_used(const struct input_mt *mt,
				    const struct input_mt_slot *slot)
{
	return slot->frame == mt->frame;
}

static inline int input_mt_new_trkid(struct input_mt *mt)
{
	return mt->trkid++ & TRKID_MAX;
}

static inline void input_mt_slot(struct input_dev *dev, int slot)
{
	input_event(dev, EV_ABS, ABS_MT_SLOT, slot);
}

void disable_irq(unsigned int irq)
{
	might_sleep();
	if (!__disable_irq_nosync(irq))
		synchronize_irq(irq);
}

static void copy_abs(struct input_dev *dev, unsigned int dst, unsigned int src)
{
	if (dev->absinfo && test_bit(src, dev->absbit)) {
		dev->absinfo[dst] = dev->absinfo[src];
		dev->absinfo[dst].fuzz = 0;
		__set_bit(dst, dev->absbit);
	}
}

/* Preserve the exact kernel's signed slot count comparison. The kernel does
 * not enable -Wsign-compare; keep this host suppression local to that extract. */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wsign-compare"
int input_mt_init_slots(struct input_dev *dev, unsigned int num_slots,
			unsigned int flags)
{
	if (!num_slots)
		return 0;

	if (dev->mt)
		return dev->mt->num_slots != num_slots ? -EINVAL : 0;

	/* Arbitrary limit for avoiding too large memory allocation. */
	if (num_slots > 1024)
		return -EINVAL;

	struct input_mt *mt __free(kfree) =
			kzalloc_flex(*mt, slots, num_slots);
	if (!mt)
		return -ENOMEM;

	mt->num_slots = num_slots;
	mt->flags = flags;
	input_set_abs_params(dev, ABS_MT_SLOT, 0, num_slots - 1, 0, 0);
	input_set_abs_params(dev, ABS_MT_TRACKING_ID, 0, TRKID_MAX, 0, 0);

	if (flags & (INPUT_MT_POINTER | INPUT_MT_DIRECT)) {
		__set_bit(EV_KEY, dev->evbit);
		__set_bit(BTN_TOUCH, dev->keybit);

		copy_abs(dev, ABS_X, ABS_MT_POSITION_X);
		copy_abs(dev, ABS_Y, ABS_MT_POSITION_Y);
		copy_abs(dev, ABS_PRESSURE, ABS_MT_PRESSURE);
	}
	if (flags & INPUT_MT_POINTER) {
		__set_bit(BTN_TOOL_FINGER, dev->keybit);
		__set_bit(BTN_TOOL_DOUBLETAP, dev->keybit);
		if (num_slots >= 3)
			__set_bit(BTN_TOOL_TRIPLETAP, dev->keybit);
		if (num_slots >= 4)
			__set_bit(BTN_TOOL_QUADTAP, dev->keybit);
		if (num_slots >= 5)
			__set_bit(BTN_TOOL_QUINTTAP, dev->keybit);
		__set_bit(INPUT_PROP_POINTER, dev->propbit);
	}
	if (flags & INPUT_MT_DIRECT)
		__set_bit(INPUT_PROP_DIRECT, dev->propbit);
	if (flags & INPUT_MT_SEMI_MT)
		__set_bit(INPUT_PROP_SEMI_MT, dev->propbit);
	if (flags & INPUT_MT_TRACK) {
		unsigned int n2 = num_slots * num_slots;
		mt->red = kzalloc_objs(*mt->red, n2);
		if (!mt->red)
			return -ENOMEM;
	}

	/* Mark slots as 'inactive' */
	for (unsigned int i = 0; i < num_slots; i++)
		input_mt_set_value(&mt->slots[i], ABS_MT_TRACKING_ID, -1);

	/* Mark slots as 'unused' */
	mt->frame = 1;

	dev->mt = no_free_ptr(mt);
	return 0;
}
#pragma GCC diagnostic pop

void input_mt_report_finger_count(struct input_dev *dev, int count)
{
	input_event(dev, EV_KEY, BTN_TOOL_FINGER, count == 1);
	input_event(dev, EV_KEY, BTN_TOOL_DOUBLETAP, count == 2);
	input_event(dev, EV_KEY, BTN_TOOL_TRIPLETAP, count == 3);
	input_event(dev, EV_KEY, BTN_TOOL_QUADTAP, count == 4);
	input_event(dev, EV_KEY, BTN_TOOL_QUINTTAP, count == 5);
}

void input_mt_report_pointer_emulation(struct input_dev *dev, bool use_count)
{
	struct input_mt *mt = dev->mt;
	struct input_mt_slot *oldest;
	int oldid, count, i;
	int p, reported_p = 0;

	if (!mt)
		return;

	oldest = NULL;
	oldid = mt->trkid;
	count = 0;

	for (i = 0; i < mt->num_slots; ++i) {
		struct input_mt_slot *ps = &mt->slots[i];
		int id = input_mt_get_value(ps, ABS_MT_TRACKING_ID);

		if (id < 0)
			continue;
		if ((id - oldid) & TRKID_SGN) {
			oldest = ps;
			oldid = id;
		}
		if (test_bit(ABS_MT_PRESSURE, dev->absbit)) {
			p = input_mt_get_value(ps, ABS_MT_PRESSURE);
			if (mt->flags & INPUT_MT_TOTAL_FORCE)
				reported_p += p;
			else if (oldid == id)
				reported_p = p;
		}
		count++;
	}

	input_event(dev, EV_KEY, BTN_TOUCH, count > 0);

	if (use_count) {
		if (count == 0 &&
		    !test_bit(ABS_MT_DISTANCE, dev->absbit) &&
		    test_bit(ABS_DISTANCE, dev->absbit) &&
		    input_abs_get_val(dev, ABS_DISTANCE) != 0) {
			/*
			 * Force reporting BTN_TOOL_FINGER for devices that
			 * only report general hover (and not per-contact
			 * distance) when contact is in proximity but not
			 * on the surface.
			 */
			count = 1;
		}

		input_mt_report_finger_count(dev, count);
	}

	if (oldest) {
		int x = input_mt_get_value(oldest, ABS_MT_POSITION_X);
		int y = input_mt_get_value(oldest, ABS_MT_POSITION_Y);

		input_event(dev, EV_ABS, ABS_X, x);
		input_event(dev, EV_ABS, ABS_Y, y);

		if (test_bit(ABS_MT_PRESSURE, dev->absbit))
			input_event(dev, EV_ABS, ABS_PRESSURE, reported_p);
	} else {
		if (test_bit(ABS_MT_PRESSURE, dev->absbit))
			input_event(dev, EV_ABS, ABS_PRESSURE, 0);
	}
}

bool input_mt_report_slot_state(struct input_dev *dev,
				unsigned int tool_type, bool active)
{
	struct input_mt *mt = dev->mt;
	struct input_mt_slot *slot;
	int id;

	if (!mt)
		return false;

	slot = &mt->slots[mt->slot];
	slot->frame = mt->frame;

	if (!active) {
		input_event(dev, EV_ABS, ABS_MT_TRACKING_ID, -1);
		return false;
	}

	id = input_mt_get_value(slot, ABS_MT_TRACKING_ID);
	if (id < 0)
		id = input_mt_new_trkid(mt);

	input_event(dev, EV_ABS, ABS_MT_TRACKING_ID, id);
	input_event(dev, EV_ABS, ABS_MT_TOOL_TYPE, tool_type);

	return true;
}

static void __input_mt_drop_unused(struct input_dev *dev, struct input_mt *mt)
{
	int i;

	lockdep_assert_held(&dev->event_lock);

	for (i = 0; i < mt->num_slots; i++) {
		if (input_mt_is_active(&mt->slots[i]) &&
		    !input_mt_is_used(mt, &mt->slots[i])) {
			input_handle_event(dev, EV_ABS, ABS_MT_SLOT, i);
			input_handle_event(dev, EV_ABS, ABS_MT_TRACKING_ID, -1);
		}
	}
}

void input_mt_sync_frame(struct input_dev *dev)
{
	struct input_mt *mt = dev->mt;
	bool use_count = false;

	if (!mt)
		return;

	if (mt->flags & INPUT_MT_DROP_UNUSED) {
		guard(spinlock_irqsave)(&dev->event_lock);
		__input_mt_drop_unused(dev, mt);
	}

	if ((mt->flags & INPUT_MT_POINTER) && !(mt->flags & INPUT_MT_SEMI_MT))
		use_count = true;

	input_mt_report_pointer_emulation(dev, use_count);

	mt->frame++;
}

