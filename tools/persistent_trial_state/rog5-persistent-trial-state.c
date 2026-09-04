// SPDX-License-Identifier: MIT

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef ROG5_DECIDE_ROOT
#define ROG5_DECIDE_ROOT "/mnt/userdata"
#endif

#ifndef ROG5_HEALTHY_ROOT
#define ROG5_HEALTHY_ROOT "/.rog5/userdata-rw"
#endif

#define RECORD_NAME "wifi-trial-state"
#define TEMPORARY_NAME ".wifi-trial-state.next"
#define RECORD_CAPACITY 512
#define BUNDLE_CAPACITY 65
#define HASH_LENGTH 64

struct trial_identity {
	const char *id;
	const char *primary;
	const char *primary_hash;
	const char *fallback;
	const char *fallback_hash;
};

struct parsed_trial {
	char id[HASH_LENGTH + 1];
	char primary[BUNDLE_CAPACITY];
	char primary_hash[HASH_LENGTH + 1];
	char fallback[BUNDLE_CAPACITY];
	char fallback_hash[HASH_LENGTH + 1];
	char state[8];
};

static __attribute__((noreturn, format(printf, 1, 2)))
void fail(const char *format, ...)
{
	va_list arguments;

	fprintf(stderr, "FAIL persistent trial state: ");
	va_start(arguments, format);
	vfprintf(stderr, format, arguments);
	va_end(arguments);
	fputc('\n', stderr);
	exit(1);
}

static bool lower_hex(const char *value)
{
	size_t index;

	if (strlen(value) != HASH_LENGTH)
		return false;
	for (index = 0; index < HASH_LENGTH; index++) {
		if (!((value[index] >= '0' && value[index] <= '9') ||
		      (value[index] >= 'a' && value[index] <= 'f')))
			return false;
	}
	return true;
}

static bool bundle_name(const char *value)
{
	size_t index;
	size_t length = strlen(value);

	if (length < 1 || length >= BUNDLE_CAPACITY || strstr(value, ".."))
		return false;
	if (!((value[0] >= 'a' && value[0] <= 'z') ||
	      (value[0] >= '0' && value[0] <= '9')))
		return false;
	for (index = 1; index < length; index++) {
		char byte = value[index];

		if (!((byte >= 'a' && byte <= 'z') ||
		      (byte >= '0' && byte <= '9') || byte == '.' ||
		      byte == '_' || byte == '-'))
			return false;
	}
	return true;
}

static void validate_identity(const struct trial_identity *identity)
{
	if (!lower_hex(identity->id) || !bundle_name(identity->primary) ||
	    !lower_hex(identity->primary_hash) ||
	    !bundle_name(identity->fallback) ||
	    !lower_hex(identity->fallback_hash) ||
	    strcmp(identity->primary, identity->fallback) == 0)
		fail("invalid trial identity");
}

static size_t render_record(char *output, size_t capacity,
			    const struct trial_identity *identity,
			    const char *state)
{
	int length = snprintf(output, capacity,
			      "format=rog5-persistent-wifi-trial-v1\n"
			      "trial_id=%s\n"
			      "primary_bundle=%s\n"
			      "primary_manifest_sha256=%s\n"
			      "fallback_bundle=%s\n"
			      "fallback_manifest_sha256=%s\n"
			      "state=%s\n",
			      identity->id, identity->primary,
			      identity->primary_hash, identity->fallback,
			      identity->fallback_hash, state);

	if (length < 1 || (size_t)length >= capacity)
		fail("record is too large");
	return (size_t)length;
}

static bool take_field(char **cursor, const char *name, char *output,
		       size_t capacity)
{
	char *newline = strchr(*cursor, '\n');
	size_t name_length = strlen(name);
	size_t value_length;
	size_t index;

	if (!newline || strncmp(*cursor, name, name_length) != 0 ||
	    (*cursor)[name_length] != '=')
		return false;
	value_length = (size_t)(newline - *cursor) - name_length - 1;
	if (value_length < 1 || value_length >= capacity)
		return false;
	for (index = 0; index < value_length; index++) {
		unsigned char byte =
			(unsigned char)(*cursor)[name_length + 1 + index];

		if (byte < 0x21 || byte > 0x7e)
			return false;
	}
	memcpy(output, *cursor + name_length + 1, value_length);
	output[value_length] = '\0';
	*cursor = newline + 1;
	return true;
}

static void parse_record(char *record, struct parsed_trial *parsed)
{
	static const char format[] = "format=rog5-persistent-wifi-trial-v1\n";
	struct trial_identity identity;
	char *cursor = record;

	if (strncmp(cursor, format, sizeof(format) - 1) != 0)
		fail("invalid trial record format");
	cursor += sizeof(format) - 1;
	if (!take_field(&cursor, "trial_id", parsed->id, sizeof(parsed->id)) ||
	    !take_field(&cursor, "primary_bundle", parsed->primary,
			 sizeof(parsed->primary)) ||
	    !take_field(&cursor, "primary_manifest_sha256", parsed->primary_hash,
			 sizeof(parsed->primary_hash)) ||
	    !take_field(&cursor, "fallback_bundle", parsed->fallback,
			 sizeof(parsed->fallback)) ||
	    !take_field(&cursor, "fallback_manifest_sha256", parsed->fallback_hash,
			 sizeof(parsed->fallback_hash)) ||
	    !take_field(&cursor, "state", parsed->state, sizeof(parsed->state)) ||
	    *cursor != '\0' ||
	    (strcmp(parsed->state, "pending") != 0 &&
	     strcmp(parsed->state, "healthy") != 0))
		fail("invalid trial record fields");
	identity.id = parsed->id;
	identity.primary = parsed->primary;
	identity.primary_hash = parsed->primary_hash;
	identity.fallback = parsed->fallback;
	identity.fallback_hash = parsed->fallback_hash;
	validate_identity(&identity);
}

static void validate_directory(int descriptor, mode_t mode, const char *name)
{
	struct stat metadata;

	if (fstat(descriptor, &metadata) < 0)
		fail("cannot stat %s: %s", name, strerror(errno));
	if (!S_ISDIR(metadata.st_mode) || metadata.st_uid != geteuid() ||
	    metadata.st_gid != getegid() ||
	    (metadata.st_mode & 0777) != mode)
		fail("unsafe %s metadata", name);
}

static int open_state_directory(const char *root_path, bool create)
{
	int root;
	int rog5;
	int state;

	root = open(root_path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
	if (root < 0)
		fail("cannot open fixed state root: %s", strerror(errno));
	validate_directory(root, 0755, "state root");
	rog5 = openat(root, "rog5",
		      O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
	if (rog5 < 0)
		fail("cannot open rog5 state directory: %s", strerror(errno));
	validate_directory(rog5, 0700, "rog5 state directory");
	if (create && mkdirat(rog5, "boot", 0700) == 0) {
		if (fsync(rog5) < 0)
			fail("cannot sync new boot state directory: %s",
			     strerror(errno));
	} else if (create && errno != EEXIST) {
		fail("cannot create boot state directory: %s", strerror(errno));
	}
	state = openat(rog5, "boot",
		       O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
	if (state < 0)
		fail("cannot open boot state directory: %s", strerror(errno));
	validate_directory(state, 0700, "boot state directory");
	if (close(rog5) < 0 || close(root) < 0)
		fail("cannot close state parent directory: %s", strerror(errno));
	return state;
}

static void write_all(int descriptor, const char *data, size_t length)
{
	while (length > 0) {
		ssize_t written = write(descriptor, data, length);

		if (written < 0 && errno == EINTR)
			continue;
		if (written <= 0)
			fail("state write failed: %s", strerror(errno));
		data += written;
		length -= (size_t)written;
	}
}

static int read_record(int directory, char *output, size_t capacity,
			struct stat *metadata)
{
	struct stat path_metadata;
	int descriptor;
	size_t used = 0;

	descriptor = openat(directory, RECORD_NAME,
			    O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
	if (descriptor < 0 && errno == ENOENT)
		return -1;
	if (descriptor < 0)
		fail("cannot open trial record: %s", strerror(errno));
	if (flock(descriptor, LOCK_EX | LOCK_NB) < 0)
		fail("concurrent trial record operation");
	if (fstat(descriptor, metadata) < 0)
		fail("cannot stat trial record: %s", strerror(errno));
	if (!S_ISREG(metadata->st_mode) || metadata->st_uid != geteuid() ||
	    metadata->st_gid != getegid() ||
	    (metadata->st_mode & 0777) != 0600 || metadata->st_nlink != 1 ||
	    metadata->st_size < 1 || (uintmax_t)metadata->st_size >= capacity)
		fail("unsafe trial record metadata");
	while (used < (size_t)metadata->st_size) {
		ssize_t count = read(descriptor, output + used,
				     (size_t)metadata->st_size - used);

		if (count < 0 && errno == EINTR)
			continue;
		if (count <= 0)
			fail("short trial record read");
		used += (size_t)count;
	}
	if (fstatat(directory, RECORD_NAME, &path_metadata,
		    AT_SYMLINK_NOFOLLOW) < 0 ||
	    path_metadata.st_dev != metadata->st_dev ||
	    path_metadata.st_ino != metadata->st_ino)
		fail("trial record pathname changed");
	output[used] = '\0';
	return descriptor;
}

static void create_pending(int directory, const char *record, size_t length)
{
	int descriptor;

	descriptor = openat(directory, TEMPORARY_NAME,
			    O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW |
			    O_CLOEXEC, 0600);
	if (descriptor < 0)
		fail("cannot create trial temporary: %s", strerror(errno));
	write_all(descriptor, record, length);
	if (fsync(descriptor) < 0 || close(descriptor) < 0)
		fail("cannot sync trial temporary: %s", strerror(errno));
	if (linkat(directory, TEMPORARY_NAME, directory, RECORD_NAME, 0) < 0)
		fail("cannot publish pending trial: %s", strerror(errno));
	if (unlinkat(directory, TEMPORARY_NAME, 0) < 0 || fsync(directory) < 0)
		fail("cannot sync pending trial publication: %s", strerror(errno));
}

static void replace_record(int directory, int current,
			    const struct stat *expected,
			    const char *record, size_t length)
{
	struct stat path_metadata;
	int descriptor;

	descriptor = openat(directory, TEMPORARY_NAME,
			    O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW |
			    O_CLOEXEC, 0600);
	if (descriptor < 0)
		fail("cannot create trial temporary: %s", strerror(errno));
	write_all(descriptor, record, length);
	if (fsync(descriptor) < 0 || close(descriptor) < 0)
		fail("cannot sync trial temporary: %s", strerror(errno));
	if (fstatat(directory, RECORD_NAME, &path_metadata,
		    AT_SYMLINK_NOFOLLOW) < 0 ||
	    path_metadata.st_dev != expected->st_dev ||
	    path_metadata.st_ino != expected->st_ino)
		fail("trial record changed before replacement");
	if (renameat(directory, TEMPORARY_NAME, directory, RECORD_NAME) < 0 ||
	    fsync(directory) < 0)
		fail("cannot publish trial replacement: %s", strerror(errno));
	if (close(current) < 0)
		fail("cannot close replaced trial record: %s", strerror(errno));
}

static void print_line(const char *value)
{
	if (printf("%s\n", value) < 0 || fflush(stdout) == EOF)
		fail("cannot write result");
}

static void decide(const struct trial_identity *identity)
{
	char actual[RECORD_CAPACITY];
	char pending[RECORD_CAPACITY];
	char healthy[RECORD_CAPACITY];
	struct stat metadata;
	int directory = open_state_directory(ROG5_DECIDE_ROOT, true);
	int descriptor;

	render_record(pending, sizeof(pending), identity, "pending");
	render_record(healthy, sizeof(healthy), identity, "healthy");
	descriptor = read_record(directory, actual, sizeof(actual), &metadata);
	if (descriptor < 0) {
		create_pending(directory, pending, strlen(pending));
		descriptor = read_record(directory, actual, sizeof(actual),
					 &metadata);
		if (descriptor < 0 || strcmp(actual, pending) != 0)
			fail("pending trial publication did not revalidate");
		print_line(identity->primary);
	} else if (strcmp(actual, pending) == 0) {
		print_line(identity->fallback);
	} else if (strcmp(actual, healthy) == 0) {
		/* Accepted persistent boots also need a fresh health acknowledgment.
		 * Publish pending durably before exposing a primary decision; a lost
		 * reply or subsequent failed boot must select the signed fallback.
		 */
		replace_record(directory, descriptor, &metadata, pending,
			       strlen(pending));
		descriptor = read_record(directory, actual, sizeof(actual),
					 &metadata);
		if (descriptor < 0 || strcmp(actual, pending) != 0)
			fail("rearmed trial publication did not revalidate");
		print_line(identity->primary);
	} else {
		fail("trial record identity or state changed");
	}
	if (descriptor >= 0 && close(descriptor) < 0)
		fail("cannot close trial record: %s", strerror(errno));
	if (close(directory) < 0)
		fail("cannot close boot state directory: %s", strerror(errno));
}

static void mark_healthy(const char *expected_id, const char *expected_primary)
{
	char actual[RECORD_CAPACITY];
	char healthy[RECORD_CAPACITY];
	struct parsed_trial parsed;
	struct trial_identity identity;
	struct stat metadata;
	int directory = open_state_directory(ROG5_HEALTHY_ROOT, false);
	int descriptor;

	descriptor = read_record(directory, actual, sizeof(actual), &metadata);
	if (descriptor < 0)
		fail("pending trial record is absent");
	parse_record(actual, &parsed);
	if (strcmp(parsed.id, expected_id) != 0 ||
	    strcmp(parsed.primary, expected_primary) != 0)
		fail("running trial identity does not match pending state");
	identity.id = parsed.id;
	identity.primary = parsed.primary;
	identity.primary_hash = parsed.primary_hash;
	identity.fallback = parsed.fallback;
	identity.fallback_hash = parsed.fallback_hash;
	render_record(healthy, sizeof(healthy), &identity, "healthy");
	if (strcmp(parsed.state, "healthy") == 0) {
		print_line("already-healthy");
		if (close(descriptor) < 0)
			fail("cannot close healthy trial record: %s", strerror(errno));
	} else if (strcmp(parsed.state, "pending") == 0) {
		replace_record(directory, descriptor, &metadata, healthy,
				strlen(healthy));
		descriptor = read_record(directory, actual, sizeof(actual),
					 &metadata);
		if (descriptor < 0 || strcmp(actual, healthy) != 0)
			fail("healthy trial publication did not revalidate");
		if (close(descriptor) < 0)
			fail("cannot close committed trial record: %s",
			     strerror(errno));
		print_line("healthy");
	} else {
		fail("pending trial identity or state changed");
	}
	if (close(directory) < 0)
		fail("cannot close boot state directory: %s", strerror(errno));
}

int main(int argc, char **argv)
{
	struct trial_identity identity;

	if (argc == 7 && strcmp(argv[1], "decide") == 0) {
		identity.id = argv[2];
		identity.primary = argv[3];
		identity.primary_hash = argv[4];
		identity.fallback = argv[5];
		identity.fallback_hash = argv[6];
		validate_identity(&identity);
		decide(&identity);
	} else if (argc == 4 && strcmp(argv[1], "healthy") == 0) {
		if (!lower_hex(argv[2]) || !bundle_name(argv[3]))
			fail("invalid running trial identity");
		mark_healthy(argv[2], argv[3]);
	} else {
		fail("usage: decide TRIAL_ID PRIMARY PRIMARY_HASH FALLBACK "
		     "FALLBACK_HASH | healthy TRIAL_ID PRIMARY");
	}
	return 0;
}
