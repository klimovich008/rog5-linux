#define _GNU_SOURCE

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <unistd.h>

#define FRAME_MAX 4096
#define RESPONSE_MAX 2048
#define STATE_FILE_MAX 8192
#define LEDGER_MAX 32
#define ID_LENGTH 32
#define HASH_LENGTH 64
#define BUNDLE_MAX 64
#define PLAN_MAX 2048
#define CMDLINE_MAX 1024
#define PROFILE_MAX 31
#define TARGET_MAX 64
#define RELEASE_MAX 96
#define HANDOFF_FD 3
#define HANDOFF_DESCRIPTOR_COUNT 3
/* Linux limits one SCM_RIGHTS packet to SCM_MAX_FD (253) descriptors. */
#define HANDOFF_CONTROL_FD_MAX 253
#define FETCH_TIMEOUT_MS 65000
#define VERIFY_TIMEOUT_MS 30000
#define KEXEC_LOAD_TIMEOUT_MS 15000
#define CHILD_REAP_TIMEOUT_MS 1000
#define FETCH_BUNDLE_CONFLICT_EXIT 42
#define KERNEL_MAX (128ULL * 1024 * 1024)
#define DTB_MAX (2ULL * 1024 * 1024)
#define INITRAMFS_MAX (256ULL * 1024 * 1024)
#define REQUIRED_SEALS \
	(F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE)

#define ZERO_ID "00000000000000000000000000000000"
#define ZERO_HASH \
	"0000000000000000000000000000000000000000000000000000000000000000"

struct sha256 {
	uint32_t state[8];
	uint64_t bytes;
	unsigned char buffer[64];
	size_t used;
};

struct request {
	char session[ID_LENGTH + 1];
	char request[ID_LENGTH + 1];
	char verb[16];
	char body_sha256[HASH_LENGTH + 1];
	char bundle[BUNDLE_MAX + 1];
	char manifest_sha256[HASH_LENGTH + 1];
	char prepare_request[ID_LENGTH + 1];
	char fingerprint[HASH_LENGTH + 1];
};

enum phase {
	PHASE_IDLE,
	PHASE_PREPARED,
	PHASE_CLAIMED,
	PHASE_EXEC_FAILED,
};

enum prepare_outcome {
	PREPARE_OUTCOME_OK,
	PREPARE_OUTCOME_FETCH_FAILED,
	PREPARE_OUTCOME_BUNDLE_ID_CONFLICT,
	PREPARE_OUTCOME_VERIFY_FAILED,
};

struct control_state {
	char session[ID_LENGTH + 1];
	enum phase phase;
	char prepared_bundle[BUNDLE_MAX + 1];
	char manifest_sha256[HASH_LENGTH + 1];
	char prepare_request[ID_LENGTH + 1];
	char prepare_fingerprint[HASH_LENGTH + 1];
	char commit_request[ID_LENGTH + 1];
	char commit_fingerprint[HASH_LENGTH + 1];
	bool execution_started;
	char last_error[24];
};

struct response_action {
	char payload[RESPONSE_MAX];
	size_t payload_length;
	bool execute;
};

struct verified_plan {
	char bundle[BUNDLE_MAX + 1];
	char manifest_sha256[HASH_LENGTH + 1];
	char profile[PROFILE_MAX + 1];
	char target_id[TARGET_MAX + 1];
	char target_release[RELEASE_MAX + 1];
	uint64_t target_timeout;
	char command_line[CMDLINE_MAX];
};

static int state_fd = -1;
static int ledger_fd = -1;
static int watchdog_pidfd = -1;
static const char *device_path = "/dev/ttyGS0";
/* Production state must remain session-scoped tmpfs, never persistent media. */
static const char *state_path = "/run/rog5-control";
static const char *watchdog_path = "/run/rog5-recovery-watchdog.lease";
static const char *fetcher_path = "/usr/libexec/rog5-bundle-fetch";
static const char *verifier_path = "/usr/libexec/rog5-bundle-verify";
static const char *kexec_path = "/usr/sbin/kexec";
static unsigned int io_timeout_ms = 2000;
static unsigned int fetch_timeout_ms = FETCH_TIMEOUT_MS;
static unsigned int verify_timeout_ms = VERIFY_TIMEOUT_MS;
static unsigned int kexec_load_timeout_ms = KEXEC_LOAD_TIMEOUT_MS;
#ifdef ROG5_CONTROL_TESTING
static bool test_kexec_configured;
#endif

static void fail(const char *format, ...)
{
	va_list arguments;

	va_start(arguments, format);
	fputs("rog5-recovery-control: ", stderr);
	vfprintf(stderr, format, arguments);
	fputc('\n', stderr);
	va_end(arguments);
	exit(EXIT_FAILURE);
}

static void sleep_milliseconds(unsigned int milliseconds)
{
	struct timespec delay = {
		.tv_sec = milliseconds / 1000,
		.tv_nsec = (long)(milliseconds % 1000) * 1000000L,
	};

	while (nanosleep(&delay, &delay) < 0 && errno == EINTR)
		;
}

static uint32_t rotate_right(uint32_t value, unsigned int bits)
{
	return (value >> bits) | (value << (32 - bits));
}

static void sha256_transform(struct sha256 *context,
			     const unsigned char block[64])
{
	static const uint32_t constants[64] = {
		0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
		0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
		0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
		0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
		0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
		0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
		0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
		0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
		0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
		0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
		0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
		0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
		0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
		0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
		0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
		0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
	};
	uint32_t words[64];
	uint32_t a;
	uint32_t b;
	uint32_t c;
	uint32_t d;
	uint32_t e;
	uint32_t f;
	uint32_t g;
	uint32_t h;
	unsigned int index;

	for (index = 0; index < 16; index++) {
		words[index] = (uint32_t)block[index * 4] << 24;
		words[index] |= (uint32_t)block[index * 4 + 1] << 16;
		words[index] |= (uint32_t)block[index * 4 + 2] << 8;
		words[index] |= block[index * 4 + 3];
	}
	for (index = 16; index < 64; index++) {
		uint32_t first = rotate_right(words[index - 15], 7) ^
			rotate_right(words[index - 15], 18) ^
			(words[index - 15] >> 3);
		uint32_t second = rotate_right(words[index - 2], 17) ^
			rotate_right(words[index - 2], 19) ^
			(words[index - 2] >> 10);

		words[index] = words[index - 16] + first +
			words[index - 7] + second;
	}

	a = context->state[0];
	b = context->state[1];
	c = context->state[2];
	d = context->state[3];
	e = context->state[4];
	f = context->state[5];
	g = context->state[6];
	h = context->state[7];
	for (index = 0; index < 64; index++) {
		uint32_t choice = (e & f) ^ (~e & g);
		uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
		uint32_t upper_e = rotate_right(e, 6) ^
			rotate_right(e, 11) ^ rotate_right(e, 25);
		uint32_t upper_a = rotate_right(a, 2) ^
			rotate_right(a, 13) ^ rotate_right(a, 22);
		uint32_t first = h + upper_e + choice +
			constants[index] + words[index];
		uint32_t second = upper_a + majority;

		h = g;
		g = f;
		f = e;
		e = d + first;
		d = c;
		c = b;
		b = a;
		a = first + second;
	}
	context->state[0] += a;
	context->state[1] += b;
	context->state[2] += c;
	context->state[3] += d;
	context->state[4] += e;
	context->state[5] += f;
	context->state[6] += g;
	context->state[7] += h;
}

static void sha256_init(struct sha256 *context)
{
	static const uint32_t initial[8] = {
		0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
		0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
	};

	memcpy(context->state, initial, sizeof(initial));
	context->bytes = 0;
	context->used = 0;
}

static void sha256_update(struct sha256 *context, const void *input,
			  size_t length)
{
	const unsigned char *bytes = input;

	context->bytes += length;
	while (length > 0) {
		size_t available = sizeof(context->buffer) - context->used;
		size_t take = length < available ? length : available;

		memcpy(context->buffer + context->used, bytes, take);
		context->used += take;
		bytes += take;
		length -= take;
		if (context->used == sizeof(context->buffer)) {
			sha256_transform(context, context->buffer);
			context->used = 0;
		}
	}
}

static void sha256_final(struct sha256 *context, unsigned char output[32])
{
	uint64_t bits = context->bytes * 8;
	unsigned int index;

	context->buffer[context->used++] = 0x80;
	if (context->used > 56) {
		memset(context->buffer + context->used, 0,
		       sizeof(context->buffer) - context->used);
		sha256_transform(context, context->buffer);
		context->used = 0;
	}
	memset(context->buffer + context->used, 0, 56 - context->used);
	for (index = 0; index < 8; index++)
		context->buffer[63 - index] = (unsigned char)(bits >> (index * 8));
	sha256_transform(context, context->buffer);
	for (index = 0; index < 8; index++) {
		output[index * 4] =
			(unsigned char)(context->state[index] >> 24);
		output[index * 4 + 1] =
			(unsigned char)(context->state[index] >> 16);
		output[index * 4 + 2] =
			(unsigned char)(context->state[index] >> 8);
		output[index * 4 + 3] =
			(unsigned char)context->state[index];
	}
}

static void hash_bytes(const void *data, size_t length,
		       char output[HASH_LENGTH + 1])
{
	static const char digits[] = "0123456789abcdef";
	struct sha256 context;
	unsigned char digest[32];
	unsigned int index;

	sha256_init(&context);
	sha256_update(&context, data, length);
	sha256_final(&context, digest);
	for (index = 0; index < sizeof(digest); index++) {
		output[index * 2] = digits[digest[index] >> 4];
		output[index * 2 + 1] = digits[digest[index] & 0xf];
	}
	output[HASH_LENGTH] = '\0';
}

static bool valid_hex(const char *value, size_t length)
{
	size_t index;

	if (strlen(value) != length)
		return false;
	for (index = 0; index < length; index++) {
		if (!((value[index] >= '0' && value[index] <= '9') ||
		      (value[index] >= 'a' && value[index] <= 'f')))
			return false;
	}
	return true;
}

static bool valid_id(const char *value, bool allow_zero)
{
	return valid_hex(value, ID_LENGTH) &&
		(allow_zero || strcmp(value, ZERO_ID) != 0);
}

static bool valid_hash(const char *value, bool allow_zero)
{
	return valid_hex(value, HASH_LENGTH) &&
		(allow_zero || strcmp(value, ZERO_HASH) != 0);
}

static bool valid_bundle(const char *value)
{
	size_t length = strlen(value);
	size_t index;

	if (length < 1 || length > BUNDLE_MAX || strcmp(value, "none") == 0)
		return false;
	if (!((value[0] >= 'a' && value[0] <= 'z') ||
	      (value[0] >= '0' && value[0] <= '9')))
		return false;
	if (strstr(value, "..") != NULL)
		return false;
	for (index = 1; index < length; index++) {
		char byte = value[index];

		if (!((byte >= 'a' && byte <= 'z') ||
		      (byte >= '0' && byte <= '9') ||
		      byte == '.' || byte == '_' || byte == '-'))
			return false;
	}
	return true;
}

static bool valid_result_for_verb(const char *verb, const char *result)
{
	if (strcmp(result, "REQUEST_CONFLICT") == 0 ||
	    strcmp(result, "LEDGER_FULL") == 0)
		return true;
	if (strcmp(verb, "PREPARE") == 0) {
		return strcmp(result, "PREPARED") == 0 ||
			strcmp(result, "FETCH_FAILED") == 0 ||
			strcmp(result, "BUNDLE_ID_CONFLICT") == 0 ||
			strcmp(result, "VERIFY_FAILED") == 0 ||
			strcmp(result, "PREPARE_ID_CONFLICT") == 0 ||
			strcmp(result, "BUNDLE_CONFLICT") == 0 ||
			strcmp(result, "SESSION_CONSUMED") == 0;
	}
	if (strcmp(verb, "COMMIT_EXEC") == 0) {
		return strcmp(result, "PREPARE_REQUIRED") == 0 ||
			strcmp(result, "PREPARE_MISMATCH") == 0 ||
			strcmp(result, "CLAIMED") == 0 ||
			strcmp(result, "ALREADY_CLAIMED") == 0;
	}
	return false;
}

static void random_hex(char output[ID_LENGTH + 1])
{
	static const char digits[] = "0123456789abcdef";
	unsigned char bytes[ID_LENGTH / 2];
	ssize_t count;
	size_t index;
	bool nonzero = false;

	do {
		count = getrandom(bytes, sizeof(bytes), 0);
	} while (count < 0 && errno == EINTR);
	if (count != (ssize_t)sizeof(bytes))
		fail("getrandom failed: %s", strerror(errno));
	for (index = 0; index < sizeof(bytes); index++) {
		output[index * 2] = digits[bytes[index] >> 4];
		output[index * 2 + 1] = digits[bytes[index] & 0xf];
		if (bytes[index] != 0)
			nonzero = true;
	}
	if (!nonzero)
		fail("getrandom returned an all-zero session");
	output[ID_LENGTH] = '\0';
}

static void write_all(int descriptor, const void *data, size_t length)
{
	const unsigned char *bytes = data;

	while (length > 0) {
		ssize_t count = write(descriptor, bytes, length);

		if (count < 0 && errno == EINTR)
			continue;
		if (count <= 0)
			fail("state write failed: %s", strerror(errno));
		bytes += count;
		length -= (size_t)count;
	}
}

static void persistence_crash(const char *name, const char *stage)
{
#ifdef ROG5_CONTROL_TESTING
	const char *selected = getenv("ROG5_TEST_PERSIST_CRASH");
	char expected[128];
	int length;

	if (selected == NULL)
		return;
	length = snprintf(expected, sizeof(expected), "%s:%s", name, stage);
	if (length < 0 || length >= (int)sizeof(expected))
		fail("persistence crash selector is too large");
	if (strcmp(selected, expected) == 0)
		_exit(88);
#else
	(void)name;
	(void)stage;
#endif
}

static int create_immutable_at(int directory, const char *name,
			       const void *data, size_t length)
{
	char temporary[96];
	char nonce[ID_LENGTH + 1];
	int descriptor;
	int result;

	random_hex(nonce);
	if (snprintf(temporary, sizeof(temporary), ".tmp-%ld-%s",
		     (long)getpid(), nonce) >= (int)sizeof(temporary))
		fail("temporary state name is too long");
	descriptor = openat(directory, temporary,
			    O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW |
			    O_CLOEXEC, 0600);
	if (descriptor < 0)
		fail("cannot create state temporary: %s", strerror(errno));
	persistence_crash(name, "before_write");
	write_all(descriptor, data, length);
	persistence_crash(name, "after_write");
	if (fsync(descriptor) < 0)
		fail("cannot fsync state temporary: %s", strerror(errno));
	persistence_crash(name, "after_file_fsync");
	if (close(descriptor) < 0)
		fail("cannot close state temporary: %s", strerror(errno));

	result = linkat(directory, temporary, directory, name, 0);
	if (result < 0 && errno != EEXIST)
		fail("cannot publish immutable state: %s", strerror(errno));
	if (result == 0)
		persistence_crash(name, "after_link");
	if (unlinkat(directory, temporary, 0) < 0)
		fail("cannot remove state temporary: %s", strerror(errno));
	if (result == 0)
		persistence_crash(name, "after_unlink");
	if (result == 0 && fsync(directory) < 0)
		fail("cannot fsync state directory: %s", strerror(errno));
	if (result == 0)
		persistence_crash(name, "after_dir_fsync");
	return result == 0 ? 1 : 0;
}

static void replace_at(int directory, const char *name,
		       const void *data, size_t length)
{
	char temporary[96];
	char nonce[ID_LENGTH + 1];
	int descriptor;

	random_hex(nonce);
	if (snprintf(temporary, sizeof(temporary), ".tmp-%ld-%s",
		     (long)getpid(), nonce) >= (int)sizeof(temporary))
		fail("temporary state name is too long");
	descriptor = openat(directory, temporary,
			    O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW |
			    O_CLOEXEC, 0600);
	if (descriptor < 0)
		fail("cannot create state temporary: %s", strerror(errno));
	persistence_crash(name, "before_write");
	write_all(descriptor, data, length);
	persistence_crash(name, "after_write");
	if (fsync(descriptor) < 0)
		fail("cannot fsync state temporary: %s", strerror(errno));
	persistence_crash(name, "after_file_fsync");
	if (close(descriptor) < 0)
		fail("cannot close state temporary: %s", strerror(errno));
	persistence_crash(name, "before_rename");
	if (renameat(directory, temporary, directory, name) < 0)
		fail("cannot publish state: %s", strerror(errno));
	persistence_crash(name, "after_rename");
	if (fsync(directory) < 0)
		fail("cannot fsync state directory: %s", strerror(errno));
	persistence_crash(name, "after_dir_fsync");
}

static int read_file_at(int directory, const char *name, char *output,
			size_t capacity, size_t *length)
{
	struct stat metadata;
	int descriptor;
	size_t used = 0;

	descriptor = openat(directory, name,
			    O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
	if (descriptor < 0 && errno == ENOENT)
		return 0;
	if (descriptor < 0)
		fail("cannot open state file %s: %s", name, strerror(errno));
	if (fstat(descriptor, &metadata) < 0)
		fail("cannot stat state file %s: %s", name, strerror(errno));
	if (!S_ISREG(metadata.st_mode) || metadata.st_uid != geteuid() ||
	    (metadata.st_mode & 0077) != 0 || metadata.st_size < 1 ||
	    (uintmax_t)metadata.st_size >= capacity)
		fail("unsafe state file: %s", name);
	while (used < (size_t)metadata.st_size) {
		ssize_t count = read(descriptor, output + used,
				     (size_t)metadata.st_size - used);

		if (count < 0 && errno == EINTR)
			continue;
		if (count <= 0)
			fail("short state read: %s", name);
		used += (size_t)count;
	}
	if (close(descriptor) < 0)
		fail("cannot close state file %s: %s", name, strerror(errno));
	output[used] = '\0';
	*length = used;
	return 1;
}

static void open_state_directories(void)
{
	struct stat metadata;

	if (mkdir(state_path, 0700) < 0 && errno != EEXIST)
		fail("cannot create state directory: %s", strerror(errno));
	state_fd = open(state_path,
			O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
	if (state_fd < 0)
		fail("cannot open state directory: %s", strerror(errno));
	if (fstat(state_fd, &metadata) < 0)
		fail("cannot stat state directory: %s", strerror(errno));
	if (!S_ISDIR(metadata.st_mode) || metadata.st_uid != geteuid() ||
	    (metadata.st_mode & 0077) != 0)
		fail("unsafe state directory");
	if (mkdirat(state_fd, "requests", 0700) < 0 && errno != EEXIST)
		fail("cannot create request ledger: %s", strerror(errno));
	ledger_fd = openat(state_fd, "requests",
			   O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
	if (ledger_fd < 0)
		fail("cannot open request ledger: %s", strerror(errno));
	if (fstat(ledger_fd, &metadata) < 0)
		fail("cannot stat request ledger: %s", strerror(errno));
	if (!S_ISDIR(metadata.st_mode) || metadata.st_uid != geteuid() ||
	    (metadata.st_mode & 0077) != 0)
		fail("unsafe request ledger");
	if (fsync(state_fd) < 0)
		fail("cannot fsync state directory: %s", strerror(errno));
}

static int take_field(char **cursor, const char *name, char *output,
		      size_t capacity)
{
	char *start = *cursor;
	char *newline = strchr(start, '\n');
	size_t name_length = strlen(name);
	size_t value_length;
	size_t index;

	if (newline == NULL || strncmp(start, name, name_length) != 0 ||
	    start[name_length] != '=')
		return -1;
	value_length = (size_t)(newline - start) - name_length - 1;
	if (value_length < 1 || value_length >= capacity)
		return -1;
	for (index = 0; index < value_length; index++) {
		unsigned char byte =
			(unsigned char)start[name_length + 1 + index];

		if (byte < 0x21 || byte > 0x7e)
			return -1;
	}
	memcpy(output, start + name_length + 1, value_length);
	output[value_length] = '\0';
	*cursor = newline + 1;
	return 0;
}

static const char *phase_name(enum phase phase)
{
	switch (phase) {
	case PHASE_IDLE:
		return "IDLE";
	case PHASE_PREPARED:
		return "PREPARED";
	case PHASE_CLAIMED:
		return "CLAIMED";
	case PHASE_EXEC_FAILED:
		return "EXEC_FAILED";
	}
	fail("invalid control phase");
	return NULL;
}

static void set_last_error(struct control_state *state, const char *error)
{
	char payload[64];
	int length;

	length = snprintf(payload, sizeof(payload), "error=%s\n", error);
	if (length < 0 || length >= (int)sizeof(payload))
		fail("last-error payload is too large");
	replace_at(state_fd, "last-error", payload, (size_t)length);
	if (snprintf(state->last_error, sizeof(state->last_error), "%s",
		     error) >= (int)sizeof(state->last_error))
		fail("last-error token is too large");
}

static void load_session(struct control_state *state)
{
	char payload[96];
	char generated[ID_LENGTH + 1];
	char *cursor;
	size_t length;
	int created;

	if (read_file_at(state_fd, "session", payload, sizeof(payload),
			 &length)) {
		cursor = payload;
		if (take_field(&cursor, "session", state->session,
			       sizeof(state->session)) < 0 ||
		    *cursor != '\0' || !valid_id(state->session, false))
			fail("invalid persisted session");
		return;
	}

	random_hex(generated);
	if (snprintf(payload, sizeof(payload), "session=%s\n", generated) >=
	    (int)sizeof(payload))
		fail("session payload is too large");
	created = create_immutable_at(state_fd, "session", payload,
				      strlen(payload));
	if (!created) {
		load_session(state);
		return;
	}
	memcpy(state->session, generated, sizeof(state->session));
}

static void load_state(struct control_state *state)
{
	char payload[512];
	char *cursor;
	size_t length;

	memset(state, 0, sizeof(*state));
	state->phase = PHASE_IDLE;
	memcpy(state->last_error, "NONE", sizeof("NONE"));
	load_session(state);

	if (read_file_at(state_fd, "prepared", payload, sizeof(payload),
			 &length)) {
		cursor = payload;
		if (take_field(&cursor, "bundle", state->prepared_bundle,
			       sizeof(state->prepared_bundle)) < 0 ||
		    take_field(&cursor, "manifest_sha256",
			       state->manifest_sha256,
			       sizeof(state->manifest_sha256)) < 0 ||
		    take_field(&cursor, "prepare_request",
			       state->prepare_request,
			       sizeof(state->prepare_request)) < 0 ||
		    take_field(&cursor, "prepare_fingerprint",
			       state->prepare_fingerprint,
			       sizeof(state->prepare_fingerprint)) < 0 ||
		    *cursor != '\0' ||
		    !valid_bundle(state->prepared_bundle) ||
		    !valid_hash(state->manifest_sha256, false) ||
		    !valid_id(state->prepare_request, false) ||
		    !valid_hash(state->prepare_fingerprint, false))
			fail("invalid prepared state");
		state->phase = PHASE_PREPARED;
	}

	if (read_file_at(state_fd, "claim", payload, sizeof(payload),
			 &length)) {
		char prepare[ID_LENGTH + 1];
		char manifest[HASH_LENGTH + 1];

		if (state->phase != PHASE_PREPARED)
			fail("claim exists without prepared state");
		cursor = payload;
		if (take_field(&cursor, "request", state->commit_request,
			       sizeof(state->commit_request)) < 0 ||
		    take_field(&cursor, "fingerprint",
			       state->commit_fingerprint,
			       sizeof(state->commit_fingerprint)) < 0 ||
		    take_field(&cursor, "prepare_request", prepare,
			       sizeof(prepare)) < 0 ||
		    take_field(&cursor, "manifest_sha256", manifest,
			       sizeof(manifest)) < 0 ||
		    *cursor != '\0' ||
		    !valid_id(state->commit_request, false) ||
		    !valid_hash(state->commit_fingerprint, false) ||
		    strcmp(prepare, state->prepare_request) != 0 ||
		    strcmp(manifest, state->manifest_sha256) != 0)
			fail("invalid commit claim");
		state->phase = PHASE_CLAIMED;
	}

	if (read_file_at(state_fd, "execution-started", payload,
			 sizeof(payload), &length)) {
		char fingerprint[HASH_LENGTH + 1];

		if (state->phase != PHASE_CLAIMED)
			fail("execution marker exists without a claim");
		cursor = payload;
		if (take_field(&cursor, "commit_fingerprint", fingerprint,
			       sizeof(fingerprint)) < 0 ||
		    *cursor != '\0' ||
		    strcmp(fingerprint, state->commit_fingerprint) != 0)
			fail("invalid execution marker");
		state->execution_started = true;
	}

	if (read_file_at(state_fd, "last-error", payload, sizeof(payload),
			 &length)) {
		cursor = payload;
		if (take_field(&cursor, "error", state->last_error,
			       sizeof(state->last_error)) < 0 ||
		    *cursor != '\0')
			fail("invalid last-error state");
		if (strcmp(state->last_error, "NONE") != 0 &&
		    strcmp(state->last_error, "FETCH_FAILED") != 0 &&
		    strcmp(state->last_error, "BUNDLE_ID_CONFLICT") != 0 &&
		    strcmp(state->last_error, "VERIFY_FAILED") != 0 &&
		    strcmp(state->last_error, "LEDGER_FULL") != 0 &&
		    strcmp(state->last_error, "EXEC_FAILED") != 0 &&
		    strcmp(state->last_error, "EXEC_RETURNED") != 0)
			fail("unknown last-error state");
	}

	if (read_file_at(state_fd, "failure", payload, sizeof(payload),
			 &length)) {
		char error[24];

		if (state->phase != PHASE_CLAIMED ||
		    !state->execution_started)
			fail("failure exists without execution");
		cursor = payload;
		if (take_field(&cursor, "error", error, sizeof(error)) < 0 ||
		    *cursor != '\0' ||
		    (strcmp(error, "EXEC_FAILED") != 0 &&
		     strcmp(error, "EXEC_RETURNED") != 0))
			fail("invalid execution failure");
		state->phase = PHASE_EXEC_FAILED;
		memcpy(state->last_error, error, strlen(error) + 1);
	}
}

static int decode_request(const unsigned char *payload, size_t length,
			  struct request *request)
{
	char copy[FRAME_MAX + 1];
	char version[8];
	char kind[16];
	char *cursor;
	char body[256];
	char calculated[HASH_LENGTH + 1];
	size_t index;
	int body_length = 0;

	if (length < 1 || length > FRAME_MAX ||
	    payload[length - 1] != '\n')
		return -1;
	for (index = 0; index < length; index++) {
		unsigned char byte = payload[index];

		if (byte == '\n')
			continue;
		if (byte < 0x21 || byte > 0x7e)
			return -1;
	}
	memcpy(copy, payload, length);
	copy[length] = '\0';
	memset(request, 0, sizeof(*request));
	cursor = copy;
	if (take_field(&cursor, "version", version, sizeof(version)) < 0 ||
	    take_field(&cursor, "kind", kind, sizeof(kind)) < 0 ||
	    take_field(&cursor, "session", request->session,
		       sizeof(request->session)) < 0 ||
	    take_field(&cursor, "request", request->request,
		       sizeof(request->request)) < 0 ||
	    take_field(&cursor, "verb", request->verb,
		       sizeof(request->verb)) < 0 ||
	    take_field(&cursor, "body_sha256", request->body_sha256,
		       sizeof(request->body_sha256)) < 0)
		return -1;
	if (strcmp(version, "1") != 0 || strcmp(kind, "request") != 0 ||
	    !valid_id(request->request, false) ||
	    !valid_hash(request->body_sha256, true))
		return -1;

	if (strcmp(request->verb, "HELLO") == 0 ||
	    strcmp(request->verb, "STATUS") == 0) {
		if (*cursor != '\0')
			return -1;
		if ((strcmp(request->verb, "HELLO") == 0 &&
		     strcmp(request->session, ZERO_ID) != 0) ||
		    (strcmp(request->verb, "STATUS") == 0 &&
		     !valid_id(request->session, false)))
			return -1;
		body[0] = '\0';
	} else if (strcmp(request->verb, "PREPARE") == 0) {
		if (!valid_id(request->session, false) ||
		    take_field(&cursor, "bundle", request->bundle,
			       sizeof(request->bundle)) < 0 ||
		    take_field(&cursor, "manifest_sha256",
			       request->manifest_sha256,
			       sizeof(request->manifest_sha256)) < 0 ||
		    *cursor != '\0' || !valid_bundle(request->bundle) ||
		    !valid_hash(request->manifest_sha256, false))
			return -1;
		body_length = snprintf(body, sizeof(body),
				       "bundle=%s\nmanifest_sha256=%s\n",
				       request->bundle,
				       request->manifest_sha256);
	} else if (strcmp(request->verb, "COMMIT_EXEC") == 0) {
		if (!valid_id(request->session, false) ||
		    take_field(&cursor, "prepare_request",
			       request->prepare_request,
			       sizeof(request->prepare_request)) < 0 ||
		    take_field(&cursor, "manifest_sha256",
			       request->manifest_sha256,
			       sizeof(request->manifest_sha256)) < 0 ||
		    *cursor != '\0' ||
		    !valid_id(request->prepare_request, false) ||
		    !valid_hash(request->manifest_sha256, false))
			return -1;
		body_length = snprintf(body, sizeof(body),
				       "prepare_request=%s\n"
				       "manifest_sha256=%s\n",
				       request->prepare_request,
				       request->manifest_sha256);
	} else {
		return -1;
	}
	if (body_length < 0 || body_length >= (int)sizeof(body))
		return -1;
	hash_bytes(body, (size_t)body_length, calculated);
	if (strcmp(calculated, request->body_sha256) != 0)
		return -1;
	hash_bytes(payload, length, request->fingerprint);
	return 0;
}

static bool read_process_starttime(pid_t pid, uint64_t *starttime)
{
	char path[64];
	char record[1024];
	char *closing;
	char *cursor;
	char *save = NULL;
	char *token;
	size_t used = 0;
	int descriptor;
	int field;

	if (snprintf(path, sizeof(path), "/proc/%ld/stat", (long)pid) >=
	    (int)sizeof(path))
		return false;
	descriptor = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
	if (descriptor < 0)
		return false;
	while (used < sizeof(record) - 1) {
		ssize_t count = read(descriptor, record + used,
				     sizeof(record) - 1 - used);

		if (count < 0 && errno == EINTR)
			continue;
		if (count < 0) {
			close(descriptor);
			return false;
		}
		if (count == 0)
			break;
		used += (size_t)count;
	}
	if (close(descriptor) < 0 || used == 0 ||
	    used == sizeof(record) - 1)
		return false;
	record[used] = '\0';
	closing = strrchr(record, ')');
	if (closing == NULL || closing[1] != ' ')
		return false;
	cursor = closing + 2;
	for (field = 3, token = strtok_r(cursor, " ", &save);
	     token != NULL;
	     field++, token = strtok_r(NULL, " ", &save)) {
		char *end = NULL;
		unsigned long long value;

		if (field != 22)
			continue;
		errno = 0;
		value = strtoull(token, &end, 10);
		if (errno != 0 || end == token || *end != '\0' || value == 0)
			return false;
		*starttime = (uint64_t)value;
		return true;
	}
	return false;
}

static void open_watchdog_lease(void)
{
	struct stat metadata;
	char record[128];
	char canonical[128];
	unsigned long long pid_value;
	unsigned long long lease_starttime;
	uint64_t observed_starttime;
	size_t used = 0;
	int descriptor;
	int length;
	int consumed = 0;

	descriptor = open(watchdog_path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
	if (descriptor < 0)
		fail("cannot open rollback-watchdog lease: %s", strerror(errno));
	if (fstat(descriptor, &metadata) < 0)
		fail("cannot stat rollback-watchdog lease: %s", strerror(errno));
	if (!S_ISREG(metadata.st_mode) || metadata.st_uid != geteuid() ||
	    (metadata.st_mode & 0077) != 0 || metadata.st_nlink != 1 ||
	    metadata.st_size < 1 ||
	    (uintmax_t)metadata.st_size >= sizeof(record))
		fail("unsafe rollback-watchdog lease");
	while (used < (size_t)metadata.st_size) {
		ssize_t count = read(descriptor, record + used,
				     (size_t)metadata.st_size - used);

		if (count < 0 && errno == EINTR)
			continue;
		if (count <= 0)
			fail("short rollback-watchdog lease read");
		used += (size_t)count;
	}
	if (close(descriptor) < 0)
		fail("cannot close rollback-watchdog lease: %s",
		     strerror(errno));
	record[used] = '\0';
	if (sscanf(record, "pid=%llu\nstarttime=%llu\n%n",
		   &pid_value, &lease_starttime, &consumed) != 2 ||
	    consumed != (int)used || pid_value == 0 ||
	    pid_value > (unsigned long long)INT_MAX ||
	    lease_starttime == 0)
		fail("invalid rollback-watchdog lease");
	length = snprintf(canonical, sizeof(canonical),
			  "pid=%llu\nstarttime=%llu\n",
			  pid_value, lease_starttime);
	if (length != (int)used ||
	    memcmp(record, canonical, used) != 0)
		fail("noncanonical rollback-watchdog lease");
	if (!read_process_starttime((pid_t)pid_value, &observed_starttime) ||
	    observed_starttime != (uint64_t)lease_starttime)
		fail("stale rollback-watchdog lease");
	watchdog_pidfd = (int)syscall(SYS_pidfd_open, (pid_t)pid_value, 0);
	if (watchdog_pidfd < 0)
		fail("cannot pin rollback-watchdog process: %s",
		     strerror(errno));
	if (!read_process_starttime((pid_t)pid_value, &observed_starttime) ||
	    observed_starttime != (uint64_t)lease_starttime)
		fail("rollback-watchdog identity changed");
}

static int64_t monotonic_milliseconds(void)
{
	struct timespec now;

	if (clock_gettime(CLOCK_MONOTONIC, &now) < 0)
		fail("cannot read monotonic clock: %s", strerror(errno));
	return (int64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

static bool watchdog_armed(void)
{
	struct pollfd descriptor = {
		.fd = watchdog_pidfd,
		.events = POLLIN | POLLHUP,
	};
	int result;

	if (watchdog_pidfd < 0)
		return false;
	do {
		result = poll(&descriptor, 1, 0);
	} while (result < 0 && errno == EINTR);
	return result == 0;
}

static void wait_with_watchdog(unsigned int milliseconds)
{
	struct pollfd descriptor = {
		.fd = watchdog_pidfd,
		.events = POLLIN | POLLHUP,
	};
	int result;

	do {
		result = poll(&descriptor, 1, (int)milliseconds);
	} while (result < 0 && errno == EINTR);
	if (result < 0)
		fail("cannot poll rollback watchdog: %s", strerror(errno));
	if (result != 0)
		fail("rollback watchdog process died while waiting");
}

static int wait_io(int descriptor, short events, int64_t deadline)
{
	struct pollfd item = {
		.fd = descriptor,
		.events = events,
	};

	while (true) {
		int64_t remaining;
		int result;

		if (!watchdog_armed())
			fail("rollback watchdog process is not alive");
		remaining = deadline - monotonic_milliseconds();
		if (remaining <= 0)
			return 0;
		if (remaining > 100)
			remaining = 100;
		result = poll(&item, 1, (int)remaining);
		if (result < 0 && errno == EINTR)
			continue;
		if (result < 0)
			return -1;
		if (result == 0)
			continue;
		if ((item.revents & (POLLERR | POLLHUP | POLLNVAL)) != 0)
			return -1;
		if ((item.revents & events) != 0)
			return 1;
	}
}

static int read_byte(int descriptor, unsigned char *byte, int64_t deadline)
{
	while (true) {
		ssize_t count;
		int ready = wait_io(descriptor, POLLIN, deadline);

		if (ready <= 0)
			return ready;
		count = read(descriptor, byte, 1);
		if (count == 1)
			return 1;
		if (count == 0)
			return -1;
		if (errno == EINTR || errno == EAGAIN || errno == EWOULDBLOCK)
			continue;
		return -1;
	}
}

static int read_frame(int descriptor,
		      unsigned char payload[FRAME_MAX + 1],
		      size_t *payload_length)
{
	char digits[5];
	size_t used = 0;
	size_t length;
	size_t received = 0;
	unsigned char byte;
	int64_t deadline;

	while (true) {
		int ready;
		struct pollfd item = {
			.fd = descriptor,
			.events = POLLIN,
		};

		if (!watchdog_armed())
			fail("rollback watchdog process is not alive while idle");
		ready = poll(&item, 1, 100);
		if (ready < 0 && errno == EINTR)
			continue;
		if (ready < 0)
			return -1;
		if (ready == 0)
			continue;
		if ((item.revents & (POLLERR | POLLHUP | POLLNVAL)) != 0)
			return 0;
		if ((item.revents & POLLIN) != 0)
			break;
	}
	deadline = monotonic_milliseconds() + io_timeout_ms;
	while (true) {
		int ready = read_byte(descriptor, &byte, deadline);

		if (ready <= 0)
			return ready;
		if (byte == ':')
			break;
		if (byte < '0' || byte > '9' || used >= sizeof(digits) - 1)
			return -1;
		digits[used++] = (char)byte;
	}
	if (used == 0 || (used > 1 && digits[0] == '0'))
		return -1;
	digits[used] = '\0';
	errno = 0;
	length = strtoul(digits, NULL, 10);
	if (errno != 0 || length > FRAME_MAX)
		return -1;
	while (received < length + 1) {
		int ready = wait_io(descriptor, POLLIN, deadline);
		ssize_t count;

		if (ready <= 0)
			return ready;
		count = read(descriptor, payload + received,
			     length + 1 - received);
		if (count > 0) {
			received += (size_t)count;
			continue;
		}
		if (count < 0 &&
		    (errno == EINTR || errno == EAGAIN ||
		     errno == EWOULDBLOCK))
			continue;
		return -1;
	}
	if (payload[length] != ',')
		return -1;
	*payload_length = length;
	return 1;
}

static void build_response(const struct control_state *state,
			   const struct request *request, const char *result,
			   char output[RESPONSE_MAX], size_t *output_length)
{
	const char *bundle = state->phase == PHASE_IDLE ?
		"none" : state->prepared_bundle;
	const char *manifest = state->phase == PHASE_IDLE ?
		ZERO_HASH : state->manifest_sha256;
	const char *prepare = state->phase == PHASE_IDLE ?
		ZERO_ID : state->prepare_request;
	const char *commit = state->phase == PHASE_IDLE ||
		state->phase == PHASE_PREPARED ?
		ZERO_ID : state->commit_request;
	const char *fingerprint = state->phase == PHASE_IDLE ||
		state->phase == PHASE_PREPARED ?
		ZERO_HASH : state->commit_fingerprint;
	char body[768];
	char body_hash[HASH_LENGTH + 1];
	int body_length;
	int length;

	if (!watchdog_armed())
		fail("rollback watchdog is not armed");
	body_length = snprintf(
		body, sizeof(body),
		"state=%s\n"
		"prepared_bundle=%s\n"
		"manifest_sha256=%s\n"
		"prepare_request=%s\n"
		"commit_request=%s\n"
		"commit_fingerprint=%s\n"
		"execution_started=%s\n"
		"watchdog=ARMED\n"
		"last_error=%s\n",
		phase_name(state->phase), bundle, manifest, prepare, commit,
		fingerprint, state->execution_started ? "YES" : "NO",
		state->last_error);
	if (body_length < 0 || body_length >= (int)sizeof(body))
		fail("response body is too large");
	hash_bytes(body, (size_t)body_length, body_hash);
	length = snprintf(
		output, RESPONSE_MAX,
		"version=1\n"
		"kind=response\n"
		"session=%s\n"
		"request=%s\n"
		"verb=%s\n"
		"result=%s\n"
		"body_sha256=%s\n"
		"%s",
		state->session, request->request, request->verb, result,
		body_hash, body);
	if (length < 0 || length >= RESPONSE_MAX || length > FRAME_MAX)
		fail("response payload is too large");
	*output_length = (size_t)length;
}

static void read_ledger_record(
	const char *request_id, char fingerprint[HASH_LENGTH + 1],
	char verb[16], char result[24])
{
	char record[256];
	char *cursor;
	size_t length;

	if (!read_file_at(ledger_fd, request_id, record,
			  sizeof(record), &length))
		fail("request-ledger record disappeared");
	cursor = record;
	if (take_field(&cursor, "fingerprint", fingerprint,
		       HASH_LENGTH + 1) < 0 ||
	    take_field(&cursor, "verb", verb, 16) < 0 ||
	    take_field(&cursor, "result", result, 24) < 0 ||
	    *cursor != '\0' ||
	    !valid_hash(fingerprint, false) ||
	    (strcmp(verb, "PREPARE") != 0 &&
	     strcmp(verb, "COMMIT_EXEC") != 0) ||
	    !valid_result_for_verb(verb, result))
		fail("invalid request-ledger decision");
}

static int ledger_count(bool *fetch_decided)
{
	DIR *directory;
	struct dirent *entry;
	int count = 0;
	int duplicate = openat(ledger_fd, ".",
			       O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);

	if (duplicate < 0)
		fail("cannot duplicate ledger descriptor: %s", strerror(errno));
	directory = fdopendir(duplicate);
	if (directory == NULL)
		fail("cannot inspect request ledger: %s", strerror(errno));
	*fetch_decided = false;
	while ((entry = readdir(directory)) != NULL) {
		char fingerprint[HASH_LENGTH + 1];
		char result[24];
		char verb[16];
		struct stat metadata;

		if (entry->d_name[0] == '.')
			continue;
		if (!valid_id(entry->d_name, false))
			fail("unsafe request-ledger name");
		if (fstatat(ledger_fd, entry->d_name, &metadata,
			    AT_SYMLINK_NOFOLLOW) < 0 ||
		    !S_ISREG(metadata.st_mode) ||
		    metadata.st_uid != geteuid() ||
		    (metadata.st_mode & 0077) != 0)
			fail("unsafe request-ledger record");
		read_ledger_record(
			entry->d_name, fingerprint, verb, result);
		if (strcmp(verb, "PREPARE") == 0 &&
		    (strcmp(result, "FETCH_FAILED") == 0 ||
		     strcmp(result, "BUNDLE_ID_CONFLICT") == 0 ||
		     strcmp(result, "PREPARE_ID_CONFLICT") == 0))
			*fetch_decided = true;
		count++;
	}
	if (closedir(directory) < 0)
		fail("cannot close request ledger: %s", strerror(errno));
	if (count > LEDGER_MAX)
		fail("request ledger exceeds its fixed bound");
	return count;
}

static int read_ledger(const struct request *request,
		       char fingerprint[HASH_LENGTH + 1],
		       char result[24])
{
	char recorded_verb[16];
	struct stat metadata;

	if (fstatat(ledger_fd, request->request, &metadata,
		    AT_SYMLINK_NOFOLLOW) < 0) {
		if (errno == ENOENT)
			return 0;
		fail("cannot stat request-ledger decision");
	}
	if (!S_ISREG(metadata.st_mode) ||
	    metadata.st_uid != geteuid() ||
	    (metadata.st_mode & 0077) != 0)
		fail("unsafe request-ledger record");
	read_ledger_record(
		request->request, fingerprint, recorded_verb, result);
	return 1;
}

static void remember_decision(const struct request *request,
			      const char *result)
{
	char record[256];
	int length;

	if (!valid_result_for_verb(request->verb, result))
		fail("cannot persist an invalid request decision");
	length = snprintf(record, sizeof(record),
			  "fingerprint=%s\nverb=%s\nresult=%s\n",
			  request->fingerprint, request->verb, result);
	if (length < 0 || length >= (int)sizeof(record))
		fail("request-ledger decision is too large");
	if (!create_immutable_at(ledger_fd, request->request, record,
				 (size_t)length))
		fail("request-ledger publication raced");
}

static bool valid_plan_identity(const char *value, size_t maximum)
{
	size_t length = strlen(value);
	size_t index;

	if (length < 1 || length > maximum || value[0] == '.' ||
	    strstr(value, "..") != NULL)
		return false;
	for (index = 0; index < length; index++) {
		char byte = value[index];

		if (!((byte >= 'a' && byte <= 'z') ||
		      (byte >= 'A' && byte <= 'Z') ||
		      (byte >= '0' && byte <= '9') ||
		      byte == '.' || byte == '_' || byte == '+' ||
		      byte == '-'))
			return false;
	}
	return true;
}

static bool valid_plan_profile(const char *profile)
{
	return strcmp(profile, "diagnostic-initramfs-v1") == 0 ||
		strcmp(profile, "network-root-v1") == 0 ||
		strcmp(profile, "persistent-root-ro-v1") == 0;
}

static bool parse_plan_number(const char *value, uint64_t minimum,
			      uint64_t maximum, uint64_t *output)
{
	char canonical[32];
	char *end = NULL;
	unsigned long long parsed;
	int length;

	if (value[0] == '\0' ||
	    (value[0] == '0' && value[1] != '\0'))
		return false;
	errno = 0;
	parsed = strtoull(value, &end, 10);
	if (errno != 0 || end == value || *end != '\0' ||
	    parsed < minimum || parsed > maximum)
		return false;
	length = snprintf(canonical, sizeof(canonical), "%llu", parsed);
	if (length < 0 || length >= (int)sizeof(canonical) ||
	    strcmp(canonical, value) != 0)
		return false;
	*output = (uint64_t)parsed;
	return true;
}

static bool parse_verified_plan(char *record, size_t record_length,
				const struct request *request,
				struct verified_plan *plan)
{
	char format[32];
	char kernel_file[32];
	char dtb_file[32];
	char initramfs_file[32];
	char target_timeout[32];
	char command_hash[HASH_LENGTH + 1];
	char actual_command_hash[HASH_LENGTH + 1];
	char *cursor = record;
	char *newline;
	size_t command_length;
	size_t index;

	if (record_length < 1 || record_length > PLAN_MAX ||
	    memchr(record, '\0', record_length) != NULL)
		return false;
	record[record_length] = '\0';
	memset(plan, 0, sizeof(*plan));
	if (take_field(&cursor, "format", format, sizeof(format)) < 0 ||
	    take_field(&cursor, "bundle", plan->bundle,
		       sizeof(plan->bundle)) < 0 ||
	    take_field(&cursor, "manifest_sha256", plan->manifest_sha256,
		       sizeof(plan->manifest_sha256)) < 0 ||
	    take_field(&cursor, "profile", plan->profile,
		       sizeof(plan->profile)) < 0 ||
	    take_field(&cursor, "kernel_file", kernel_file,
		       sizeof(kernel_file)) < 0 ||
	    take_field(&cursor, "dtb_file", dtb_file,
		       sizeof(dtb_file)) < 0 ||
	    take_field(&cursor, "initramfs_file", initramfs_file,
		       sizeof(initramfs_file)) < 0 ||
	    take_field(&cursor, "target_id", plan->target_id,
		       sizeof(plan->target_id)) < 0 ||
	    take_field(&cursor, "target_release", plan->target_release,
		       sizeof(plan->target_release)) < 0 ||
	    take_field(&cursor, "target_timeout", target_timeout,
		       sizeof(target_timeout)) < 0 ||
	    take_field(&cursor, "cmdline_sha256", command_hash,
		       sizeof(command_hash)) < 0 ||
	    strncmp(cursor, "cmdline=", 8) != 0)
		return false;
	cursor += 8;
	newline = strchr(cursor, '\n');
	if (newline == NULL || newline[1] != '\0')
		return false;
	command_length = (size_t)(newline - cursor);
	if (command_length < 1 ||
	    command_length >= sizeof(plan->command_line))
		return false;
	for (index = 0; index < command_length; index++) {
		unsigned char byte = (unsigned char)cursor[index];

		if (byte < 0x20 || byte > 0x7e)
			return false;
	}
	if (cursor[0] == ' ' || cursor[command_length - 1] == ' ')
		return false;
	memcpy(plan->command_line, cursor, command_length);
	plan->command_line[command_length] = '\0';
	hash_bytes(plan->command_line, command_length, actual_command_hash);
	if (strcmp(format, "rog5-verified-plan-v1") != 0 ||
	    strcmp(plan->bundle, request->bundle) != 0 ||
	    strcmp(plan->manifest_sha256,
		   request->manifest_sha256) != 0 ||
	    !valid_bundle(plan->bundle) ||
	    !valid_hash(plan->manifest_sha256, false) ||
	    !valid_plan_profile(plan->profile) ||
	    strcmp(kernel_file, "Image") != 0 ||
	    strcmp(dtb_file, "board.dtb") != 0 ||
	    strcmp(initramfs_file, "initramfs.cpio.gz") != 0 ||
	    !valid_plan_identity(plan->target_id, TARGET_MAX) ||
	    !valid_plan_identity(plan->target_release, RELEASE_MAX) ||
	    !parse_plan_number(target_timeout, 30, 600,
			       &plan->target_timeout) ||
	    !valid_hash(command_hash, false) ||
	    strcmp(command_hash, actual_command_hash) != 0)
		return false;
	return true;
}

static void close_artifact_descriptors(
	int descriptors[HANDOFF_DESCRIPTOR_COUNT])
{
	size_t index;

	for (index = 0; index < HANDOFF_DESCRIPTOR_COUNT; index++) {
		if (descriptors[index] >= 0) {
			close(descriptors[index]);
			descriptors[index] = -1;
		}
	}
}

static bool stop_child(pid_t child)
{
	int64_t deadline = monotonic_milliseconds() +
		CHILD_REAP_TIMEOUT_MS;

	if (kill(child, SIGKILL) < 0 && errno != ESRCH)
		return false;
	while (true) {
		int status;
		pid_t waited = waitpid(child, &status, WNOHANG);

		if (waited == child)
			return true;
		if (waited < 0) {
			if (errno == EINTR)
				continue;
			if (errno == ECHILD)
				return true;
			return false;
		}
		if (monotonic_milliseconds() >= deadline)
			return false;
		sleep_milliseconds(10);
	}
}

static void stop_child_or_fail(pid_t child)
{
	if (!stop_child(child))
		fail("cannot stop and reap PREPARE child");
}

static bool wait_child_bounded(pid_t child, int64_t deadline, int *status)
{
	while (true) {
		pid_t waited = waitpid(child, status, WNOHANG);
		int64_t remaining;
		unsigned int interval;

		if (waited == child)
			return true;
		if (waited < 0 && errno == EINTR)
			continue;
		if (waited < 0)
			return false;
		if (!watchdog_armed()) {
			stop_child_or_fail(child);
			fail("rollback watchdog died during PREPARE");
		}
		remaining = deadline - monotonic_milliseconds();
		if (remaining <= 0)
			return false;
		interval = remaining > 10 ? 10 : (unsigned int)remaining;
		sleep_milliseconds(interval);
	}
}

static bool unload_kexec_image(void)
{
	char *const environment[] = {
		"PATH=/sbin:/bin:/usr/sbin:/usr/bin",
		NULL,
	};
	int status;
	int64_t deadline;
	pid_t child = fork();

	if (child < 0)
		return false;
	if (child == 0) {
		char *const arguments[] = {
			"rog5-kexec",
			"-c",
			"-u",
			NULL,
		};

		if (!watchdog_armed())
			_exit(126);
		execve(kexec_path, arguments, environment);
		_exit(127);
	}
	deadline = monotonic_milliseconds() + kexec_load_timeout_ms;
	if (!wait_child_bounded(child, deadline, &status)) {
		stop_child_or_fail(child);
		return false;
	}
	return WIFEXITED(status) && WEXITSTATUS(status) == 0;
}

static void reconcile_uncommitted_image(const char *context)
{
#ifdef ROG5_CONTROL_TESTING
	if (!test_kexec_configured)
		return;
#endif
	if (!unload_kexec_image())
		fail("cannot unload uncommitted kexec image during %s", context);
}

static int wait_handoff_packet(int descriptor, int64_t deadline)
{
	while (true) {
		struct pollfd items[2] = {
			{
				.fd = descriptor,
				.events = POLLIN,
			},
			{
				.fd = watchdog_pidfd,
				.events = POLLIN | POLLHUP,
			},
		};
		int64_t remaining = deadline - monotonic_milliseconds();
		int timeout;
		int result;

		if (remaining <= 0)
			return false;
		timeout = remaining > 100 ? 100 : (int)remaining;
		do {
			result = poll(items, 2, timeout);
		} while (result < 0 && errno == EINTR);
		if (result < 0)
			return false;
		if (result == 0)
			continue;
		if (items[1].revents != 0)
			return -1;
		if ((items[0].revents & POLLIN) != 0)
			return true;
		if ((items[0].revents &
		     (POLLERR | POLLHUP | POLLNVAL)) != 0)
			return false;
	}
}

static bool validate_handoff_peer(int descriptor)
{
	struct ucred peer;
	socklen_t length = sizeof(peer);
	int type;
	socklen_t type_length = sizeof(type);

	return getsockopt(descriptor, SOL_SOCKET, SO_TYPE,
			  &type, &type_length) == 0 &&
		type_length == sizeof(type) && type == SOCK_SEQPACKET &&
		getsockopt(descriptor, SOL_SOCKET, SO_PEERCRED,
			   &peer, &length) == 0 &&
		length == sizeof(peer) && peer.pid > 0 &&
		peer.uid == geteuid() && peer.gid == getegid();
}

static int receive_verified_handoff(
	int descriptor, int64_t deadline,
	char plan[PLAN_MAX + 1], size_t *plan_length,
	int artifacts[HANDOFF_DESCRIPTOR_COUNT])
{
	union {
		struct cmsghdr alignment;
		unsigned char bytes[
			CMSG_SPACE(HANDOFF_CONTROL_FD_MAX * sizeof(int))];
	} control = { 0 };
	struct iovec vector = {
		.iov_base = plan,
		.iov_len = PLAN_MAX,
	};
	struct msghdr message = {
		.msg_iov = &vector,
		.msg_iovlen = 1,
		.msg_control = control.bytes,
		.msg_controllen = sizeof(control.bytes),
	};
	struct cmsghdr *header;
	int received_descriptors[HANDOFF_CONTROL_FD_MAX];
	size_t ancillary_count = 0;
	size_t received_count = 0;
	bool valid = true;
	ssize_t count;
	int ready;

	if (!validate_handoff_peer(descriptor))
		return false;
	ready = wait_handoff_packet(descriptor, deadline);
	if (ready <= 0)
		return ready;
	do {
		count = recvmsg(
			descriptor, &message, MSG_CMSG_CLOEXEC | MSG_DONTWAIT);
	} while (count < 0 && errno == EINTR);
	if (count <= 0)
		valid = false;
	if ((message.msg_flags & (MSG_TRUNC | MSG_CTRUNC)) != 0)
		valid = false;
	for (header = CMSG_FIRSTHDR(&message); header != NULL;
	     header = CMSG_NXTHDR(&message, header)) {
		size_t payload_length;
		size_t received;

		ancillary_count++;
		if (header->cmsg_level != SOL_SOCKET ||
		    header->cmsg_type != SCM_RIGHTS ||
		    header->cmsg_len < CMSG_LEN(0)) {
			valid = false;
			continue;
		}
		payload_length = header->cmsg_len - CMSG_LEN(0);
		if (payload_length % sizeof(int) != 0) {
			valid = false;
			continue;
		}
		received = payload_length / sizeof(int);
		if (received > HANDOFF_CONTROL_FD_MAX - received_count) {
			valid = false;
			received = HANDOFF_CONTROL_FD_MAX - received_count;
		}
		memcpy(received_descriptors + received_count, CMSG_DATA(header),
		       received * sizeof(int));
		received_count += received;
	}
	if (ancillary_count != 1 ||
	    received_count != HANDOFF_DESCRIPTOR_COUNT)
		valid = false;
	if (!valid) {
		size_t index;

		for (index = 0; index < received_count; index++)
			close(received_descriptors[index]);
		return false;
	}
	memcpy(artifacts, received_descriptors, sizeof(int) *
	       HANDOFF_DESCRIPTOR_COUNT);
	*plan_length = (size_t)count;
	return true;
}

static bool validate_artifact_descriptors(
	int descriptors[HANDOFF_DESCRIPTOR_COUNT])
{
	static const uint64_t minimum[] = { 64, 40, 2 };
	static const uint64_t maximum[] = {
		KERNEL_MAX,
		DTB_MAX,
		INITRAMFS_MAX,
	};
	struct stat metadata[HANDOFF_DESCRIPTOR_COUNT];
	size_t index;
	size_t other;

	for (index = 0; index < HANDOFF_DESCRIPTOR_COUNT; index++) {
		int descriptor_flags;
		int seals;
		int status_flags;

		if (descriptors[index] < 0 ||
		    fstat(descriptors[index], &metadata[index]) < 0 ||
		    !S_ISREG(metadata[index].st_mode) ||
		    metadata[index].st_uid != geteuid() ||
		    metadata[index].st_nlink != 0 ||
		    (metadata[index].st_mode & 0222) != 0 ||
		    metadata[index].st_size < (off_t)minimum[index] ||
		    (uint64_t)metadata[index].st_size > maximum[index])
			return false;
		descriptor_flags =
			fcntl(descriptors[index], F_GETFD);
		seals = fcntl(descriptors[index], F_GET_SEALS);
		status_flags = fcntl(descriptors[index], F_GETFL);
		if (descriptor_flags < 0 || seals != REQUIRED_SEALS ||
		    status_flags < 0 ||
		    (descriptor_flags & FD_CLOEXEC) == 0 ||
		    (status_flags & O_ACCMODE) == O_WRONLY ||
		    lseek(descriptors[index], 0, SEEK_CUR) != 0)
			return false;
	}
	for (index = 0; index < HANDOFF_DESCRIPTOR_COUNT; index++) {
		for (other = index + 1;
		     other < HANDOFF_DESCRIPTOR_COUNT; other++) {
			if (metadata[index].st_dev == metadata[other].st_dev &&
			    metadata[index].st_ino == metadata[other].st_ino)
				return false;
		}
	}
	return true;
}

static enum prepare_outcome run_bundle_fetcher(
	const struct request *request)
{
	char *const environment[] = {
		"PATH=/sbin:/bin:/usr/sbin:/usr/bin",
		NULL,
	};
	int status;
	int64_t deadline;
	pid_t parent = getpid();
	pid_t child = fork();

	if (child < 0)
		return PREPARE_OUTCOME_FETCH_FAILED;
	if (child == 0) {
		char *const arguments[] = {
			"rog5-bundle-fetch",
			(char *)request->bundle,
			(char *)request->manifest_sha256,
			NULL,
		};

		if (prctl(PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0) < 0 ||
		    getppid() != parent || !watchdog_armed())
			_exit(126);
		execve(fetcher_path, arguments, environment);
		_exit(127);
	}
	deadline = monotonic_milliseconds() + fetch_timeout_ms;
	if (!wait_child_bounded(child, deadline, &status)) {
		stop_child_or_fail(child);
		return PREPARE_OUTCOME_FETCH_FAILED;
	}
	if (!WIFEXITED(status))
		return PREPARE_OUTCOME_FETCH_FAILED;
	if (WEXITSTATUS(status) == 0)
		return PREPARE_OUTCOME_OK;
	if (WEXITSTATUS(status) == FETCH_BUNDLE_CONFLICT_EXIT)
		return PREPARE_OUTCOME_BUNDLE_ID_CONFLICT;
	return PREPARE_OUTCOME_FETCH_FAILED;
}

static bool run_bundle_verifier(
	const struct request *request, struct verified_plan *plan,
	int artifacts[HANDOFF_DESCRIPTOR_COUNT])
{
	char record[PLAN_MAX + 1];
	char *const environment[] = {
		"PATH=/sbin:/bin:/usr/sbin:/usr/bin",
		NULL,
	};
	int sockets[2];
	int status;
	int64_t deadline;
	size_t record_length = 0;
	pid_t child;
	int received;

	if (socketpair(AF_UNIX,
		       SOCK_SEQPACKET | SOCK_CLOEXEC | SOCK_NONBLOCK,
		       0, sockets) < 0)
		return false;
	child = fork();
	if (child < 0) {
		close(sockets[0]);
		close(sockets[1]);
		return false;
	}
	if (child == 0) {
		char *const arguments[] = {
			"rog5-bundle-verify",
			"--handoff-fd3",
			(char *)request->bundle,
			(char *)request->manifest_sha256,
			NULL,
		};
		int flags;

		close(sockets[0]);
		if (sockets[1] != HANDOFF_FD) {
			if (dup3(sockets[1], HANDOFF_FD, 0) < 0)
				_exit(126);
			close(sockets[1]);
		} else {
			flags = fcntl(HANDOFF_FD, F_GETFD);
			if (flags < 0 ||
			    fcntl(HANDOFF_FD, F_SETFD,
				  flags & ~FD_CLOEXEC) < 0)
				_exit(126);
		}
		execve(verifier_path, arguments, environment);
		_exit(127);
	}
	close(sockets[1]);
	deadline = monotonic_milliseconds() + verify_timeout_ms;
	received = receive_verified_handoff(
		sockets[0], deadline, record, &record_length, artifacts);
	close(sockets[0]);
	if (!received) {
		stop_child_or_fail(child);
		return false;
	}
	if (received < 0) {
		stop_child_or_fail(child);
		fail("rollback watchdog died during verifier handoff");
	}
	if (!wait_child_bounded(child, deadline, &status)) {
		stop_child_or_fail(child);
		close_artifact_descriptors(artifacts);
		return false;
	}
	if (!WIFEXITED(status) || WEXITSTATUS(status) != 0 ||
	    !parse_verified_plan(
		    record, record_length, request, plan) ||
	    !validate_artifact_descriptors(artifacts)) {
		close_artifact_descriptors(artifacts);
		return false;
	}
	return true;
}

static bool load_verified_plan(
	const struct verified_plan *plan,
	int artifacts[HANDOFF_DESCRIPTOR_COUNT])
{
	char kernel_path[64];
	char dtb_option[96];
	char initramfs_option[96];
	char command_option[CMDLINE_MAX + 32];
	char *const environment[] = {
		"PATH=/sbin:/bin:/usr/sbin:/usr/bin",
		NULL,
	};
	int status;
	int64_t deadline;
	pid_t child;
	int length;

	length = snprintf(
		kernel_path, sizeof(kernel_path),
		"/proc/self/fd/%d", artifacts[0]);
	if (length < 0 || length >= (int)sizeof(kernel_path))
		return false;
	length = snprintf(
		dtb_option, sizeof(dtb_option),
		"--dtb=/proc/self/fd/%d", artifacts[1]);
	if (length < 0 || length >= (int)sizeof(dtb_option))
		return false;
	length = snprintf(
		initramfs_option, sizeof(initramfs_option),
		"--initrd=/proc/self/fd/%d", artifacts[2]);
	if (length < 0 || length >= (int)sizeof(initramfs_option))
		return false;
	length = snprintf(
		command_option, sizeof(command_option),
		"--command-line=%s", plan->command_line);
	if (length < 0 || length >= (int)sizeof(command_option))
		return false;

	child = fork();
	if (child < 0)
		return false;
	if (child == 0) {
		char *const arguments[] = {
			"rog5-kexec",
			"-c",
			"-l",
			kernel_path,
			initramfs_option,
			dtb_option,
			command_option,
			NULL,
		};
		size_t index;

		for (index = 0; index < HANDOFF_DESCRIPTOR_COUNT; index++) {
			int flags = fcntl(artifacts[index], F_GETFD);

			if (flags < 0 ||
			    fcntl(artifacts[index], F_SETFD,
				  flags & ~FD_CLOEXEC) < 0)
				_exit(126);
		}
		if (!watchdog_armed())
			_exit(126);
		execve(kexec_path, arguments, environment);
		_exit(127);
	}
	deadline = monotonic_milliseconds() + kexec_load_timeout_ms;
	if (!wait_child_bounded(child, deadline, &status)) {
		stop_child_or_fail(child);
		reconcile_uncommitted_image("failed PREPARE load");
		return false;
	}
	if (WIFEXITED(status) && WEXITSTATUS(status) == 0)
		return true;
	reconcile_uncommitted_image("rejected PREPARE load");
	return false;
}

static enum prepare_outcome verify_prepare(const struct request *request)
{
	struct verified_plan plan;
	int artifacts[HANDOFF_DESCRIPTOR_COUNT] = { -1, -1, -1 };
	enum prepare_outcome outcome;
	bool loaded;

#ifdef ROG5_CONTROL_TESTING
	if (getenv("ROG5_TEST_VERIFIER_PATH") == NULL) {
		const char *allowed = getenv("ROG5_TEST_ALLOW_MANIFEST");

		return allowed != NULL &&
			strcmp(allowed, request->manifest_sha256) == 0 ?
			PREPARE_OUTCOME_OK : PREPARE_OUTCOME_VERIFY_FAILED;
	}
#endif
	outcome = run_bundle_fetcher(request);
	if (outcome != PREPARE_OUTCOME_OK)
		return outcome;
	if (!run_bundle_verifier(request, &plan, artifacts))
		return PREPARE_OUTCOME_VERIFY_FAILED;
	loaded = load_verified_plan(&plan, artifacts);
	close_artifact_descriptors(artifacts);
	return loaded ? PREPARE_OUTCOME_OK : PREPARE_OUTCOME_VERIFY_FAILED;
}

static void persist_prepared(struct control_state *state,
			     const struct request *request)
{
	char payload[384];
	int length;

	length = snprintf(payload, sizeof(payload),
			  "bundle=%s\n"
			  "manifest_sha256=%s\n"
			  "prepare_request=%s\n"
			  "prepare_fingerprint=%s\n",
			  request->bundle, request->manifest_sha256,
			  request->request, request->fingerprint);
	if (length < 0 || length >= (int)sizeof(payload))
		fail("prepared state is too large");
	if (!create_immutable_at(state_fd, "prepared", payload,
				 (size_t)length))
		fail("prepared state already exists");
	state->phase = PHASE_PREPARED;
	memcpy(state->prepared_bundle, request->bundle,
	       strlen(request->bundle) + 1);
	memcpy(state->manifest_sha256, request->manifest_sha256,
	       sizeof(state->manifest_sha256));
	memcpy(state->prepare_request, request->request,
	       sizeof(state->prepare_request));
	memcpy(state->prepare_fingerprint, request->fingerprint,
	       sizeof(state->prepare_fingerprint));
}

static void persist_claim(struct control_state *state,
			  const struct request *request)
{
	char payload[384];
	int length;

	length = snprintf(payload, sizeof(payload),
			  "request=%s\n"
			  "fingerprint=%s\n"
			  "prepare_request=%s\n"
			  "manifest_sha256=%s\n",
			  request->request, request->fingerprint,
			  request->prepare_request, request->manifest_sha256);
	if (length < 0 || length >= (int)sizeof(payload))
		fail("commit claim is too large");
	if (!create_immutable_at(state_fd, "claim", payload,
				 (size_t)length))
		fail("commit claim already exists");
	state->phase = PHASE_CLAIMED;
	memcpy(state->commit_request, request->request,
	       sizeof(state->commit_request));
	memcpy(state->commit_fingerprint, request->fingerprint,
	       sizeof(state->commit_fingerprint));
}

static bool crash_point(const char *point)
{
#ifdef ROG5_CONTROL_TESTING
	const char *selected = getenv("ROG5_TEST_CRASH");

	return selected != NULL && strcmp(selected, point) == 0;
#else
	(void)point;
	return false;
#endif
}

static void handle_request(struct control_state *state,
			   const struct request *request,
			   struct response_action *action)
{
	char cached_fingerprint[HASH_LENGTH + 1];
	char cached_result[24];
	const char *result;
	enum prepare_outcome prepare_outcome = PREPARE_OUTCOME_VERIFY_FAILED;
	int decisions;
	bool fetch_decided;

	memset(action, 0, sizeof(*action));
	if (strcmp(request->verb, "HELLO") != 0 &&
	    strcmp(request->session, state->session) != 0) {
		build_response(state, request, "STALE_SESSION",
			       action->payload, &action->payload_length);
		return;
	}

	if (strcmp(request->verb, "HELLO") == 0 ||
	    strcmp(request->verb, "STATUS") == 0) {
		build_response(state, request, "OK", action->payload,
			       &action->payload_length);
		return;
	}

	if (read_ledger(request, cached_fingerprint, cached_result)) {
		if (strcmp(cached_fingerprint, request->fingerprint) == 0) {
			build_response(state, request, cached_result,
				       action->payload,
				       &action->payload_length);
		} else {
			build_response(state, request, "REQUEST_CONFLICT",
				       action->payload,
				       &action->payload_length);
		}
		return;
	}

	if (state->phase != PHASE_IDLE &&
	    strcmp(request->request, state->prepare_request) == 0) {
		if (strcmp(request->verb, "PREPARE") != 0 ||
		    strcmp(request->fingerprint,
			   state->prepare_fingerprint) != 0) {
			result = "REQUEST_CONFLICT";
		} else {
			result = "PREPARED";
		}
		build_response(state, request, result, action->payload,
			       &action->payload_length);
		return;
	}

	if (state->phase >= PHASE_CLAIMED &&
	    strcmp(request->request, state->commit_request) == 0) {
		if (strcmp(request->fingerprint,
			   state->commit_fingerprint) != 0) {
			build_response(state, request, "REQUEST_CONFLICT",
				       action->payload,
				       &action->payload_length);
			return;
		}
		build_response(state, request, "CLAIMED",
			       action->payload, &action->payload_length);
		return;
	}

	decisions = ledger_count(&fetch_decided);
	if (decisions >= LEDGER_MAX) {
		set_last_error(state, "LEDGER_FULL");
		build_response(state, request, "LEDGER_FULL",
			       action->payload, &action->payload_length);
		return;
	}
	if (decisions >= LEDGER_MAX - 3) {
		bool capacity_reserved = false;

		if (strcmp(request->verb, "PREPARE") == 0 &&
		    state->phase == PHASE_IDLE &&
		    decisions == LEDGER_MAX - 3) {
			capacity_reserved = true;
		} else if (strcmp(request->verb, "COMMIT_EXEC") == 0 &&
			   state->phase == PHASE_PREPARED &&
			   strcmp(request->prepare_request,
				  state->prepare_request) == 0 &&
			   strcmp(request->manifest_sha256,
				  state->manifest_sha256) == 0) {
			capacity_reserved = true;
		}
		if (!capacity_reserved) {
			set_last_error(state, "LEDGER_FULL");
			build_response(state, request, "LEDGER_FULL",
				       action->payload,
				       &action->payload_length);
			return;
		}
	}

	if (strcmp(request->verb, "PREPARE") == 0) {
		if (state->phase == PHASE_IDLE && fetch_decided) {
			result = "PREPARE_ID_CONFLICT";
		} else if (state->phase == PHASE_IDLE) {
			prepare_outcome = verify_prepare(request);
			if (prepare_outcome ==
			    PREPARE_OUTCOME_BUNDLE_ID_CONFLICT) {
				set_last_error(state, "BUNDLE_ID_CONFLICT");
				result = "BUNDLE_ID_CONFLICT";
			} else if (prepare_outcome ==
				   PREPARE_OUTCOME_FETCH_FAILED) {
				set_last_error(state, "FETCH_FAILED");
				result = "FETCH_FAILED";
			} else if (prepare_outcome ==
				   PREPARE_OUTCOME_VERIFY_FAILED) {
				set_last_error(state, "VERIFY_FAILED");
				result = "VERIFY_FAILED";
			} else {
				if (crash_point("after_prepare_load"))
					_exit(88);
				persist_prepared(state, request);
				if (crash_point("after_prepare"))
					_exit(88);
				result = "PREPARED";
			}
		} else if (state->phase == PHASE_PREPARED &&
			   strcmp(request->bundle,
				  state->prepared_bundle) == 0 &&
			   strcmp(request->manifest_sha256,
				  state->manifest_sha256) == 0) {
			result = "PREPARE_ID_CONFLICT";
		} else if (state->phase == PHASE_PREPARED) {
			result = "BUNDLE_CONFLICT";
		} else {
			result = "SESSION_CONSUMED";
		}
	} else if (strcmp(request->verb, "COMMIT_EXEC") == 0) {
		if (state->phase == PHASE_IDLE) {
			result = "PREPARE_REQUIRED";
		} else if (state->phase != PHASE_PREPARED) {
			result = "ALREADY_CLAIMED";
		} else if (strcmp(request->prepare_request,
				  state->prepare_request) != 0 ||
			   strcmp(request->manifest_sha256,
				  state->manifest_sha256) != 0) {
			result = "PREPARE_MISMATCH";
		} else {
			if (crash_point("before_claim"))
				_exit(88);
			persist_claim(state, request);
			if (crash_point("after_claim"))
				_exit(88);
			result = "CLAIMED";
			action->execute = true;
		}
	} else {
		fail("decoder admitted an unknown verb");
	}

	build_response(state, request, result, action->payload,
		       &action->payload_length);
	remember_decision(request, result);
}

static int write_bounded(int descriptor, const void *data, size_t length,
			 int64_t deadline)
{
	const unsigned char *bytes = data;
	size_t offset = 0;

	while (offset < length) {
		size_t request = length - offset;
		ssize_t count;
		int ready;

#ifdef ROG5_CONTROL_TESTING
		const char *chunk = getenv("ROG5_TEST_WRITE_CHUNK");

		if (chunk != NULL && strcmp(chunk, "1") == 0 && request > 1)
			request = 1;
#endif
		ready = wait_io(descriptor, POLLOUT, deadline);
		if (ready <= 0)
			return -1;
		count = write(descriptor, bytes + offset, request);
		if (count > 0) {
			offset += (size_t)count;
			continue;
		}
		if (count < 0 &&
		    (errno == EINTR || errno == EAGAIN ||
		     errno == EWOULDBLOCK))
			continue;
		return -1;
	}
	return 0;
}

static int drain_bounded(int descriptor, int64_t deadline)
{
#ifdef ROG5_CONTROL_TESTING
	const char *stall = getenv("ROG5_TEST_DRAIN_STALL");
	struct stat claim;

	if (stall != NULL &&
	    (strcmp(stall, "1") == 0 ||
	     (strcmp(stall, "claim") == 0 &&
	      fstatat(state_fd, "claim", &claim, AT_SYMLINK_NOFOLLOW) == 0))) {
		while (monotonic_milliseconds() < deadline) {
			if (!watchdog_armed())
				fail("rollback watchdog process died during drain");
			sleep_milliseconds(10);
		}
		return -1;
	}
#endif
	while (true) {
		int pending;

		if (!watchdog_armed())
			fail("rollback watchdog process died during drain");
		if (ioctl(descriptor, TIOCOUTQ, &pending) < 0)
			return -1;
		if (pending == 0)
			return 0;
		if (monotonic_milliseconds() >= deadline)
			return -1;
		sleep_milliseconds(1);
	}
}

static int send_frame(int descriptor, const char *payload, size_t length)
{
	char prefix[16];
	int prefix_length;
	int64_t deadline;

#ifdef ROG5_CONTROL_TESTING
	const char *delay = getenv("ROG5_TEST_REPLY_DELAY_MS");

	if (delay != NULL) {
		char *end = NULL;
		unsigned long milliseconds;

		errno = 0;
		milliseconds = strtoul(delay, &end, 10);
		if (errno == 0 && end != delay && *end == '\0' &&
		    milliseconds <= 5000)
			sleep_milliseconds((unsigned int)milliseconds);
	}
#endif
	prefix_length = snprintf(prefix, sizeof(prefix), "%zu:", length);
	if (prefix_length < 0 || prefix_length >= (int)sizeof(prefix))
		fail("response frame prefix is too large");
	deadline = monotonic_milliseconds() + io_timeout_ms;
	if (write_bounded(descriptor, prefix, (size_t)prefix_length,
			  deadline) < 0 ||
	    write_bounded(descriptor, payload, length, deadline) < 0 ||
	    write_bounded(descriptor, ",", 1, deadline) < 0)
		return -1;
	if (drain_bounded(descriptor, deadline) < 0)
		return -1;
	return 0;
}

static void persist_execution_started(struct control_state *state)
{
	char payload[128];
	int length;

	length = snprintf(payload, sizeof(payload),
			  "commit_fingerprint=%s\n",
			  state->commit_fingerprint);
	if (length < 0 || length >= (int)sizeof(payload))
		fail("execution marker is too large");
	if (!create_immutable_at(state_fd, "execution-started", payload,
				 (size_t)length))
		fail("execution marker already exists");
	state->execution_started = true;
}

static void persist_failure(struct control_state *state, const char *error)
{
	char payload[64];
	int length;

	length = snprintf(payload, sizeof(payload), "error=%s\n", error);
	if (length < 0 || length >= (int)sizeof(payload))
		fail("execution failure is too large");
	if (!create_immutable_at(state_fd, "failure", payload,
				 (size_t)length))
		fail("execution failure already exists");
	state->phase = PHASE_EXEC_FAILED;
	set_last_error(state, error);
}

static void execute_claim(struct control_state *state)
{
	if (!watchdog_armed())
		fail("rollback watchdog disappeared before execute");
	persist_execution_started(state);
	if (crash_point("after_execute_start"))
		_exit(88);
#ifdef ROG5_CONTROL_TESTING
	{
		const char *delay = getenv("ROG5_TEST_EXEC_DELAY_MS");

		if (delay != NULL) {
			char *end = NULL;
			unsigned long milliseconds;
			int64_t deadline;

			errno = 0;
			milliseconds = strtoul(delay, &end, 10);
			if (errno != 0 || end == delay || *end != '\0' ||
			    milliseconds > 5000)
				fail("invalid test execute delay");
			deadline = monotonic_milliseconds() +
				(int64_t)milliseconds;
			while (monotonic_milliseconds() < deadline) {
				if (!watchdog_armed())
					fail("rollback watchdog died after execute marker");
				sleep_milliseconds(10);
			}
		}
	}
#endif
	if (!watchdog_armed())
		fail("rollback watchdog died after execute marker");

#ifdef ROG5_CONTROL_TESTING
	{
		const char *mode = getenv("ROG5_TEST_EXEC_MODE");
		const char marker[] = "executed\n";

		if (mode == NULL)
			mode = "depart";
		if (strcmp(mode, "fixed_path") != 0) {
			if (!create_immutable_at(
				    state_fd, "test-executed", marker,
				    sizeof(marker) - 1))
				fail("test executor ran more than once");
			if (strcmp(mode, "depart") == 0)
				_exit(0);
			if (strcmp(mode, "return") == 0) {
				persist_failure(state, "EXEC_RETURNED");
				return;
			}
			if (strcmp(mode, "fail") == 0) {
				persist_failure(state, "EXEC_FAILED");
				return;
			}
			fail("invalid test execute mode");
		}
	}
#endif
	{
		pid_t child;
		int status;

		if (!watchdog_armed())
			fail("rollback watchdog died before executor fork");
		child = fork();
		if (child < 0) {
			reconcile_uncommitted_image("executor fork failure");
			persist_failure(state, "EXEC_FAILED");
			return;
		}
		if (child == 0) {
			char *const arguments[] = {
				"rog5-kexec", "-e", NULL,
			};
			char *const environment[] = {
				"PATH=/sbin:/bin:/usr/sbin:/usr/bin", NULL,
			};

			if (!watchdog_armed())
				_exit(126);
			execve(kexec_path, arguments, environment);
			_exit(127);
		}
		while (true) {
			pid_t waited = waitpid(child, &status, WNOHANG);

			if (waited == child)
				break;
			if (waited < 0 && errno == EINTR)
				continue;
			if (waited < 0) {
				reconcile_uncommitted_image(
					"executor wait failure");
				persist_failure(state, "EXEC_FAILED");
				return;
			}
			if (!watchdog_armed()) {
				stop_child_or_fail(child);
				fail("rollback watchdog died while executor ran");
			}
			sleep_milliseconds(10);
		}
		if (!watchdog_armed())
			fail("rollback watchdog died as executor exited");
		reconcile_uncommitted_image("returned executor");
		persist_failure(
			state,
			WIFEXITED(status) && WEXITSTATUS(status) == 0 ?
				"EXEC_RETURNED" : "EXEC_FAILED");
	}
}

static void configure_tty(int descriptor)
{
	struct termios settings;

	if (tcgetattr(descriptor, &settings) < 0)
		fail("cannot read TTY settings: %s", strerror(errno));
	cfmakeraw(&settings);
	settings.c_cflag |= CLOCAL | CREAD;
	settings.c_lflag &= ~(ECHO | ECHONL);
	if (tcsetattr(descriptor, TCSANOW, &settings) < 0)
		fail("cannot apply raw TTY settings: %s", strerror(errno));
	if (tcflush(descriptor, TCIOFLUSH) < 0)
		fail("cannot flush TTY: %s", strerror(errno));
}

static void report_test_ready(void)
{
#ifdef ROG5_CONTROL_TESTING
	const char *path = getenv("ROG5_TEST_READY_FILE");
	int descriptor;

	if (path == NULL)
		return;
	descriptor = open(path, O_WRONLY | O_CREAT | O_TRUNC |
			  O_NOFOLLOW | O_CLOEXEC, 0600);
	if (descriptor < 0)
		fail("cannot create test readiness marker: %s",
		     strerror(errno));
	write_all(descriptor, "ready\n", sizeof("ready\n") - 1);
	if (close(descriptor) < 0)
		fail("cannot close test readiness marker: %s",
		     strerror(errno));
#endif
}

static void serve_connection(int descriptor, struct control_state *state)
{
	unsigned char payload[FRAME_MAX + 1];

	while (true) {
		struct request request;
		struct response_action action;
		size_t payload_length;
		int frame = read_frame(descriptor, payload, &payload_length);

		if (frame <= 0)
			return;
		if (decode_request(payload, payload_length, &request) < 0)
			return;
		handle_request(state, &request, &action);
		if (send_frame(descriptor, action.payload,
			       action.payload_length) < 0)
			return;
		if (action.execute) {
			if (crash_point("after_response"))
				_exit(88);
			execute_claim(state);
		}
	}
}

static void parse_arguments(int argc, char **argv)
{
#ifdef ROG5_CONTROL_TESTING
	int index;

	for (index = 1; index < argc; index += 2) {
		if (index + 1 >= argc)
			fail("test option lacks a value");
		if (strcmp(argv[index], "--device") == 0)
			device_path = argv[index + 1];
		else if (strcmp(argv[index], "--state-dir") == 0)
			state_path = argv[index + 1];
		else if (strcmp(argv[index], "--watchdog") == 0)
			watchdog_path = argv[index + 1];
		else
			fail("unknown test option");
	}
#else
	if (argc != 1)
		fail("production responder accepts no arguments");
	(void)argv;
#endif
}

static void configure_test_runtime(void)
{
#ifdef ROG5_CONTROL_TESTING
	const char *test_fetcher = getenv("ROG5_TEST_FETCHER_PATH");
	const char *test_verifier = getenv("ROG5_TEST_VERIFIER_PATH");
	const char *test_kexec = getenv("ROG5_TEST_KEXEC_PATH");
	const char *timeout = getenv("ROG5_TEST_IO_TIMEOUT_MS");

	if ((test_fetcher == NULL) != (test_verifier == NULL) ||
	    (test_verifier == NULL) != (test_kexec == NULL))
		fail("test PREPARE paths must be configured together");
	if (test_fetcher != NULL) {
		if (test_fetcher[0] != '/' ||
		    test_verifier[0] != '/' || test_kexec[0] != '/' ||
		    strnlen(test_fetcher, PATH_MAX) >= PATH_MAX ||
		    strnlen(test_verifier, PATH_MAX) >= PATH_MAX ||
		    strnlen(test_kexec, PATH_MAX) >= PATH_MAX ||
		    access(test_fetcher, X_OK) < 0 ||
		    access(test_verifier, X_OK) < 0 ||
		    access(test_kexec, X_OK) < 0)
			fail("invalid test PREPARE executable path");
		fetcher_path = test_fetcher;
		verifier_path = test_verifier;
		kexec_path = test_kexec;
		test_kexec_configured = true;
	}
	if (timeout != NULL) {
		char *end = NULL;
		unsigned long value;

		errno = 0;
		value = strtoul(timeout, &end, 10);
		if (errno != 0 || end == timeout || *end != '\0' ||
		    value < 50 || value > 10000)
			fail("invalid test I/O timeout");
		io_timeout_ms = (unsigned int)value;
	}
	timeout = getenv("ROG5_TEST_FETCH_TIMEOUT_MS");
	if (timeout != NULL) {
		char *end = NULL;
		unsigned long value;

		errno = 0;
		value = strtoul(timeout, &end, 10);
		if (errno != 0 || end == timeout || *end != '\0' ||
		    value < 50 || value > FETCH_TIMEOUT_MS)
			fail("invalid test fetch timeout");
		fetch_timeout_ms = (unsigned int)value;
	}
	timeout = getenv("ROG5_TEST_VERIFY_TIMEOUT_MS");
	if (timeout != NULL) {
		char *end = NULL;
		unsigned long value;

		errno = 0;
		value = strtoul(timeout, &end, 10);
		if (errno != 0 || end == timeout || *end != '\0' ||
		    value < 50 || value > VERIFY_TIMEOUT_MS)
			fail("invalid test verifier timeout");
		verify_timeout_ms = (unsigned int)value;
	}
	timeout = getenv("ROG5_TEST_LOAD_TIMEOUT_MS");
	if (timeout != NULL) {
		char *end = NULL;
		unsigned long value;

		errno = 0;
		value = strtoul(timeout, &end, 10);
		if (errno != 0 || end == timeout || *end != '\0' ||
		    value < 50 || value > KEXEC_LOAD_TIMEOUT_MS)
			fail("invalid test load timeout");
		kexec_load_timeout_ms = (unsigned int)value;
	}
#endif
}

int main(int argc, char **argv)
{
	struct control_state state;

	umask(0077);
	parse_arguments(argc, argv);
	configure_test_runtime();
	open_state_directories();
	open_watchdog_lease();
	if (!watchdog_armed())
		fail("rollback watchdog is not armed at startup");
	load_state(&state);
	if (state.phase != PHASE_PREPARED)
		reconcile_uncommitted_image("startup reconciliation");

	while (true) {
		int descriptor = open(device_path,
				      O_RDWR | O_NOCTTY | O_CLOEXEC |
				      O_NONBLOCK);

		if (descriptor < 0) {
			if (errno == ENOENT || errno == ENXIO ||
			    errno == EIO) {
				wait_with_watchdog(100);
				continue;
			}
			fail("cannot open control TTY: %s", strerror(errno));
		}
		configure_tty(descriptor);
		report_test_ready();
		serve_connection(descriptor, &state);
		close(descriptor);
		sleep_milliseconds(100);
	}
}
