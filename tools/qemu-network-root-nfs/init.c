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
#define SERVER_PROBE_MOUNTPOINT "/mnt/server-ro-probe"

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

static void verify_seeded_systemd(void)
{
	static const unsigned char elf_magic[] = { 0x7f, 'E', 'L', 'F' };
	unsigned char actual[sizeof(elf_magic)];
	ssize_t count;
	int descriptor;

	descriptor = open(MOUNTPOINT "/usr/lib/systemd/systemd",
			  O_RDONLY | O_CLOEXEC);
	if (descriptor == -1)
		fail("open-seeded-systemd");
	count = read(descriptor, actual, sizeof(actual));
	if (count != (ssize_t)sizeof(actual))
		fail("read-seeded-systemd");
	if (close(descriptor) == -1)
		fail("close-seeded-systemd");
	if (memcmp(actual, elf_magic, sizeof(actual)) != 0) {
		errno = ENOEXEC;
		fail("seeded-systemd-elf");
	}
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

static void verify_server_probe_client_rw(void)
{
	char mountinfo[16384];
	ssize_t count;
	int descriptor;

	descriptor = open("/proc/self/mountinfo", O_RDONLY | O_CLOEXEC);
	if (descriptor == -1)
		fail("open-server-probe-mountinfo");
	count = read(descriptor, mountinfo, sizeof(mountinfo) - 1);
	if (count <= 0)
		fail("read-server-probe-mountinfo");
	if (close(descriptor) == -1)
		fail("close-server-probe-mountinfo");
	mountinfo[count] = '\0';
	if (strstr(mountinfo, " /mnt/server-ro-probe rw,") == NULL ||
	    strstr(mountinfo, " - nfs4 169.254.77.1:/ rw,") == NULL) {
		errno = EROFS;
		fail("server-probe-client-not-rw");
	}
}

static void verify_server_read_only(const char *mount_options)
{
	struct statfs filesystem;
	int descriptor;

	require_directory(SERVER_PROBE_MOUNTPOINT);
	if (mount(EXPORT_SOURCE, SERVER_PROBE_MOUNTPOINT, "nfs4",
		  MS_NOSUID | MS_NODEV, mount_options) == -1)
		fail("mount-server-ro-probe");
	if (statfs(SERVER_PROBE_MOUNTPOINT, &filesystem) == -1)
		fail("statfs-server-ro-probe");
	if ((unsigned long)filesystem.f_type != NFS_SUPER_MAGIC) {
		errno = ENODEV;
		fail("server-ro-probe-filesystem-type");
	}
	verify_server_probe_client_rw();
	descriptor = open(SERVER_PROBE_MOUNTPOINT "/must-not-exist",
			  O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
	if (descriptor != -1) {
		(void)close(descriptor);
		errno = EPROTO;
		fail("server-rw-create-succeeded");
	}
	if (errno != EROFS)
		fail("server-rw-create-error");
	if (umount2(SERVER_PROBE_MOUNTPOINT, MNT_DETACH) == -1)
		fail("unmount-server-ro-probe");
	dprintf(STDOUT_FILENO,
		"PASS QEMU NFS server rejected an RW client write\n");
}

static void enter_production_probe(void)
{
	dprintf(STDOUT_FILENO,
		"PASS Linux 7.1.4 mounted exact NFSv4.2 root read-only\n");
	execl("/bin/sh", "sh", "/production-init", NULL);
	fail("exec-production-init");
}

int main(void)
{
	static const char production_options[] =
		"vers=4.2,proto=tcp,port=2049,ro,soft,timeo=30,retrans=2";
	static const char server_probe_options_base[] =
		"vers=4.2,proto=tcp,port=2049,rw,soft,timeo=30,retrans=2";
	char kernel_options[sizeof(production_options) +
			    sizeof(",addr=169.254.77.1")];
	char server_probe_options[sizeof(server_probe_options_base) +
				  sizeof(",addr=169.254.77.1")];

	/* mount.nfs resolves the source and appends addr before sys_mount(). */
	if (snprintf(kernel_options, sizeof(kernel_options), "%s,addr=%s",
		     production_options, "169.254.77.1") >=
	    (int)sizeof(kernel_options)) {
		errno = EOVERFLOW;
		fail("kernel-options");
	}
	if (snprintf(server_probe_options, sizeof(server_probe_options),
		     "%s,addr=%s", server_probe_options_base,
		     "169.254.77.1") >= (int)sizeof(server_probe_options)) {
		errno = EOVERFLOW;
		fail("server-probe-options");
	}

	require_directory("/proc");
	require_directory("/mnt");
	require_directory(MOUNTPOINT);
	if (mount("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC,
		  NULL) == -1)
		fail("mount-proc");
	verify_server_read_only(server_probe_options);
	if (mount(EXPORT_SOURCE, MOUNTPOINT, "nfs4",
		  MS_RDONLY | MS_NOSUID | MS_NODEV, kernel_options) == -1)
		fail("mount-nfs4");
	verify_mount();
	verify_read_only_enforcement();
	verify_seeded_systemd();
	if (umount2(MOUNTPOINT, MNT_DETACH) == -1)
		fail("unmount-nfs4");
	enter_production_probe();
}
