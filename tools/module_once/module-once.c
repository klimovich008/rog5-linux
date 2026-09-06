// SPDX-License-Identifier: GPL-2.0-only
/* finit_module exactly once: no ENOSYS/EINVAL/EINTR init_module fallback. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

static int insert_once(int fd, const char *parameters)
{
	return syscall(SYS_finit_module, fd, parameters, 0);
}

int main(int argc, char **argv)
{
	struct stat st;
	int fd, ret, error;

	if ((argc != 2 && argc != 3) || geteuid() != 0) {
		fprintf(stderr, "usage (root): module-once MODULE [PARAMETERS]\n");
		return 2;
	}
	fd = open(argv[1], O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
	if (fd < 0) {
		perror("module-once open");
		return 2;
	}
	if (fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_uid != 0 ||
	    (st.st_mode & 022) || st.st_size < 1 || st.st_size > 64 * 1024 * 1024) {
		fprintf(stderr, "module-once unsafe file\n");
		close(fd);
		return 2;
	}
	ret = insert_once(fd, argc == 3 ? argv[2] : "");
	error = errno;
	close(fd);
	if (ret) {
		fprintf(stderr, "module-once finit_module errno=%d (%s); no retry\n",
			error, strerror(error));
		return 1;
	}
	return 0;
}
