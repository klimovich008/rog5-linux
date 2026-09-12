/* SPDX-License-Identifier: GPL-2.0-only */
static struct i2c_client client;
static struct rog5_fts *touch;
static void setup(void)
{
	CHECK(!resource_count && !allocated);
	memset(&input, 0, sizeof(input));
	memset(&mt, 0, sizeof(mt));
	client = (struct i2c_client){ .dev = { .of_node = &client },
				      .addr = 0x38,
				      .irq = 23 };
	reset.level = 1;
	io_enable.level = 0;
	vdd.votes = io.votes = 0;
	fault = NULL;
	second_fault = NULL;
	faults_left = second_faults_left = 0;
	irq_during_request = false;
	short_transfer = 0;
	reads = identity_reads = disables = 0;
	jiffies = 0;
	normal_id = true;
	irq_available = irq_disabled = irq_inflight = block_read =
		read_entered = read_continue = false;
	memset(frame_bytes, 0xff, sizeof(frame_bytes));
	frame_bytes[0] = frame_bytes[1] = 0;
}
static void finish(void)
{
	unwind();
	CHECK(!irq_available && !irq_inflight && !input.valid);
	CHECK(!vdd.votes && !io.votes);
	CHECK(reset.level == 1 && io_enable.level == 0);
	free(allocated);
	allocated = NULL;
}
static void start(void)
{
	CHECK(rog5_fts_probe(&client) == 0);
	touch = client.data;
	CHECK(touch->irq_running && touch->vdd_vote && touch->io_vote &&
	      input.registered);
	CHECK(identity_reads == 2 &&
	      jiffies == 207); /* Existing 1+1+5+200 ms sequence. */
}
static void put_point(unsigned index, unsigned slot, unsigned event, unsigned x,
		      unsigned y)
{
	u8 *p = frame_bytes + 2 + index * 6;
	p[0] = (event << 6) | ((x >> 12) & 15);
	p[1] = x >> 4;
	p[2] = (slot << 4) | ((y >> 12) & 15);
	p[3] = y >> 4;
	p[4] = ((x & 15) << 4) | (y & 15);
	p[5] = 0xa1;
}
static unsigned active(void)
{
	unsigned value = 0;
	for (unsigned i = 0; i < 10; i++)
		if (mt.slots[i].id >= 0)
			value |= BIT(i);
	return value;
}
static void invoke_irq(void)
{
	CHECK(irq_available && !irq_disabled);
	CHECK(irq_handler(client.irq, irq_data) == IRQ_HANDLED);
}
static void contact(void)
{
	frame_bytes[1] = 1;
	put_point(0, 4, 0, 17279, 39167);
	invoke_irq();
	CHECK(active() == BIT(4));
	CHECK(mt.slots[4].x == 17279 && mt.slots[4].y == 39167 &&
	      mt.slots[4].area == 10);
}
static void probe_failures(void)
{
	const char *faults[] = { "power-action",   "gpio:reset:1",
				 "enable:io:1",	   "gpio:io:1",
				 "enable:vdd:1",   "gpio:reset:0",
				 "read:high",	   "read:low",
				 "input-allocate", "input-slots",
				 "input-register", "irq-request",
				 "stop-action" };
	for (unsigned i = 0; i < ARRAY_SIZE(faults); i++) {
		setup();
		fault = faults[i];
		faults_left = 1;
		CHECK(rog5_fts_probe(&client) < 0);
		CHECK(!faults_left);
		finish();
	}
}
static void vote_retry(const char *rail)
{
	setup();
	start();
	rog5_fts_stop(touch);
	fault = rail;
	faults_left = 1;
	CHECK(rog5_fts_power_off(touch) == -EIO);
	bool is_vdd = !strcmp(rail, "disable:vdd:0");
	CHECK(touch->vdd_vote == is_vdd && touch->io_vote == !is_vdd);
	CHECK(vdd.votes == (int)is_vdd && io.votes == (int)!is_vdd);
	CHECK(rog5_fts_power_on(touch) == -EBUSY);
	CHECK(rog5_fts_power_off(touch) == 0);
	CHECK(!touch->vdd_vote && !touch->io_vote);
	CHECK(rog5_fts_power_on(touch) == 0);
	CHECK(rog5_fts_identify(touch) == 0);
	finish();
}
static void gpio_off_error(const char *line)
{
	setup();
	start();
	rog5_fts_stop(touch);
	fault = line;
	faults_left = 1;
	CHECK(rog5_fts_power_off(touch) == -EIO);
	CHECK(!touch->vdd_vote && !touch->io_vote);
	CHECK(rog5_fts_power_off(touch) == 0);
	finish();
}
static void *irq_worker(void *unused)
{
	(void)unused;
	pthread_mutex_lock(&irq_lock);
	CHECK(!irq_disabled);
	irq_inflight = true;
	pthread_mutex_unlock(&irq_lock);
	CHECK(irq_handler(client.irq, irq_data) == IRQ_HANDLED);
	pthread_mutex_lock(&irq_lock);
	irq_inflight = false;
	pthread_cond_broadcast(&irq_cond);
	pthread_mutex_unlock(&irq_lock);
	return NULL;
}
static void *shutdown_worker(void *unused)
{
	(void)unused;
	rog5_fts_shutdown(&client);
	return NULL;
}
static void shutdown_race(void)
{
	pthread_t irq_thread, stop_thread;
	setup();
	start();
	contact();
	block_read = true;
	CHECK(!pthread_create(&irq_thread, NULL, irq_worker, NULL));
	pthread_mutex_lock(&irq_lock);
	while (!read_entered)
		pthread_cond_wait(&irq_cond, &irq_lock);
	pthread_mutex_unlock(&irq_lock);
	CHECK(!pthread_create(&stop_thread, NULL, shutdown_worker, NULL));
	pthread_mutex_lock(&irq_lock);
	while (!irq_disabled)
		pthread_cond_wait(&irq_cond, &irq_lock);
	CHECK(irq_inflight && vdd.votes == 1 && io.votes == 1 &&
	      input.registered);
	read_continue = true;
	pthread_cond_broadcast(&irq_cond);
	pthread_mutex_unlock(&irq_lock);
	CHECK(!pthread_join(irq_thread, NULL));
	CHECK(!pthread_join(stop_thread, NULL));
	CHECK(!active() && !touch->irq_running && !vdd.votes && !io.votes &&
	      disables == 1);
	finish();
	CHECK(disables == 1);
}
int main(int argc, char **argv)
{
	CHECK(argc == 2);
	const char *name = argv[1];
	if (!strcmp(name, "probe-unwind")) {
		probe_failures();
		return 0;
	}
	if (!strcmp(name, "vote-vdd-retry")) {
		vote_retry("disable:vdd:0");
		return 0;
	}
	if (!strcmp(name, "vote-io-retry")) {
		vote_retry("disable:io:0");
		return 0;
	}
	if (!strcmp(name, "off-reset-error")) {
		gpio_off_error("gpio:reset:1");
		return 0;
	}
	if (!strcmp(name, "off-io-error")) {
		gpio_off_error("gpio:io:0");
		return 0;
	}
	if (!strcmp(name, "shutdown-drains-irq")) {
		shutdown_race();
		return 0;
	}
	if (!strcmp(name, "prepare-cleanup-retry")) {
		setup();
		fault = "gpio:reset:0";
		faults_left = 1;
		second_fault = "disable:vdd:0";
		second_faults_left = 1;
		CHECK(rog5_fts_probe(&client) == -EIO);
		touch = client.data;
		CHECK(touch->vdd_vote && !touch->io_vote && !faults_left &&
		      !second_faults_left);
		finish();
		return 0;
	}
	if (!strcmp(name, "irq-at-registration")) {
		setup();
		irq_during_request = true;
		frame_bytes[1] = 1;
		put_point(0, 4, 0, 100, 200);
		start();
		CHECK(active() == BIT(4) && input.syncs == 1);
		finish();
		return 0;
	}
	if (!strcmp(name, "normal-id-refusal")) {
		setup();
		normal_id = false;
		CHECK(rog5_fts_probe(&client) == -ENODEV);
		CHECK(identity_reads == 40 && jiffies == 1157);
		finish();
		return 0;
	}
	setup();
	start();
	if (!strcmp(name, "irq-short-transfer")) {
		contact();
		short_transfer = 1;
		invoke_irq();
		CHECK(!active());
	} else if (!strcmp(name, "irq-io-error")) {
		contact();
		short_transfer = -EREMOTEIO;
		invoke_irq();
		CHECK(!active());
	} else if (!strcmp(name, "irq-invalid-frame")) {
		contact();
		frame_bytes[2] |= 0xc0;
		invoke_irq();
		CHECK(!active());
	} else if (!strcmp(name, "irq-drop-unused")) {
		contact();
		frame_bytes[1] = 1;
		put_point(0, 7, 0, 100, 200);
		invoke_irq();
		CHECK(active() == BIT(7));
		memset(frame_bytes, 0xff, sizeof(frame_bytes));
		frame_bytes[1] = 0;
		invoke_irq();
		CHECK(!active());
	} else if (!strcmp(name, "shutdown-idempotent")) {
		contact();
		rog5_fts_shutdown(&client);
		rog5_fts_shutdown(&client);
		CHECK(disables == 1 && !active() && !vdd.votes && !io.votes);
	} else if (!strcmp(name, "suspend-refused")) {
		contact();
		CHECK(rog5_fts_suspend(&client.dev) == -EBUSY);
		CHECK(active() == BIT(4) && !irq_disabled && touch->vdd_vote &&
		      touch->io_vote);
	} else
		CHECK(!"unknown case");
	finish();
	return 0;
}
