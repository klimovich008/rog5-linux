/* SPDX-License-Identifier: GPL-2.0-only */
/* Oracles contain input tuples and consumer-visible state, not copies of the
 * kernel disposition/slot/flush algorithms. setup/start/put_point/invoke_irq/
 * finish are reused from the unchanged lifecycle cases, whose main is renamed.
 * NONE of that file's 27 historical cases is executed by this main. */
#define A(code, value) { EV_ABS, (code), (value) }
#define K(value) { EV_KEY, BTN_TOUCH, (value) }
#define S(value) { EV_SYN, SYN_REPORT, (value) }
#define VALUE(type, code, value) ((struct input_value){ (type), (code), (value) })

static struct {
	int slot, id[10], x[10], y[10], major[10], touch, pointer_x, pointer_y;
} consumer;

/* Decode only the delivered stream. In particular, NEVER label a received
 * value with input.mt->slot: it can already refer to a later staged slot. */
static void consume(const struct delivered_batch *batch)
{
	for (unsigned i = 0; i < batch->count; i++) {
		const struct input_value *v = &batch->values[i];
		if (v->type == EV_SYN) {
			CHECK(v->code == SYN_REPORT && i + 1 == batch->count);
			continue;
		}
		if (v->type == EV_KEY) {
			CHECK(v->code == BTN_TOUCH);
			consumer.touch = v->value;
			continue;
		}
		CHECK(v->type == EV_ABS);
		switch (v->code) {
		case ABS_MT_SLOT:
			CHECK(v->value >= 0 && v->value < 10);
			consumer.slot = v->value;
			break;
		case ABS_MT_TRACKING_ID: consumer.id[consumer.slot] = v->value; break;
		case ABS_MT_POSITION_X: consumer.x[consumer.slot] = v->value; break;
		case ABS_MT_POSITION_Y: consumer.y[consumer.slot] = v->value; break;
		case ABS_MT_TOUCH_MAJOR: consumer.major[consumer.slot] = v->value; break;
		case ABS_X: consumer.pointer_x = v->value; break;
		case ABS_Y: consumer.pointer_y = v->value; break;
		default: CHECK(!"unadvertised/unexpected delivered axis");
		}
	}
}
static unsigned consumer_active(void)
{
	unsigned mask = 0;
	for (unsigned i = 0; i < 10; i++)
		if (consumer.id[i] >= 0)
			mask |= BIT(i);
	return mask;
}
static void expect_batch(unsigned index, const struct input_value *expected, unsigned count)
{
	CHECK(index < delivered_count);
	const struct delivered_batch *batch = &delivered[index];
	if (batch->count != count) {
		fprintf(stderr, "FAIL batch %u count: received=%u expected=%u\n",
			index, batch->count, count);
		exit(1);
	}
	for (unsigned i = 0; i < count; i++) {
		const struct input_value *v = &batch->values[i], *e = &expected[i];
		if (v->type != e->type || v->code != e->code || v->value != e->value) {
			fprintf(stderr, "FAIL batch %u event %u: received=(%u,%u,%d) expected=(%u,%u,%d)\n",
				index, i, v->type, v->code, v->value, e->type, e->code, e->value);
			exit(1);
		}
	}
	consume(batch);
}
#define ONE(...) do {                                                   \
	const struct input_value expected[] = { __VA_ARGS__ };            \
	CHECK(delivered_count == 1);                                     \
	expect_batch(0, expected, ARRAY_SIZE(expected));                  \
} while (0)
static void none(void) { CHECK(delivered_count == 0); }
static void clear_delivery(void)
{
	CHECK(input.num_vals == 0); /* Do not hide pending core events. */
	delivered_count = 0;
}
static void next_frame(unsigned count)
{
	clear_delivery();
	memset(frame_bytes, 0xff, sizeof(frame_bytes));
	frame_bytes[0] = 0;
	frame_bytes[1] = count;
}
static void begin_delivery(void)
{
	setup();
	start();
	memset(&consumer, 0, sizeof(consumer));
	for (unsigned i = 0; i < 10; i++)
		consumer.id[i] = -1;
	none();
	CHECK(input.max_vals == HOST_VAL_CAPACITY && input.num_vals == 0);
	CHECK(test_bit(EV_SYN, input.evbit));
	CHECK(test_bit(INPUT_PROP_DIRECT, input.propbit));
	CHECK(!test_bit(ABS_MT_TOOL_TYPE, input.absbit));
	CHECK(!test_bit(ABS_PRESSURE, input.absbit));
	CHECK(!test_bit(BTN_TOOL_FINGER, input.keybit));
}
static void seed_one(int id)
{
	next_frame(1);
	put_point(0, 7, 0, 100, 200);
	invoke_irq();
	ONE(A(ABS_MT_SLOT, 7), A(ABS_MT_TRACKING_ID, id),
	    A(ABS_MT_POSITION_X, 100), A(ABS_MT_POSITION_Y, 200),
	    A(ABS_MT_TOUCH_MAJOR, 10), K(1), A(ABS_X, 100), A(ABS_Y, 200), S(0));
	CHECK(consumer_active() == BIT(7) && consumer.id[7] == id);
}
static void seed_two(void)
{
	next_frame(2);
	put_point(0, 7, 0, 100, 200);
	put_point(1, 1, 0, 300, 400);
	invoke_irq();
	ONE(A(ABS_MT_SLOT, 7), A(ABS_MT_TRACKING_ID, 0),
	    A(ABS_MT_POSITION_X, 100), A(ABS_MT_POSITION_Y, 200), A(ABS_MT_TOUCH_MAJOR, 10),
	    A(ABS_MT_SLOT, 1), A(ABS_MT_TRACKING_ID, 1),
	    A(ABS_MT_POSITION_X, 300), A(ABS_MT_POSITION_Y, 400), A(ABS_MT_TOUCH_MAJOR, 10),
	    K(1), A(ABS_X, 100), A(ABS_Y, 200), S(0));
	CHECK(consumer_active() == (BIT(1) | BIT(7)));
	CHECK(consumer.pointer_x == 100 && consumer.pointer_y == 200);
}
static void expect_release_two(void)
{
	/* The last delivered slot was 1. Release visits 0..9, but only two
	 * contacts change: no invented slot0/slot9 packets or ten fake ups. */
	ONE(A(ABS_MT_TRACKING_ID, -1), A(ABS_MT_SLOT, 7),
	    A(ABS_MT_TRACKING_ID, -1), K(0), S(0));
	CHECK(consumer_active() == 0 && consumer.touch == 0);
}
static void down_move_up(void)
{
	begin_delivery();
	seed_one(0);
	next_frame(1);
	put_point(0, 7, 2, 150, 210);
	invoke_irq();
	ONE(A(ABS_MT_POSITION_X, 150), A(ABS_MT_POSITION_Y, 210),
	    A(ABS_X, 150), A(ABS_Y, 210), S(0));
	CHECK(consumer.id[7] == 0 && consumer.touch == 1);
	CHECK(consumer.x[7] == 150 && consumer.y[7] == 210);
	next_frame(0);
	put_point(0, 7, 1, 65535, 65535); /* UP coordinates must not escape. */
	invoke_irq();
	ONE(A(ABS_MT_TRACKING_ID, -1), K(0), S(0));
	CHECK(consumer_active() == 0 && consumer.pointer_x == 150);
	finish();
}
static void unchanged_empty(void)
{
	begin_delivery();
	next_frame(0);
	invoke_irq();
	none();
	for (unsigned i = 0; i < 3; i++)
		input_sync(&input);
	none();
	seed_one(0);
	for (unsigned i = 0; i < 3; i++) {
		next_frame(1);
		put_point(0, 7, 2, 100, 200);
		invoke_irq();
		none(); /* Driver requested SYN, tracking ID, axes, BTN_TOUCH. */
		CHECK(consumer.id[7] == 0 && consumer.touch == 1);
	}
	next_frame(0);
	invoke_irq();
	ONE(A(ABS_MT_TRACKING_ID, -1), K(0), S(0));
	next_frame(0);
	invoke_irq();
	none();
	finish();
}
static void delayed_slot(void)
{
	begin_delivery();
	input_mt_slot(&input, 3);
	input_mt_slot(&input, 7);
	input_report_abs(&input, ABS_MT_POSITION_X, 0); /* unchanged */
	input_report_abs(&input, ABS_MT_TOOL_TYPE, MT_TOOL_FINGER); /* unsupported */
	input_sync(&input);
	none();
	CHECK(consumer.slot == 0);
	seed_one(0);
	clear_delivery();
	input_mt_slot(&input, 1);
	input_report_abs(&input, ABS_MT_POSITION_X, 300);
	none(); /* A changed value is queued, not delivered before the sync. */
	CHECK(input.num_vals == 2);
	input_mt_slot(&input, 9); /* staged AFTER the queued slot1 value */
	none();
	input_sync(&input);
	ONE(A(ABS_MT_SLOT, 1), A(ABS_MT_POSITION_X, 300), S(0));
	CHECK(consumer.slot == 1 && consumer.x[1] == 300);
	/* This producer-only slot is intentionally not used as an event label. */
	CHECK(mt.slot == 9);
	next_frame(1);
	put_point(0, 7, 2, 100, 200);
	invoke_irq();
	none(); /* Switching back to an unchanged contact emits no slot. */
	CHECK(consumer.slot == 1);
	next_frame(1);
	put_point(0, 7, 2, 101, 200);
	invoke_irq();
	ONE(A(ABS_MT_SLOT, 7), A(ABS_MT_POSITION_X, 101), A(ABS_X, 101), S(0));
	CHECK(consumer.slot == 7 && consumer.x[7] == 101);
	finish();
}
static void multiple(void)
{
	begin_delivery();
	seed_two();
	next_frame(2);
	put_point(0, 1, 2, 300, 400);
	put_point(1, 7, 2, 100, 200);
	invoke_irq();
	none();
	CHECK(consumer.slot == 1); /* last delivered, not last requested */
	next_frame(2);
	put_point(0, 7, 2, 101, 200);
	put_point(1, 1, 2, 300, 400);
	invoke_irq();
	ONE(A(ABS_MT_SLOT, 7), A(ABS_MT_POSITION_X, 101), A(ABS_X, 101), S(0));
	CHECK(consumer.x[7] == 101 && consumer.x[1] == 300);
	next_frame(2);
	put_point(0, 1, 2, 301, 401);
	put_point(1, 7, 2, 102, 202);
	invoke_irq();
	ONE(A(ABS_MT_SLOT, 1), A(ABS_MT_POSITION_X, 301), A(ABS_MT_POSITION_Y, 401),
	    A(ABS_MT_SLOT, 7), A(ABS_MT_POSITION_X, 102), A(ABS_MT_POSITION_Y, 202),
	    A(ABS_X, 102), A(ABS_Y, 202), S(0));
	CHECK(consumer.id[7] == 0 && consumer.id[1] == 1);
	finish();
}
static void missing(void)
{
	begin_delivery();
	seed_two();
	next_frame(1);
	put_point(0, 1, 2, 300, 400); /* oldest slot7 absent, no explicit UP */
	invoke_irq();
	ONE(A(ABS_MT_SLOT, 7), A(ABS_MT_TRACKING_ID, -1),
	    A(ABS_X, 300), A(ABS_Y, 400), S(0));
	CHECK(consumer_active() == BIT(1) && consumer.id[1] == 1);
	CHECK(consumer.touch == 1 && consumer.pointer_x == 300);
	next_frame(0);
	invoke_irq();
	ONE(A(ABS_MT_SLOT, 1), A(ABS_MT_TRACKING_ID, -1), K(0), S(0));
	CHECK(consumer_active() == 0);
	finish();
}
static void error_release(const char *name)
{
	begin_delivery();
	seed_two();
	next_frame(1);
	put_point(0, 7, 3, 100, 200);
	if (!strcmp(name, "short-transfer"))
		short_transfer = 1;
	else if (!strcmp(name, "io-error"))
		short_transfer = -EREMOTEIO;
	else
		CHECK(!strcmp(name, "invalid-frame"));
	invoke_irq();
	expect_release_two();
	clear_delivery();
	invoke_irq(); /* same error with no contacts: no empty delivered SYN */
	none();
	finish();
}
static void suspend_delivery(void)
{
	begin_delivery();
	seed_two();
	clear_delivery();
	CHECK(rog5_fts_suspend(&client.dev) == 0);
	expect_release_two();
	CHECK(touch->suspended && disables == 1);
	clear_delivery();
	CHECK(rog5_fts_suspend(&client.dev) == 0);
	none();
	CHECK(rog5_fts_resume(&client.dev) == 0);
	none();
	next_frame(1);
	put_point(0, 1, 0, 300, 400); /* same per-slot coordinates, NEW contact */
	invoke_irq();
	ONE(A(ABS_MT_SLOT, 1), A(ABS_MT_TRACKING_ID, 2),
	    K(1), A(ABS_X, 300), A(ABS_Y, 400), S(0));
	CHECK(consumer.id[1] == 2 && consumer_active() == BIT(1));
	finish();
}
static void wrap_oldest(void)
{
	begin_delivery();
	mt.trkid = TRKID_MAX; /* boundary seeding, not billions of contacts/INT_MAX */
	seed_one(65535);
	next_frame(2);
	put_point(0, 1, 0, 1000, 2000); /* lower slot and earlier record, but newer */
	put_point(1, 7, 2, 101, 201);
	invoke_irq();
	ONE(A(ABS_MT_SLOT, 1), A(ABS_MT_TRACKING_ID, 0), A(ABS_MT_POSITION_X, 1000),
	    A(ABS_MT_POSITION_Y, 2000), A(ABS_MT_TOUCH_MAJOR, 10),
	    A(ABS_MT_SLOT, 7), A(ABS_MT_POSITION_X, 101), A(ABS_MT_POSITION_Y, 201),
	    A(ABS_X, 101), A(ABS_Y, 201), S(0));
	CHECK(consumer.id[7] == 65535 && consumer.id[1] == 0);
	CHECK(consumer.pointer_x == 101 && consumer.pointer_y == 201);
	next_frame(1);
	put_point(0, 7, 1, 65535, 65535);
	put_point(1, 1, 2, 1001, 2001);
	invoke_irq();
	ONE(A(ABS_MT_TRACKING_ID, -1), A(ABS_MT_SLOT, 1),
	    A(ABS_MT_POSITION_X, 1001), A(ABS_MT_POSITION_Y, 2001),
	    A(ABS_X, 1001), A(ABS_Y, 2001), S(0));
	CHECK(consumer_active() == BIT(1));
	next_frame(2);
	put_point(0, 7, 0, 101, 201);
	put_point(1, 1, 2, 1001, 2001);
	invoke_irq();
	ONE(A(ABS_MT_SLOT, 7), A(ABS_MT_TRACKING_ID, 1), S(0));
	CHECK(consumer.id[7] == 1 && consumer.id[1] == 0);
	CHECK(consumer.pointer_x == 1001 && consumer.pointer_y == 2001);
	next_frame(0);
	invoke_irq();
	ONE(A(ABS_MT_SLOT, 1), A(ABS_MT_TRACKING_ID, -1),
	    A(ABS_MT_SLOT, 7), A(ABS_MT_TRACKING_ID, -1), K(0), S(0));
	CHECK(consumer_active() == 0);
	finish();
}
static void ten_contacts(void)
{
	begin_delivery();
	next_frame(10);
	struct input_value expected[64];
	unsigned n = 0;
	for (unsigned i = 0; i < 10; i++) {
		put_point(i, i, 0, 100 + i, 200 + i);
		if (i)
			expected[n++] = VALUE(EV_ABS, ABS_MT_SLOT, i);
		expected[n++] = VALUE(EV_ABS, ABS_MT_TRACKING_ID, i);
		expected[n++] = VALUE(EV_ABS, ABS_MT_POSITION_X, 100 + i);
		expected[n++] = VALUE(EV_ABS, ABS_MT_POSITION_Y, 200 + i);
		expected[n++] = VALUE(EV_ABS, ABS_MT_TOUCH_MAJOR, 10);
	}
	expected[n++] = VALUE(EV_KEY, BTN_TOUCH, 1);
	expected[n++] = VALUE(EV_ABS, ABS_X, 100);
	expected[n++] = VALUE(EV_ABS, ABS_Y, 200);
	expected[n++] = VALUE(EV_SYN, SYN_REPORT, 0);
	CHECK(n == 53);
	invoke_irq();
	CHECK(delivered_count == 1);
	expect_batch(0, expected, n);
	CHECK(consumer_active() == 0x3ff);
	for (unsigned i = 0; i < 10; i++) {
		CHECK(consumer.id[i] == (int)i && consumer.x[i] == (int)(100 + i));
		CHECK(consumer.y[i] == (int)(200 + i) && consumer.major[i] == 10);
	}
	next_frame(0);
	n = 0;
	for (unsigned i = 0; i < 10; i++) {
		expected[n++] = VALUE(EV_ABS, ABS_MT_SLOT, i);
		expected[n++] = VALUE(EV_ABS, ABS_MT_TRACKING_ID, -1);
	}
	expected[n++] = VALUE(EV_KEY, BTN_TOUCH, 0);
	expected[n++] = VALUE(EV_SYN, SYN_REPORT, 0);
	invoke_irq();
	CHECK(delivered_count == 1 && n == 22);
	expect_batch(0, expected, n);
	CHECK(consumer_active() == 0 && consumer.touch == 0);
	finish();
}
static void capacity(void)
{
	begin_delivery();
	input.max_vals = 8; /* fault-injected capacity, NOT production allocation size */
	input.storage[8] = VALUE(0xabcd, 0x1234, 0x5678);
	next_frame(1);
	put_point(0, 7, 0, 100, 200);
	invoke_irq();
	const struct input_value first[] = {
		A(ABS_MT_SLOT, 7), A(ABS_MT_TRACKING_ID, 0), A(ABS_MT_POSITION_X, 100),
		A(ABS_MT_POSITION_Y, 200), A(ABS_MT_TOUCH_MAJOR, 10), K(1), S(1)
	};
	const struct input_value second[] = { A(ABS_X, 100), A(ABS_Y, 200), S(0) };
	CHECK(delivered_count == 2); /* ONE driver SYN request, TWO callbacks */
	expect_batch(0, first, ARRAY_SIZE(first));
	expect_batch(1, second, ARRAY_SIZE(second));
	CHECK(input.storage[8].type == 0xabcd && input.storage[8].code == 0x1234 &&
	      input.storage[8].value == 0x5678);
	clear_delivery();
	/* Six changed values exactly fill the threshold. The later explicit
	 * SYN has nothing left to deliver: it does not become a second packet. */
	for (unsigned i = 0; i < 6; i++)
		input_report_abs(&input, ABS_X, 1000 + i);
	ONE(A(ABS_X, 1000), A(ABS_X, 1001), A(ABS_X, 1002),
	    A(ABS_X, 1003), A(ABS_X, 1004), A(ABS_X, 1005), S(1));
	input_sync(&input);
	CHECK(delivered_count == 1 && input.num_vals == 0);
	input.max_vals = HOST_VAL_CAPACITY;
	finish();
}
static void handler_closed(void)
{
	begin_delivery();
	seed_one(0);
	observer_handle.open = 0;
	next_frame(1);
	put_point(0, 7, 2, 101, 201);
	invoke_irq();
	none();
	observer_handle.open = 1;
	next_frame(1);
	put_point(0, 7, 2, 101, 201);
	invoke_irq();
	none(); /* No queued replay of the discarded closed-handle batch. */
	next_frame(0);
	invoke_irq();
	ONE(A(ABS_MT_TRACKING_ID, -1), K(0), S(0));
	CHECK(consumer_active() == 0);
	finish();
}
int main(int argc, char **argv)
{
	CHECK(argc == 2);
	const char *name = argv[1];
	if (!strcmp(name, "down-move-up")) down_move_up();
	else if (!strcmp(name, "unchanged-empty")) unchanged_empty();
	else if (!strcmp(name, "delayed-slot")) delayed_slot();
	else if (!strcmp(name, "multiple")) multiple();
	else if (!strcmp(name, "missing")) missing();
	else if (!strcmp(name, "short-transfer") || !strcmp(name, "io-error") ||
		 !strcmp(name, "invalid-frame")) error_release(name);
	else if (!strcmp(name, "suspend")) suspend_delivery();
	else if (!strcmp(name, "wrap-oldest")) wrap_oldest();
	else if (!strcmp(name, "ten-contacts")) ten_contacts();
	else if (!strcmp(name, "capacity")) capacity();
	else if (!strcmp(name, "handler-closed")) handler_closed();
	else CHECK(!"unknown delivered-event case");
	return 0;
}
