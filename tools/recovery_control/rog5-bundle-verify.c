#define _GNU_SOURCE

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <zlib.h>

#define MANIFEST_MAX 4096
#define KERNEL_MAX (128ULL * 1024 * 1024)
#define KERNEL_MEMORY_MAX (256ULL * 1024 * 1024)
#define DTB_MAX (2ULL * 1024 * 1024)
#define INITRAMFS_MAX (256ULL * 1024 * 1024)
#define INITRAMFS_UNCOMPRESSED_MAX (128ULL * 1024 * 1024)
#define BUNDLE_MAX 64
#define TARGET_MAX 64
#define RELEASE_MAX 96
#define HASH_LENGTH 64
#define CMDLINE_MAX 1024
#define FDT_DEPTH_MAX 64
#define FDT_RANGES_MAX 128
#define CPIO_HEADER_SIZE 110
#define CPIO_NAME_MAX 4096
#define CPIO_ENTRIES_MAX 8192
#define PLAN_MAX 2048
#define HANDOFF_FD 3
#define HANDOFF_DESCRIPTOR_COUNT 3
#define REQUIRED_SEALS \
	(F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE)

#define FDT_MAGIC 0xd00dfeedU
#define FDT_BEGIN_NODE 1U
#define FDT_END_NODE 2U
#define FDT_PROP 3U
#define FDT_NOP 4U
#define FDT_END 9U

#define ZERO_HASH \
	"0000000000000000000000000000000000000000000000000000000000000000"

struct profile_policy {
	const char *name;
	const char *command_line;
	uint64_t minimum_rollback;
	bool binds_a660_root;
	bool requires_early_target_reporter;
};

struct bundle_manifest {
	char bundle[BUNDLE_MAX + 1];
	char profile[32];
	const struct profile_policy *policy;
	uint64_t kernel_size;
	char kernel_sha256[HASH_LENGTH + 1];
	uint64_t dtb_size;
	char dtb_sha256[HASH_LENGTH + 1];
	uint64_t initramfs_size;
	char initramfs_sha256[HASH_LENGTH + 1];
	char target_id[TARGET_MAX + 1];
	char target_release[RELEASE_MAX + 1];
	uint64_t rollback_timeout;
	uint64_t target_timeout;
	char a660_command_manifest_sha256[HASH_LENGTH + 1];
	char root_generation[32];
	char root_tree_sha256[HASH_LENGTH + 1];
	char root_seal_sha256[HASH_LENGTH + 1];
	uint64_t root_tree_entries;
	char root_subtree[32];
};

struct fdt_range {
	uint64_t start;
	uint64_t size;
};

enum cpio_phase {
	CPIO_HEADER,
	CPIO_NAME,
	CPIO_NAME_PADDING,
	CPIO_DATA,
	CPIO_DATA_PADDING,
	CPIO_DONE,
};

struct cpio_parser {
	enum cpio_phase phase;
	unsigned char header[CPIO_HEADER_SIZE];
	size_t header_used;
	char name[CPIO_NAME_MAX + 1];
	size_t name_size;
	size_t name_used;
	char previous_name[CPIO_NAME_MAX + 1];
	uint32_t mode;
	uint32_t expected_checksum;
	uint32_t checksum;
	uint64_t file_size;
	uint64_t file_remaining;
	size_t padding_remaining;
	size_t entry_count;
	bool crc;
	bool current_trailer;
	bool seen_init;
	bool seen_persistent_root_verifier;
	bool seen_early_target_reporter;
	bool seen_trailer;
};

static const char *bundle_root = "/run/rog5-bundles";
static const char *trust_key_path =
	"/etc/rog5/recovery-bundle-ed25519.pub";
static const struct profile_policy profile_policies[] = {
	{
		.name = "diagnostic-initramfs-v1",
		.command_line = "rog5.netroot=1 rog5.diagnostic=1",
		.minimum_rollback = 60,
		.binds_a660_root = true,
		.requires_early_target_reporter = true,
	},
	{
		.name = "network-root-v1",
		.command_line = "rog5.netroot=1",
		.minimum_rollback = 60,
		.binds_a660_root = true,
		.requires_early_target_reporter = false,
	},
	{
		.name = "persistent-root-ro-v1",
		.command_line =
			"rog5.ufs_discovery=1 rog5.persistent_ro=1",
		.minimum_rollback = 300,
		.binds_a660_root = false,
		.requires_early_target_reporter = false,
	},
};

static void fail(const char *format, ...)
{
	va_list arguments;

	va_start(arguments, format);
	fputs("rog5-bundle-verify: ", stderr);
	vfprintf(stderr, format, arguments);
	fputc('\n', stderr);
	va_end(arguments);
	exit(EXIT_FAILURE);
}

static uint32_t read_be32(const unsigned char *value)
{
	return (uint32_t)value[0] << 24 |
		(uint32_t)value[1] << 16 |
		(uint32_t)value[2] << 8 |
		(uint32_t)value[3];
}

static uint64_t read_be_cells(const unsigned char *value,
			      unsigned int cells)
{
	uint64_t result = 0;
	unsigned int index;

	for (index = 0; index < cells; index++)
		result = result << 32 | read_be32(value + index * 4);
	return result;
}

static uint64_t read_le64(const unsigned char *value)
{
	uint64_t result = 0;
	unsigned int index;

	for (index = 0; index < 8; index++)
		result |= (uint64_t)value[index] << (index * 8);
	return result;
}

static bool range_within(size_t offset, size_t length, size_t total)
{
	return offset <= total && length <= total - offset;
}

static bool valid_hash(const char *value)
{
	size_t index;

	if (strlen(value) != HASH_LENGTH || strcmp(value, ZERO_HASH) == 0)
		return false;
	for (index = 0; index < HASH_LENGTH; index++) {
		if ((value[index] < '0' || value[index] > '9') &&
		    (value[index] < 'a' || value[index] > 'f'))
			return false;
	}
	return true;
}

static bool valid_bundle(const char *value)
{
	size_t length = strlen(value);
	size_t index;

	if (length < 1 || length > BUNDLE_MAX ||
	    strcmp(value, "none") == 0 ||
	    !((value[0] >= 'a' && value[0] <= 'z') ||
	      (value[0] >= '0' && value[0] <= '9')) ||
	    strstr(value, "..") != NULL)
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
		      byte == '.' || byte == '_' || byte == '+' ||
		      byte == '-'))
			return false;
	}
	return value[0] != '.' && strstr(value, "..") == NULL;
}

static const struct profile_policy *find_profile_policy(const char *name)
{
	size_t index;

	for (index = 0; index < sizeof(profile_policies) /
	     sizeof(profile_policies[0]); index++) {
		if (strcmp(name, profile_policies[index].name) == 0)
			return &profile_policies[index];
	}
	return NULL;
}

static uint64_t parse_number(const char *value, uint64_t minimum,
			     uint64_t maximum)
{
	uint64_t result = 0;
	size_t index;

	if (*value == '\0' || (value[0] == '0' && value[1] != '\0'))
		fail("noncanonical numeric manifest field");
	for (index = 0; value[index] != '\0'; index++) {
		unsigned int digit;

		if (value[index] < '0' || value[index] > '9')
			fail("invalid numeric manifest field");
		digit = (unsigned int)(value[index] - '0');
		if (result > (UINT64_MAX - digit) / 10)
			fail("numeric manifest field overflow");
		result = result * 10 + digit;
	}
	if (result < minimum || result > maximum)
		fail("numeric manifest field is outside policy");
	return result;
}

static int take_field(char **cursor, const char *name, char *output,
		      size_t capacity)
{
	size_t name_length = strlen(name);
	char *newline;
	size_t length;

	if (strncmp(*cursor, name, name_length) != 0 ||
	    (*cursor)[name_length] != '=')
		return -1;
	*cursor += name_length + 1;
	newline = strchr(*cursor, '\n');
	if (newline == NULL)
		return -1;
	length = (size_t)(newline - *cursor);
	if (length + 1 > capacity)
		return -1;
	memcpy(output, *cursor, length);
	output[length] = '\0';
	*cursor = newline + 1;
	return 0;
}

static void validate_manifest_bytes(const unsigned char *record, size_t length)
{
	size_t index;

	if (length == 0 || record[length - 1] != '\n')
		fail("manifest is not a newline-terminated ASCII record");
	for (index = 0; index < length; index++) {
		unsigned char byte = record[index];

		if (byte != '\n' && (byte < 0x20 || byte > 0x7e))
			fail("manifest contains a noncanonical byte");
	}
}

static void parse_manifest(char *record, const char *expected_bundle,
			   struct bundle_manifest *manifest)
{
	char format[32];
	char kernel_size[32];
	char dtb_size[32];
	char initramfs_size[32];
	char rollback_timeout[32];
	char target_timeout[32];
	char root_tree_entries[32];
	char *cursor = record;

	memset(manifest, 0, sizeof(*manifest));
	if (take_field(&cursor, "format", format, sizeof(format)) < 0 ||
	    take_field(&cursor, "bundle", manifest->bundle,
		       sizeof(manifest->bundle)) < 0 ||
	    take_field(&cursor, "profile", manifest->profile,
		       sizeof(manifest->profile)) < 0 ||
	    take_field(&cursor, "kernel_size", kernel_size,
		       sizeof(kernel_size)) < 0 ||
	    take_field(&cursor, "kernel_sha256", manifest->kernel_sha256,
		       sizeof(manifest->kernel_sha256)) < 0 ||
	    take_field(&cursor, "dtb_size", dtb_size,
		       sizeof(dtb_size)) < 0 ||
	    take_field(&cursor, "dtb_sha256", manifest->dtb_sha256,
		       sizeof(manifest->dtb_sha256)) < 0 ||
	    take_field(&cursor, "initramfs_size", initramfs_size,
		       sizeof(initramfs_size)) < 0 ||
	    take_field(&cursor, "initramfs_sha256",
		       manifest->initramfs_sha256,
		       sizeof(manifest->initramfs_sha256)) < 0 ||
	    take_field(&cursor, "target_id", manifest->target_id,
		       sizeof(manifest->target_id)) < 0 ||
	    take_field(&cursor, "target_release", manifest->target_release,
		       sizeof(manifest->target_release)) < 0 ||
	    take_field(&cursor, "rollback_timeout", rollback_timeout,
		       sizeof(rollback_timeout)) < 0 ||
	    take_field(&cursor, "target_timeout", target_timeout,
		       sizeof(target_timeout)) < 0 ||
	    take_field(&cursor, "a660_command_manifest_sha256",
		       manifest->a660_command_manifest_sha256,
		       sizeof(manifest->a660_command_manifest_sha256)) < 0 ||
	    take_field(&cursor, "root_generation",
		       manifest->root_generation,
		       sizeof(manifest->root_generation)) < 0 ||
	    take_field(&cursor, "root_tree_sha256",
		       manifest->root_tree_sha256,
		       sizeof(manifest->root_tree_sha256)) < 0 ||
	    take_field(&cursor, "root_seal_sha256",
		       manifest->root_seal_sha256,
		       sizeof(manifest->root_seal_sha256)) < 0 ||
	    take_field(&cursor, "root_tree_entries", root_tree_entries,
		       sizeof(root_tree_entries)) < 0 ||
	    take_field(&cursor, "root_subtree", manifest->root_subtree,
		       sizeof(manifest->root_subtree)) < 0 ||
	    *cursor != '\0')
		fail("manifest is not the canonical v2 record");
	manifest->policy = find_profile_policy(manifest->profile);
	if (strcmp(format, "rog5-recovery-bundle-v2") != 0 ||
	    strcmp(manifest->bundle, expected_bundle) != 0 ||
	    !valid_bundle(manifest->bundle) ||
	    manifest->policy == NULL ||
	    !valid_hash(manifest->kernel_sha256) ||
	    !valid_hash(manifest->dtb_sha256) ||
	    !valid_hash(manifest->initramfs_sha256) ||
	    !valid_identity(manifest->target_id, TARGET_MAX) ||
	    !valid_identity(manifest->target_release, RELEASE_MAX))
		fail("manifest violates fixed identity policy");
	manifest->kernel_size = parse_number(kernel_size, 64, KERNEL_MAX);
	manifest->dtb_size = parse_number(dtb_size, 40, DTB_MAX);
	manifest->initramfs_size =
		parse_number(initramfs_size, 2, INITRAMFS_MAX);
	manifest->rollback_timeout =
		parse_number(rollback_timeout, 60, 900);
	manifest->target_timeout = parse_number(target_timeout, 30, 600);
	if (manifest->rollback_timeout < manifest->policy->minimum_rollback)
		fail("profile rollback timeout is too short");
	if (manifest->target_timeout > manifest->rollback_timeout - 30)
		fail("target timeout does not leave rollback margin");
	if (manifest->policy->binds_a660_root) {
		if (!valid_hash(manifest->a660_command_manifest_sha256) ||
		    strcmp(manifest->root_generation, "arch-a") != 0 ||
		    !valid_hash(manifest->root_tree_sha256) ||
		    !valid_hash(manifest->root_seal_sha256) ||
		    strcmp(manifest->root_subtree, "/") != 0)
			fail("network-root trust identity is invalid");
		manifest->root_tree_entries =
			parse_number(root_tree_entries, 1, INT64_MAX);
	} else {
		if (strcmp(manifest->a660_command_manifest_sha256,
			   ZERO_HASH) != 0 ||
		    strcmp(manifest->root_generation, "none") != 0 ||
		    strcmp(manifest->root_tree_sha256, ZERO_HASH) != 0 ||
		    strcmp(manifest->root_seal_sha256, ZERO_HASH) != 0 ||
		    strcmp(root_tree_entries, "0") != 0 ||
		    strcmp(manifest->root_subtree, "none") != 0)
			fail("non-network profile carries root trust identity");
		manifest->root_tree_entries = 0;
	}
}

static int open_directory_checked(const char *path)
{
	struct stat metadata;
	int descriptor;

	descriptor = open(path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW |
			  O_CLOEXEC);
	if (descriptor < 0)
		fail("cannot open directory %s: %s", path, strerror(errno));
	if (fstat(descriptor, &metadata) < 0 ||
	    !S_ISDIR(metadata.st_mode) || metadata.st_uid != geteuid() ||
	    (metadata.st_mode & 0022) != 0)
		fail("unsafe directory: %s", path);
	return descriptor;
}

static int open_directory_at_checked(int parent, const char *name)
{
	struct stat metadata;
	int descriptor;

	descriptor = openat(parent, name, O_RDONLY | O_DIRECTORY |
			    O_NOFOLLOW | O_CLOEXEC);
	if (descriptor < 0)
		fail("cannot open bundle directory: %s", strerror(errno));
	if (fstat(descriptor, &metadata) < 0 ||
	    !S_ISDIR(metadata.st_mode) || metadata.st_uid != geteuid() ||
	    (metadata.st_mode & 0022) != 0)
		fail("unsafe bundle directory");
	return descriptor;
}

static int open_file_at_checked(int directory, const char *name,
				uint64_t minimum, uint64_t maximum,
				uint64_t exact)
{
	struct stat metadata;
	int descriptor;

	descriptor = openat(directory, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
	if (descriptor < 0)
		fail("cannot open bundle file %s: %s", name, strerror(errno));
	if (fstat(descriptor, &metadata) < 0 ||
	    !S_ISREG(metadata.st_mode) || metadata.st_uid != geteuid() ||
	    (metadata.st_mode & 0022) != 0 || metadata.st_nlink != 1 ||
	    metadata.st_size < 0 ||
	    (uint64_t)metadata.st_size < minimum ||
	    (uint64_t)metadata.st_size > maximum ||
	    (exact != 0 && (uint64_t)metadata.st_size != exact))
		fail("unsafe bundle file: %s", name);
	return descriptor;
}

static int open_key_checked(const char *path)
{
	struct stat metadata;
	int descriptor = open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);

	if (descriptor < 0)
		fail("cannot open trust key: %s", strerror(errno));
	if (fstat(descriptor, &metadata) < 0 ||
	    !S_ISREG(metadata.st_mode) || metadata.st_uid != geteuid() ||
	    (metadata.st_mode & 0022) != 0 || metadata.st_nlink != 1 ||
	    metadata.st_size != 32)
		fail("unsafe trust key");
	return descriptor;
}

static unsigned char *read_exact(int descriptor, size_t length)
{
	unsigned char *result = malloc(length + 1);
	size_t used = 0;

	if (result == NULL)
		fail("out of memory");
	while (used < length) {
		ssize_t count = read(descriptor, result + used, length - used);

		if (count < 0 && errno == EINTR)
			continue;
		if (count <= 0)
			fail("short bundle file read");
		used += (size_t)count;
	}
	result[length] = '\0';
	return result;
}

static void bytes_to_hex(const unsigned char *input, size_t length,
			 char *output)
{
	static const char digits[] = "0123456789abcdef";
	size_t index;

	for (index = 0; index < length; index++) {
		output[index * 2] = digits[input[index] >> 4];
		output[index * 2 + 1] = digits[input[index] & 0xf];
	}
	output[length * 2] = '\0';
}

static void sha256_memory(const void *data, size_t length,
			  char output[HASH_LENGTH + 1])
{
	EVP_MD_CTX *context = EVP_MD_CTX_new();
	unsigned char digest[EVP_MAX_MD_SIZE];
	unsigned int digest_length = 0;

	if (context == NULL ||
	    EVP_DigestInit_ex(context, EVP_sha256(), NULL) != 1 ||
	    EVP_DigestUpdate(context, data, length) != 1 ||
	    EVP_DigestFinal_ex(context, digest, &digest_length) != 1 ||
	    digest_length != 32)
		fail("SHA-256 operation failed");
	EVP_MD_CTX_free(context);
	bytes_to_hex(digest, digest_length, output);
}

static void sha256_file(int descriptor, char output[HASH_LENGTH + 1])
{
	unsigned char buffer[64 * 1024];
	unsigned char digest[EVP_MAX_MD_SIZE];
	unsigned int digest_length = 0;
	EVP_MD_CTX *context = EVP_MD_CTX_new();

	if (context == NULL ||
	    EVP_DigestInit_ex(context, EVP_sha256(), NULL) != 1)
		fail("cannot initialize file hash");
	if (lseek(descriptor, 0, SEEK_SET) < 0)
		fail("cannot rewind bundle file");
	while (true) {
		ssize_t count = read(descriptor, buffer, sizeof(buffer));

		if (count < 0 && errno == EINTR)
			continue;
		if (count < 0)
			fail("cannot read bundle artifact");
		if (count == 0)
			break;
		if (EVP_DigestUpdate(context, buffer, (size_t)count) != 1)
			fail("cannot update file hash");
	}
	if (EVP_DigestFinal_ex(context, digest, &digest_length) != 1 ||
	    digest_length != 32)
		fail("cannot finalize file hash");
	EVP_MD_CTX_free(context);
	bytes_to_hex(digest, digest_length, output);
}

static void verify_signature(const unsigned char key[32],
			     const unsigned char signature[64],
			     const unsigned char *manifest,
			     size_t manifest_length)
{
	EVP_PKEY *public_key;
	EVP_MD_CTX *context;
	int result;

	public_key = EVP_PKEY_new_raw_public_key_ex(
		NULL, "ED25519", NULL, key, 32);
	context = EVP_MD_CTX_new();
	if (public_key == NULL || context == NULL ||
	    EVP_DigestVerifyInit(context, NULL, NULL, NULL, public_key) != 1)
		fail("cannot initialize Ed25519 verifier");
	result = EVP_DigestVerify(
		context, signature, 64, manifest, manifest_length);
	EVP_MD_CTX_free(context);
	EVP_PKEY_free(public_key);
	if (result != 1)
		fail("manifest signature is invalid");
}

static bool allowed_bundle_entry(const char *name)
{
	return strcmp(name, "manifest") == 0 ||
		strcmp(name, "manifest.sig") == 0 ||
		strcmp(name, "Image") == 0 ||
		strcmp(name, "board.dtb") == 0 ||
		strcmp(name, "initramfs.cpio.gz") == 0;
}

static void verify_directory_inventory(int directory)
{
	bool seen_manifest = false;
	bool seen_signature = false;
	bool seen_kernel = false;
	bool seen_dtb = false;
	bool seen_initramfs = false;
	DIR *stream;
	struct dirent *entry;
	int duplicate = openat(directory, ".", O_RDONLY | O_DIRECTORY |
			       O_NOFOLLOW | O_CLOEXEC);

	if (duplicate < 0)
		fail("cannot duplicate bundle directory");
	stream = fdopendir(duplicate);
	if (stream == NULL)
		fail("cannot inspect bundle directory");
	errno = 0;
	while ((entry = readdir(stream)) != NULL) {
		if (strcmp(entry->d_name, ".") == 0 ||
		    strcmp(entry->d_name, "..") == 0)
			continue;
		if (!allowed_bundle_entry(entry->d_name))
			fail("unexpected bundle directory entry");
		if (strcmp(entry->d_name, "manifest") == 0)
			seen_manifest = true;
		else if (strcmp(entry->d_name, "manifest.sig") == 0)
			seen_signature = true;
		else if (strcmp(entry->d_name, "Image") == 0)
			seen_kernel = true;
		else if (strcmp(entry->d_name, "board.dtb") == 0)
			seen_dtb = true;
		else if (strcmp(entry->d_name, "initramfs.cpio.gz") == 0)
			seen_initramfs = true;
	}
	if (errno != 0)
		fail("cannot enumerate bundle directory");
	if (closedir(stream) < 0)
		fail("cannot close bundle inventory");
	if (!seen_manifest || !seen_signature || !seen_kernel ||
	    !seen_dtb || !seen_initramfs)
		fail("bundle directory is incomplete");
}

static void verify_kernel_image(int descriptor, uint64_t file_size)
{
	unsigned char header[64];
	ssize_t count;
	uint64_t image_size;
	uint64_t flags;

	count = pread(descriptor, header, sizeof(header), 0);
	if (count != (ssize_t)sizeof(header))
		fail("short ARM64 Image header");
	image_size = read_le64(header + 16);
	flags = read_le64(header + 24);
	if (memcmp(header + 56, "ARM\x64", 4) != 0 ||
	    image_size < file_size || image_size > KERNEL_MEMORY_MAX ||
	    (flags & ~0xfULL) != 0 ||
	    read_le64(header + 32) != 0 ||
	    read_le64(header + 40) != 0 ||
	    read_le64(header + 48) != 0)
		fail("invalid ARM64 Image header");
}

static uint32_t parse_hex32(const unsigned char value[8])
{
	uint32_t result = 0;
	unsigned int index;

	for (index = 0; index < 8; index++) {
		unsigned char byte = value[index];
		unsigned int digit;

		if (byte >= '0' && byte <= '9')
			digit = byte - '0';
		else if (byte >= 'a' && byte <= 'f')
			digit = byte - 'a' + 10;
		else if (byte >= 'A' && byte <= 'F')
			digit = byte - 'A' + 10;
		else
			fail("initramfs has a non-hex newc field");
		result = result << 4 | digit;
	}
	return result;
}

static bool safe_cpio_name(const char *name, size_t length)
{
	size_t component = 0;
	size_t index;

	if (length == 0 || name[0] == '/' || name[length - 1] == '/')
		return false;
	for (index = 0; index <= length; index++) {
		unsigned char byte = (unsigned char)name[index];

		if (index < length && (byte < 0x21 || byte > 0x7e))
			return false;
		if (index == length || byte == '/') {
			size_t component_length = index - component;

			if (component_length == 0 ||
			    (component_length == 1 &&
			     name[component] == '.') ||
			    (component_length == 2 &&
			     name[component] == '.' &&
			     name[component + 1] == '.'))
				return false;
			component = index + 1;
		}
	}
	return true;
}

static void cpio_begin_entry(struct cpio_parser *parser)
{
	uint32_t fields[13];
	unsigned int index;

	if (memcmp(parser->header, "070701", 6) == 0) {
		parser->crc = false;
	} else if (memcmp(parser->header, "070702", 6) == 0) {
		parser->crc = true;
	} else {
		fail("initramfs is not a newc CPIO archive");
	}
	for (index = 0; index < 13; index++)
		fields[index] =
			parse_hex32(parser->header + 6 + index * 8);
	parser->mode = fields[1];
	parser->file_size = fields[6];
	parser->file_remaining = parser->file_size;
	parser->name_size = fields[11];
	parser->expected_checksum = fields[12];
	if (parser->name_size < 2 ||
	    parser->name_size > CPIO_NAME_MAX + 1)
		fail("initramfs has an unsafe newc pathname size");
	if (!parser->crc && parser->expected_checksum != 0)
		fail("initramfs newc checksum field is not canonical");
	parser->checksum = 0;
	parser->name_used = 0;
	parser->current_trailer = false;
	parser->phase = CPIO_NAME;
}

static void cpio_complete_data(struct cpio_parser *parser)
{
	if (parser->crc && parser->checksum != parser->expected_checksum)
		fail("initramfs newc data checksum mismatch");
	parser->padding_remaining =
		(size_t)((4 - (parser->file_size & 3)) & 3);
	if (parser->padding_remaining != 0) {
		parser->phase = CPIO_DATA_PADDING;
	} else {
		parser->header_used = 0;
		parser->phase = CPIO_HEADER;
	}
}

static void cpio_after_name_padding(struct cpio_parser *parser)
{
	if (parser->current_trailer) {
		parser->phase = CPIO_DONE;
	} else if (parser->file_remaining != 0) {
		parser->phase = CPIO_DATA;
	} else {
		cpio_complete_data(parser);
	}
}

static void cpio_complete_name(struct cpio_parser *parser)
{
	size_t length = parser->name_size - 1;

	if (parser->name[length] != '\0' ||
	    memchr(parser->name, '\0', length) != NULL ||
	    !safe_cpio_name(parser->name, length))
		fail("initramfs has an unsafe newc pathname");
	parser->current_trailer =
		strcmp(parser->name, "TRAILER!!!") == 0;
	if (parser->current_trailer) {
		if (parser->seen_trailer || !parser->seen_init ||
		    parser->file_size != 0 ||
		    parser->expected_checksum != 0)
			fail("invalid initramfs newc trailer");
		parser->seen_trailer = true;
	} else {
		if (parser->entry_count >= CPIO_ENTRIES_MAX ||
		    (parser->previous_name[0] != '\0' &&
		     strcmp(parser->previous_name, parser->name) >= 0))
			fail("initramfs newc entries are not unique and sorted");
		memcpy(parser->previous_name, parser->name,
		       parser->name_size);
		parser->entry_count++;
		if (strcmp(parser->name, "init") == 0) {
			if (parser->seen_init || !S_ISREG(parser->mode) ||
			    (parser->mode & 0111) == 0 ||
			    parser->file_size == 0)
				fail("initramfs has no executable regular /init");
			parser->seen_init = true;
		} else if (strcmp(parser->name,
				  "sbin/persistent-root-verify") == 0) {
			if (parser->seen_persistent_root_verifier ||
			    !S_ISREG(parser->mode) ||
			    (parser->mode & 0111) == 0 ||
			    parser->file_size == 0)
				fail("initramfs has no executable persistent-root verifier");
			parser->seen_persistent_root_verifier = true;
		} else if (strcmp(parser->name,
				  "sbin/rog5-early-target-diag") == 0) {
			if (parser->seen_early_target_reporter ||
			    !S_ISREG(parser->mode) ||
			    (parser->mode & 0111) == 0 || parser->file_size == 0)
				fail("initramfs has no executable early-target reporter");
			parser->seen_early_target_reporter = true;
		}
	}
	parser->padding_remaining =
		(4 - ((CPIO_HEADER_SIZE + parser->name_size) & 3)) & 3;
	if (parser->padding_remaining != 0)
		parser->phase = CPIO_NAME_PADDING;
	else
		cpio_after_name_padding(parser);
}

static void cpio_feed(struct cpio_parser *parser,
		      const unsigned char *data, size_t length)
{
	while (length != 0) {
		size_t take;

		if (parser->phase == CPIO_HEADER) {
			take = CPIO_HEADER_SIZE - parser->header_used;
			if (take > length)
				take = length;
			memcpy(parser->header + parser->header_used, data, take);
			parser->header_used += take;
			if (parser->header_used == CPIO_HEADER_SIZE)
				cpio_begin_entry(parser);
		} else if (parser->phase == CPIO_NAME) {
			take = parser->name_size - parser->name_used;
			if (take > length)
				take = length;
			memcpy(parser->name + parser->name_used, data, take);
			parser->name_used += take;
			if (parser->name_used == parser->name_size)
				cpio_complete_name(parser);
		} else if (parser->phase == CPIO_NAME_PADDING ||
			   parser->phase == CPIO_DATA_PADDING) {
			take = parser->padding_remaining;
			if (take > length)
				take = length;
			{
				size_t index;

				for (index = 0; index < take; index++) {
					if (data[index] != 0)
						fail("nonzero initramfs newc padding");
				}
			}
			parser->padding_remaining -= take;
			if (parser->padding_remaining == 0) {
				if (parser->phase == CPIO_NAME_PADDING) {
					cpio_after_name_padding(parser);
				} else {
					parser->header_used = 0;
					parser->phase = CPIO_HEADER;
				}
			}
		} else if (parser->phase == CPIO_DATA) {
			uint64_t available = parser->file_remaining;
			size_t index;

			take = available < length ? (size_t)available : length;
			if (parser->crc) {
				for (index = 0; index < take; index++)
					parser->checksum += data[index];
			}
			parser->file_remaining -= take;
			if (parser->file_remaining == 0)
				cpio_complete_data(parser);
		} else {
			for (take = 0; take < length; take++) {
				if (data[take] != 0)
					fail("data follows initramfs newc trailer");
			}
			return;
		}
		data += take;
		length -= take;
	}
}

static void cpio_finish(const struct cpio_parser *parser,
			bool require_persistent_root_verifier,
			bool require_early_target_reporter)
{
	if (parser->phase != CPIO_DONE || !parser->seen_init ||
	    !parser->seen_trailer || parser->entry_count == 0)
		fail("truncated or incomplete initramfs newc archive");
	if (require_persistent_root_verifier &&
	    !parser->seen_persistent_root_verifier)
		fail("network-root initramfs lacks persistent-root verifier");
	if (require_early_target_reporter &&
	    !parser->seen_early_target_reporter)
		fail("diagnostic initramfs lacks early-target reporter");
	if (!require_early_target_reporter &&
	    parser->seen_early_target_reporter)
		fail("non-diagnostic initramfs carries early-target reporter");
}

static void verify_initramfs_gzip(int descriptor,
				  bool require_persistent_root_verifier,
				  bool require_early_target_reporter)
{
	unsigned char input[64 * 1024];
	unsigned char output[64 * 1024];
	z_stream stream = { 0 };
	struct cpio_parser cpio = { 0 };
	uint64_t total = 0;
	bool ended = false;
	bool input_eof = false;

	if (lseek(descriptor, 0, SEEK_SET) < 0)
		fail("cannot rewind initramfs");
	if (inflateInit2(&stream, 15 + 16) != Z_OK)
		fail("cannot initialize gzip verifier");
	while (!ended) {
		int result;
		size_t produced;

		if (stream.avail_in == 0 && !input_eof) {
			ssize_t count;

			do {
				count = read(descriptor, input, sizeof(input));
			} while (count < 0 && errno == EINTR);
			if (count < 0)
				fail("cannot read initramfs gzip stream");
			if (count == 0) {
				input_eof = true;
			} else {
				stream.next_in = input;
				stream.avail_in = (uInt)count;
			}
		}
		if (input_eof && stream.avail_in == 0)
			fail("truncated initramfs gzip stream");
		stream.next_out = output;
		stream.avail_out = sizeof(output);
		result = inflate(&stream, Z_NO_FLUSH);
		produced = sizeof(output) - stream.avail_out;
		if (total > INITRAMFS_UNCOMPRESSED_MAX - produced)
			fail("initramfs expands beyond policy");
		total += produced;
		cpio_feed(&cpio, output, produced);
		if (result == Z_STREAM_END)
			ended = true;
		else if (result != Z_OK)
			fail("invalid initramfs gzip stream");
	}
	if (stream.avail_in != 0)
		fail("initramfs gzip stream has trailing data");
	while (true) {
		ssize_t count = read(descriptor, input, 1);

		if (count < 0 && errno == EINTR)
			continue;
		if (count < 0)
			fail("cannot finish initramfs gzip verification");
		if (count != 0)
			fail("initramfs gzip stream has trailing data");
		break;
	}
	if (inflateEnd(&stream) != Z_OK)
		fail("cannot finish gzip verifier");
	cpio_finish(&cpio, require_persistent_root_verifier,
		    require_early_target_reporter);
}

static const char *fdt_string(const unsigned char *strings,
			      size_t strings_size, uint32_t offset)
{
	const unsigned char *end;

	if (offset >= strings_size)
		fail("FDT property name is out of bounds");
	end = memchr(strings + offset, '\0', strings_size - offset);
	if (end == NULL)
		fail("unterminated FDT property name");
	return (const char *)strings + offset;
}

static bool string_list_contains(const unsigned char *data, size_t length,
				 const char *expected)
{
	size_t offset = 0;
	bool found = false;

	while (offset < length) {
		const unsigned char *end =
			memchr(data + offset, '\0', length - offset);
		size_t item_length;

		if (end == NULL)
			fail("unterminated FDT string list");
		item_length = (size_t)(end - (data + offset));
		if (strlen(expected) == item_length &&
		    memcmp(data + offset, expected, item_length) == 0)
			found = true;
		offset += item_length + 1;
	}
	return found;
}

static bool fdt_string_equals(const unsigned char *data, size_t length,
			      const char *expected)
{
	return length == strlen(expected) + 1 &&
		memcmp(data, expected, length) == 0;
}

static bool fdt_cells_equal(const unsigned char *data, size_t length,
			    const uint32_t *expected, size_t count)
{
	size_t index;

	if (length != count * sizeof(uint32_t))
		return false;
	for (index = 0; index < count; index++) {
		if (read_be32(data + index * sizeof(uint32_t)) != expected[index])
			return false;
	}
	return true;
}

static void add_fdt_ranges(const unsigned char *data, size_t length,
			   unsigned int address_cells,
			   unsigned int size_cells,
			   struct fdt_range ranges[FDT_RANGES_MAX],
			   size_t *range_count, bool *has_ramoops)
{
	size_t tuple_cells = address_cells + size_cells;
	size_t tuple_size = tuple_cells * 4;
	size_t offset;

	if ((address_cells != 1 && address_cells != 2) ||
	    (size_cells != 1 && size_cells != 2) ||
	    tuple_size == 0 || length == 0 || length % tuple_size != 0)
		fail("invalid reserved-memory reg property");
	for (offset = 0; offset < length; offset += tuple_size) {
		uint64_t start = read_be_cells(data + offset, address_cells);
		uint64_t size = read_be_cells(
			data + offset + address_cells * 4, size_cells);

		if (size == 0 || start > UINT64_MAX - size ||
		    *range_count >= FDT_RANGES_MAX)
			fail("invalid reserved-memory range");
		ranges[*range_count] = (struct fdt_range){
			.start = start,
			.size = size,
		};
		(*range_count)++;
		if (start == 0x9b800000ULL && size == 0x400000ULL)
			*has_ramoops = true;
	}
}

static void verify_fdt(const unsigned char *blob, size_t length)
{
	static const uint32_t soc_ranges[] = { 0, 0, 0, 0, 0x10, 0 };
	static const uint32_t qup_reg[] = { 0, 0x9c0000, 0, 0x6000 };
	static const uint32_t uart_reg[] = { 0, 0x98c000, 0, 0x4000 };
	static const uint32_t two_cells[] = { 2 };
	struct fdt_range ranges[FDT_RANGES_MAX];
	const char *nodes[FDT_DEPTH_MAX] = { 0 };
	size_t range_count = 0;
	uint32_t total;
	uint32_t struct_offset;
	uint32_t strings_offset;
	uint32_t reserve_offset;
	uint32_t version;
	uint32_t last_compatible;
	uint32_t strings_size;
	uint32_t struct_size;
	const unsigned char *structure;
	const unsigned char *strings;
	size_t cursor = 0;
	int depth = 0;
	int reserved_depth = 0;
	unsigned int address_cells = 0;
	unsigned int size_cells = 0;
	bool has_asus = false;
	bool has_sm8350 = false;
	bool has_model = false;
	bool has_ramoops = false;
	bool has_reserved_node = false;
	bool seen_compatible = false;
	bool seen_model = false;
	bool seen_address_cells = false;
	bool seen_size_cells = false;
	bool seen_ranges = false;
	bool reserved_children_started = false;
	bool child_reg_seen = false;
	bool root_seen = false;
	bool ended = false;
	bool seen_stdout_path = false;
	bool valid_stdout_path = false;
	bool seen_serial_alias = false;
	bool valid_serial_alias = false;
	bool seen_root_address_cells = false;
	bool valid_root_address_cells = false;
	bool seen_root_size_cells = false;
	bool valid_root_size_cells = false;
	bool seen_soc_compatible = false;
	bool valid_soc_compatible = false;
	bool seen_soc_address_cells = false;
	bool valid_soc_address_cells = false;
	bool seen_soc_size_cells = false;
	bool valid_soc_size_cells = false;
	bool seen_soc_ranges = false;
	bool valid_soc_ranges = false;
	bool seen_soc_status = false;
	bool valid_soc_status = true;
	bool seen_qup_compatible = false;
	bool valid_qup_compatible = false;
	bool seen_qup_reg = false;
	bool valid_qup_reg = false;
	bool seen_qup_address_cells = false;
	bool valid_qup_address_cells = false;
	bool seen_qup_size_cells = false;
	bool valid_qup_size_cells = false;
	bool seen_qup_ranges = false;
	bool valid_qup_ranges = false;
	bool seen_qup_status = false;
	bool valid_qup_status = false;
	bool seen_uart_compatible = false;
	bool valid_uart_compatible = false;
	bool seen_uart_reg = false;
	bool valid_uart_reg = false;
	bool seen_uart_status = false;
	bool valid_uart_status = false;
	bool seen_uart_pinctrl = false;
	bool seen_uart_pin_phandle = false;
	bool seen_uart_rx_pins = false;
	bool valid_uart_rx_pins = false;
	bool seen_uart_rx_function = false;
	bool valid_uart_rx_function = false;
	bool seen_uart_tx_pins = false;
	bool valid_uart_tx_pins = false;
	bool seen_uart_tx_function = false;
	bool valid_uart_tx_function = false;
	uint32_t uart_pinctrl_phandle = 0;
	uint32_t uart_pin_phandle = 0;
	size_t index;

	if (length < 40 || read_be32(blob) != FDT_MAGIC)
		fail("invalid FDT header");
	total = read_be32(blob + 4);
	struct_offset = read_be32(blob + 8);
	strings_offset = read_be32(blob + 12);
	reserve_offset = read_be32(blob + 16);
	version = read_be32(blob + 20);
	last_compatible = read_be32(blob + 24);
	strings_size = read_be32(blob + 32);
	struct_size = read_be32(blob + 36);
	if (total != length || version != 17 || last_compatible != 16 ||
	    reserve_offset != 40 || struct_offset != 56 ||
	    strings_offset != (size_t)struct_offset + struct_size ||
	    (size_t)strings_offset + strings_size != length ||
	    struct_size == 0 || strings_size == 0 ||
	    struct_offset % 4 != 0 || strings_offset % 4 != 0 ||
	    reserve_offset % 8 != 0 ||
	    !range_within(struct_offset, struct_size, length) ||
	    !range_within(strings_offset, strings_size, length) ||
	    !range_within(reserve_offset, 16, length))
		fail("unsafe FDT layout");
	for (index = reserve_offset; index + 16 <= length; index += 16) {
		uint64_t address = read_be_cells(blob + index, 2);
		uint64_t size = read_be_cells(blob + index + 8, 2);

		if (address == 0 && size == 0)
			break;
		fail("FDT reservation map must be empty");
	}
	if (index + 16 > length || index + 16 > struct_offset)
		fail("unterminated FDT reservation map");
	structure = blob + struct_offset;
	strings = blob + strings_offset;
	while (cursor + 4 <= struct_size) {
		uint32_t token = read_be32(structure + cursor);

		cursor += 4;
		if (token == FDT_BEGIN_NODE) {
			const unsigned char *end;
			size_t name_length;
			const char *name;

			end = memchr(structure + cursor, '\0',
				     struct_size - cursor);
			if (end == NULL || depth >= FDT_DEPTH_MAX)
				fail("invalid FDT node");
			name = (const char *)structure + cursor;
			name_length = (size_t)(end - (structure + cursor));
			cursor += name_length + 1;
			cursor = (cursor + 3) & ~(size_t)3;
			if (cursor > struct_size)
				fail("FDT node exceeds structure block");
			if (depth == 0) {
				if (root_seen || name_length != 0)
					fail("invalid FDT root node");
				root_seen = true;
			}
			nodes[depth] = name;
			if (reserved_depth != 0 &&
			    depth == reserved_depth) {
				if (!seen_address_cells || !seen_size_cells ||
				    !seen_ranges)
					fail("incomplete reserved-memory policy");
				reserved_children_started = true;
				child_reg_seen = false;
			} else if (reserved_depth != 0 &&
				   depth > reserved_depth) {
				fail("nested reserved-memory child");
			}
			depth++;
			if (depth == 2 && strcmp(name, "reserved-memory") == 0) {
				if (has_reserved_node)
					fail("duplicate reserved-memory node");
				has_reserved_node = true;
				reserved_depth = depth;
			}
		} else if (token == FDT_END_NODE) {
			if (depth < 1)
				fail("unbalanced FDT node");
			if (reserved_depth != 0 &&
			    depth == reserved_depth + 1 &&
			    !child_reg_seen)
				fail("reserved-memory child has no reg");
			if (depth == reserved_depth) {
				if (!seen_address_cells || !seen_size_cells ||
				    !seen_ranges)
					fail("incomplete reserved-memory policy");
				reserved_depth = 0;
			}
			nodes[depth - 1] = NULL;
			depth--;
		} else if (token == FDT_PROP) {
			uint32_t property_length;
			uint32_t name_offset;
			const unsigned char *data;
			const char *name;

			if (depth < 1)
				fail("FDT property is outside the root node");
			if (!range_within(cursor, 8, struct_size))
				fail("truncated FDT property");
			property_length = read_be32(structure + cursor);
			name_offset = read_be32(structure + cursor + 4);
			cursor += 8;
			if (!range_within(cursor, property_length, struct_size))
				fail("FDT property exceeds structure block");
			data = structure + cursor;
			cursor += property_length;
			cursor = (cursor + 3) & ~(size_t)3;
			if (cursor > struct_size)
				fail("FDT property padding exceeds structure block");
			name = fdt_string(strings, strings_size, name_offset);
			if (strcmp(name, "bootargs") == 0)
				fail("DTB contains forbidden bootargs");
			if (depth == 2 && strcmp(nodes[1], "chosen") == 0 &&
			    strcmp(name, "stdout-path") == 0) {
				if (seen_stdout_path)
					fail("duplicate latent serial property");
				seen_stdout_path = true;
				valid_stdout_path = fdt_string_equals(
					data, property_length, "serial0:115200n8");
			} else if (depth == 2 &&
				   strcmp(nodes[1], "aliases") == 0 &&
				   strcmp(name, "serial0") == 0) {
				if (seen_serial_alias)
					fail("duplicate latent serial property");
				seen_serial_alias = true;
				valid_serial_alias = fdt_string_equals(
					data, property_length,
					"/soc@0/geniqup@9c0000/serial@98c000");
			} else if (depth == 2 &&
				   strcmp(nodes[1], "soc@0") == 0) {
				if (strcmp(name, "compatible") == 0) {
					if (seen_soc_compatible)
						fail("duplicate latent serial property");
					seen_soc_compatible = true;
					valid_soc_compatible = fdt_string_equals(
						data, property_length, "simple-bus");
				} else if (strcmp(name, "#address-cells") == 0) {
					if (seen_soc_address_cells)
						fail("duplicate latent serial property");
					seen_soc_address_cells = true;
					valid_soc_address_cells = fdt_cells_equal(
						data, property_length, two_cells,
						sizeof(two_cells) /
						sizeof(two_cells[0]));
				} else if (strcmp(name, "#size-cells") == 0) {
					if (seen_soc_size_cells)
						fail("duplicate latent serial property");
					seen_soc_size_cells = true;
					valid_soc_size_cells = fdt_cells_equal(
						data, property_length, two_cells,
						sizeof(two_cells) /
						sizeof(two_cells[0]));
				} else if (strcmp(name, "ranges") == 0) {
					if (seen_soc_ranges)
						fail("duplicate latent serial property");
					seen_soc_ranges = true;
					valid_soc_ranges = fdt_cells_equal(
						data, property_length, soc_ranges,
						sizeof(soc_ranges) /
						sizeof(soc_ranges[0]));
				} else if (strcmp(name, "status") == 0) {
					if (seen_soc_status)
						fail("duplicate latent serial property");
					seen_soc_status = true;
					valid_soc_status = fdt_string_equals(
						data, property_length, "okay");
				}
			} else if (depth == 3 && strcmp(nodes[1], "soc@0") == 0 &&
				   strcmp(nodes[2], "geniqup@9c0000") == 0) {
				if (strcmp(name, "compatible") == 0) {
					if (seen_qup_compatible)
						fail("duplicate latent serial property");
					seen_qup_compatible = true;
					valid_qup_compatible = fdt_string_equals(
						data, property_length,
						"qcom,geni-se-qup");
				} else if (strcmp(name, "reg") == 0) {
					if (seen_qup_reg)
						fail("duplicate latent serial property");
					seen_qup_reg = true;
					valid_qup_reg = fdt_cells_equal(
						data, property_length, qup_reg,
						sizeof(qup_reg) /
						sizeof(qup_reg[0]));
				} else if (strcmp(name, "#address-cells") == 0) {
					if (seen_qup_address_cells)
						fail("duplicate latent serial property");
					seen_qup_address_cells = true;
					valid_qup_address_cells = fdt_cells_equal(
						data, property_length, two_cells,
						sizeof(two_cells) /
						sizeof(two_cells[0]));
				} else if (strcmp(name, "#size-cells") == 0) {
					if (seen_qup_size_cells)
						fail("duplicate latent serial property");
					seen_qup_size_cells = true;
					valid_qup_size_cells = fdt_cells_equal(
						data, property_length, two_cells,
						sizeof(two_cells) /
						sizeof(two_cells[0]));
				} else if (strcmp(name, "ranges") == 0) {
					if (seen_qup_ranges)
						fail("duplicate latent serial property");
					seen_qup_ranges = true;
					valid_qup_ranges = property_length == 0;
				} else if (strcmp(name, "status") == 0) {
					if (seen_qup_status)
						fail("duplicate latent serial property");
					seen_qup_status = true;
					valid_qup_status = fdt_string_equals(
						data, property_length, "okay");
				}
			} else if (depth == 4 && strcmp(nodes[1], "soc@0") == 0 &&
				   strcmp(nodes[2], "geniqup@9c0000") == 0 &&
				   strcmp(nodes[3], "serial@98c000") == 0) {
				if (strcmp(name, "compatible") == 0) {
					if (seen_uart_compatible)
						fail("duplicate latent serial property");
					seen_uart_compatible = true;
					valid_uart_compatible = fdt_string_equals(
						data, property_length,
						"qcom,geni-debug-uart");
				} else if (strcmp(name, "reg") == 0) {
					if (seen_uart_reg)
						fail("duplicate latent serial property");
					seen_uart_reg = true;
					valid_uart_reg = fdt_cells_equal(
						data, property_length, uart_reg,
						sizeof(uart_reg) /
						sizeof(uart_reg[0]));
				} else if (strcmp(name, "status") == 0) {
					if (seen_uart_status)
						fail("duplicate latent serial property");
					seen_uart_status = true;
					valid_uart_status = fdt_string_equals(
						data, property_length, "okay");
				} else if (strcmp(name, "pinctrl-0") == 0) {
					if (seen_uart_pinctrl)
						fail("duplicate latent serial property");
					seen_uart_pinctrl = true;
					if (property_length == 4)
						uart_pinctrl_phandle = read_be32(data);
				}
			} else if (depth == 4 && strcmp(nodes[1], "soc@0") == 0 &&
				   strcmp(nodes[2], "pinctrl@f100000") == 0 &&
				   strcmp(nodes[3],
					  "qup-uart3-default-state") == 0 &&
				   strcmp(name, "phandle") == 0) {
				if (seen_uart_pin_phandle)
					fail("duplicate latent serial property");
				seen_uart_pin_phandle = true;
				if (property_length == 4)
					uart_pin_phandle = read_be32(data);
			} else if (depth == 5 && strcmp(nodes[1], "soc@0") == 0 &&
				   strcmp(nodes[2], "pinctrl@f100000") == 0 &&
				   strcmp(nodes[3],
					  "qup-uart3-default-state") == 0 &&
				   strcmp(nodes[4], "rx-pins") == 0) {
				if (strcmp(name, "pins") == 0) {
					if (seen_uart_rx_pins)
						fail("duplicate latent serial property");
					seen_uart_rx_pins = true;
					valid_uart_rx_pins = fdt_string_equals(
						data, property_length, "gpio18");
				} else if (strcmp(name, "function") == 0) {
					if (seen_uart_rx_function)
						fail("duplicate latent serial property");
					seen_uart_rx_function = true;
					valid_uart_rx_function = fdt_string_equals(
						data, property_length, "qup3");
				}
			} else if (depth == 5 && strcmp(nodes[1], "soc@0") == 0 &&
				   strcmp(nodes[2], "pinctrl@f100000") == 0 &&
				   strcmp(nodes[3],
					  "qup-uart3-default-state") == 0 &&
				   strcmp(nodes[4], "tx-pins") == 0) {
				if (strcmp(name, "pins") == 0) {
					if (seen_uart_tx_pins)
						fail("duplicate latent serial property");
					seen_uart_tx_pins = true;
					valid_uart_tx_pins = fdt_string_equals(
						data, property_length, "gpio19");
				} else if (strcmp(name, "function") == 0) {
					if (seen_uart_tx_function)
						fail("duplicate latent serial property");
					seen_uart_tx_function = true;
					valid_uart_tx_function = fdt_string_equals(
						data, property_length, "qup3");
				}
			}
			if (depth == reserved_depth &&
			    reserved_children_started)
				fail("reserved-memory property follows a child");
			if (depth == 1 && strcmp(name, "#address-cells") == 0) {
				if (seen_root_address_cells)
					fail("duplicate latent serial property");
				seen_root_address_cells = true;
				valid_root_address_cells = fdt_cells_equal(
					data, property_length, two_cells,
					sizeof(two_cells) / sizeof(two_cells[0]));
			} else if (depth == 1 &&
				   strcmp(name, "#size-cells") == 0) {
				if (seen_root_size_cells)
					fail("duplicate latent serial property");
				seen_root_size_cells = true;
				valid_root_size_cells = fdt_cells_equal(
					data, property_length, two_cells,
					sizeof(two_cells) / sizeof(two_cells[0]));
			} else if (depth == 1 && strcmp(name, "compatible") == 0) {
				if (seen_compatible)
					fail("duplicate root compatible property");
				seen_compatible = true;
				has_asus = string_list_contains(
					data, property_length, "asus,rog-phone5");
				has_sm8350 = string_list_contains(
					data, property_length, "qcom,sm8350");
			} else if (depth == 1 && strcmp(name, "model") == 0) {
				if (seen_model)
					fail("duplicate root model property");
				seen_model = true;
				has_model = property_length ==
					sizeof("ASUS ROG Phone 5") &&
					memcmp(data, "ASUS ROG Phone 5",
					       sizeof("ASUS ROG Phone 5")) == 0;
			} else if (depth == reserved_depth &&
				   strcmp(name, "#address-cells") == 0) {
				if (seen_address_cells ||
				    property_length != 4 ||
				    read_be32(data) != 2)
					fail("invalid reserved-memory address cells");
				seen_address_cells = true;
				address_cells = 2;
			} else if (depth == reserved_depth &&
				   strcmp(name, "#size-cells") == 0) {
				if (seen_size_cells ||
				    property_length != 4 ||
				    read_be32(data) != 2)
					fail("invalid reserved-memory size cells");
				seen_size_cells = true;
				size_cells = 2;
			} else if (depth == reserved_depth &&
				   strcmp(name, "ranges") == 0) {
				if (seen_ranges || property_length != 0)
					fail("reserved-memory ranges is not empty");
				seen_ranges = true;
			} else if (reserved_depth != 0 &&
				   depth == reserved_depth + 1 &&
				   strcmp(name, "reg") == 0) {
				if (child_reg_seen)
					fail("duplicate reserved-memory reg");
				child_reg_seen = true;
				add_fdt_ranges(data, property_length,
					       address_cells, size_cells,
					       ranges, &range_count,
					       &has_ramoops);
			}
		} else if (token == FDT_NOP) {
			continue;
		} else if (token == FDT_END) {
			if (depth != 0)
				fail("FDT ended inside a node");
			if (cursor != struct_size)
				fail("FDT has trailing structure data");
			ended = true;
			break;
		} else {
			fail("unknown FDT structure token");
		}
	}
	if (!ended || !root_seen || !has_asus || !has_sm8350 || !has_model ||
	    !has_reserved_node || !seen_address_cells || !seen_size_cells ||
	    !seen_ranges || !has_ramoops || range_count == 0)
		fail("DTB lacks the fixed ROG Phone 5 contract");
	if (!seen_stdout_path || !valid_stdout_path ||
	    !seen_serial_alias || !valid_serial_alias ||
	    !seen_root_address_cells || !valid_root_address_cells ||
	    !seen_root_size_cells || !valid_root_size_cells ||
	    !seen_soc_compatible || !valid_soc_compatible ||
	    !seen_soc_address_cells || !valid_soc_address_cells ||
	    !seen_soc_size_cells || !valid_soc_size_cells ||
	    !seen_soc_ranges || !valid_soc_ranges ||
	    !valid_soc_status ||
	    !seen_qup_compatible || !valid_qup_compatible ||
	    !seen_qup_reg || !valid_qup_reg ||
	    !seen_qup_address_cells || !valid_qup_address_cells ||
	    !seen_qup_size_cells || !valid_qup_size_cells ||
	    !seen_qup_ranges || !valid_qup_ranges ||
	    !seen_qup_status || !valid_qup_status ||
	    !seen_uart_compatible || !valid_uart_compatible ||
	    !seen_uart_reg || !valid_uart_reg ||
	    !seen_uart_status || !valid_uart_status ||
	    !seen_uart_pinctrl || uart_pinctrl_phandle == 0 ||
	    !seen_uart_pin_phandle || uart_pin_phandle == 0 ||
	    uart_pinctrl_phandle != uart_pin_phandle ||
	    !seen_uart_rx_pins || !valid_uart_rx_pins ||
	    !seen_uart_rx_function || !valid_uart_rx_function ||
	    !seen_uart_tx_pins || !valid_uart_tx_pins ||
	    !seen_uart_tx_function || !valid_uart_tx_function)
		fail("DTB lacks the latent serial observability contract");
	for (index = 0; index < range_count; index++) {
		size_t other;
		uint64_t end = ranges[index].start + ranges[index].size;

		for (other = index + 1; other < range_count; other++) {
			uint64_t other_end =
				ranges[other].start + ranges[other].size;

			if (ranges[index].start < other_end &&
			    ranges[other].start < end)
				fail("overlapping DTB reserved-memory ranges");
		}
	}
}

static void build_cmdline(const struct bundle_manifest *manifest,
			  char output[CMDLINE_MAX])
{
	static const char base[] =
		"console=ttyMSM0,115200n8 rdinit=/init panic=10 "
		"oops=panic loglevel=8 ignore_loglevel "
		"printk.always_kmsg_dump=Y";
	static const char ramoops[] =
		"ramoops.mem_address=0x9b800000 "
		"ramoops.mem_size=0x400000 "
		"ramoops.record_size=0x100000 "
		"ramoops.console_size=0x300000 "
		"ramoops.pmsg_size=0 ramoops.ftrace_size=0 "
		"ramoops.dump_oops=1";
	char root_trust[512] = "";
	int length;

	if (manifest->policy->binds_a660_root) {
		length = snprintf(
			root_trust, sizeof(root_trust),
			" rog5.a660_command_manifest_sha256=%s"
			" rog5.root_generation=%s"
			" rog5.root_tree_sha256=%s"
			" rog5.root_seal_sha256=%s"
			" rog5.root_tree_entries=%" PRIu64
			" rog5.root_subtree=%s",
			manifest->a660_command_manifest_sha256,
			manifest->root_generation,
			manifest->root_tree_sha256,
			manifest->root_seal_sha256,
			manifest->root_tree_entries,
			manifest->root_subtree);
		if (length < 0 || (size_t)length >= sizeof(root_trust))
			fail("generated root trust command line is too long");
	}
	length = snprintf(
		output, CMDLINE_MAX,
		"%s %s %s rog5.bundle=%s rog5.target_timeout=%" PRIu64
		" rog5.recovery_timeout=%" PRIu64 "%s",
		base, manifest->policy->command_line, ramoops, manifest->bundle,
		manifest->target_timeout, manifest->rollback_timeout,
		root_trust);
	if (length < 0 || length >= CMDLINE_MAX)
		fail("generated command line is too long");
}

static void verify_hash(int descriptor, const char *expected,
			const char *name)
{
	char actual[HASH_LENGTH + 1];

	sha256_file(descriptor, actual);
	if (strcmp(actual, expected) != 0)
		fail("%s SHA-256 mismatch", name);
}

static void validate_handoff_socket(void)
{
	struct ucred peer;
	struct stat metadata;
	socklen_t peer_length = sizeof(peer);
	socklen_t type_length;
	int type;

	if (fstat(HANDOFF_FD, &metadata) < 0 ||
	    !S_ISSOCK(metadata.st_mode))
		fail("handoff descriptor is not a socket");
	type_length = sizeof(type);
	if (getsockopt(HANDOFF_FD, SOL_SOCKET, SO_TYPE,
		       &type, &type_length) < 0 ||
	    type_length != sizeof(type) || type != SOCK_SEQPACKET)
		fail("handoff descriptor is not a SEQPACKET socket");
	if (getsockopt(HANDOFF_FD, SOL_SOCKET, SO_PEERCRED,
		       &peer, &peer_length) < 0 ||
	    peer_length != sizeof(peer) || peer.pid <= 0 ||
	    peer.uid != geteuid() || peer.gid != getegid())
		fail("handoff peer credentials violate policy");
}

static void rewind_artifact(int descriptor, const char *name)
{
	if (lseek(descriptor, 0, SEEK_SET) < 0)
		fail("cannot rewind verified %s", name);
}

static int snapshot_artifact(int source, uint64_t expected_size,
			     const char *name)
{
	unsigned char buffer[64 * 1024];
	uint64_t remaining = expected_size;
	int snapshot;

	snapshot = memfd_create(
		name, MFD_CLOEXEC | MFD_ALLOW_SEALING);
	if (snapshot < 0)
		fail("cannot create sealed %s snapshot", name);
	if (lseek(source, 0, SEEK_SET) < 0)
		fail("cannot rewind source %s", name);
	while (remaining != 0) {
		size_t requested = remaining < sizeof(buffer) ?
			(size_t)remaining : sizeof(buffer);
		size_t offset = 0;
		ssize_t count;

		do {
			count = read(source, buffer, requested);
		} while (count < 0 && errno == EINTR);
		if (count <= 0)
			fail("cannot snapshot complete %s", name);
		while (offset < (size_t)count) {
			ssize_t written = write(
				snapshot, buffer + offset,
				(size_t)count - offset);

			if (written < 0 && errno == EINTR)
				continue;
			if (written <= 0)
				fail("cannot write %s snapshot", name);
			offset += (size_t)written;
		}
		remaining -= (uint64_t)count;
	}
	while (true) {
		ssize_t count = read(source, buffer, 1);

		if (count < 0 && errno == EINTR)
			continue;
		if (count < 0)
			fail("cannot finish %s snapshot", name);
		if (count != 0)
			fail("%s changed size during snapshot", name);
		break;
	}
	if (fchmod(snapshot, 0400) < 0 ||
	    fcntl(snapshot, F_ADD_SEALS, REQUIRED_SEALS) < 0 ||
	    fcntl(snapshot, F_GET_SEALS) != REQUIRED_SEALS)
		fail("cannot seal %s snapshot", name);
	errno = 0;
	if (pwrite(snapshot, buffer, 1, 0) >= 0 || errno != EPERM)
		fail("%s snapshot remains writable", name);
	rewind_artifact(snapshot, name);
	return snapshot;
}

static void send_handoff(const char *plan, size_t plan_length,
			 int kernel_fd, int dtb_fd, int initramfs_fd)
{
	int descriptors[HANDOFF_DESCRIPTOR_COUNT] = {
		kernel_fd,
		dtb_fd,
		initramfs_fd,
	};
	union {
		struct cmsghdr alignment;
		unsigned char bytes[CMSG_SPACE(sizeof(descriptors))];
	} control = { 0 };
	struct iovec vector = {
		.iov_base = (void *)plan,
		.iov_len = plan_length,
	};
	struct msghdr message = {
		.msg_iov = &vector,
		.msg_iovlen = 1,
		.msg_control = control.bytes,
		.msg_controllen = sizeof(control.bytes),
	};
	struct cmsghdr *header = CMSG_FIRSTHDR(&message);
	ssize_t count;

	if (header == NULL)
		fail("cannot construct descriptor handoff");
	header->cmsg_level = SOL_SOCKET;
	header->cmsg_type = SCM_RIGHTS;
	header->cmsg_len = CMSG_LEN(sizeof(descriptors));
	memcpy(CMSG_DATA(header), descriptors, sizeof(descriptors));
	message.msg_controllen = CMSG_SPACE(sizeof(descriptors));
	do {
		count = sendmsg(HANDOFF_FD, &message, MSG_NOSIGNAL);
	} while (count < 0 && errno == EINTR);
	if (count < 0)
		fail("cannot send verified descriptor handoff");
	if ((size_t)count != plan_length)
		fail("short verified descriptor handoff");
}

static size_t build_plan(const struct bundle_manifest *parsed,
			 const char *manifest_hash,
			 const char *command_hash,
			 const char *command_line,
			 char output[PLAN_MAX])
{
	int length;

	length = snprintf(
		output, PLAN_MAX,
		"format=rog5-verified-plan-v1\n"
		"bundle=%s\n"
		"manifest_sha256=%s\n"
		"profile=%s\n"
		"kernel_file=Image\n"
		"dtb_file=board.dtb\n"
		"initramfs_file=initramfs.cpio.gz\n"
		"target_id=%s\n"
		"target_release=%s\n"
		"target_timeout=%" PRIu64 "\n"
		"cmdline_sha256=%s\n"
		"cmdline=%s\n",
		parsed->bundle, manifest_hash, parsed->profile,
		parsed->target_id, parsed->target_release,
		parsed->target_timeout, command_hash, command_line);
	if (length < 0 || length >= PLAN_MAX)
		fail("verified plan is too large");
	return (size_t)length;
}

static void parse_arguments(int argc, char **argv, int *bundle_index,
			    bool *handoff)
{
	int index = 1;

#ifdef ROG5_BUNDLE_TESTING
	while (index + 1 < argc) {
		if (strcmp(argv[index], "--bundle-root") == 0)
			bundle_root = argv[index + 1];
		else if (strcmp(argv[index], "--trust-key") == 0)
			trust_key_path = argv[index + 1];
		else
			break;
		index += 2;
	}
#endif
	*handoff = false;
	if (index < argc && strcmp(argv[index], "--handoff-fd3") == 0) {
		*handoff = true;
		index++;
	}
	*bundle_index = index;
	if (argc - *bundle_index != 2)
		fail("usage: rog5-bundle-verify [--handoff-fd3] "
		     "BUNDLE MANIFEST_SHA256");
}

int main(int argc, char **argv)
{
	struct bundle_manifest parsed;
	struct stat manifest_stat;
	char manifest_hash[HASH_LENGTH + 1];
	char command_line[CMDLINE_MAX];
	char command_hash[HASH_LENGTH + 1];
	char plan[PLAN_MAX];
	const char *bundle;
	const char *expected_manifest_hash;
	unsigned char *manifest;
	unsigned char *signature;
	unsigned char *key;
	unsigned char *dtb;
	int root_fd;
	int bundle_fd;
	int manifest_fd;
	int signature_fd;
	int key_fd;
	int kernel_fd;
	int dtb_fd;
	int initramfs_fd;
	int bundle_index;
	size_t plan_length;
	bool handoff;

	umask(0077);
	if (OPENSSL_init_crypto(OPENSSL_INIT_NO_LOAD_CONFIG, NULL) != 1)
		fail("cannot initialize OpenSSL");
	parse_arguments(argc, argv, &bundle_index, &handoff);
	if (handoff)
		validate_handoff_socket();
	bundle = argv[bundle_index];
	expected_manifest_hash = argv[bundle_index + 1];
	if (!valid_bundle(bundle) || !valid_hash(expected_manifest_hash))
		fail("invalid requested bundle identity");
	root_fd = open_directory_checked(bundle_root);
	bundle_fd = open_directory_at_checked(root_fd, bundle);
	verify_directory_inventory(bundle_fd);
	manifest_fd = open_file_at_checked(
		bundle_fd, "manifest", 1, MANIFEST_MAX, 0);
	if (fstat(manifest_fd, &manifest_stat) < 0)
		fail("cannot stat manifest");
	signature_fd = open_file_at_checked(
		bundle_fd, "manifest.sig", 64, 64, 64);
	key_fd = open_key_checked(trust_key_path);
	manifest = read_exact(manifest_fd, (size_t)manifest_stat.st_size);
	signature = read_exact(signature_fd, 64);
	key = read_exact(key_fd, 32);
	sha256_memory(
		manifest, (size_t)manifest_stat.st_size, manifest_hash);
	if (strcmp(manifest_hash, expected_manifest_hash) != 0)
		fail("requested manifest SHA-256 mismatch");
	validate_manifest_bytes(manifest, (size_t)manifest_stat.st_size);
	parse_manifest((char *)manifest, bundle, &parsed);
	verify_signature(key, signature, manifest,
			 (size_t)manifest_stat.st_size);

	kernel_fd = open_file_at_checked(
		bundle_fd, "Image", 64, KERNEL_MAX, parsed.kernel_size);
	dtb_fd = open_file_at_checked(
		bundle_fd, "board.dtb", 40, DTB_MAX, parsed.dtb_size);
	initramfs_fd = open_file_at_checked(
		bundle_fd, "initramfs.cpio.gz", 2, INITRAMFS_MAX,
		parsed.initramfs_size);
	if (handoff) {
		int source_kernel = kernel_fd;
		int source_dtb = dtb_fd;
		int source_initramfs = initramfs_fd;

		kernel_fd = snapshot_artifact(
			source_kernel, parsed.kernel_size, "rog5-kernel");
		dtb_fd = snapshot_artifact(
			source_dtb, parsed.dtb_size, "rog5-dtb");
		initramfs_fd = snapshot_artifact(
			source_initramfs, parsed.initramfs_size,
			"rog5-initramfs");
		if (close(source_initramfs) < 0 ||
		    close(source_dtb) < 0 || close(source_kernel) < 0)
			fail("cannot close source bundle artifacts");
	}
	verify_hash(kernel_fd, parsed.kernel_sha256, "kernel");
	verify_hash(dtb_fd, parsed.dtb_sha256, "DTB");
	verify_hash(initramfs_fd, parsed.initramfs_sha256, "initramfs");
	verify_kernel_image(kernel_fd, parsed.kernel_size);
	verify_initramfs_gzip(
		initramfs_fd, parsed.policy->binds_a660_root,
		parsed.policy->requires_early_target_reporter);
	if (lseek(dtb_fd, 0, SEEK_SET) < 0)
		fail("cannot rewind DTB");
	dtb = read_exact(dtb_fd, (size_t)parsed.dtb_size);
	verify_fdt(dtb, (size_t)parsed.dtb_size);
	build_cmdline(&parsed, command_line);
	sha256_memory(command_line, strlen(command_line), command_hash);
	plan_length = build_plan(
		&parsed, manifest_hash, command_hash, command_line, plan);
	rewind_artifact(kernel_fd, "kernel");
	rewind_artifact(dtb_fd, "DTB");
	rewind_artifact(initramfs_fd, "initramfs");
	if (handoff) {
		send_handoff(
			plan, plan_length, kernel_fd, dtb_fd, initramfs_fd);
	} else if (fwrite(plan, 1, plan_length, stdout) != plan_length ||
		   fflush(stdout) != 0 || ferror(stdout) != 0) {
		fail("cannot write verified plan");
	}
	free(dtb);
	free(key);
	free(signature);
	free(manifest);
	if (close(initramfs_fd) < 0 || close(dtb_fd) < 0 ||
	    close(kernel_fd) < 0 || close(key_fd) < 0 ||
	    close(signature_fd) < 0 || close(manifest_fd) < 0 ||
	    close(bundle_fd) < 0 || close(root_fd) < 0 ||
	    (handoff && close(HANDOFF_FD) < 0))
		fail("cannot close verified bundle");
	return EXIT_SUCCESS;
}
