/* SPDX-License-Identifier: GPL-2.0-only */
/* Explicit generic infrastructure substitutions, only for serial host tests.
 * Existing GPIO/I2C/regulator/devres/IRQ substitutes are reused unchanged.
 * Kernel spinlock guard/lockdep operations remain no-ops. This is NOT a
 * concurrency, RCU, timer, registration, evdev, or libinput qualification. */
static void __change_bit(unsigned bit, unsigned long *bits)
{
	bits[bit / (8 * sizeof(*bits))] ^= 1UL << (bit % (8 * sizeof(*bits)));
}
/* One lexical scope, with break leaving it (needed for the grab branch).
 * No kernel cleanup.h or RCU implementation is claimed. */
#define scoped_guard(...) for (bool host_once = true; host_once; host_once = false)
#define rcu_dereference(p) (p)
/* Immutable, ordered, bounded host array instead of intrusive RCU lists.
 * The production body still selects open handles and invokes handle_events.
 * The supplied cases use one ungrabbed handle, never concurrent mutation. */
#define list_for_each_entry_rcu(pos, head, member)                       \
	for (unsigned host_i = 0; host_i < (head)->count &&                \
	     (((pos) = (head)->items[host_i]), true); host_i++)
static void mod_timer(struct timer_list *t, unsigned long expires)
{
	CHECK(!"autorepeat timer outside fixture scope");
}
/* Namespace the kernel timer API away from libc timer_delete(timer_t). */
#define timer_delete host_timer_delete
static void host_timer_delete(struct timer_list *t)
{
	CHECK(!"autorepeat timer outside fixture scope");
}
static ktime_t ktime_set(long seconds, unsigned long ns)
{
	CHECK(seconds == 0 && ns == 0); /* Only invalidation, not clock generation. */
	return 0;
}
static void add_input_randomness(unsigned type, unsigned code, int value)
{
	/* Entropy collection excluded. */
}
static void input_alloc_absinfo(struct input_dev *dev)
{
	CHECK(dev->absinfo == dev->axes); /* Fixed, zeroed allocation, not slab. */
}

#define HOST_BATCHES 64
struct delivered_batch {
	unsigned count;
	struct input_value values[HOST_VAL_CAPACITY];
};
static struct delivered_batch delivered[HOST_BATCHES];
static unsigned delivered_count;
static struct input_handler observer;
static struct input_handle observer_handle;

/* The ONLY producer of the delivered-event log. No assertions about contents
 * here: expected tuples and packet boundaries belong to the semantic cases.
 * Copy now because input.c reuses dev->vals; return the production API count. */
static unsigned int observe_events(struct input_handle *handle,
				   struct input_value *vals, unsigned int count)
{
	CHECK(handle == &observer_handle && handle->dev == &input);
	CHECK(input.valid && input.registered);
	CHECK(count <= input.max_vals && count <= HOST_VAL_CAPACITY);
	CHECK(delivered_count < HOST_BATCHES);
	struct delivered_batch *batch = &delivered[delivered_count++];
	batch->count = count;
	memcpy(batch->values, vals, count * sizeof(*vals));
	return count;
}
static void fixture_input_allocate(struct input_dev *dev)
{
	/* Deliberately NOT input_allocate_device()/input_device_tune_vals().
	 * 128 values bound normal ten-contact cases without a capacity flush.
	 * The capacity case explicitly injects max_vals=8, with the same backing. */
	dev->vals = dev->storage;
	dev->max_vals = HOST_VAL_CAPACITY;
	dev->num_vals = 0;
	delivered_count = 0;
	memset(delivered, 0, sizeof(delivered));
	memset(&observer, 0, sizeof(observer));
	memset(&observer_handle, 0, sizeof(observer_handle));
}
static void fixture_input_register(struct input_dev *dev)
{
	/* input_register_device's required EV_SYN setup, but no device core.
	 * No EV_REP support is set: the exact autorepeat helpers never arm timers.
	 * The actual handle callback selector is run; registration/open and list
	 * insertion themselves are controlled, serialized fixture boundaries. */
	__set_bit(EV_SYN, dev->evbit);
	CHECK(!test_bit(EV_REP, dev->evbit));
	observer.events = observe_events;
	observer_handle.dev = dev;
	observer_handle.handler = &observer;
	observer_handle.open = 1;
	input_handle_setup_event_handler(&observer_handle);
	CHECK(observer_handle.handle_events == observe_events);
	dev->h_list.items[0] = &observer_handle;
	dev->h_list.count = 1;
}
