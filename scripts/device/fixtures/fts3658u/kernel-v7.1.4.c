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
void disable_irq(unsigned int irq)
{
	might_sleep();
	if (!__disable_irq_nosync(irq))
		synchronize_irq(irq);
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

