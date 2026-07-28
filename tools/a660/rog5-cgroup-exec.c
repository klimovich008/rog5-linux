// SPDX-License-Identifier: MIT
/*
 * Fixed descriptor-only launcher for the A660 acceptance harness.
 *
 * The parent opens a new cgroup.procs file and a sealed executable snapshot.
 * This helper joins that cgroup before dropping credentials and fexecve().
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define MAX_GROUPS 256U
#define REQUIRED_SEALS \
	(F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE)

extern char **environ;

static void fail(const char *message)
{
	fprintf(stderr, "FAIL cgroup executor: %s\n", message);
	_exit(126);
}

static uint64_t parse_number(const char *value, uint64_t maximum)
{
	char *end = NULL;
	unsigned long long parsed;

	if (!value[0] || (value[0] == '0' && value[1]))
		fail("numeric argument is not canonical");
	errno = 0;
	parsed = strtoull(value, &end, 10);
	if (errno || !end || *end || parsed > maximum)
		fail("numeric argument is outside policy");
	return (uint64_t)parsed;
}

static size_t parse_groups(char *value, gid_t groups[MAX_GROUPS])
{
	char *cursor = value;
	size_t count = 0;
	uint64_t previous = 0;

	if (!strcmp(value, "-"))
		return 0;
	while (*cursor) {
		char *separator = strchr(cursor, ',');
		uint64_t parsed;

		if (separator)
			*separator = '\0';
		parsed = parse_number(cursor, UINT32_MAX);
		if (count >= MAX_GROUPS || (count && parsed <= previous))
			fail("supplementary groups are not canonical");
		groups[count++] = (gid_t)parsed;
		previous = parsed;
		if (!separator)
			break;
		cursor = separator + 1;
		if (!*cursor)
			fail("supplementary groups are not canonical");
	}
	return count;
}

static int compare_groups(const void *left, const void *right)
{
	gid_t first = *(const gid_t *)left;
	gid_t second = *(const gid_t *)right;

	return (first > second) - (first < second);
}

static void join_cgroup(int descriptor)
{
	static const char membership[] = "0\n";
	struct stat metadata;
	ssize_t written;

	if (fstat(descriptor, &metadata) < 0 ||
	    !S_ISREG(metadata.st_mode))
		fail("cgroup descriptor is unsafe");
	written = write(descriptor, membership, sizeof(membership) - 1U);
	if (written != (ssize_t)(sizeof(membership) - 1U))
		fail("cannot join command cgroup");
	if (close(descriptor) < 0)
		fail("cannot close cgroup descriptor");
}

static void validate_target(int descriptor)
{
	struct stat metadata;
	int seals;
	int descriptor_flags;

	if (fstat(descriptor, &metadata) < 0 ||
	    !S_ISREG(metadata.st_mode) ||
	    (metadata.st_mode & 0777) != 0555)
		fail("target descriptor is unsafe");
	seals = fcntl(descriptor, F_GET_SEALS);
	if (seals != REQUIRED_SEALS)
		fail("target descriptor is not sealed");
	descriptor_flags = fcntl(descriptor, F_GETFD);
	if (descriptor_flags < 0 ||
	    fcntl(descriptor, F_SETFD, descriptor_flags & ~FD_CLOEXEC) < 0)
		fail("cannot prepare target descriptor");
}

static bool credentials_match(uid_t uid, gid_t gid,
			      const gid_t *groups, size_t count)
{
	gid_t observed[MAX_GROUPS];
	int observed_count;

	if (geteuid() != uid || getegid() != gid)
		return false;
	observed_count = getgroups((int)MAX_GROUPS, observed);
	if (observed_count < 0 || (size_t)observed_count != count)
		return false;
	qsort(observed, (size_t)observed_count, sizeof(observed[0]),
	      compare_groups);
	for (size_t index = 0; index < count; index++) {
		if (observed[index] != groups[index])
			return false;
	}
	return true;
}

int main(int argc, char **argv)
{
	gid_t supplementary[MAX_GROUPS];
	size_t supplementary_count;
	uint64_t target_value;
	uint64_t cgroup_value;
	uint64_t uid_value;
	uint64_t gid_value;

	if (argc < 13 ||
	    strcmp(argv[1], "--target-fd") ||
	    strcmp(argv[3], "--cgroup-fd") ||
	    strcmp(argv[5], "--uid") ||
	    strcmp(argv[7], "--gid") ||
	    strcmp(argv[9], "--groups") ||
	    strcmp(argv[11], "--") ||
	    argv[12][0] != '/')
		fail("argument contract changed");
	target_value = parse_number(argv[2], INT_MAX);
	cgroup_value = parse_number(argv[4], INT_MAX);
	uid_value = parse_number(argv[6], UINT32_MAX);
	gid_value = parse_number(argv[8], UINT32_MAX);
	if (target_value < 3 || cgroup_value < 3 ||
	    target_value == cgroup_value)
		fail("descriptor argument is outside policy");
	supplementary_count = parse_groups(argv[10], supplementary);

	validate_target((int)target_value);
	join_cgroup((int)cgroup_value);
	if (!credentials_match((uid_t)uid_value, (gid_t)gid_value,
			       supplementary, supplementary_count)) {
		if (setgroups(supplementary_count, supplementary) < 0 ||
		    setresgid((gid_t)gid_value, (gid_t)gid_value,
			      (gid_t)gid_value) < 0 ||
		    setresuid((uid_t)uid_value, (uid_t)uid_value,
			      (uid_t)uid_value) < 0)
			fail("cannot apply target credentials");
	}
	fexecve((int)target_value, &argv[12], environ);
	fail("cannot execute sealed target");
}
