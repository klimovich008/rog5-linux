#define _GNU_SOURCE

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

/*
 * Keep the initramfs verifier independent of libattr headers. These are the
 * Linux libc interfaces used by Python's follow_symlinks=False xattr calls.
 */
extern ssize_t llistxattr(const char *path, char *list, size_t size);
extern ssize_t lgetxattr(const char *path, const char *name, void *value,
			 size_t size);

#define ARRAY_SIZE(array) (sizeof(array) / sizeof((array)[0]))
#define SEAL_NAME ".rog5-persistent-seal"
#define NFS4_ACL_XATTR "system.nfs4_acl"
#define PROJECTION_FORMAT "format=rog5-nfs4-xattr-projection-v1"
#define PROJECTION_MAX_SIZE (64 * 1024)
#define PROJECTION_MAX_ENTRIES 64

struct sha256 {
	uint32_t state[8];
	uint64_t bit_count;
	unsigned char block[64];
	size_t block_size;
};

struct counters {
	uint64_t entries;
	uint64_t regular_files;
	uint64_t directories;
	uint64_t symlinks;
	uint64_t bytes;
	uint64_t xattrs;
};

struct expected_tree {
	struct counters counters;
	char hash[65];
};

struct string_list {
	char **items;
	size_t count;
};

struct projected_xattr {
	char *path;
	char *name;
	unsigned char *value;
	size_t value_length;
	bool used;
};

struct xattr_projection {
	struct projected_xattr *items;
	size_t count;
};

static void fail(const char *format, ...)
{
	va_list arguments;

	fputs("FAIL ", stderr);
	va_start(arguments, format);
	vfprintf(stderr, format, arguments);
	va_end(arguments);
	fputc('\n', stderr);
	exit(EXIT_FAILURE);
}

static void *allocate(size_t size)
{
	void *result;

	result = malloc(size ? size : 1);
	if (!result)
		fail("out of memory");
	return result;
}

static char *duplicate_bytes(const char *data, size_t length)
{
	char *result;

	result = allocate(length + 1);
	memcpy(result, data, length);
	result[length] = '\0';
	return result;
}

static unsigned char decode_hex_digit(char value)
{
	if (value >= '0' && value <= '9')
		return (unsigned char)(value - '0');
	if (value >= 'a' && value <= 'f')
		return (unsigned char)(value - 'a' + 10);
	fail("xattr projection contains non-lowercase hex");
	return 0;
}

static bool valid_relative_path(const char *path)
{
	const char *component = path;
	const char *cursor;

	if (!*path || *path == '/')
		return false;
	for (cursor = path;; cursor++) {
		if (*cursor != '/' && *cursor != '\0')
			continue;
		if (cursor == component ||
		    (cursor - component == 1 && component[0] == '.') ||
		    (cursor - component == 2 && component[0] == '.' &&
		     component[1] == '.'))
			return false;
		if (!*cursor)
			return true;
		component = cursor + 1;
	}
}

static bool valid_xattr_name(const char *name)
{
	const unsigned char *cursor = (const unsigned char *)name;

	if (strncmp(name, "user.", 5) &&
	    strcmp(name, "security.capability"))
		return false;
	for (; *cursor; cursor++) {
		if ((*cursor >= 'a' && *cursor <= 'z') ||
		    (*cursor >= '0' && *cursor <= '9') ||
		    *cursor == '.' || *cursor == '_' || *cursor == '-')
			continue;
		return false;
	}
	return true;
}

static int compare_projected_xattrs(const struct projected_xattr *left,
				    const struct projected_xattr *right)
{
	int order;

	order = strcmp(left->path, right->path);
	if (order)
		return order;
	return strcmp(left->name, right->name);
}

static char *read_small_regular(const char *path, size_t *length)
{
	struct stat before;
	struct stat after;
	char *result;
	size_t offset = 0;
	ssize_t amount;
	int descriptor;

	descriptor = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
	if (descriptor < 0)
		fail("cannot open xattr projection");
	if (fstat(descriptor, &before) < 0)
		fail("cannot stat xattr projection");
	if (!S_ISREG(before.st_mode) || (before.st_mode & 07777) != 0444 ||
	    before.st_size <= 0 || before.st_size > PROJECTION_MAX_SIZE)
		fail("xattr projection type, mode, or size changed");
	result = allocate((size_t)before.st_size + 1);
	while (offset < (size_t)before.st_size) {
		amount = read(descriptor, result + offset,
			      (size_t)before.st_size - offset);
		if (amount > 0) {
			offset += (size_t)amount;
			continue;
		}
		if (amount < 0 && errno == EINTR)
			continue;
		fail("cannot read xattr projection");
	}
	if (fstat(descriptor, &after) < 0)
		fail("cannot restat xattr projection");
	if (close(descriptor) < 0)
		fail("cannot close xattr projection");
	if (before.st_dev != after.st_dev || before.st_ino != after.st_ino ||
	    before.st_mode != after.st_mode || before.st_size != after.st_size ||
	    before.st_mtim.tv_sec != after.st_mtim.tv_sec ||
	    before.st_mtim.tv_nsec != after.st_mtim.tv_nsec)
		fail("xattr projection changed while being read");
	result[offset] = '\0';
	*length = offset;
	return result;
}

static struct xattr_projection read_projection(const char *path)
{
	struct xattr_projection result = { 0 };
	char *payload;
	char *cursor;
	char *end;
	size_t length;

	payload = read_small_regular(path, &length);
	cursor = payload;
	end = payload + length;
	if (length <= strlen(PROJECTION_FORMAT) ||
	    memcmp(cursor, PROJECTION_FORMAT, strlen(PROJECTION_FORMAT)) ||
	    cursor[strlen(PROJECTION_FORMAT)] != '\n')
		fail("xattr projection format changed");
	cursor += strlen(PROJECTION_FORMAT) + 1;
	while (cursor < end) {
		struct projected_xattr item = { 0 };
		struct projected_xattr *resized;
		char *newline;
		char *first;
		char *second;
		size_t hex_length;
		size_t index;
		size_t name_length;
		size_t path_length;

		if (result.count == PROJECTION_MAX_ENTRIES)
			fail("xattr projection has too many entries");
		newline = memchr(cursor, '\n', (size_t)(end - cursor));
		if (!newline)
			fail("xattr projection lacks a final newline");
		first = memchr(cursor, '\t', (size_t)(newline - cursor));
		if (!first)
			fail("xattr projection entry is malformed");
		second = memchr(first + 1, '\t',
				(size_t)(newline - first - 1));
		if (!second || memchr(second + 1, '\t',
					(size_t)(newline - second - 1)))
			fail("xattr projection entry is malformed");
		path_length = (size_t)(first - cursor);
		name_length = (size_t)(second - first - 1);
		item.path = duplicate_bytes(cursor, path_length);
		item.name = duplicate_bytes(first + 1, name_length);
		if (strlen(item.path) != path_length ||
		    strlen(item.name) != name_length)
			fail("xattr projection identity contains a null byte");
		if (!valid_relative_path(item.path) ||
		    !valid_xattr_name(item.name))
			fail("xattr projection identity is invalid");
		hex_length = (size_t)(newline - second - 1);
		if (!hex_length || hex_length % 2 || hex_length > 16384)
			fail("xattr projection value size is invalid");
		item.value_length = hex_length / 2;
		item.value = allocate(item.value_length);
		for (index = 0; index < item.value_length; index++)
			item.value[index] =
				(decode_hex_digit(second[1 + index * 2]) << 4) |
				decode_hex_digit(second[2 + index * 2]);
		if (result.count &&
		    compare_projected_xattrs(&result.items[result.count - 1],
					     &item) >= 0)
			fail("xattr projection entries are not uniquely sorted");
		resized = realloc(result.items,
				  (result.count + 1) * sizeof(*result.items));
		if (!resized)
			fail("out of memory");
		result.items = resized;
		result.items[result.count++] = item;
		cursor = newline + 1;
	}
	free(payload);
	if (!result.count)
		fail("xattr projection is empty");
	return result;
}

static void free_projection(struct xattr_projection *projection)
{
	size_t index;

	for (index = 0; index < projection->count; index++) {
		free(projection->items[index].path);
		free(projection->items[index].name);
		free(projection->items[index].value);
	}
	free(projection->items);
	*projection = (struct xattr_projection){ 0 };
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
		const unsigned char *value = block + index * 4;

		words[index] = (uint32_t)value[0] << 24 |
			       (uint32_t)value[1] << 16 |
			       (uint32_t)value[2] << 8 |
			       (uint32_t)value[3];
	}
	for (; index < 64; index++) {
		uint32_t first;
		uint32_t second;

		first = rotate_right(words[index - 15], 7) ^
			rotate_right(words[index - 15], 18) ^
			(words[index - 15] >> 3);
		second = rotate_right(words[index - 2], 17) ^
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
		uint32_t choose;
		uint32_t majority;
		uint32_t first;
		uint32_t second;
		uint32_t temporary1;
		uint32_t temporary2;

		first = rotate_right(e, 6) ^ rotate_right(e, 11) ^
			rotate_right(e, 25);
		choose = (e & f) ^ (~e & g);
		temporary1 = h + first + choose + constants[index] +
			     words[index];
		second = rotate_right(a, 2) ^ rotate_right(a, 13) ^
			 rotate_right(a, 22);
		majority = (a & b) ^ (a & c) ^ (b & c);
		temporary2 = second + majority;

		h = g;
		g = f;
		f = e;
		e = d + temporary1;
		d = c;
		c = b;
		b = a;
		a = temporary1 + temporary2;
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
	*context = (struct sha256){
		.state = {
			0x6a09e667,
			0xbb67ae85,
			0x3c6ef372,
			0xa54ff53a,
			0x510e527f,
			0x9b05688c,
			0x1f83d9ab,
			0x5be0cd19,
		},
	};
}

static void sha256_update(struct sha256 *context, const void *input,
			  size_t length)
{
	const unsigned char *data = input;

	while (length) {
		size_t available = sizeof(context->block) - context->block_size;
		size_t amount = length < available ? length : available;

		memcpy(context->block + context->block_size, data, amount);
		context->block_size += amount;
		data += amount;
		length -= amount;
		if (context->block_size != sizeof(context->block))
			continue;
		sha256_transform(context, context->block);
		context->bit_count += 512;
		context->block_size = 0;
	}
}

static void sha256_final(struct sha256 *context, unsigned char output[32])
{
	uint64_t total_bits;
	size_t index;

	total_bits = context->bit_count + context->block_size * 8;
	context->block[context->block_size++] = 0x80;
	if (context->block_size > 56) {
		memset(context->block + context->block_size, 0,
		       sizeof(context->block) - context->block_size);
		sha256_transform(context, context->block);
		context->block_size = 0;
	}
	memset(context->block + context->block_size, 0,
	       56 - context->block_size);
	for (index = 0; index < 8; index++)
		context->block[63 - index] =
			(unsigned char)(total_bits >> (index * 8));
	sha256_transform(context, context->block);

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

static bool valid_hash(const char *value)
{
	size_t index;

	if (strlen(value) != 64)
		return false;
	for (index = 0; index < 64; index++) {
		if ((value[index] < '0' || value[index] > '9') &&
		    (value[index] < 'a' || value[index] > 'f'))
			return false;
	}
	return true;
}

static uint64_t parse_number(const char *value, bool require_nonzero)
{
	uint64_t result = 0;
	const unsigned char *cursor = (const unsigned char *)value;

	if (!*cursor)
		fail("empty numeric seal field");
	while (*cursor) {
		unsigned int digit;

		if (*cursor < '0' || *cursor > '9')
			fail("malformed numeric seal field");
		digit = *cursor - '0';
		if (result > (UINT64_MAX - digit) / 10)
			fail("numeric seal field overflow");
		result = result * 10 + digit;
		cursor++;
	}
	if (require_nonzero && !result)
		fail("numeric seal field must be nonzero");
	return result;
}

static void hash_regular_file(const char *path, const struct stat *expected,
			      unsigned char output[32])
{
	unsigned char buffer[1024 * 1024];
	struct sha256 digest;
	struct stat actual;
	ssize_t amount;
	int descriptor;

	descriptor = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
	if (descriptor < 0)
		fail("cannot open regular file: %s", path);
	if (fstat(descriptor, &actual) < 0)
		fail("cannot stat opened regular file: %s", path);
	if (actual.st_dev != expected->st_dev ||
	    actual.st_ino != expected->st_ino ||
	    actual.st_mode != expected->st_mode ||
	    actual.st_size != expected->st_size)
		fail("tree entry changed while being verified: %s", path);

	sha256_init(&digest);
	for (;;) {
		amount = read(descriptor, buffer, sizeof(buffer));
		if (amount > 0) {
			sha256_update(&digest, buffer, (size_t)amount);
			continue;
		}
		if (!amount)
			break;
		if (errno == EINTR)
			continue;
		fail("cannot read regular file: %s", path);
	}
	if (close(descriptor) < 0)
		fail("cannot close regular file: %s", path);
	sha256_final(&digest, output);
}

static char *read_link(const char *path, const struct stat *metadata,
		       size_t *length)
{
	size_t capacity;
	char *result;
	ssize_t amount;

	capacity = metadata->st_size > 0 ? (size_t)metadata->st_size + 1 : 256;
	for (;;) {
		result = allocate(capacity);
		amount = readlink(path, result, capacity);
		if (amount < 0)
			fail("cannot read symbolic link: %s", path);
		if ((size_t)amount < capacity) {
			*length = (size_t)amount;
			return result;
		}
		free(result);
		if (capacity > SIZE_MAX / 2)
			fail("symbolic-link target is too large: %s", path);
		capacity *= 2;
	}
}

static int compare_strings(const void *left, const void *right)
{
	const char *const *left_string = left;
	const char *const *right_string = right;

	return strcmp(*left_string, *right_string);
}

static struct string_list list_directory(const char *path)
{
	struct string_list result = { 0 };
	struct dirent *entry;
	DIR *directory;

	directory = opendir(path);
	if (!directory)
		fail("cannot open directory: %s", path);
	errno = 0;
	while ((entry = readdir(directory))) {
		char **resized;

		if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, ".."))
			continue;
		if (result.count == SIZE_MAX / sizeof(*result.items))
			fail("too many directory entries: %s", path);
		resized = realloc(result.items,
				  (result.count + 1) * sizeof(*result.items));
		if (!resized)
			fail("out of memory");
		result.items = resized;
		result.items[result.count++] = strdup(entry->d_name);
		if (!result.items[result.count - 1])
			fail("out of memory");
		errno = 0;
	}
	if (errno)
		fail("cannot read directory: %s", path);
	if (closedir(directory) < 0)
		fail("cannot close directory: %s", path);
	qsort(result.items, result.count, sizeof(*result.items),
	      compare_strings);
	return result;
}

static void free_string_list(struct string_list *list)
{
	size_t index;

	for (index = 0; index < list->count; index++)
		free(list->items[index]);
	free(list->items);
	*list = (struct string_list){ 0 };
}

static struct string_list list_xattrs(const char *path, bool nfs4_projection)
{
	struct string_list result = { 0 };
	ssize_t required;
	ssize_t actual;
	char *buffer;
	char *cursor;
	char *end;

	required = llistxattr(path, NULL, 0);
	if (required < 0) {
		if (errno == ENOTSUP || errno == EOPNOTSUPP)
			fail("filesystem does not support xattrs: %s", path);
		fail("cannot list xattrs: %s", path);
	}
	if (!required)
		return result;

	buffer = allocate((size_t)required);
	actual = llistxattr(path, buffer, (size_t)required);
	if (actual != required)
		fail("xattr list changed while being verified: %s", path);
	cursor = buffer;
	end = buffer + actual;
	while (cursor < end) {
		size_t length = strnlen(cursor, (size_t)(end - cursor));
		char **resized;

		if (!length || cursor + length >= end)
			fail("malformed xattr list: %s", path);
		resized = realloc(result.items,
				  (result.count + 1) * sizeof(*result.items));
		if (!resized)
			fail("out of memory");
		result.items = resized;
		if (nfs4_projection &&
		    length == strlen(NFS4_ACL_XATTR) &&
		    !memcmp(cursor, NFS4_ACL_XATTR, length)) {
			cursor += length + 1;
			continue;
		}
		result.items[result.count++] = duplicate_bytes(cursor, length);
		cursor += length + 1;
	}
	free(buffer);
	qsort(result.items, result.count, sizeof(*result.items),
	      compare_strings);
	return result;
}

static unsigned char *read_xattr(const char *path, const char *name,
				 size_t *length)
{
	ssize_t required;
	ssize_t actual;
	unsigned char *value;

	required = lgetxattr(path, name, NULL, 0);
	if (required < 0)
		fail("cannot size xattr %s on %s", name, path);
	value = allocate((size_t)required);
	actual = lgetxattr(path, name, value, (size_t)required);
	if (actual != required)
		fail("xattr changed while being verified: %s on %s", name, path);
	*length = (size_t)actual;
	return value;
}

static size_t projection_start(const struct xattr_projection *projection,
			       const char *relative)
{
	size_t index;

	for (index = 0; index < projection->count; index++) {
		int order = strcmp(projection->items[index].path, relative);

		if (order >= 0)
			return index;
	}
	return projection->count;
}

static void put_field(struct sha256 *digest, const void *value, size_t length)
{
	unsigned char encoded_length[8];
	uint64_t size = length;
	size_t index;

	for (index = 0; index < sizeof(encoded_length); index++)
		encoded_length[7 - index] =
			(unsigned char)(size >> (index * 8));
	sha256_update(digest, encoded_length, sizeof(encoded_length));
	sha256_update(digest, value, length);
}

static void hash_xattr(struct sha256 *digest, const char *name,
		       const unsigned char *value, size_t value_length)
{
	put_field(digest, name, strlen(name));
	put_field(digest, value, value_length);
}

static void put_unsigned(struct sha256 *digest, uint64_t value)
{
	char encoded[32];
	int length;

	length = snprintf(encoded, sizeof(encoded), "%" PRIu64, value);
	if (length < 0 || (size_t)length >= sizeof(encoded))
		fail("cannot encode unsigned metadata");
	put_field(digest, encoded, (size_t)length);
}

static void put_signed(struct sha256 *digest, int64_t value)
{
	char encoded[32];
	int length;

	length = snprintf(encoded, sizeof(encoded), "%" PRId64, value);
	if (length < 0 || (size_t)length >= sizeof(encoded))
		fail("cannot encode signed metadata");
	put_field(digest, encoded, (size_t)length);
}

static int64_t mtime_nanoseconds(const struct stat *metadata)
{
	int64_t seconds = metadata->st_mtim.tv_sec;
	int64_t nanoseconds = metadata->st_mtim.tv_nsec;

	if (nanoseconds < 0 || nanoseconds >= 1000000000)
		fail("invalid nanosecond timestamp");
	if (seconds > (INT64_MAX - nanoseconds) / 1000000000 ||
	    seconds < INT64_MIN / 1000000000)
		fail("timestamp is outside the seal format");
	return seconds * 1000000000 + nanoseconds;
}

static char *join_path(const char *parent, const char *child)
{
	size_t parent_length = strlen(parent);
	size_t child_length = strlen(child);
	bool slash = parent_length && parent[parent_length - 1] != '/';
	char *result;

	if (parent_length > SIZE_MAX - child_length - 2)
		fail("path is too long");
	result = allocate(parent_length + slash + child_length + 1);
	memcpy(result, parent, parent_length);
	if (slash)
		result[parent_length++] = '/';
	memcpy(result + parent_length, child, child_length + 1);
	return result;
}

static char *join_relative(const char *parent, const char *child)
{
	if (!strcmp(parent, "."))
		return strdup(child);
	return join_path(parent, child);
}

static void verify_entry(const char *path, const char *relative,
			 dev_t root_device, struct sha256 *digest,
			 struct counters *counters,
			 struct xattr_projection *projection)
{
	static const unsigned char empty[] = "";
	unsigned char content_hash[32];
	const void *content = empty;
	size_t content_length = 0;
	char *link_target = NULL;
	size_t link_length = 0;
	const char *kind;
	struct string_list xattrs;
	struct stat metadata;
	size_t index;

	if (lstat(path, &metadata) < 0)
		fail("cannot stat tree entry: %s", path);
	if (metadata.st_dev != root_device)
		fail("tree crosses a filesystem boundary: %s", relative);
	if (S_ISREG(metadata.st_mode)) {
		kind = "file";
		hash_regular_file(path, &metadata, content_hash);
		content = content_hash;
		content_length = sizeof(content_hash);
		counters->regular_files++;
		if (metadata.st_size < 0 ||
		    (uint64_t)metadata.st_size >
			    UINT64_MAX - counters->bytes)
			fail("regular-file byte count overflow: %s", relative);
		counters->bytes += (uint64_t)metadata.st_size;
	} else if (S_ISDIR(metadata.st_mode)) {
		kind = "directory";
		counters->directories++;
	} else if (S_ISLNK(metadata.st_mode)) {
		kind = "symlink";
		link_target = read_link(path, &metadata, &link_length);
		counters->symlinks++;
	} else {
		fail("tree contains an unsupported entry: %s", relative);
	}

	xattrs = list_xattrs(path, projection->count != 0);
	{
		size_t actual_index = 0;
		size_t projected_index = projection_start(projection, relative);
		size_t projected_count = 0;
		size_t merged_count;

		while (projected_index + projected_count < projection->count &&
		       !strcmp(projection->items[
			       projected_index + projected_count].path, relative))
			projected_count++;
		if (projected_count && !S_ISREG(metadata.st_mode))
			fail("xattr projection targets a non-regular file: %s",
			     relative);
		if (projected_count > SIZE_MAX - xattrs.count)
			fail("xattr count overflow");
		merged_count = xattrs.count + projected_count;
		for (index = 0; index < xattrs.count; index++) {
			size_t projection_index;

			for (projection_index = projected_index;
			     projection_index < projected_index + projected_count;
			     projection_index++) {
				if (!strcmp(xattrs.items[index],
					    projection->items[
						    projection_index].name)) {
					merged_count--;
					break;
				}
			}
		}
		if (merged_count > UINT64_MAX - counters->xattrs)
			fail("xattr count overflow");
		counters->xattrs += merged_count;
		counters->entries++;

		put_field(digest, relative, strlen(relative));
		put_field(digest, kind, strlen(kind));
		put_unsigned(digest, metadata.st_mode & 07777);
		put_unsigned(digest, metadata.st_uid);
		put_unsigned(digest, metadata.st_gid);
		if (metadata.st_size < 0)
			fail("negative tree-entry size: %s", relative);
		put_unsigned(digest, (uint64_t)metadata.st_size);
		put_signed(digest, mtime_nanoseconds(&metadata));
		put_unsigned(digest, metadata.st_nlink);
		put_field(digest, content, content_length);
		put_field(digest,
			  link_target ? (const void *)link_target :
					(const void *)empty,
			  link_length);
		put_unsigned(digest, merged_count);

		index = 0;
		while (actual_index < xattrs.count ||
		       index < projected_count) {
			struct projected_xattr *projected =
				index < projected_count ?
				&projection->items[projected_index + index] : NULL;
			const char *actual = actual_index < xattrs.count ?
				xattrs.items[actual_index] : NULL;
			int order = actual && projected ?
				strcmp(actual, projected->name) :
				(actual ? -1 : 1);

			if (order < 0) {
				unsigned char *value;
				size_t value_length;

				value = read_xattr(path, actual, &value_length);
				hash_xattr(digest, actual, value, value_length);
				free(value);
				actual_index++;
			} else if (order > 0) {
				hash_xattr(digest, projected->name,
					   projected->value,
					   projected->value_length);
				projected->used = true;
				index++;
			} else {
				unsigned char *value;
				size_t value_length;

				value = read_xattr(path, actual, &value_length);
				if (value_length != projected->value_length ||
				    memcmp(value, projected->value, value_length))
					fail("projected xattr changed: %s on %s",
					     actual, relative);
				hash_xattr(digest, actual, value, value_length);
				free(value);
				projected->used = true;
				actual_index++;
				index++;
			}
		}
	}
	free(link_target);
	free_string_list(&xattrs);

	if (S_ISDIR(metadata.st_mode)) {
		struct string_list children = list_directory(path);

		for (index = 0; index < children.count; index++) {
			char *child_path;
			char *child_relative;

			if (!strcmp(relative, ".") &&
			    !strcmp(children.items[index], SEAL_NAME))
				continue;
			child_path = join_path(path, children.items[index]);
			child_relative =
				join_relative(relative, children.items[index]);
			if (!child_relative)
				fail("out of memory");
			verify_entry(child_path, child_relative, root_device,
				     digest, counters, projection);
			free(child_relative);
			free(child_path);
		}
		free_string_list(&children);
	}
}

static char *read_anchored_seal(const char *path, const char *expected_hash,
				size_t *length)
{
	unsigned char actual_digest[32];
	char actual_hash[65];
	struct sha256 digest;
	struct stat before;
	struct stat after;
	char *result;
	size_t offset = 0;
	ssize_t amount;
	int descriptor;

	if (!valid_hash(expected_hash))
		fail("expected seal SHA-256 is malformed");
	descriptor = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
	if (descriptor < 0)
		fail("cannot open persistent-root seal");
	if (fstat(descriptor, &before) < 0)
		fail("cannot stat persistent-root seal");
	if (!S_ISREG(before.st_mode) || (before.st_mode & 07777) != 0444)
		fail("persistent-root seal type or mode changed");
	if (before.st_size <= 0 || before.st_size > 65536)
		fail("persistent-root seal size is invalid");

	result = allocate((size_t)before.st_size + 1);
	sha256_init(&digest);
	while (offset < (size_t)before.st_size) {
		amount = read(descriptor, result + offset,
			      (size_t)before.st_size - offset);
		if (amount > 0) {
			sha256_update(&digest, result + offset, (size_t)amount);
			offset += (size_t)amount;
			continue;
		}
		if (amount < 0 && errno == EINTR)
			continue;
		fail("cannot read persistent-root seal");
	}
	if (fstat(descriptor, &after) < 0)
		fail("cannot restat persistent-root seal");
	if (close(descriptor) < 0)
		fail("cannot close persistent-root seal");
	if (before.st_dev != after.st_dev || before.st_ino != after.st_ino ||
	    before.st_mode != after.st_mode || before.st_size != after.st_size ||
	    before.st_mtim.tv_sec != after.st_mtim.tv_sec ||
	    before.st_mtim.tv_nsec != after.st_mtim.tv_nsec)
		fail("persistent-root seal changed while being read");

	sha256_final(&digest, actual_digest);
	bytes_to_hex(actual_digest, sizeof(actual_digest), actual_hash);
	if (strcmp(actual_hash, expected_hash))
		fail("persistent-root seal SHA-256 changed");
	result[offset] = '\0';
	*length = offset;
	return result;
}

static struct expected_tree parse_seal(char *seal, size_t length)
{
	static const char *const keys[] = {
		"seal_format",
		"generation",
		"source_archive_size",
		"source_archive_sha256",
		"promotion_state",
		"tree_format",
		"tree_entries",
		"tree_regular_files",
		"tree_directories",
		"tree_symlinks",
		"tree_bytes",
		"tree_xattrs",
		"tree_sha256",
	};
	char *values[ARRAY_SIZE(keys)] = { 0 };
	struct expected_tree result;
	char *cursor = seal;
	char *end = seal + length;
	size_t index;

	for (index = 0; index < ARRAY_SIZE(keys); index++) {
		char *newline;
		char *separator;
		size_t key_length;
		size_t value_length;

		if (cursor >= end)
			fail("persistent-root seal has missing fields");
		newline = memchr(cursor, '\n', (size_t)(end - cursor));
		if (!newline)
			fail("persistent-root seal lacks a final newline");
		separator = memchr(cursor, '=', (size_t)(newline - cursor));
		if (!separator)
			fail("persistent-root seal field is malformed");
		key_length = (size_t)(separator - cursor);
		value_length = (size_t)(newline - separator - 1);
		if (key_length != strlen(keys[index]) ||
		    memcmp(cursor, keys[index], key_length))
			fail("persistent-root seal fields or ordering changed");
		if (!value_length)
			fail("persistent-root seal contains an empty value");
		values[index] = duplicate_bytes(separator + 1, value_length);
		cursor = newline + 1;
	}
	if (cursor != end)
		fail("persistent-root seal has extra fields");

	if (strcmp(values[0], "rog5-persistent-root-v1") ||
	    strcmp(values[1], "arch-a") ||
	    strcmp(values[4], "UNBOOTED") ||
	    strcmp(values[5], "rog5-persistent-tree-v1"))
		fail("persistent-root seal identity or state changed");
	parse_number(values[2], true);
	if (!valid_hash(values[3]) || !valid_hash(values[12]))
		fail("persistent-root seal hash field is malformed");

	result = (struct expected_tree){
		.counters = {
			.entries = parse_number(values[6], true),
			.regular_files = parse_number(values[7], false),
			.directories = parse_number(values[8], true),
			.symlinks = parse_number(values[9], false),
			.bytes = parse_number(values[10], false),
			.xattrs = parse_number(values[11], false),
		},
	};
	memcpy(result.hash, values[12], sizeof(result.hash));
	for (index = 0; index < ARRAY_SIZE(values); index++)
		free(values[index]);
	return result;
}

static void compare_tree(const struct counters *actual,
			 const struct expected_tree *expected,
			 const char *actual_hash)
{
	if (actual->entries != expected->counters.entries)
		fail("sealed tree changed: tree_entries");
	if (actual->regular_files != expected->counters.regular_files)
		fail("sealed tree changed: tree_regular_files");
	if (actual->directories != expected->counters.directories)
		fail("sealed tree changed: tree_directories");
	if (actual->symlinks != expected->counters.symlinks)
		fail("sealed tree changed: tree_symlinks");
	if (actual->bytes != expected->counters.bytes)
		fail("sealed tree changed: tree_bytes");
	if (actual->xattrs != expected->counters.xattrs)
		fail("sealed tree changed: tree_xattrs");
	if (strcmp(actual_hash, expected->hash))
		fail("sealed tree changed: tree_sha256");
}

int main(int argument_count, char **arguments)
{
	static const unsigned char prefix[] = "rog5-persistent-tree-v1";
	unsigned char tree_digest[32];
	char tree_hash[65];
	struct expected_tree expected;
	struct counters actual = { 0 };
	struct sha256 digest;
	struct stat root_metadata;
	struct xattr_projection projection = { 0 };
	char *seal_data;
	char *root;
	size_t seal_length;

	if (argument_count != 4 && argument_count != 6) {
		fprintf(stderr,
			"usage: %s ROOT SEAL EXPECTED_SEAL_SHA256 "
			"[--nfs4-xattr-projection FILE]\n",
			arguments[0]);
		return EXIT_FAILURE;
	}
	if (argument_count == 6) {
		if (strcmp(arguments[4], "--nfs4-xattr-projection"))
			fail("unknown persistent-root verifier option");
		projection = read_projection(arguments[5]);
	}
	if (lstat(arguments[1], &root_metadata) < 0 ||
	    !S_ISDIR(root_metadata.st_mode) ||
	    S_ISLNK(root_metadata.st_mode))
		fail("tree root is not a real directory");
	root = realpath(arguments[1], NULL);
	if (!root)
		fail("cannot resolve tree root");

	seal_data = read_anchored_seal(arguments[2], arguments[3],
				       &seal_length);
	expected = parse_seal(seal_data, seal_length);
	free(seal_data);

	sha256_init(&digest);
	sha256_update(&digest, prefix, sizeof(prefix));
	verify_entry(root, ".", root_metadata.st_dev, &digest, &actual,
		     &projection);
	for (size_t index = 0; index < projection.count; index++) {
		if (!projection.items[index].used)
			fail("xattr projection path was not verified: %s",
			     projection.items[index].path);
	}
	sha256_final(&digest, tree_digest);
	bytes_to_hex(tree_digest, sizeof(tree_digest), tree_hash);
	compare_tree(&actual, &expected, tree_hash);

	printf("PASS persistent root matches anchored seal entries=%" PRIu64
	       " tree_sha256=%s\n",
	       actual.entries, tree_hash);
	free_projection(&projection);
	free(root);
	return EXIT_SUCCESS;
}
