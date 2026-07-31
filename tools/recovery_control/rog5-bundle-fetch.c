#define _GNU_SOURCE

#include <arpa/inet.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <inttypes.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define ROG5_AUDIT_ARCH_64BIT 0x80000000U
#define ROG5_AUDIT_ARCH_LITTLE_ENDIAN 0x40000000U
#define ROG5_AUDIT_ARCH_AARCH64 \
	(ROG5_AUDIT_ARCH_64BIT | ROG5_AUDIT_ARCH_LITTLE_ENDIAN | 183U)
#define ROG5_AUDIT_ARCH_X86_64 \
	(ROG5_AUDIT_ARCH_64BIT | ROG5_AUDIT_ARCH_LITTLE_ENDIAN | 62U)
#define ROG5_BPF_LD 0x00U
#define ROG5_BPF_W 0x00U
#define ROG5_BPF_ABS 0x20U
#define ROG5_BPF_JMP 0x05U
#define ROG5_BPF_JEQ 0x10U
#define ROG5_BPF_K 0x00U
#define ROG5_BPF_RET 0x06U
#define ROG5_SECCOMP_MODE_FILTER 2U
#define ROG5_SECCOMP_RET_KILL_PROCESS 0x80000000U
#define ROG5_SECCOMP_RET_ALLOW 0x7fff0000U
#define ROG5_CAPABILITY_VERSION_3 0x20080522U
#define ROG5_SYS_CLOSE_RANGE 436

struct rog5_sock_filter {
	uint16_t code;
	uint8_t jump_true;
	uint8_t jump_false;
	uint32_t value;
};

struct rog5_sock_fprog {
	unsigned short length;
	struct rog5_sock_filter *filter;
};

struct rog5_seccomp_data {
	int syscall_number;
	uint32_t architecture;
	uint64_t instruction_pointer;
	uint64_t arguments[6];
};

struct rog5_cap_header {
	uint32_t version;
	int process;
};

struct rog5_cap_data {
	uint32_t effective;
	uint32_t permitted;
	uint32_t inheritable;
};

_Static_assert(sizeof(struct rog5_sock_filter) == 8,
	       "classic BPF instruction ABI mismatch");
_Static_assert(sizeof(struct rog5_sock_fprog) == 16 &&
	       offsetof(struct rog5_sock_fprog, filter) == 8,
	       "classic BPF program ABI mismatch");
_Static_assert(offsetof(struct rog5_seccomp_data, syscall_number) == 0 &&
	       offsetof(struct rog5_seccomp_data, architecture) == 4,
	       "seccomp data ABI mismatch");
_Static_assert(sizeof(struct rog5_cap_header) == 8 &&
	       sizeof(struct rog5_cap_data) == 12,
	       "capability ABI mismatch");

#define ROG5_BPF_STATEMENT(operation, constant) \
	{ (uint16_t)(operation), 0, 0, (constant) }
#define ROG5_BPF_JUMP(operation, constant, yes, no) \
	{ (uint16_t)(operation), (yes), (no), (constant) }

#define BUNDLE_MAX 64
#define HASH_LENGTH 64
#define MANIFEST_MAX 4096
#define HEADER_MAX 1024
#define REQUEST_MAX 256
#define PROFILE_MAX 31
#define TARGET_MAX 64
#define RELEASE_MAX 96
#define FETCH_TIMEOUT_MS 180000
#define WORKER_UID 65534
#define WORKER_GID 65534
#define WORKER_EXIT_SETUP 120
#define WORKER_EXIT_TRANSPORT 121
#define WORKER_EXIT_HEADER 122
#define WORKER_EXIT_MANIFEST 123
#define WORKER_EXIT_ARTIFACT 124
#define WORKER_EXIT_EOF 125
#define EXIT_BUNDLE_CONFLICT 42
#define EXIT_FETCH_ROOT_FAILED 43
#define EXIT_FETCH_STAGE_FAILED 44
#define EXIT_FETCH_CONNECT_FAILED 45
#define EXIT_FETCH_WORKER_TIMEOUT 46
#define EXIT_FETCH_WORKER_SIGNAL 47
#define EXIT_FETCH_TRANSPORT_FAILED 48
#define EXIT_FETCH_HEADER_FAILED 49
#define EXIT_FETCH_MANIFEST_FAILED 50
#define EXIT_FETCH_ARTIFACT_FAILED 51
#define EXIT_FETCH_EOF_FAILED 52
#define EXIT_FETCH_PARENT_VERIFY_FAILED 53
#define EXIT_FETCH_NORMALIZE_FAILED 54
#define EXIT_FETCH_FINAL_VERIFY_FAILED 55
#define EXIT_FETCH_PUBLISH_FAILED 56
#define EXIT_FETCH_WORKER_SETUP_FAILED 57
#define EXIT_FETCH_WORKER_FORK_FAILED 58
#define KERNEL_MAX (128ULL * 1024 * 1024)
#define DTB_MAX (2ULL * 1024 * 1024)
#define INITRAMFS_MAX (256ULL * 1024 * 1024)

#define ZERO_HASH \
	"0000000000000000000000000000000000000000000000000000000000000000"

struct sha256 {
	uint32_t state[8];
	uint64_t bytes;
	unsigned char buffer[64];
	size_t used;
};

struct manifest_policy {
	uint64_t kernel_size;
	char kernel_sha256[HASH_LENGTH + 1];
	uint64_t dtb_size;
	char dtb_sha256[HASH_LENGTH + 1];
	uint64_t initramfs_size;
	char initramfs_sha256[HASH_LENGTH + 1];
};

struct response_policy {
	uint64_t manifest_size;
	uint64_t signature_size;
	uint64_t kernel_size;
	uint64_t dtb_size;
	uint64_t initramfs_size;
};

struct artifact_policy {
	const char *name;
	uint64_t minimum;
	uint64_t maximum;
};

static const struct artifact_policy artifacts[] = {
	{ "manifest", 1, MANIFEST_MAX },
	{ "manifest.sig", 64, 64 },
	{ "Image", 64, KERNEL_MAX },
	{ "board.dtb", 40, DTB_MAX },
	{ "initramfs.cpio.gz", 2, INITRAMFS_MAX },
};

static const char *bundle_root = "/run/rog5-bundles";
static const char *server_ip = "169.254.77.1";
static const char *source_ip = "169.254.77.2";
static const char *network_interface = "usb0";
static uint16_t server_port = 8080;
static unsigned int fetch_timeout_ms = FETCH_TIMEOUT_MS;
static uid_t worker_uid = WORKER_UID;
static gid_t worker_gid = WORKER_GID;
#ifdef ROG5_FETCH_TESTING
static bool skip_device_bind;
static bool skip_seccomp;
static bool probe_forbidden_syscall;
static const char *fail_write_artifact;
#endif

static void fail(const char *format, ...)
{
	va_list arguments;

	va_start(arguments, format);
	fputs("rog5-bundle-fetch: ", stderr);
	vfprintf(stderr, format, arguments);
	fputc('\n', stderr);
	va_end(arguments);
	exit(EXIT_FAILURE);
}

static int64_t monotonic_milliseconds(void)
{
	struct timespec value;

	if (clock_gettime(CLOCK_MONOTONIC, &value) < 0)
		fail("cannot read monotonic clock");
	return (int64_t)value.tv_sec * 1000 + value.tv_nsec / 1000000;
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
		context->buffer[63 - index] =
			(unsigned char)(bits >> (index * 8));
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

static void digest_hex(const unsigned char digest[32],
		       char output[HASH_LENGTH + 1])
{
	static const char digits[] = "0123456789abcdef";
	size_t index;

	for (index = 0; index < 32; index++) {
		output[index * 2] = digits[digest[index] >> 4];
		output[index * 2 + 1] = digits[digest[index] & 0xf];
	}
	output[HASH_LENGTH] = '\0';
}

static void hash_memory(const void *data, size_t length,
			char output[HASH_LENGTH + 1])
{
	struct sha256 context;
	unsigned char digest[32];

	sha256_init(&context);
	sha256_update(&context, data, length);
	sha256_final(&context, digest);
	digest_hex(digest, output);
}

static bool valid_hash(const char *value)
{
	size_t index;

	if (strlen(value) != HASH_LENGTH || strcmp(value, ZERO_HASH) == 0)
		return false;
	for (index = 0; index < HASH_LENGTH; index++) {
		if (!((value[index] >= '0' && value[index] <= '9') ||
		      (value[index] >= 'a' && value[index] <= 'f')))
			return false;
	}
	return true;
}

static bool valid_bundle(const char *value)
{
	size_t length = strlen(value);
	size_t index;

	if (length < 1 || length > BUNDLE_MAX ||
	    !((value[0] >= 'a' && value[0] <= 'z') ||
	      (value[0] >= '0' && value[0] <= '9')) ||
	    strcmp(value, "none") == 0 || strstr(value, "..") != NULL)
		return false;
	for (index = 0; index < length; index++) {
		char byte = value[index];

		if (!((byte >= 'a' && byte <= 'z') ||
		      (byte >= '0' && byte <= '9') ||
		      byte == '.' || byte == '_' || byte == '-'))
			return false;
	}
	return true;
}

static bool valid_identity(const char *value, size_t maximum)
{
	size_t length = strlen(value);
	size_t index;

	if (length < 1 || length > maximum)
		return false;
	for (index = 0; index < length; index++) {
		char byte = value[index];

		if (!((byte >= 'a' && byte <= 'z') ||
		      (byte >= 'A' && byte <= 'Z') ||
		      (byte >= '0' && byte <= '9') ||
		      byte == '.' || byte == '_' || byte == '-' ||
		      byte == '+'))
			return false;
	}
	return value[0] != '.' && strstr(value, "..") == NULL;
}

static int take_field(char **cursor, const char *name,
		      char *output, size_t output_size)
{
	char *newline = strchr(*cursor, '\n');
	size_t name_length = strlen(name);
	size_t value_length;

	if (newline == NULL || strncmp(*cursor, name, name_length) != 0 ||
	    (*cursor)[name_length] != '=')
		return -1;
	value_length = (size_t)(newline - (*cursor + name_length + 1));
	if (value_length == 0 || value_length >= output_size)
		return -1;
	memcpy(output, *cursor + name_length + 1, value_length);
	output[value_length] = '\0';
	*cursor = newline + 1;
	return 0;
}

static uint64_t parse_number(const char *value, uint64_t minimum,
			     uint64_t maximum)
{
	uint64_t result = 0;
	size_t length = strlen(value);
	size_t index;

	if (length == 0 || (length > 1 && value[0] == '0'))
		return UINT64_MAX;
	for (index = 0; index < length; index++) {
		unsigned int digit;

		if (value[index] < '0' || value[index] > '9')
			return UINT64_MAX;
		digit = (unsigned int)(value[index] - '0');
		if (result > (UINT64_MAX - digit) / 10)
			return UINT64_MAX;
		result = result * 10 + digit;
	}
	if (result < minimum || result > maximum)
		return UINT64_MAX;
	return result;
}

static bool parse_manifest(char *manifest, const char *bundle,
			   struct manifest_policy *policy)
{
	char format[32];
	char parsed_bundle[BUNDLE_MAX + 1];
	char profile[PROFILE_MAX + 1];
	char kernel_size[32];
	char dtb_size[32];
	char initramfs_size[32];
	char target_id[TARGET_MAX + 1];
	char target_release[RELEASE_MAX + 1];
	char rollback_timeout[32];
	char target_timeout[32];
	char command_manifest_sha256[HASH_LENGTH + 1];
	char root_generation[32];
	char root_tree_sha256[HASH_LENGTH + 1];
	char root_seal_sha256[HASH_LENGTH + 1];
	char root_tree_entries[32];
	char root_subtree[32];
	char *cursor = manifest;
	uint64_t rollback;
	uint64_t target;

	if (take_field(&cursor, "format", format, sizeof(format)) < 0 ||
	    take_field(&cursor, "bundle", parsed_bundle,
		       sizeof(parsed_bundle)) < 0 ||
	    take_field(&cursor, "profile", profile, sizeof(profile)) < 0 ||
	    take_field(&cursor, "kernel_size", kernel_size,
		       sizeof(kernel_size)) < 0 ||
	    take_field(&cursor, "kernel_sha256", policy->kernel_sha256,
		       sizeof(policy->kernel_sha256)) < 0 ||
	    take_field(&cursor, "dtb_size", dtb_size,
		       sizeof(dtb_size)) < 0 ||
	    take_field(&cursor, "dtb_sha256", policy->dtb_sha256,
		       sizeof(policy->dtb_sha256)) < 0 ||
	    take_field(&cursor, "initramfs_size", initramfs_size,
		       sizeof(initramfs_size)) < 0 ||
	    take_field(&cursor, "initramfs_sha256",
		       policy->initramfs_sha256,
		       sizeof(policy->initramfs_sha256)) < 0 ||
	    take_field(&cursor, "target_id", target_id,
		       sizeof(target_id)) < 0 ||
	    take_field(&cursor, "target_release", target_release,
		       sizeof(target_release)) < 0 ||
	    take_field(&cursor, "rollback_timeout", rollback_timeout,
		       sizeof(rollback_timeout)) < 0 ||
	    take_field(&cursor, "target_timeout", target_timeout,
		       sizeof(target_timeout)) < 0 ||
	    take_field(&cursor, "a660_command_manifest_sha256",
		       command_manifest_sha256,
		       sizeof(command_manifest_sha256)) < 0 ||
	    take_field(&cursor, "root_generation", root_generation,
		       sizeof(root_generation)) < 0 ||
	    take_field(&cursor, "root_tree_sha256", root_tree_sha256,
		       sizeof(root_tree_sha256)) < 0 ||
	    take_field(&cursor, "root_seal_sha256", root_seal_sha256,
		       sizeof(root_seal_sha256)) < 0 ||
	    take_field(&cursor, "root_tree_entries", root_tree_entries,
		       sizeof(root_tree_entries)) < 0 ||
	    take_field(&cursor, "root_subtree", root_subtree,
		       sizeof(root_subtree)) < 0 ||
	    *cursor != '\0' ||
	    strcmp(format, "rog5-recovery-bundle-v2") != 0 ||
	    strcmp(parsed_bundle, bundle) != 0 ||
	    !valid_bundle(parsed_bundle) ||
	    !valid_identity(profile, PROFILE_MAX) ||
	    !valid_identity(target_id, TARGET_MAX) ||
	    !valid_identity(target_release, RELEASE_MAX) ||
	    !valid_hash(policy->kernel_sha256) ||
	    !valid_hash(policy->dtb_sha256) ||
	    !valid_hash(policy->initramfs_sha256))
		return false;
	rollback = parse_number(rollback_timeout, 60, 900);
	target = parse_number(target_timeout, 30, 600);
	if (rollback == UINT64_MAX || target == UINT64_MAX ||
	    target > rollback - 30)
		return false;
	if (strcmp(profile, "network-root-v1") == 0) {
		if (!valid_hash(command_manifest_sha256) ||
		    strcmp(root_generation, "arch-a") != 0 ||
		    !valid_hash(root_tree_sha256) ||
		    !valid_hash(root_seal_sha256) ||
		    parse_number(root_tree_entries, 1, INT64_MAX) ==
			    UINT64_MAX ||
		    strcmp(root_subtree, "/") != 0)
			return false;
	} else if (strcmp(profile, "diagnostic-initramfs-v1") == 0 ||
		   strcmp(profile, "persistent-root-ro-v1") == 0) {
		if (strcmp(command_manifest_sha256, ZERO_HASH) != 0 ||
		    strcmp(root_generation, "none") != 0 ||
		    strcmp(root_tree_sha256, ZERO_HASH) != 0 ||
		    strcmp(root_seal_sha256, ZERO_HASH) != 0 ||
		    strcmp(root_tree_entries, "0") != 0 ||
		    strcmp(root_subtree, "none") != 0 ||
		    (strcmp(profile, "persistent-root-ro-v1") == 0 &&
		     rollback < 300))
			return false;
	} else {
		return false;
	}
	policy->kernel_size =
		parse_number(kernel_size, 64, KERNEL_MAX);
	policy->dtb_size = parse_number(dtb_size, 40, DTB_MAX);
	policy->initramfs_size =
		parse_number(initramfs_size, 2, INITRAMFS_MAX);
	return policy->kernel_size != UINT64_MAX &&
		policy->dtb_size != UINT64_MAX &&
		policy->initramfs_size != UINT64_MAX;
}

static bool valid_manifest_bytes(const unsigned char *manifest, size_t length)
{
	size_t index;

	if (length < 1 || length > MANIFEST_MAX ||
	    manifest[length - 1] != '\n')
		return false;
	for (index = 0; index < length; index++) {
		unsigned char byte = manifest[index];

		if (byte == '\n')
			continue;
		if (byte < 0x21 || byte > 0x7e)
			return false;
	}
	return true;
}

static int wait_descriptor(int descriptor, short events, int64_t deadline)
{
	while (true) {
		struct pollfd item = {
			.fd = descriptor,
			.events = events,
		};
		struct timespec timeout;
		int64_t remaining = deadline - monotonic_milliseconds();
		int result;

		if (remaining <= 0)
			return false;
		timeout.tv_sec = remaining / 1000;
		timeout.tv_nsec = (remaining % 1000) * 1000000L;
		do {
			result = (int)syscall(
				SYS_ppoll, &item, 1, &timeout, NULL, 0);
		} while (result < 0 && errno == EINTR);
		if (result <= 0)
			return false;
		if ((item.revents & events) != 0)
			return true;
		if ((events & POLLIN) != 0 &&
		    (item.revents & POLLHUP) != 0)
			return true;
		if ((item.revents &
		     (POLLERR | POLLHUP | POLLNVAL)) != 0)
			return false;
	}
}

static bool send_exact(int descriptor, const void *buffer, size_t length,
		       int64_t deadline)
{
	const unsigned char *cursor = buffer;

	while (length != 0) {
		ssize_t count;

		if (!wait_descriptor(descriptor, POLLOUT, deadline))
			return false;
		count = send(descriptor, cursor, length, MSG_NOSIGNAL);
		if (count < 0 && (errno == EINTR || errno == EAGAIN ||
				 errno == EWOULDBLOCK))
			continue;
		if (count <= 0)
			return false;
		cursor += (size_t)count;
		length -= (size_t)count;
	}
	return true;
}

static bool receive_exact(int descriptor, void *buffer, size_t length,
			  int64_t deadline)
{
	unsigned char *cursor = buffer;

	while (length != 0) {
		ssize_t count;

		if (!wait_descriptor(descriptor, POLLIN, deadline))
			return false;
		count = recv(descriptor, cursor, length, 0);
		if (count < 0 && (errno == EINTR || errno == EAGAIN ||
				 errno == EWOULDBLOCK))
			continue;
		if (count <= 0)
			return false;
		cursor += (size_t)count;
		length -= (size_t)count;
	}
	return true;
}

static void encode_u32(uint32_t value, unsigned char output[4])
{
	output[0] = (unsigned char)(value >> 24);
	output[1] = (unsigned char)(value >> 16);
	output[2] = (unsigned char)(value >> 8);
	output[3] = (unsigned char)value;
}

static uint32_t decode_u32(const unsigned char input[4])
{
	return (uint32_t)input[0] << 24 |
		(uint32_t)input[1] << 16 |
		(uint32_t)input[2] << 8 |
		input[3];
}

static bool parse_response_header(char *header, const char *bundle,
				  const char *manifest_hash,
				  struct response_policy *policy)
{
	char format[32];
	char parsed_bundle[BUNDLE_MAX + 1];
	char parsed_hash[HASH_LENGTH + 1];
	char manifest_size[32];
	char signature_size[32];
	char kernel_size[32];
	char dtb_size[32];
	char initramfs_size[32];
	char *cursor = header;

	if (take_field(&cursor, "format", format, sizeof(format)) < 0 ||
	    take_field(&cursor, "bundle", parsed_bundle,
		       sizeof(parsed_bundle)) < 0 ||
	    take_field(&cursor, "manifest_sha256", parsed_hash,
		       sizeof(parsed_hash)) < 0 ||
	    take_field(&cursor, "manifest_size", manifest_size,
		       sizeof(manifest_size)) < 0 ||
	    take_field(&cursor, "signature_size", signature_size,
		       sizeof(signature_size)) < 0 ||
	    take_field(&cursor, "kernel_size", kernel_size,
		       sizeof(kernel_size)) < 0 ||
	    take_field(&cursor, "dtb_size", dtb_size,
		       sizeof(dtb_size)) < 0 ||
	    take_field(&cursor, "initramfs_size", initramfs_size,
		       sizeof(initramfs_size)) < 0 ||
	    *cursor != '\0' ||
	    strcmp(format, "rog5-fetch-response-v1") != 0 ||
	    strcmp(parsed_bundle, bundle) != 0 ||
	    strcmp(parsed_hash, manifest_hash) != 0 ||
	    !valid_bundle(parsed_bundle) || !valid_hash(parsed_hash))
		return false;
	policy->manifest_size =
		parse_number(manifest_size, 1, MANIFEST_MAX);
	policy->signature_size = parse_number(signature_size, 64, 64);
	policy->kernel_size = parse_number(kernel_size, 64, KERNEL_MAX);
	policy->dtb_size = parse_number(dtb_size, 40, DTB_MAX);
	policy->initramfs_size =
		parse_number(initramfs_size, 2, INITRAMFS_MAX);
	return policy->manifest_size != UINT64_MAX &&
		policy->signature_size == 64 &&
		policy->kernel_size != UINT64_MAX &&
		policy->dtb_size != UINT64_MAX &&
		policy->initramfs_size != UINT64_MAX;
}

static bool worker_receive_file(int socket_descriptor, int directory,
				const char *name, uint64_t length,
				const char *expected_hash,
				unsigned char *capture,
				int64_t deadline)
{
	struct sha256 hash;
	unsigned char digest[32];
	char actual_hash[HASH_LENGTH + 1];
	uint64_t received = 0;
	int output;

	output = openat(directory, name,
			O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC,
			0600);
	if (output < 0)
		return false;
	sha256_init(&hash);
	while (received < length) {
		unsigned char buffer[64 * 1024];
		size_t requested = length - received < sizeof(buffer) ?
			(size_t)(length - received) : sizeof(buffer);
		size_t written = 0;
		ssize_t count;

		if (!wait_descriptor(socket_descriptor, POLLIN, deadline)) {
			close(output);
			return false;
		}
		count = recv(socket_descriptor, buffer, requested, 0);
		if (count < 0 && (errno == EINTR || errno == EAGAIN ||
				 errno == EWOULDBLOCK))
			continue;
		if (count <= 0) {
			close(output);
			return false;
		}
		sha256_update(&hash, buffer, (size_t)count);
		if (capture != NULL)
			memcpy(capture + received, buffer, (size_t)count);
		while (written < (size_t)count) {
			size_t write_size = (size_t)count - written;
#ifdef ROG5_FETCH_TESTING
			bool inject_enospc = fail_write_artifact != NULL &&
				strcmp(fail_write_artifact, name) == 0;

			if (inject_enospc && write_size > 1)
				write_size /= 2;
#endif
			ssize_t output_count = write(
				output, buffer + written,
				write_size);

			if (output_count < 0 && errno == EINTR)
				continue;
			if (output_count <= 0) {
				close(output);
				return false;
			}
			written += (size_t)output_count;
#ifdef ROG5_FETCH_TESTING
			if (inject_enospc) {
				errno = ENOSPC;
				close(output);
				return false;
			}
#endif
		}
		received += (uint64_t)count;
	}
	sha256_final(&hash, digest);
	digest_hex(digest, actual_hash);
	{
		bool valid = expected_hash == NULL ||
			strcmp(actual_hash, expected_hash) == 0;

		if (fsync(output) < 0)
			valid = false;
		if (close(output) < 0)
			valid = false;
		return valid;
	}
}

#if defined(__aarch64__)
#define ROG5_AUDIT_ARCH ROG5_AUDIT_ARCH_AARCH64
#elif defined(__x86_64__)
#define ROG5_AUDIT_ARCH ROG5_AUDIT_ARCH_X86_64
#else
#error unsupported fetch-worker architecture
#endif

#define ALLOW_SYSCALL(number) \
	ROG5_BPF_JUMP(ROG5_BPF_JMP | ROG5_BPF_JEQ | ROG5_BPF_K, \
		      (number), 0, 1), \
	ROG5_BPF_STATEMENT(ROG5_BPF_RET | ROG5_BPF_K, \
			   ROG5_SECCOMP_RET_ALLOW)

static void install_worker_filter(void)
{
	static const struct rog5_sock_filter instructions[] = {
		ROG5_BPF_STATEMENT(
			ROG5_BPF_LD | ROG5_BPF_W | ROG5_BPF_ABS,
			offsetof(struct rog5_seccomp_data, architecture)),
		ROG5_BPF_JUMP(
			ROG5_BPF_JMP | ROG5_BPF_JEQ | ROG5_BPF_K,
			ROG5_AUDIT_ARCH, 1, 0),
		ROG5_BPF_STATEMENT(
			ROG5_BPF_RET | ROG5_BPF_K,
			ROG5_SECCOMP_RET_KILL_PROCESS),
		ROG5_BPF_STATEMENT(
			ROG5_BPF_LD | ROG5_BPF_W | ROG5_BPF_ABS,
			offsetof(struct rog5_seccomp_data, syscall_number)),
		ALLOW_SYSCALL(__NR_read),
		ALLOW_SYSCALL(__NR_write),
		ALLOW_SYSCALL(__NR_close),
		ALLOW_SYSCALL(__NR_openat),
#ifdef __NR_fstat
		ALLOW_SYSCALL(__NR_fstat),
#endif
#ifdef __NR_newfstatat
		ALLOW_SYSCALL(__NR_newfstatat),
#endif
		ALLOW_SYSCALL(__NR_fsync),
		ALLOW_SYSCALL(__NR_recvfrom),
		ALLOW_SYSCALL(__NR_sendto),
		ALLOW_SYSCALL(__NR_shutdown),
		ALLOW_SYSCALL(__NR_ppoll),
		ALLOW_SYSCALL(__NR_clock_gettime),
#ifdef __NR_restart_syscall
		ALLOW_SYSCALL(__NR_restart_syscall),
#endif
		ALLOW_SYSCALL(__NR_rt_sigreturn),
#ifdef __NR_exit
		ALLOW_SYSCALL(__NR_exit),
#endif
		ALLOW_SYSCALL(__NR_exit_group),
		ROG5_BPF_STATEMENT(
			ROG5_BPF_RET | ROG5_BPF_K,
			ROG5_SECCOMP_RET_KILL_PROCESS),
	};
	static const struct rog5_sock_fprog program = {
		.length = (unsigned short)(
			sizeof(instructions) / sizeof(instructions[0])),
		.filter = (struct rog5_sock_filter *)instructions,
	};

#ifdef ROG5_FETCH_TESTING
	if (skip_seccomp) {
		if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) < 0)
			_exit(120);
		return;
	}
#endif
	if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) < 0 ||
	    prctl(PR_SET_SECCOMP, ROG5_SECCOMP_MODE_FILTER, &program) < 0)
		_exit(120);
}

static bool close_descriptor_checked(int descriptor);

static bool close_descriptors_from_proc(void)
{
	DIR *stream = opendir("/proc/self/fd");
	struct dirent *entry;
	int stream_descriptor;
	bool success = true;

	if (stream == NULL)
		return false;
	stream_descriptor = dirfd(stream);
	while (true) {
		unsigned long descriptor = 0;
		const char *cursor;

		errno = 0;
		entry = readdir(stream);
		if (entry == NULL) {
			if (errno != 0)
				success = false;
			break;
		}
		if (entry->d_name[0] == '.')
			continue;
		for (cursor = entry->d_name; *cursor != '\0'; cursor++) {
			if (*cursor < '0' || *cursor > '9' ||
			    descriptor > (INT_MAX -
				    (unsigned int)(*cursor - '0')) / 10U) {
				success = false;
				break;
			}
			descriptor = descriptor * 10U +
				(unsigned int)(*cursor - '0');
		}
		if (!success)
			break;
		if ((int)descriptor == stream_descriptor ||
		    descriptor == 3 || descriptor == 4)
			continue;
		if (!close_descriptor_checked((int)descriptor)) {
			success = false;
			break;
		}
	}
	if (closedir(stream) < 0)
		success = false;
	return success;
}

static bool close_descriptor_checked(int descriptor)
{
	while (close(descriptor) < 0) {
		if (errno == EBADF)
			return true;
		if (errno != EINTR)
			return false;
	}
	return true;
}

static void close_worker_descriptors(int socket_descriptor, int directory)
{
	int socket_copy;
	int directory_copy;

	socket_copy = fcntl(socket_descriptor, F_DUPFD_CLOEXEC, 5);
	directory_copy = fcntl(directory, F_DUPFD_CLOEXEC, 5);
	if (socket_copy < 0 || directory_copy < 0)
		_exit(120);
	if (dup3(socket_copy, 3, O_CLOEXEC) < 0 ||
	    dup3(directory_copy, 4, O_CLOEXEC) < 0)
		_exit(120);
	if (syscall(ROG5_SYS_CLOSE_RANGE, 5U, UINT_MAX, 0U) == 0 &&
	    syscall(ROG5_SYS_CLOSE_RANGE, 0U, 2U, 0U) == 0)
		return;
	if (close_descriptors_from_proc())
		return;
	_exit(120);
}

static void drop_worker_privileges(pid_t parent)
{
	struct rog5_cap_header header = {
		.version = ROG5_CAPABILITY_VERSION_3,
		.process = 0,
	};
	struct rog5_cap_data capabilities[2] = { { 0 }, { 0 } };
	int capability;

	if (prctl(PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0) < 0 ||
	    getppid() != parent)
		_exit(120);
#ifdef ROG5_FETCH_TESTING
	if (geteuid() != 0) {
		if (geteuid() != worker_uid || getegid() != worker_gid)
			_exit(120);
		goto capabilities_cleared;
	}
#endif
	if (fchdir(4) < 0 || chroot(".") < 0 || chdir("/") < 0)
		_exit(120);
	for (capability = 0; capability < INT_MAX; capability++) {
		if (prctl(PR_CAPBSET_DROP, capability, 0, 0, 0) == 0)
			continue;
		if (errno == EINVAL)
			break;
		_exit(120);
	}
	if (prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL, 0, 0, 0) < 0 &&
	    errno != EINVAL)
		_exit(120);
	if (setgroups(0, NULL) < 0 ||
	    setresgid(worker_gid, worker_gid, worker_gid) < 0 ||
	    setresuid(worker_uid, worker_uid, worker_uid) < 0)
		_exit(120);
#ifdef ROG5_FETCH_TESTING
capabilities_cleared:
#endif
	if (syscall(SYS_capset, &header, capabilities) < 0)
		_exit(120);
	if (prctl(PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0) < 0 ||
	    getppid() != parent)
		_exit(120);
	install_worker_filter();
}

static void run_worker(int socket_descriptor, int directory,
		       const char *bundle, const char *manifest_hash,
		       int64_t deadline, pid_t parent)
{
	unsigned char manifest[MANIFEST_MAX + 1];
	unsigned char prefix[4];
	char request[REQUEST_MAX];
	char response[HEADER_MAX + 1];
	char actual_manifest_hash[HASH_LENGTH + 1];
	struct manifest_policy manifest_policy;
	struct response_policy response_policy;
	int request_length;
	uint32_t response_length;

	if (prctl(PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0) < 0 ||
	    getppid() != parent)
		_exit(120);
	request_length = snprintf(
		request, sizeof(request),
		"format=rog5-fetch-request-v1\n"
		"bundle=%s\n"
		"manifest_sha256=%s\n",
		bundle, manifest_hash);
	if (request_length < 0 || request_length >= (int)sizeof(request))
		_exit(120);
	close_worker_descriptors(socket_descriptor, directory);
	drop_worker_privileges(parent);
#ifdef ROG5_FETCH_TESTING
	if (probe_forbidden_syscall)
		(void)syscall(SYS_getuid);
#endif
	encode_u32((uint32_t)request_length, prefix);
	if (!send_exact(3, prefix, sizeof(prefix), deadline) ||
	    !send_exact(3, request, (size_t)request_length, deadline) ||
	    shutdown(3, SHUT_WR) < 0 ||
	    !receive_exact(3, prefix, sizeof(prefix), deadline))
		_exit(121);
	response_length = decode_u32(prefix);
	if (response_length < 1 || response_length > HEADER_MAX ||
	    !receive_exact(3, response, response_length, deadline))
		_exit(121);
	response[response_length] = '\0';
	if (!valid_manifest_bytes(
		    (const unsigned char *)response, response_length) ||
	    !parse_response_header(
		    response, bundle, manifest_hash, &response_policy))
		_exit(122);
	if (!worker_receive_file(
		    3, 4, "manifest", response_policy.manifest_size,
		    manifest_hash, manifest, deadline))
		_exit(123);
	manifest[response_policy.manifest_size] = '\0';
	hash_memory(
		manifest, (size_t)response_policy.manifest_size,
		actual_manifest_hash);
	if (strcmp(actual_manifest_hash, manifest_hash) != 0 ||
	    !valid_manifest_bytes(
		    manifest, (size_t)response_policy.manifest_size) ||
	    !parse_manifest((char *)manifest, bundle, &manifest_policy) ||
	    manifest_policy.kernel_size != response_policy.kernel_size ||
	    manifest_policy.dtb_size != response_policy.dtb_size ||
	    manifest_policy.initramfs_size !=
		    response_policy.initramfs_size)
		_exit(123);
	if (!worker_receive_file(
		    3, 4, "manifest.sig", response_policy.signature_size,
		    NULL, NULL, deadline) ||
	    !worker_receive_file(
		    3, 4, "Image", response_policy.kernel_size,
		    manifest_policy.kernel_sha256, NULL, deadline) ||
	    !worker_receive_file(
		    3, 4, "board.dtb", response_policy.dtb_size,
		    manifest_policy.dtb_sha256, NULL, deadline) ||
	    !worker_receive_file(
		    3, 4, "initramfs.cpio.gz",
		    response_policy.initramfs_size,
		    manifest_policy.initramfs_sha256, NULL, deadline))
		_exit(124);
	if (!wait_descriptor(3, POLLIN, deadline))
		_exit(125);
	{
		unsigned char extra;
		ssize_t count = recv(3, &extra, 1, 0);

		if (count != 0)
			_exit(125);
	}
	if (close(4) < 0 || close(3) < 0)
		_exit(125);
	_exit(0);
}

enum final_state {
	FINAL_INVALID,
	FINAL_MATCH,
	FINAL_HASH_CONFLICT,
};

struct root_inventory {
	unsigned int final_count;
	unsigned int staging_count;
	char final_name[BUNDLE_MAX + 1];
	char staging_name[BUNDLE_MAX + sizeof(".incoming.")];
};

static uid_t publication_uid;
static gid_t publication_gid;
#ifdef ROG5_FETCH_TESTING
static const char *crash_stage;
#endif

static void log_error(const char *format, ...)
{
	va_list arguments;

	va_start(arguments, format);
	fputs("rog5-bundle-fetch: ", stderr);
	vfprintf(stderr, format, arguments);
	fputc('\n', stderr);
	va_end(arguments);
}

static void crash_point(const char *stage)
{
#ifdef ROG5_FETCH_TESTING
	if (crash_stage != NULL && strcmp(crash_stage, stage) == 0)
		_exit(99);
#else
	(void)stage;
#endif
}

static int artifact_index(const char *name)
{
	size_t index;

	for (index = 0; index < sizeof(artifacts) / sizeof(artifacts[0]);
	     index++) {
		if (strcmp(name, artifacts[index].name) == 0)
			return (int)index;
	}
	return -1;
}

static bool safe_root_metadata(int descriptor)
{
	struct stat metadata;

	return fstat(descriptor, &metadata) == 0 &&
		S_ISDIR(metadata.st_mode) &&
		metadata.st_uid == publication_uid &&
		metadata.st_gid == publication_gid &&
		(metadata.st_mode & 07777) == 0700;
}

static bool scan_root(int root, struct root_inventory *inventory)
{
	DIR *stream;
	struct dirent *entry;
	int copy;
	bool success = true;

	memset(inventory, 0, sizeof(*inventory));
	copy = openat(root, ".", O_RDONLY | O_DIRECTORY |
		      O_NOFOLLOW | O_CLOEXEC);
	if (copy < 0)
		return false;
	stream = fdopendir(copy);
	if (stream == NULL) {
		close(copy);
		return false;
	}
	while (true) {
		struct stat metadata;
		const char *suffix;

		errno = 0;
		entry = readdir(stream);
		if (entry == NULL) {
			if (errno != 0)
				success = false;
			break;
		}
		if (strcmp(entry->d_name, ".") == 0 ||
		    strcmp(entry->d_name, "..") == 0)
			continue;
		if (fstatat(root, entry->d_name, &metadata,
			    AT_SYMLINK_NOFOLLOW) < 0 ||
		    !S_ISDIR(metadata.st_mode)) {
			success = false;
			break;
		}
		if (strncmp(entry->d_name, ".incoming.",
			    strlen(".incoming.")) == 0) {
			suffix = entry->d_name + strlen(".incoming.");
			if (!valid_bundle(suffix) ||
			    ++inventory->staging_count != 1 ||
			    strlen(entry->d_name) >=
				    sizeof(inventory->staging_name)) {
				success = false;
				break;
			}
			strcpy(inventory->staging_name, entry->d_name);
			continue;
		}
		if (!valid_bundle(entry->d_name) ||
		    ++inventory->final_count != 1) {
			success = false;
			break;
		}
		strcpy(inventory->final_name, entry->d_name);
	}
	if (closedir(stream) < 0)
		success = false;
	return success;
}

static bool safe_staging_metadata(const struct stat *metadata, bool file)
{
	mode_t permissions = metadata->st_mode & 07777;
	bool owner = metadata->st_uid == publication_uid ||
		metadata->st_uid == worker_uid;

	if (!owner)
		return false;
	if (file)
		return S_ISREG(metadata->st_mode) &&
			metadata->st_nlink == 1 &&
			(permissions == 0600 || permissions == 0400);
	return S_ISDIR(metadata->st_mode) &&
		(permissions == 0700 || permissions == 0500);
}

static bool cleanup_staging(int root, const char *name)
{
	bool seen[sizeof(artifacts) / sizeof(artifacts[0])] = { false };
	struct stat directory_metadata;
	DIR *stream;
	struct dirent *entry;
	int directory;
	int copy;
	bool success = true;

	directory = openat(root, name, O_RDONLY | O_DIRECTORY |
			   O_NOFOLLOW | O_CLOEXEC);
	if (directory < 0 ||
	    fstat(directory, &directory_metadata) < 0 ||
	    !safe_staging_metadata(&directory_metadata, false)) {
		if (directory >= 0)
			close(directory);
		return false;
	}
	copy = openat(directory, ".", O_RDONLY | O_DIRECTORY |
		      O_NOFOLLOW | O_CLOEXEC);
	if (copy < 0) {
		close(directory);
		return false;
	}
	stream = fdopendir(copy);
	if (stream == NULL) {
		close(copy);
		close(directory);
		return false;
	}
	while (true) {
		struct stat metadata;
		int index;

		errno = 0;
		entry = readdir(stream);
		if (entry == NULL) {
			if (errno != 0)
				success = false;
			break;
		}
		if (strcmp(entry->d_name, ".") == 0 ||
		    strcmp(entry->d_name, "..") == 0)
			continue;
		index = artifact_index(entry->d_name);
		if (index < 0 || seen[index] ||
		    fstatat(directory, entry->d_name, &metadata,
			    AT_SYMLINK_NOFOLLOW) < 0 ||
		    !safe_staging_metadata(&metadata, true) ||
		    metadata.st_size < 0 ||
		    (uint64_t)metadata.st_size > artifacts[index].maximum) {
			success = false;
			break;
		}
		seen[index] = true;
	}
	if (closedir(stream) < 0)
		success = false;
	if (success && fchmod(directory, 0700) < 0)
		success = false;
	if (success) {
		size_t index;

		for (index = 0;
		     index < sizeof(artifacts) / sizeof(artifacts[0]);
		     index++) {
			if (seen[index] &&
			    unlinkat(directory, artifacts[index].name, 0) < 0) {
				success = false;
				break;
			}
		}
	}
	if (close(directory) < 0)
		success = false;
	if (success && unlinkat(root, name, AT_REMOVEDIR) < 0)
		success = false;
	return success;
}

static bool scan_complete_directory(int directory, uid_t owner,
				    mode_t file_mode, mode_t directory_mode)
{
	bool seen[sizeof(artifacts) / sizeof(artifacts[0])] = { false };
	struct stat directory_metadata;
	DIR *stream;
	struct dirent *entry;
	int copy;
	bool success = true;
	size_t count = 0;

	if (fstat(directory, &directory_metadata) < 0 ||
	    !S_ISDIR(directory_metadata.st_mode) ||
	    directory_metadata.st_uid != owner ||
	    (directory_metadata.st_mode & 07777) != directory_mode) {
		log_error("bundle directory metadata does not match policy");
		return false;
	}
	copy = openat(directory, ".", O_RDONLY | O_DIRECTORY |
		      O_NOFOLLOW | O_CLOEXEC);
	if (copy < 0)
		return false;
	stream = fdopendir(copy);
	if (stream == NULL) {
		close(copy);
		return false;
	}
	while (true) {
		struct stat metadata;
		int index;

		errno = 0;
		entry = readdir(stream);
		if (entry == NULL) {
			if (errno != 0)
				success = false;
			break;
		}
		if (strcmp(entry->d_name, ".") == 0 ||
		    strcmp(entry->d_name, "..") == 0)
			continue;
		index = artifact_index(entry->d_name);
		if (index < 0 || seen[index] ||
		    fstatat(directory, entry->d_name, &metadata,
			    AT_SYMLINK_NOFOLLOW) < 0 ||
		    !S_ISREG(metadata.st_mode) ||
		    metadata.st_uid != owner || metadata.st_nlink != 1 ||
		    (metadata.st_mode & 07777) != file_mode ||
		    metadata.st_size < 0 ||
		    (uint64_t)metadata.st_size < artifacts[index].minimum ||
		    (uint64_t)metadata.st_size > artifacts[index].maximum) {
			log_error("bundle file metadata does not match policy: %s",
				  entry->d_name);
			success = false;
			break;
		}
		seen[index] = true;
		count++;
	}
	if (closedir(stream) < 0)
		success = false;
	if (success &&
	    count != sizeof(artifacts) / sizeof(artifacts[0]))
		log_error("bundle inventory is incomplete: %zu entries", count);
	return success &&
		count == sizeof(artifacts) / sizeof(artifacts[0]);
}

static bool read_file_at(int directory, const char *name,
			 unsigned char *output, size_t length,
			 int64_t deadline)
{
	size_t used = 0;
	int descriptor = openat(
		directory, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);

	if (descriptor < 0)
		return false;
	while (used < length) {
		ssize_t count = read(descriptor, output + used, length - used);

		if (monotonic_milliseconds() >= deadline) {
			close(descriptor);
			return false;
		}
		if (count < 0 && errno == EINTR)
			continue;
		if (count <= 0) {
			close(descriptor);
			return false;
		}
		used += (size_t)count;
	}
	{
		unsigned char extra;
		ssize_t count;

		do {
			count = read(descriptor, &extra, 1);
		} while (count < 0 && errno == EINTR);
		if (count != 0) {
			close(descriptor);
			return false;
		}
	}
	return close(descriptor) == 0;
}

static bool hash_file_at(int directory, const char *name,
			 uint64_t expected_size,
			 char output[HASH_LENGTH + 1],
			 int64_t deadline)
{
	struct sha256 context;
	unsigned char digest[32];
	unsigned char buffer[64 * 1024];
	uint64_t total = 0;
	int descriptor = openat(
		directory, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);

	if (descriptor < 0)
		return false;
	sha256_init(&context);
	while (true) {
		ssize_t count = read(descriptor, buffer, sizeof(buffer));

		if (monotonic_milliseconds() >= deadline) {
			close(descriptor);
			return false;
		}
		if (count < 0 && errno == EINTR)
			continue;
		if (count < 0) {
			close(descriptor);
			return false;
		}
		if (count == 0)
			break;
		if (total > UINT64_MAX - (uint64_t)count) {
			close(descriptor);
			return false;
		}
		total += (uint64_t)count;
		sha256_update(&context, buffer, (size_t)count);
	}
	if (close(descriptor) < 0 || total != expected_size)
		return false;
	sha256_final(&context, digest);
	digest_hex(digest, output);
	return true;
}

static enum final_state validate_complete_bundle(
	int directory, uid_t owner, mode_t file_mode, mode_t directory_mode,
	const char *bundle, const char *expected_manifest_hash,
	int64_t deadline)
{
	unsigned char manifest[MANIFEST_MAX + 1];
	char actual_hash[HASH_LENGTH + 1];
	char artifact_hash[HASH_LENGTH + 1];
	struct manifest_policy policy;
	struct stat metadata;

	if (!scan_complete_directory(
		    directory, owner, file_mode, directory_mode)) {
		log_error("bundle inventory or metadata is invalid");
		return FINAL_INVALID;
	}
	if (fstatat(directory, "manifest", &metadata,
		    AT_SYMLINK_NOFOLLOW) < 0 ||
	    metadata.st_size < 1 || metadata.st_size > MANIFEST_MAX ||
	    !read_file_at(directory, "manifest", manifest,
			  (size_t)metadata.st_size, deadline)) {
		log_error("bundle manifest cannot be read exactly");
		return FINAL_INVALID;
	}
	manifest[metadata.st_size] = '\0';
	hash_memory(manifest, (size_t)metadata.st_size, actual_hash);
	if (strcmp(actual_hash, expected_manifest_hash) != 0)
		return FINAL_HASH_CONFLICT;
	if (!valid_manifest_bytes(manifest, (size_t)metadata.st_size) ||
	    !parse_manifest((char *)manifest, bundle, &policy)) {
		log_error("bundle manifest is not canonical");
		return FINAL_INVALID;
	}
	if (fstatat(directory, "manifest.sig", &metadata,
		    AT_SYMLINK_NOFOLLOW) < 0 ||
	    metadata.st_size != 64) {
		log_error("bundle signature length is invalid");
		return FINAL_INVALID;
	}
	if (!hash_file_at(directory, "Image", policy.kernel_size,
			  artifact_hash, deadline) ||
	    strcmp(artifact_hash, policy.kernel_sha256) != 0) {
		log_error("bundle kernel size or hash is invalid");
		return FINAL_INVALID;
	}
	if (!hash_file_at(directory, "board.dtb", policy.dtb_size,
			  artifact_hash, deadline) ||
	    strcmp(artifact_hash, policy.dtb_sha256) != 0) {
		log_error("bundle DTB size or hash is invalid");
		return FINAL_INVALID;
	}
	if (!hash_file_at(directory, "initramfs.cpio.gz",
			  policy.initramfs_size, artifact_hash, deadline) ||
	    strcmp(artifact_hash, policy.initramfs_sha256) != 0) {
		log_error("bundle initramfs size or hash is invalid");
		return FINAL_INVALID;
	}
	return FINAL_MATCH;
}

static int connect_fixed(int64_t deadline)
{
	struct sockaddr_in source = {
		.sin_family = AF_INET,
	};
	struct sockaddr_in server = {
		.sin_family = AF_INET,
	};
	int descriptor;
	int error;
	socklen_t error_length = sizeof(error);

	if (inet_pton(AF_INET, source_ip, &source.sin_addr) != 1 ||
	    inet_pton(AF_INET, server_ip, &server.sin_addr) != 1)
		return -1;
	source.sin_port = htons(0);
	server.sin_port = htons(server_port);
	descriptor = socket(
		AF_INET, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC,
		IPPROTO_TCP);
	if (descriptor < 0)
		return -1;
#ifdef ROG5_FETCH_TESTING
	if (!skip_device_bind)
#endif
	{
		if (setsockopt(descriptor, SOL_SOCKET, SO_BINDTODEVICE,
			       network_interface,
			       (socklen_t)(strlen(network_interface) + 1)) < 0) {
			close(descriptor);
			return -1;
		}
	}
	if (bind(descriptor, (struct sockaddr *)&source,
		 sizeof(source)) < 0) {
		close(descriptor);
		return -1;
	}
	if (connect(descriptor, (struct sockaddr *)&server,
		    sizeof(server)) < 0) {
		if (errno != EINPROGRESS ||
		    !wait_descriptor(descriptor, POLLOUT, deadline) ||
		    getsockopt(descriptor, SOL_SOCKET, SO_ERROR, &error,
			       &error_length) < 0 ||
		    error_length != sizeof(error) || error != 0) {
			close(descriptor);
			return -1;
		}
	}
	return descriptor;
}

static bool wait_for_worker(pid_t worker, int64_t deadline, int *status)
{
	while (monotonic_milliseconds() < deadline) {
		pid_t result = waitpid(worker, status, WNOHANG);
		struct timespec delay = {
			.tv_nsec = 10 * 1000 * 1000,
		};

		if (result == worker)
			return true;
		if (result < 0 && errno != EINTR)
			break;
		nanosleep(&delay, NULL);
	}
	if (kill(worker, SIGKILL) < 0 && errno != ESRCH)
		log_error("cannot signal timed-out fetch worker");
	while (true) {
		pid_t result = waitpid(worker, status, 0);

		if (result == worker)
			break;
		if (result < 0 && errno == EINTR)
			continue;
		break;
	}
	return false;
}

enum worker_outcome {
	WORKER_OK,
	WORKER_SETUP_FAILED,
	WORKER_FORK_FAILED,
	WORKER_TIMEOUT,
	WORKER_SIGNAL,
	WORKER_TRANSPORT_FAILED,
	WORKER_HEADER_FAILED,
	WORKER_MANIFEST_FAILED,
	WORKER_ARTIFACT_FAILED,
	WORKER_EOF_FAILED,
};

static enum worker_outcome run_sandboxed_worker(
	int socket_descriptor, int directory, const char *bundle,
	const char *manifest_hash, int64_t deadline)
{
	pid_t parent = getpid();
	pid_t worker = fork();
	int status;

	if (worker < 0)
		return WORKER_FORK_FAILED;
	if (worker == 0)
		run_worker(
			socket_descriptor, directory, bundle, manifest_hash,
			deadline, parent);
	if (!wait_for_worker(worker, deadline, &status))
		return WORKER_TIMEOUT;
	if (!WIFEXITED(status))
		return WORKER_SIGNAL;
	switch (WEXITSTATUS(status)) {
	case 0:
		return WORKER_OK;
	case WORKER_EXIT_SETUP:
		return WORKER_SETUP_FAILED;
	case WORKER_EXIT_TRANSPORT:
		return WORKER_TRANSPORT_FAILED;
	case WORKER_EXIT_HEADER:
		return WORKER_HEADER_FAILED;
	case WORKER_EXIT_MANIFEST:
		return WORKER_MANIFEST_FAILED;
	case WORKER_EXIT_ARTIFACT:
		return WORKER_ARTIFACT_FAILED;
	case WORKER_EXIT_EOF:
		return WORKER_EOF_FAILED;
	default:
		return WORKER_SIGNAL;
	}
}

static bool normalize_staging(int directory, int64_t deadline)
{
	size_t index;

	if (fchown(directory, publication_uid, publication_gid) < 0 ||
	    fchmod(directory, 0500) < 0 || fsync(directory) < 0)
		return false;
	crash_point("after-directory-lockdown");
	if (monotonic_milliseconds() >= deadline)
		return false;
	for (index = 0;
	     index < sizeof(artifacts) / sizeof(artifacts[0]); index++) {
		char stage[96];
		int descriptor = openat(
			directory, artifacts[index].name,
			O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
		bool valid = descriptor >= 0;

		if (valid &&
		    fchown(descriptor, publication_uid, publication_gid) < 0)
			valid = false;
		if (valid && fchmod(descriptor, 0400) < 0)
			valid = false;
		if (valid && fsync(descriptor) < 0)
			valid = false;
		if (descriptor >= 0 && close(descriptor) < 0)
			valid = false;
		if (!valid)
			return false;
		snprintf(stage, sizeof(stage), "after-normalize-%s",
			 artifacts[index].name);
		crash_point(stage);
		if (monotonic_milliseconds() >= deadline)
			return false;
	}
	if (fsync(directory) < 0)
		return false;
	crash_point("after-directory-sync");
	return monotonic_milliseconds() < deadline;
}

static bool publish_staging(int root, const char *staging,
			    const char *bundle, int64_t deadline,
			    bool *renamed)
{
	*renamed = false;
	if (monotonic_milliseconds() >= deadline)
		return false;
	crash_point("before-rename");
	if (syscall(SYS_renameat2, root, staging, root, bundle,
		    1U) < 0)
		return false;
	*renamed = true;
	crash_point("after-rename");
	if (fsync(root) < 0)
		return false;
	crash_point("after-root-sync");
	return monotonic_milliseconds() < deadline;
}

#ifdef ROG5_FETCH_TESTING
static bool parse_unsigned(const char *value, unsigned long maximum,
			   unsigned long *output)
{
	char *end;
	unsigned long parsed;

	if (value[0] == '\0' || (value[0] == '0' && value[1] != '\0'))
		return false;
	errno = 0;
	parsed = strtoul(value, &end, 10);
	if (errno != 0 || *end != '\0' || parsed > maximum)
		return false;
	*output = parsed;
	return true;
}
#endif

static int parse_arguments(int argc, char **argv)
{
	int index = 1;

#ifdef ROG5_FETCH_TESTING
	publication_uid = geteuid();
	publication_gid = getegid();
	worker_uid = geteuid() == 0 ? WORKER_UID : geteuid();
	worker_gid = getegid() == 0 ? WORKER_GID : getegid();
	while (index < argc) {
		unsigned long parsed;

		if (strcmp(argv[index], "--skip-device-bind") == 0) {
			skip_device_bind = true;
			index++;
			continue;
		}
		if (strcmp(argv[index], "--skip-seccomp") == 0) {
			skip_seccomp = true;
			index++;
			continue;
		}
		if (strcmp(argv[index], "--probe-forbidden-syscall") == 0) {
			probe_forbidden_syscall = true;
			index++;
			continue;
		}
		if (index + 1 >= argc)
			break;
		if (strcmp(argv[index], "--bundle-root") == 0)
			bundle_root = argv[index + 1];
		else if (strcmp(argv[index], "--server-ip") == 0)
			server_ip = argv[index + 1];
		else if (strcmp(argv[index], "--source-ip") == 0)
			source_ip = argv[index + 1];
		else if (strcmp(argv[index], "--interface") == 0)
			network_interface = argv[index + 1];
		else if (strcmp(argv[index], "--crash-at") == 0)
			crash_stage = argv[index + 1];
		else if (strcmp(argv[index], "--fail-write-artifact") == 0) {
			if (artifact_index(argv[index + 1]) < 0)
				return -1;
			fail_write_artifact = argv[index + 1];
		}
		else if (strcmp(argv[index], "--port") == 0) {
			if (!parse_unsigned(argv[index + 1], UINT16_MAX,
					    &parsed) || parsed == 0)
				return -1;
			server_port = (uint16_t)parsed;
		} else if (strcmp(argv[index], "--timeout-ms") == 0) {
			if (!parse_unsigned(argv[index + 1], 600000,
					    &parsed) || parsed < 50)
				return -1;
			fetch_timeout_ms = (unsigned int)parsed;
		} else if (strcmp(argv[index], "--worker-uid") == 0) {
			if (!parse_unsigned(argv[index + 1], UINT_MAX,
					    &parsed))
				return -1;
			worker_uid = (uid_t)parsed;
		} else if (strcmp(argv[index], "--worker-gid") == 0) {
			if (!parse_unsigned(argv[index + 1], UINT_MAX,
					    &parsed))
				return -1;
			worker_gid = (gid_t)parsed;
		} else {
			break;
		}
		index += 2;
	}
#else
	(void)argv;
	publication_uid = 0;
	publication_gid = 0;
	if (geteuid() != 0)
		return -1;
#endif
	if (argc - index != 2)
		return -1;
	return index;
}

int main(int argc, char **argv)
{
	struct root_inventory inventory;
	enum final_state final_state;
	enum worker_outcome worker_outcome;
	char staging[BUNDLE_MAX + sizeof(".incoming.")];
	const char *bundle;
	const char *manifest_hash;
	int64_t deadline;
	int argument_index;
	int root = -1;
	int directory = -1;
	int socket_descriptor = -1;
	int result = EXIT_FAILURE;
	bool staging_exists = false;
	bool renamed = false;

	umask(0077);
	argument_index = parse_arguments(argc, argv);
	if (argument_index < 0) {
		log_error("usage: rog5-bundle-fetch BUNDLE MANIFEST_SHA256");
		return EXIT_FAILURE;
	}
	bundle = argv[argument_index];
	manifest_hash = argv[argument_index + 1];
	if (!valid_bundle(bundle) || !valid_hash(manifest_hash)) {
		log_error("invalid requested bundle identity");
		return EXIT_FAILURE;
	}
	deadline = monotonic_milliseconds() + fetch_timeout_ms;
	root = open(bundle_root, O_RDONLY | O_DIRECTORY |
		    O_NOFOLLOW | O_CLOEXEC);
	if (root < 0 || !safe_root_metadata(root) ||
	    flock(root, LOCK_EX | LOCK_NB) < 0 ||
	    !scan_root(root, &inventory)) {
		log_error("unsafe, busy, or over-quota bundle root");
		result = EXIT_FETCH_ROOT_FAILED;
		goto out;
	}
	if (inventory.staging_count != 0 &&
	    !cleanup_staging(root, inventory.staging_name)) {
		log_error("unsafe stale staging directory");
		result = EXIT_FETCH_STAGE_FAILED;
		goto out;
	}
	if (inventory.final_count != 0) {
		if (strcmp(inventory.final_name, bundle) != 0) {
			log_error("bundle quota conflict");
			result = EXIT_BUNDLE_CONFLICT;
			goto out;
		}
		directory = openat(
			root, bundle, O_RDONLY | O_DIRECTORY |
			O_NOFOLLOW | O_CLOEXEC);
		if (directory < 0) {
			log_error("cannot open existing bundle");
			result = EXIT_FETCH_PARENT_VERIFY_FAILED;
			goto out;
		}
		final_state = validate_complete_bundle(
			directory, publication_uid, 0400, 0500,
			bundle, manifest_hash, deadline);
		if (final_state == FINAL_MATCH) {
			result = EXIT_SUCCESS;
			goto out;
		}
		if (final_state == FINAL_HASH_CONFLICT) {
			log_error("bundle identity conflicts with manifest hash");
			result = EXIT_BUNDLE_CONFLICT;
			goto out;
		}
		log_error("existing bundle is unsafe or corrupt");
		result = EXIT_FETCH_PARENT_VERIFY_FAILED;
		goto out;
	}
	snprintf(staging, sizeof(staging), ".incoming.%s", bundle);
	if (mkdirat(root, staging, 0700) < 0) {
		log_error("cannot create staging directory");
		result = EXIT_FETCH_STAGE_FAILED;
		goto out;
	}
	staging_exists = true;
	directory = openat(
		root, staging, O_RDONLY | O_DIRECTORY |
		O_NOFOLLOW | O_CLOEXEC);
	if (directory < 0 ||
	    fchown(directory, worker_uid, worker_gid) < 0) {
		log_error("cannot delegate staging directory");
		result = EXIT_FETCH_STAGE_FAILED;
		goto out;
	}
	socket_descriptor = connect_fixed(deadline);
	if (socket_descriptor < 0) {
		log_error("fixed bundle peer is unavailable");
		result = EXIT_FETCH_CONNECT_FAILED;
		goto out;
	}
	worker_outcome = run_sandboxed_worker(
		socket_descriptor, directory, bundle, manifest_hash, deadline);
	if (worker_outcome != WORKER_OK) {
		log_error("sandboxed bundle transfer failed");
		switch (worker_outcome) {
		case WORKER_SETUP_FAILED:
			result = EXIT_FETCH_WORKER_SETUP_FAILED;
			break;
		case WORKER_FORK_FAILED:
			result = EXIT_FETCH_WORKER_FORK_FAILED;
			break;
		case WORKER_TIMEOUT:
			result = EXIT_FETCH_WORKER_TIMEOUT;
			break;
		case WORKER_SIGNAL:
			result = EXIT_FETCH_WORKER_SIGNAL;
			break;
		case WORKER_TRANSPORT_FAILED:
			result = EXIT_FETCH_TRANSPORT_FAILED;
			break;
		case WORKER_HEADER_FAILED:
			result = EXIT_FETCH_HEADER_FAILED;
			break;
		case WORKER_MANIFEST_FAILED:
			result = EXIT_FETCH_MANIFEST_FAILED;
			break;
		case WORKER_ARTIFACT_FAILED:
			result = EXIT_FETCH_ARTIFACT_FAILED;
			break;
		case WORKER_EOF_FAILED:
			result = EXIT_FETCH_EOF_FAILED;
			break;
		case WORKER_OK:
			break;
		}
		goto out;
	}
	if (close(socket_descriptor) < 0) {
		socket_descriptor = -1;
		log_error("cannot close transfer socket");
		result = EXIT_FETCH_EOF_FAILED;
		goto out;
	}
	socket_descriptor = -1;
	crash_point("after-worker");
	final_state = validate_complete_bundle(
		directory, worker_uid, 0600, 0700, bundle, manifest_hash,
		deadline);
	if (final_state != FINAL_MATCH) {
		log_error("staged bundle failed parent validation");
		result = EXIT_FETCH_PARENT_VERIFY_FAILED;
		goto out;
	}
	crash_point("after-parent-validation");
	if (!normalize_staging(directory, deadline)) {
		log_error("cannot normalize staged bundle");
		result = EXIT_FETCH_NORMALIZE_FAILED;
		goto out;
	}
	final_state = validate_complete_bundle(
		directory, publication_uid, 0400, 0500, bundle,
		manifest_hash, deadline);
	if (final_state != FINAL_MATCH) {
		log_error("normalized bundle failed final validation");
		result = EXIT_FETCH_FINAL_VERIFY_FAILED;
		goto out;
	}
	crash_point("after-final-validation");
	if (close(directory) < 0) {
		directory = -1;
		log_error("cannot close staged bundle");
		result = EXIT_FETCH_FINAL_VERIFY_FAILED;
		goto out;
	}
	directory = -1;
	if (!publish_staging(
		    root, staging, bundle, deadline, &renamed)) {
		if (renamed)
			staging_exists = false;
		log_error("cannot atomically publish staged bundle");
		result = EXIT_FETCH_PUBLISH_FAILED;
		goto out;
	}
	staging_exists = false;
	result = EXIT_SUCCESS;
out:
	if (socket_descriptor >= 0)
		close(socket_descriptor);
	if (directory >= 0)
		close(directory);
	if (staging_exists && root >= 0 &&
	    !cleanup_staging(root, staging))
		log_error("staging cleanup requires recovery restart");
	if (root >= 0)
		close(root);
	return result;
}
