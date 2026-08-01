// SPDX-License-Identifier: MIT
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define PAYLOAD_MAX 1024
#define FRAME_MAX (PAYLOAD_MAX + 32)

struct stage {
	unsigned int code;
	const char *name;
};

static const struct stage stages[] = {
	{ 10, "reporter-up" },
	{ 20, "gadget-configured" },
	{ 30, "udc-bound" },
	{ 40, "ncm-interface-up" },
	{ 50, "address-configured" },
	{ 60, "ncm-carrier-up" },
	{ 70, "nfs-mount-begin" },
	{ 80, "nfs-mount-ok" },
	{ 90, "seal-verify-ok" },
	{ 100, "overlay-ready" },
	{ 110, "handoff-begin" },
	{ 120, "switch-root-exec" },
	{ 130, "new-init-up" },
	{ 140, "sshd-active" },
	{ 200, "fault" },
	{ 210, "watchdog-pretimeout" },
};

static const char *const faults[] = {
	"none",
	"cmdline-invalid",
	"storage-visible",
	"watchdog-failed",
	"gadget-config-failed",
	"udc-bind-failed",
	"ncm-interface-failed",
	"address-failed",
	"carrier-timeout",
	"nfs-mount-failed",
	"seal-verify-failed",
	"overlay-failed",
	"identity-publish-failed",
	"storage-before-switch",
	"exitrd-failed",
	"handoff-failed",
	"switch-root-returned",
};

static void fail(const char *message)
{
	fprintf(stderr, "rog5-early-target-diag: %s\n", message);
	exit(EXIT_FAILURE);
}

static bool valid_candidate(const char *value)
{
	size_t index;
	size_t length = strlen(value);

	if (length < 1 || length > 64 ||
	    !((value[0] >= 'a' && value[0] <= 'z') ||
	      (value[0] >= '0' && value[0] <= '9')))
		return false;
	for (index = 0; index < length; index++) {
		char byte = value[index];

		if ((byte >= 'a' && byte <= 'z') ||
		    (byte >= '0' && byte <= '9') || byte == '.' || byte == '-')
			continue;
		return false;
	}
	return strstr(value, "..") == NULL;
}

static bool hex_byte(char byte)
{
	return (byte >= '0' && byte <= '9') ||
	       (byte >= 'a' && byte <= 'f');
}

static bool valid_boot_id(const char *value)
{
	static const size_t hyphens[] = { 8, 13, 18, 23 };
	size_t index;
	size_t hyphen = 0;

	if (strlen(value) != 36)
		return false;
	for (index = 0; index < 36; index++) {
		if (hyphen < 4 && index == hyphens[hyphen]) {
			if (value[index] != '-')
				return false;
			hyphen++;
		} else if (!hex_byte(value[index])) {
			return false;
		}
	}
	return true;
}

static uint64_t number(const char *value, uint64_t minimum,
		       uint64_t maximum, const char *label)
{
	char *end = NULL;
	uint64_t parsed;

	if (value[0] == '\0' || (value[0] == '0' && value[1] != '\0'))
		fail(label);
	for (end = (char *)value; *end != '\0'; end++) {
		if (*end < '0' || *end > '9')
			fail(label);
	}
	errno = 0;
	parsed = strtoull(value, &end, 10);
	if (errno != 0 || *end != '\0' || parsed < minimum || parsed > maximum)
		fail(label);
	return parsed;
}

static const char *stage_name(unsigned int code)
{
	size_t index;

	for (index = 0; index < sizeof(stages) / sizeof(stages[0]); index++) {
		if (stages[index].code == code)
			return stages[index].name;
	}
	return NULL;
}

static bool valid_progress(unsigned int code)
{
	return code >= 10 && code <= 140 && code % 10 == 0;
}

static bool valid_fault(const char *value)
{
	size_t index;

	for (index = 0; index < sizeof(faults) / sizeof(faults[0]); index++) {
		if (strcmp(value, faults[index]) == 0)
			return true;
	}
	return false;
}

static void write_all(int descriptor, const char *buffer, size_t length)
{
	while (length > 0) {
		ssize_t written = write(descriptor, buffer, length);

		if (written < 0 && errno == EINTR)
			continue;
		if (written <= 0)
			fail("cannot write frame");
		buffer += written;
		length -= (size_t)written;
	}
}

static void emit_frame(int argc, char **argv)
{
	char payload[PAYLOAD_MAX + 1];
	char frame[FRAME_MAX];
	const char *candidate;
	const char *boot_id;
	const char *name;
	const char *fault;
	uint64_t sequence;
	uint64_t boottime;
	uint64_t stage_code_raw;
	uint64_t last_good_raw;
	uint64_t deadline;
	uint64_t dropped;
	unsigned int stage_code;
	unsigned int last_good;
	int payload_length;
	int frame_length;

	if (argc != 11)
		fail("usage: frame CANDIDATE BOOT_ID SEQUENCE BOOTTIME_MS "
		     "STAGE_CODE LAST_GOOD_CODE FAULT DEADLINE_MS DROPPED");
	candidate = argv[2];
	boot_id = argv[3];
	if (!valid_candidate(candidate) || !valid_boot_id(boot_id))
		fail("invalid frame identity");
	sequence = number(argv[4], 1, UINT64_MAX, "invalid sequence");
	boottime = number(argv[5], 0, UINT64_MAX, "invalid boottime");
	stage_code_raw = number(argv[6], 10, 210, "invalid stage code");
	last_good_raw = number(argv[7], 10, 140, "invalid last-good code");
	if (stage_code_raw > UINT_MAX || last_good_raw > UINT_MAX)
		fail("stage code overflow");
	stage_code = (unsigned int)stage_code_raw;
	last_good = (unsigned int)last_good_raw;
	name = stage_name(stage_code);
	fault = argv[8];
	deadline = number(argv[9], 60000, 900000, "invalid watchdog deadline");
	dropped = number(argv[10], 0, 1000000, "invalid dropped count");
	if (name == NULL || !valid_progress(last_good) || !valid_fault(fault) ||
	    boottime > deadline)
		fail("inconsistent frame state");
	if (valid_progress(stage_code)) {
		if (stage_code != last_good || strcmp(fault, "none") != 0)
			fail("inconsistent progress frame");
	} else if (stage_code == 200) {
		if (strcmp(fault, "none") == 0)
			fail("fault frame lacks reason");
	} else if (stage_code == 210) {
		if (strcmp(fault, "none") != 0)
			fail("pretimeout frame carries fault");
	} else {
		fail("unknown stage code");
	}

	payload_length = snprintf(
		payload, sizeof(payload),
		"format=rog5-early-target-diag-v1\n"
		"candidate=%s\n"
		"boot_id=%s\n"
		"sequence=%" PRIu64 "\n"
		"boottime_ms=%" PRIu64 "\n"
		"stage_code=%u\n"
		"stage=%s\n"
		"last_good_code=%u\n"
		"fault=%s\n"
		"watchdog_deadline_ms=%" PRIu64 "\n"
		"dropped_updates=%" PRIu64 "\n",
		candidate, boot_id, sequence, boottime, stage_code, name,
		last_good, fault, deadline, dropped);
	if (payload_length < 1 || payload_length > PAYLOAD_MAX)
		fail("frame payload exceeds policy");
	frame_length = snprintf(frame, sizeof(frame), "%d:%s,",
				payload_length, payload);
	if (frame_length < 1 || (size_t)frame_length >= sizeof(frame))
		fail("encoded frame exceeds policy");
	write_all(STDOUT_FILENO, frame, (size_t)frame_length);
}

int main(int argc, char **argv)
{
	if (argc < 2 || strcmp(argv[1], "frame") != 0)
		fail("only the frame operation is implemented");
	emit_frame(argc, argv);
	return EXIT_SUCCESS;
}
