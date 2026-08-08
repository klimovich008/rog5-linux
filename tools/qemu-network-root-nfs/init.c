#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

#define EXPORT_SOURCE "169.254.77.1:/"
#define MOUNTPOINT "/mnt/root-ro"

static void stop_guest(bool passed)
{
	sync();
	reboot(RB_POWER_OFF);
	_exit(passed ? EXIT_SUCCESS : EXIT_FAILURE);
}

static void fail(const char *stage)
{
	dprintf(STDERR_FILENO, "FAIL QEMU NFS mount stage=%s errno=%d (%s)\n",
		stage, errno, strerror(errno));
	stop_guest(false);
}

static void require_directory(const char *path)
{
	if (mkdir(path, 0755) == -1 && errno != EEXIST)
		fail(path);
}

static void verify_read_only_enforcement(void)
{
	int descriptor;

	descriptor = open(MOUNTPOINT "/must-not-exist",
			  O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
	if (descriptor != -1) {
		(void)close(descriptor);
		errno = EPROTO;
		fail("read-only-create-succeeded");
	}
	if (errno != EROFS)
		fail("read-only-create-error");
}

static void verify_mount(void)
{
	char mountinfo[16384];
	struct statfs filesystem;
	ssize_t count;
	int descriptor;

	if (statfs(MOUNTPOINT, &filesystem) == -1)
		fail("statfs");
	if ((unsigned long)filesystem.f_type != NFS_SUPER_MAGIC) {
		errno = ENODEV;
		fail("filesystem-type");
	}
	descriptor = open("/proc/self/mountinfo", O_RDONLY | O_CLOEXEC);
	if (descriptor == -1)
		fail("open-mountinfo");
	count = read(descriptor, mountinfo, sizeof(mountinfo) - 1);
	if (count <= 0)
		fail("read-mountinfo");
	if (close(descriptor) == -1)
		fail("close-mountinfo");
	mountinfo[count] = '\0';
	if (strstr(mountinfo, " /mnt/root-ro ro,") == NULL ||
	    strstr(mountinfo, " - nfs4 169.254.77.1:/ ro,") == NULL) {
		errno = EROFS;
		fail("read-only-mountinfo");
	}
}

int main(void)
{
	static const char production_options[] =
		"vers=4.2,proto=tcp,port=2049,ro,nolock,soft,timeo=10,retrans=1";
	char kernel_options[sizeof(production_options) +
			    sizeof(",addr=169.254.77.1")];

	/* mount.nfs resolves the source and appends addr before sys_mount(). */
	if (snprintf(kernel_options, sizeof(kernel_options), "%s,addr=%s",
		     production_options, "169.254.77.1") >=
	    (int)sizeof(kernel_options)) {
		errno = EOVERFLOW;
		fail("kernel-options");
	}

	require_directory("/proc");
	require_directory("/mnt");
	require_directory(MOUNTPOINT);
	if (mount("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC,
		  NULL) == -1)
		fail("mount-proc");
	if (mount(EXPORT_SOURCE, MOUNTPOINT, "nfs4",
		  MS_RDONLY | MS_NOSUID | MS_NODEV, kernel_options) == -1)
		fail("mount-nfs4");
	verify_mount();
	verify_read_only_enforcement();
	if (umount2(MOUNTPOINT, MNT_DETACH) == -1)
		fail("unmount-nfs4");
	dprintf(STDOUT_FILENO,
		"PASS Linux 7.1.4 mounted exact NFSv4.2 root read-only\n");
	stop_guest(true);
}
