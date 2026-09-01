// SPDX-License-Identifier: MIT
#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <poll.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/un.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#define PAYLOAD_MAX 1024
#define FRAME_MAX (PAYLOAD_MAX + 32)
#define UPDATE_MAX 1024
#define UPDATE_BATCH_MAX 16
#define CONTROL_FDS_MAX 16
#define HEARTBEAT_MS 250
#define PRETIMEOUT_MS 5000
#define WATCHDOG_INTERVAL_MAX_MS 900000
#define SOCKET_NAME "rog5-early-target-diag-v1"

struct stage {
	unsigned int code;
	const char *name;
};

struct diagnostic_record {
	const char *candidate;
	const char *boot_id;
	uint64_t sequence;
	uint64_t boottime;
	unsigned int stage_code;
	unsigned int last_good;
	const char *fault;
	uint64_t deadline;
	uint64_t dropped;
};

struct power_evidence {
	char category[97];
	char name[97];
	char status[8];
	char value[513];
	uint64_t sequence;
};

static const struct stage stages[] = {
	{ 10, "reporter-up" },
	{ 20, "gadget-configured" },
	{ 30, "udc-bound" },
	{ 40, "ncm-interface-up" },
	{ 50, "address-configured" },
	{ 60, "ncm-carrier-up" },
	{ 70, "nfs-mount-begin" },
	{ 75, "nfs-mount-returned" },
	{ 80, "nfs-mount-ok" },
	{ 90, "seal-verify-ok" },
	{ 100, "overlay-ready" },
	{ 110, "handoff-begin" },
	{ 120, "switch-root-exec" },
	{ 130, "new-init-up" },
	{ 140, "sshd-active" },
	{ 141, "charging-exec" },
	{ 142, "charging-runtime-ready" },
	{ 143, "charging-mounts-ready" },
	{ 144, "charging-dt-ready" },
	{ 145, "charging-firmware-inventory-ready" },
	{ 150, "ssh-key-accepted" },
	{ 151, "charging-probe-start" },
	{ 152, "charging-firmware-selected" },
	{ 153, "charging-adsp-running" },
	{ 154, "charging-qrtr-ready" },
	{ 155, "charging-pmic-glink-ready" },
	{ 156, "charging-battmgr-ready" },
	{ 157, "charging-ucsi-ready" },
	{ 158, "charging-telemetry-readable" },
	{ 159, "charging-usb-online" },
	{ 170, "charging-status-charging" },
	{ 171, "charging-status-not-charging" },
	{ 172, "charging-status-discharging" },
	{ 173, "charging-status-full" },
	{ 174, "charging-status-unknown" },
	{ 175, "charging-current-positive" },
	{ 176, "charging-current-zero" },
	{ 177, "charging-current-negative" },
	{ 180, "charging-voltage-rising" },
	{ 181, "charging-voltage-flat" },
	{ 182, "charging-voltage-falling" },
	{ 190, "charging-probe-complete" },
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
	"route-failed",
	"host-port-probe-failed",
	"host-port-unreachable",
	"host-port-timeout",
	"nfs-mount-failed",
	"seal-verify-failed",
	"overlay-failed",
	"diagnostic-units-failed",
	"identity-publish-failed",
	"storage-before-switch",
	"exitrd-failed",
	"handoff-failed",
	"switch-root-returned",
	"charging-probe-failed",
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
	return code < 200 && stage_name(code) != NULL;
}

static const char *canonical_fault(const char *value)
{
	size_t index;

	for (index = 0; index < sizeof(faults) / sizeof(faults[0]); index++) {
		if (strcmp(value, faults[index]) == 0)
			return faults[index];
	}
	return NULL;
}

static bool valid_fault(const char *value)
{
	return canonical_fault(value) != NULL;
}

static bool valid_evidence_token(const char *value)
{
	size_t index;
	size_t length = strlen(value);

	if (length < 1 || length > 96 || value[0] < 'a' || value[0] > 'z')
		return false;
	for (index = 0; index < length; index++) {
		char byte = value[index];

		if ((byte >= 'a' && byte <= 'z') ||
		    (byte >= '0' && byte <= '9') || byte == '_' || byte == '.' ||
		    byte == ':' || byte == '-')
			continue;
		return false;
	}
	return true;
}

static bool valid_evidence_value(const char *value)
{
	size_t index;
	size_t length = strlen(value);

	if (length > 512 || (length % 2) != 0)
		return false;
	for (index = 0; index < length; index++) {
		if (!hex_byte(value[index]))
			return false;
	}
	return true;
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

static void validate_record(const struct diagnostic_record *record)
{
	const char *name;

	if (!valid_candidate(record->candidate) ||
	    !valid_boot_id(record->boot_id))
		fail("invalid frame identity");
	name = stage_name(record->stage_code);
	if (record->sequence < 1 || name == NULL ||
	    !valid_progress(record->last_good) ||
	    !valid_fault(record->fault) || record->deadline < 1 ||
	    (record->boottime >= record->deadline &&
	     record->stage_code != 210) ||
	    record->dropped > 1000000)
		fail("inconsistent frame state");
	if (valid_progress(record->stage_code)) {
		if (record->stage_code != record->last_good ||
		    strcmp(record->fault, "none") != 0)
			fail("inconsistent progress frame");
	} else if (record->stage_code == 200) {
		if (strcmp(record->fault, "none") == 0)
			fail("fault frame lacks reason");
	} else if (record->stage_code == 210) {
		if (strcmp(record->fault, "none") != 0)
			fail("pretimeout frame carries fault");
	} else {
		fail("unknown stage code");
	}
}

static size_t format_frame(const struct diagnostic_record *record,
			   char frame[FRAME_MAX])
{
	char payload[PAYLOAD_MAX + 1];
	const char *name;
	int payload_length;
	int frame_length;

	validate_record(record);
	name = stage_name(record->stage_code);

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
		record->candidate, record->boot_id, record->sequence,
		record->boottime, record->stage_code, name, record->last_good,
		record->fault, record->deadline, record->dropped);
	if (payload_length < 1 || payload_length > PAYLOAD_MAX)
		fail("frame payload exceeds policy");
	frame_length = snprintf(frame, FRAME_MAX, "%d:%s,",
				payload_length, payload);
	if (frame_length < 1 || frame_length >= FRAME_MAX)
		fail("encoded frame exceeds policy");
	return (size_t)frame_length;
}

static size_t format_evidence_frame(const struct diagnostic_record *record,
				    const struct power_evidence *evidence,
				    char frame[FRAME_MAX])
{
	char payload[PAYLOAD_MAX + 1];
	int payload_length;
	int frame_length;

	payload_length = snprintf(
		payload, sizeof(payload),
		"format=rog5-early-power-evidence-v1\n"
		"candidate=%s\n"
		"boot_id=%s\n"
		"sequence=%" PRIu64 "\n"
		"boottime_ms=%" PRIu64 "\n"
		"category=%s\n"
		"name=%s\n"
		"status=%s\n"
		"encoding=hex\n"
		"value=%s\n",
		record->candidate, record->boot_id, evidence->sequence,
		record->boottime, evidence->category, evidence->name,
		evidence->status, evidence->value);
	if (payload_length < 1 || payload_length > PAYLOAD_MAX)
		fail("power evidence payload exceeds policy");
	frame_length = snprintf(frame, FRAME_MAX, "%d:%s,",
				payload_length, payload);
	if (frame_length < 1 || frame_length >= FRAME_MAX)
		fail("encoded power evidence exceeds policy");
	return (size_t)frame_length;
}

static void emit_frame(int argc, char **argv)
{
	char frame[FRAME_MAX];
	uint64_t stage_code;
	uint64_t last_good;
	struct diagnostic_record record;
	size_t frame_length;

	if (argc != 11)
		fail("usage: frame CANDIDATE BOOT_ID SEQUENCE BOOTTIME_MS "
		     "STAGE_CODE LAST_GOOD_CODE FAULT DEADLINE_MS DROPPED");
	stage_code = number(argv[6], 10, 210, "invalid stage code");
	last_good = number(argv[7], 10, 190, "invalid last-good code");
	if (stage_code > UINT_MAX || last_good > UINT_MAX)
		fail("stage code overflow");
	record = (struct diagnostic_record) {
		.candidate = argv[2],
		.boot_id = argv[3],
		.sequence = number(argv[4], 1, UINT64_MAX,
				   "invalid sequence"),
		.boottime = number(argv[5], 0, UINT64_MAX,
				  "invalid boottime"),
		.stage_code = (unsigned int)stage_code,
		.last_good = (unsigned int)last_good,
		.fault = argv[8],
		.deadline = number(argv[9], 1, UINT64_MAX,
				   "invalid watchdog deadline"),
		.dropped = number(argv[10], 0, 1000000,
				  "invalid dropped count"),
	};
	frame_length = format_frame(&record, frame);
	write_all(STDOUT_FILENO, frame, frame_length);
}

static bool parse_small_decimal(const char *value, uint64_t *result);

static uint64_t monotonic_milliseconds(void)
{
#ifdef ROG5_DIAG_TESTING
	static bool initialized;
	static bool fake;
	static uint64_t fake_now;
	static uint64_t fake_step;
	const char *start;
	const char *step;

	if (!initialized) {
		initialized = true;
		start = getenv("ROG5_DIAG_TEST_CLOCK_START_MS");
		step = getenv("ROG5_DIAG_TEST_CLOCK_STEP_MS");
		if (start != NULL) {
			if (!parse_small_decimal(start, &fake_now) ||
			    step == NULL || !parse_small_decimal(step, &fake_step) ||
			    fake_step < 1 || fake_step > 1000)
				fail("invalid testing clock");
			fake = true;
		}
	}
	if (fake) {
		uint64_t result = fake_now;

		if (fake_now > UINT64_MAX - fake_step)
			fail("testing clock overflow");
		fake_now += fake_step;
		return result;
	}
#endif
	struct timespec now;

	if (clock_gettime(CLOCK_BOOTTIME, &now) < 0)
		fail("cannot read boottime clock");
	if ((uint64_t)now.tv_sec > (UINT64_MAX - 999) / 1000)
		fail("boottime clock overflow");
	return (uint64_t)now.tv_sec * 1000 +
	       (uint64_t)now.tv_nsec / 1000000;
}

static socklen_t diagnostic_address(struct sockaddr_un *address)
{
	const char *name = SOCKET_NAME;
	size_t length = strlen(name);

#ifdef ROG5_DIAG_TESTING
	const char *suffix = getenv("ROG5_DIAG_TEST_SOCKET_SUFFIX");
	static char testing_name[sizeof(address->sun_path) - 1];
	size_t index;

	if (suffix != NULL) {
		if (strlen(suffix) < 1 || strlen(suffix) > 24)
			fail("invalid testing socket suffix");
		for (index = 0; suffix[index] != '\0'; index++) {
			if ((suffix[index] < 'a' || suffix[index] > 'z') &&
			    (suffix[index] < '0' || suffix[index] > '9'))
				fail("invalid testing socket suffix");
		}
		if (snprintf(testing_name, sizeof(testing_name), "%s-%s",
			     SOCKET_NAME, suffix) >= (int)sizeof(testing_name))
			fail("testing socket name exceeds policy");
		name = testing_name;
		length = strlen(name);
	}
#endif
	if (length + 1 > sizeof(address->sun_path))
		fail("diagnostic socket name exceeds policy");
	memset(address, 0, sizeof(*address));
	address->sun_family = AF_UNIX;
	memcpy(address->sun_path + 1, name, length);
	return (socklen_t)(offsetof(struct sockaddr_un, sun_path) + 1 + length);
}

static bool parse_small_decimal(const char *value, uint64_t *result)
{
	uint64_t parsed = 0;
	const char *cursor;

	if (*value == '\0' || (value[0] == '0' && value[1] != '\0'))
		return false;
	for (cursor = value; *cursor != '\0'; cursor++) {
		unsigned int digit;

		if (*cursor < '0' || *cursor > '9')
			return false;
		digit = (unsigned int)(*cursor - '0');
		if (parsed > (UINT64_MAX - digit) / 10)
			return false;
		parsed = parsed * 10 + digit;
	}
	*result = parsed;
	return true;
}

static bool parse_update(char *message, size_t length,
			 unsigned int *stage_code, const char **fault)
{
	static const char stage_prefix[] = "stage_code=";
	static const char fault_prefix[] = "fault=";
	char *newline;
	char *fault_value;
	uint64_t parsed;

	if (length < 1 || length >= UPDATE_MAX || message[length - 1] != '\n')
		return false;
	message[length] = '\0';
	if (strncmp(message, stage_prefix, sizeof(stage_prefix) - 1) != 0)
		return false;
	newline = strchr(message, '\n');
	if (newline == NULL)
		return false;
	*newline = '\0';
	if (!parse_small_decimal(message + sizeof(stage_prefix) - 1, &parsed) ||
	    parsed > UINT_MAX)
		return false;
	fault_value = newline + 1;
	if (strncmp(fault_value, fault_prefix, sizeof(fault_prefix) - 1) != 0)
		return false;
	fault_value += sizeof(fault_prefix) - 1;
	newline = strchr(fault_value, '\n');
	if (newline == NULL || newline[1] != '\0')
		return false;
	*newline = '\0';
	*fault = canonical_fault(fault_value);
	if (*fault == NULL)
		return false;
	*stage_code = (unsigned int)parsed;
	return true;
}

static bool take_evidence_field(char **cursor, const char *prefix,
				char *output, size_t output_size)
{
	char *newline;
	size_t length;

	if (strncmp(*cursor, prefix, strlen(prefix)) != 0)
		return false;
	*cursor += strlen(prefix);
	newline = strchr(*cursor, '\n');
	if (newline == NULL)
		return false;
	length = (size_t)(newline - *cursor);
	if (length >= output_size)
		return false;
	memcpy(output, *cursor, length);
	output[length] = '\0';
	*cursor = newline + 1;
	return true;
}

static bool parse_evidence_update(char *message, size_t length,
				  struct power_evidence *evidence)
{
	char *cursor = message;

	if (length < 1 || length >= UPDATE_MAX || message[length - 1] != '\n')
		return false;
	message[length] = '\0';
	if (!take_evidence_field(&cursor, "category=", evidence->category,
				 sizeof(evidence->category)) ||
	    !take_evidence_field(&cursor, "name=", evidence->name,
				 sizeof(evidence->name)) ||
	    !take_evidence_field(&cursor, "status=", evidence->status,
				 sizeof(evidence->status)) ||
	    !take_evidence_field(&cursor, "value=", evidence->value,
				 sizeof(evidence->value)) ||
	    *cursor != '\0' || !valid_evidence_token(evidence->category) ||
	    !valid_evidence_token(evidence->name) ||
	    (strcmp(evidence->status, "present") != 0 &&
	     strcmp(evidence->status, "absent") != 0 &&
	     strcmp(evidence->status, "error") != 0) ||
	    !valid_evidence_value(evidence->value) ||
	    (strcmp(evidence->status, "present") == 0 &&
	     evidence->value[0] == '\0'))
		return false;
	return true;
}

static bool apply_update(struct diagnostic_record *record,
			 unsigned int stage_code, const char *fault,
			 bool *terminal)
{
	if (valid_progress(stage_code)) {
		if (*terminal || stage_code < record->last_good ||
		    strcmp(fault, "none") != 0)
			return false;
		record->stage_code = stage_code;
		record->last_good = stage_code;
		record->fault = "none";
		return true;
	}
	if (stage_code != 200 || strcmp(fault, "none") == 0)
		return false;
	if (*terminal)
		return record->stage_code == 200 &&
		       strcmp(record->fault, fault) == 0;
	record->stage_code = 200;
	record->fault = fault;
	*terminal = true;
	return true;
}

static void count_dropped_update(struct diagnostic_record *record)
{
	if (record->dropped < 1000000)
		record->dropped++;
}

static void receive_updates(int descriptor,
			    struct diagnostic_record *record, bool *terminal,
			    struct power_evidence *evidence,
			    bool *evidence_pending)
{
	unsigned int received;

	if (*evidence_pending)
		return;
	for (received = 0; received < UPDATE_BATCH_MAX; received++) {
		char message[UPDATE_MAX];
		union {
			struct cmsghdr alignment;
			unsigned char bytes[
				CMSG_SPACE(sizeof(struct ucred)) +
				CMSG_SPACE(sizeof(int) * CONTROL_FDS_MAX)
			];
		} control;
		const char *fault;
		struct iovec vector = {
			.iov_base = message,
			.iov_len = sizeof(message) - 1,
		};
		struct msghdr header = {
			.msg_iov = &vector,
			.msg_iovlen = 1,
			.msg_control = control.bytes,
			.msg_controllen = sizeof(control.bytes),
		};
		struct cmsghdr *item;
		struct ucred credentials;
		unsigned int stage_code;
		bool credentials_seen = false;
		bool rights_seen = false;
		ssize_t length;

		length = recvmsg(descriptor, &header,
				 MSG_DONTWAIT | MSG_TRUNC | MSG_CMSG_CLOEXEC);
		if (length < 0 && errno == EINTR)
			continue;
		if (length < 0 && (errno == EAGAIN || errno == EWOULDBLOCK))
			return;
		if (length < 0) {
			count_dropped_update(record);
			return;
		}
		for (item = CMSG_FIRSTHDR(&header); item != NULL;
		     item = CMSG_NXTHDR(&header, item)) {
			if (item->cmsg_level != SOL_SOCKET)
				continue;
			if (item->cmsg_type == SCM_RIGHTS) {
				size_t data_length;
				size_t index;
				int *descriptors;

				rights_seen = true;
				if (item->cmsg_len < CMSG_LEN(0))
					continue;
				data_length = item->cmsg_len - CMSG_LEN(0);
				descriptors = (int *)CMSG_DATA(item);
				for (index = 0; index < data_length / sizeof(int);
				     index++)
					close(descriptors[index]);
			} else if (item->cmsg_type == SCM_CREDENTIALS &&
				   item->cmsg_len ==
					CMSG_LEN(sizeof(struct ucred))) {
				if (credentials_seen) {
					rights_seen = true;
					continue;
				}
				memcpy(&credentials, CMSG_DATA(item),
				       sizeof(credentials));
				credentials_seen = true;
			}
		}
		if ((header.msg_flags & MSG_CTRUNC) != 0 || rights_seen ||
		    !credentials_seen || credentials.pid <= 0 ||
#ifdef ROG5_DIAG_TESTING
		    credentials.uid != geteuid()
#else
		    credentials.uid != 0
#endif
		    ) {
			count_dropped_update(record);
			continue;
		}
		if (parse_update(message, (size_t)length, &stage_code, &fault)) {
			if (!apply_update(record, stage_code, fault, terminal))
				count_dropped_update(record);
			continue;
		}
		if (!*terminal && parse_evidence_update(
			    message, (size_t)length, evidence)) {
			evidence->sequence++;
			*evidence_pending = true;
			return;
		}
		count_dropped_update(record);
	}
}

static int create_update_server(void)
{
	struct sockaddr_un address;
	socklen_t length = diagnostic_address(&address);
	int descriptor;
	int enabled = 1;

	descriptor = socket(AF_UNIX,
			    SOCK_DGRAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
	if (descriptor < 0)
		fail("cannot create diagnostic update socket");
	if (setsockopt(descriptor, SOL_SOCKET, SO_PASSCRED,
		       &enabled, sizeof(enabled)) < 0) {
		close(descriptor);
		fail("cannot require diagnostic peer credentials");
	}
	if (bind(descriptor, (struct sockaddr *)&address, length) < 0) {
		close(descriptor);
		fail("cannot bind diagnostic update socket");
	}
	return descriptor;
}

static int open_output(void)
{
#ifdef ROG5_DIAG_TESTING
	const char *testing = getenv("ROG5_DIAG_TEST_OUTPUT_FD");

	if (testing != NULL) {
		uint64_t descriptor;

		if (!parse_small_decimal(testing, &descriptor) ||
		    descriptor > INT_MAX)
			fail("invalid testing output descriptor");
		return dup((int)descriptor);
	}
#endif
	{
		struct termios attributes;
		int descriptor;

		descriptor = open("/dev/ttyGS0",
				  O_WRONLY | O_NONBLOCK | O_NOCTTY | O_CLOEXEC);
		if (descriptor < 0)
			return -1;
		if (ioctl(descriptor, TIOCEXCL) < 0 ||
		    tcgetattr(descriptor, &attributes) < 0) {
			close(descriptor);
			return -1;
		}
		attributes.c_iflag &=
			~(IGNBRK | BRKINT | PARMRK | ISTRIP | INLCR | IGNCR |
			  ICRNL | IXON);
		attributes.c_oflag &= ~OPOST;
		attributes.c_lflag &= ~(ECHO | ECHONL | ICANON | ISIG | IEXTEN);
		attributes.c_cflag &= ~(CSIZE | PARENB | HUPCL);
		attributes.c_cflag |= CS8 | CLOCAL;
		if (cfsetispeed(&attributes, B115200) < 0 ||
		    cfsetospeed(&attributes, B115200) < 0 ||
		    tcsetattr(descriptor, TCSANOW, &attributes) < 0) {
			close(descriptor);
			return -1;
		}
		return descriptor;
	}
}

static uint64_t testing_frame_limit(void)
{
#ifdef ROG5_DIAG_TESTING
	const char *value = getenv("ROG5_DIAG_TEST_FRAME_LIMIT");
	uint64_t limit;

	if (value != NULL) {
		if (!parse_small_decimal(value, &limit) || limit < 1 || limit > 100)
			fail("invalid testing frame limit");
		return limit;
	}
#endif
	return 0;
}

static void serve_diagnostics(int argc, char **argv)
{
	struct power_evidence evidence = { .sequence = 0 };
	char pending[FRAME_MAX];
	struct diagnostic_record record;
	struct pollfd update_poll;
	uint64_t frame_limit;
	uint64_t frames = 0;
	uint64_t next_frame;
	size_t pending_length = 0;
	size_t pending_offset = 0;
	bool terminal = false;
	bool evidence_pending = false;
	int output = -1;
	int update_socket;

	if (argc != 5)
		fail("usage: serve CANDIDATE BOOT_ID WATCHDOG_DEADLINE_MS");
	record = (struct diagnostic_record) {
		.candidate = argv[2],
		.boot_id = argv[3],
		.sequence = 1,
		.boottime = monotonic_milliseconds(),
		.stage_code = 10,
		.last_good = 10,
		.fault = "none",
		.deadline = number(argv[4], 1, UINT64_MAX,
				   "invalid watchdog deadline"),
		.dropped = 0,
	};
	validate_record(&record);
	if (record.boottime >= record.deadline ||
	    record.deadline - record.boottime > WATCHDOG_INTERVAL_MAX_MS)
		fail("invalid remaining watchdog interval");
	update_socket = create_update_server();
	update_poll = (struct pollfd) {
		.fd = update_socket,
		.events = POLLIN,
	};
	frame_limit = testing_frame_limit();
	/* Identity must reach the stream before socket-ready evidence updates. */
	pending_length = format_frame(&record, pending);
	record.sequence++;
	next_frame = record.boottime + HEARTBEAT_MS;

	while (true) {
		uint64_t now = monotonic_milliseconds();
		int timeout;

		receive_updates(update_socket, &record, &terminal, &evidence,
				&evidence_pending);
		if (!terminal && record.deadline >= PRETIMEOUT_MS &&
		    now >= record.deadline - PRETIMEOUT_MS) {
			record.stage_code = 210;
			record.fault = "none";
			terminal = true;
		}
		if (pending_length == 0 && evidence_pending) {
			record.boottime = now;
			pending_length = format_evidence_frame(
				&record, &evidence, pending);
			pending_offset = 0;
			evidence_pending = false;
		} else if (pending_length == 0 && now >= next_frame) {
			record.boottime = now;
			pending_length = format_frame(&record, pending);
			pending_offset = 0;
			record.sequence++;
			next_frame = now + HEARTBEAT_MS;
		}
		if (output < 0)
			output = open_output();
		if (output >= 0 && pending_length > pending_offset) {
			ssize_t written = write(output, pending + pending_offset,
						pending_length - pending_offset);

			if (written > 0) {
				pending_offset += (size_t)written;
				if (pending_offset == pending_length) {
					pending_length = 0;
					frames++;
					if (frame_limit != 0 && frames >= frame_limit)
						break;
				}
			} else if (written < 0 && errno != EINTR &&
				   errno != EAGAIN && errno != EWOULDBLOCK) {
				close(output);
				output = -1;
				pending_length = 0;
				pending_offset = 0;
			}
		}
		now = monotonic_milliseconds();
		if (next_frame <= now)
			timeout = 0;
		else if (next_frame - now > 25)
			timeout = 25;
		else
			timeout = (int)(next_frame - now);
		if (poll(&update_poll, 1, timeout) < 0 && errno != EINTR)
			fail("diagnostic update poll failed");
	}
	if (output >= 0)
		close(output);
	close(update_socket);
}

static void send_update(int argc, char **argv)
{
	char message[UPDATE_MAX];
	struct sockaddr_un address;
	uint64_t stage_code;
	socklen_t address_length;
	const char *fault;
	int descriptor;
	int length;
	ssize_t sent;

	if (argc != 3 && argc != 4)
		fail("usage: emit STAGE_CODE [FAULT]");
	stage_code = number(argv[2], 10, 200, "invalid update stage code");
	if (stage_code > UINT_MAX)
		fail("update stage code overflow");
	fault = argc == 4 ? argv[3] : "none";
	if (!valid_fault(fault) ||
	    (valid_progress((unsigned int)stage_code) &&
	     strcmp(fault, "none") != 0) ||
	    (stage_code == 200 && strcmp(fault, "none") == 0) ||
	    (!valid_progress((unsigned int)stage_code) && stage_code != 200))
		fail("inconsistent diagnostic update");
	length = snprintf(message, sizeof(message),
			  "stage_code=%" PRIu64 "\nfault=%s\n",
			  stage_code, fault);
	if (length < 1 || (size_t)length >= sizeof(message))
		fail("diagnostic update exceeds policy");
	descriptor = socket(AF_UNIX,
			    SOCK_DGRAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
	if (descriptor < 0)
		fail("cannot create diagnostic update client");
	address_length = diagnostic_address(&address);
	sent = sendto(descriptor, message, (size_t)length,
		      MSG_DONTWAIT | MSG_NOSIGNAL,
		      (struct sockaddr *)&address, address_length);
	close(descriptor);
	if (sent != length)
		fail("cannot publish diagnostic update");
}

static void send_evidence(int argc, char **argv)
{
	char message[UPDATE_MAX];
	struct sockaddr_un address;
	socklen_t address_length;
	int descriptor;
	int length;
	ssize_t sent;

	if (argc != 6)
		fail("usage: evidence CATEGORY NAME STATUS HEX_VALUE");
	if (!valid_evidence_token(argv[2]) ||
	    !valid_evidence_token(argv[3]) ||
	    (strcmp(argv[4], "present") != 0 &&
	     strcmp(argv[4], "absent") != 0 &&
	     strcmp(argv[4], "error") != 0) ||
	    !valid_evidence_value(argv[5]) ||
	    (strcmp(argv[4], "present") == 0 && argv[5][0] == '\0'))
		fail("invalid power evidence update");
	length = snprintf(message, sizeof(message),
			  "category=%s\nname=%s\nstatus=%s\nvalue=%s\n",
			  argv[2], argv[3], argv[4], argv[5]);
	if (length < 1 || (size_t)length >= sizeof(message))
		fail("power evidence update exceeds policy");
	descriptor = socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0);
	if (descriptor < 0)
		fail("cannot create power evidence client");
	address_length = diagnostic_address(&address);
	sent = sendto(descriptor, message, (size_t)length, MSG_NOSIGNAL,
		      (struct sockaddr *)&address, address_length);
	close(descriptor);
	if (sent != length)
		fail("cannot publish power evidence update");
}

int main(int argc, char **argv)
{
	if (argc < 2)
		fail("missing diagnostic operation");
	if (strcmp(argv[1], "frame") == 0)
		emit_frame(argc, argv);
	else if (strcmp(argv[1], "serve") == 0)
		serve_diagnostics(argc, argv);
	else if (strcmp(argv[1], "emit") == 0)
		send_update(argc, argv);
	else if (strcmp(argv[1], "evidence") == 0)
		send_evidence(argc, argv);
	else
		fail("unknown diagnostic operation");
	return EXIT_SUCCESS;
}
