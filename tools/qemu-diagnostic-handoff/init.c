// SPDX-License-Identifier: GPL-2.0-only

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/ioctl.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define REPORTER "/sbin/rog5-early-target-diag"
#define RETAINED_REPORTER "/run/initramfs/sbin/rog5-early-target-diag"
#define CANDIDATE "headless-netroot-early-diag-v1"
#define SYSTEMD "/usr/lib/systemd/systemd"
#define PUBLICATION_SETTLE_MS 500

static void console_write(const char *message)
{
	int descriptor = open("/dev/console", O_WRONLY | O_CLOEXEC);
	size_t remaining = strlen(message);

	if (descriptor < 0)
		descriptor = STDERR_FILENO;
	while (remaining > 0) {
		ssize_t written = write(descriptor, message, remaining);

		if (written > 0) {
			message += written;
			remaining -= (size_t)written;
			continue;
		}
		if (written < 0 && errno == EINTR)
			continue;
		break;
	}
	if (descriptor != STDERR_FILENO)
		(void)close(descriptor);
}

__attribute__((noreturn)) static void stop(const char *message)
{
	console_write("FAIL qemu diagnostic handoff: ");
	console_write(message);
	console_write("\n");
	(void)reboot(RB_POWER_OFF);
	for (;;)
		pause();
}

static void make_directory(const char *path)
{
	if (mkdir(path, 0755) < 0 && errno != EEXIST)
		stop("cannot create directory");
}

static void make_file(const char *path)
{
	int descriptor = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC,
			      0755);

	if (descriptor < 0)
		stop("cannot create bind target");
	if (close(descriptor) < 0)
		stop("cannot close bind target");
}

static void write_control(const char *path, const char *value)
{
	int descriptor = open(path, O_WRONLY | O_CLOEXEC);
	size_t length = strlen(value);

	if (descriptor < 0)
		stop("cannot open kernel diagnostic control");
	if (write(descriptor, value, length) != (ssize_t)length ||
	    close(descriptor) < 0)
		stop("cannot enable kernel diagnostic control");
}

static void bind_file(const char *source, const char *target)
{
	make_file(target);
	if (mount(source, target, NULL, MS_BIND, NULL) < 0)
		stop("cannot bind handoff executable");
}

static void detach_controlling_terminal(void)
{
	struct sigaction ignored = {
		.sa_handler = SIG_IGN,
	};
	struct sigaction previous;
	int descriptor;

	descriptor = open("/dev/tty", O_RDWR | O_NOCTTY | O_CLOEXEC | O_NONBLOCK);
	if (descriptor < 0) {
		if (errno == ENXIO || errno == ENODEV || errno == ENOENT)
			return;
		stop("cannot inspect controlling terminal");
	}
	if (sigemptyset(&ignored.sa_mask) < 0 ||
	    sigaction(SIGHUP, &ignored, &previous) < 0)
		stop("cannot guard controlling-terminal release");
	if (ioctl(descriptor, TIOCNOTTY) < 0 && errno != ENOTTY)
		stop("cannot release controlling terminal");
	if (sigaction(SIGHUP, &previous, NULL) < 0 || close(descriptor) < 0)
		stop("cannot finish controlling-terminal release");
}

static void sleep_milliseconds(long milliseconds)
{
	struct timespec delay = {
		.tv_sec = milliseconds / 1000,
		.tv_nsec = milliseconds % 1000 * 1000000,
	};

	while (nanosleep(&delay, &delay) < 0 && errno == EINTR)
		;
}

static int wait_child(pid_t child)
{
	int status;

	while (waitpid(child, &status, 0) < 0) {
		if (errno != EINTR)
			return -1;
	}
	return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}

static int emit_stage(const char *stage)
{
	pid_t child = fork();

	if (child < 0)
		return -1;
	if (child == 0) {
		int null_descriptor = open("/dev/null", O_WRONLY | O_CLOEXEC);

		if (null_descriptor >= 0) {
			(void)dup2(null_descriptor, STDERR_FILENO);
			(void)close(null_descriptor);
		}
		execl(REPORTER, REPORTER, "emit", stage, (char *)NULL);
		_exit(127);
	}
	return wait_child(child);
}

static void require_emit(const char *stage)
{
	for (unsigned int attempt = 0; attempt < 200; attempt++) {
		if (emit_stage(stage) == 0)
			return;
		sleep_milliseconds(10);
	}
	stop("diagnostic stage update failed");
}

static void read_boot_id(char *boot_id, size_t capacity)
{
	int descriptor;
	size_t used = 0;

	descriptor = open("/proc/sys/kernel/random/boot_id",
			  O_RDONLY | O_CLOEXEC);
	if (descriptor < 0)
		stop("cannot open boot ID");
	while (used < capacity - 1) {
		ssize_t length = read(descriptor, boot_id + used,
				      capacity - 1 - used);

		if (length > 0) {
			used += (size_t)length;
			continue;
		}
		if (length == 0)
			break;
		if (errno != EINTR)
			stop("cannot read boot ID");
	}
	(void)close(descriptor);
	if (used == 37 && boot_id[36] == '\n')
		used--;
	if (used != 36)
		stop("invalid boot ID");
	boot_id[used] = '\0';
}

static unsigned long long watchdog_deadline(void)
{
	struct timespec now;
	unsigned long long milliseconds;

	if (clock_gettime(CLOCK_BOOTTIME, &now) < 0)
		stop("cannot read boot clock");
	milliseconds = (unsigned long long)now.tv_sec * 1000ULL;
	milliseconds += (unsigned long long)now.tv_nsec / 1000000ULL;
	if (milliseconds > 300000ULL)
		stop("QEMU boot exceeded diagnostic setup bound");
	return milliseconds + 600000ULL;
}

static pid_t start_reporter(void)
{
	char boot_id[37];
	char deadline[32];
	pid_t child;

	read_boot_id(boot_id, sizeof(boot_id));
	if (snprintf(deadline, sizeof(deadline), "%llu", watchdog_deadline()) < 1)
		stop("cannot format watchdog deadline");
	child = fork();
	if (child < 0)
		stop("cannot fork reporter");
	if (child == 0) {
		int console_descriptor;

		(void)setsid();
		console_descriptor = open("/dev/console", O_WRONLY | O_CLOEXEC);
		if (console_descriptor >= 0) {
			(void)dup2(console_descriptor, STDERR_FILENO);
			(void)close(console_descriptor);
		}
		execl(REPORTER, REPORTER, "serve", CANDIDATE, boot_id,
		      deadline, (char *)NULL);
		_exit(127);
	}
	return child;
}

static void move_handoff_mount(const char *source, const char *target)
{
	if (mount(source, target, NULL, MS_MOVE, NULL) < 0)
		stop("cannot move handoff mount");
}

__attribute__((noreturn)) static void enter_new_root(const char *new_root,
						      const char *new_init)
{
	char *const arguments[] = {(char *)new_init, NULL};

	if (chdir(new_root) < 0)
		stop("cannot enter new-root mount");
	if (mount(".", "/", NULL, MS_MOVE, NULL) < 0)
		stop("cannot move new root over old root");
	if (chroot(".") < 0 || chdir("/") < 0)
		stop("cannot change root");
	execv(new_init, arguments);
	stop("new init returned from exec");
}

__attribute__((noreturn)) static void systemd_success(void)
{
	char pid_one[128];
	char pid_text[32];
	char *end = NULL;
	long reporter_pid;
	int descriptor;
	ssize_t length;

	length = readlink("/proc/1/exe", pid_one, sizeof(pid_one) - 1);
	if (length < 1 || (size_t)length >= sizeof(pid_one))
		stop("cannot inspect systemd PID 1");
	pid_one[length] = '\0';
	if (strcmp(pid_one, SYSTEMD) != 0)
		stop("generated units did not run under systemd PID 1");
	sleep_milliseconds(PUBLICATION_SETTLE_MS);
	console_write("PASS generated diagnostic units ran under ARM64 systemd\n");
	descriptor = open("/run/rog5-qemu-reporter.pid", O_RDONLY | O_CLOEXEC);
	if (descriptor >= 0) {
		length = read(descriptor, pid_text, sizeof(pid_text) - 1);
		(void)close(descriptor);
		if (length > 0) {
			pid_text[length] = '\0';
			errno = 0;
			reporter_pid = strtol(pid_text, &end, 10);
			if (errno == 0 && end != pid_text && reporter_pid > 1)
				(void)kill((pid_t)reporter_pid, SIGTERM);
		}
	}
	(void)sync();
	(void)reboot(RB_POWER_OFF);
	for (;;)
		pause();
}

__attribute__((noreturn)) static void initial_init(void)
{
	char pid_record[32];
	int descriptor;
	pid_t reporter_pid;

	make_directory("/dev");
	make_directory("/proc");
	make_directory("/run");
	make_directory("/sys");
	make_directory("/newroot");
	if (mount("devtmpfs", "/dev", "devtmpfs", 0, NULL) < 0 &&
	    errno != EBUSY)
		stop("cannot mount devtmpfs");
	if (mount("proc", "/proc", "proc", 0, NULL) < 0)
		stop("cannot mount proc");
	write_control("/proc/sys/debug/exception-trace", "1\n");
	write_control("/proc/sys/kernel/print-fatal-signals", "1\n");
	if (mount("sysfs", "/sys", "sysfs", 0, NULL) < 0)
		stop("cannot mount sysfs");
	make_directory("/sys/fs");
	make_directory("/sys/fs/cgroup");
	if (mount("cgroup2", "/sys/fs/cgroup", "cgroup2", 0, NULL) < 0)
		stop("cannot mount cgroup2");
	if (mount("tmpfs", "/run", "tmpfs", 0, "mode=0755,size=8m") < 0)
		stop("cannot mount run tmpfs");
	reporter_pid = start_reporter();
	descriptor = open("/run/rog5-qemu-reporter.pid",
			  O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
	if (descriptor < 0)
		stop("cannot publish reporter PID");
	if (snprintf(pid_record, sizeof(pid_record), "%ld\n",
		     (long)reporter_pid) < 1 ||
	    write(descriptor, pid_record, strlen(pid_record)) !=
		    (ssize_t)strlen(pid_record) ||
	    close(descriptor) < 0)
		stop("cannot write reporter PID");
	require_emit("10");
	for (unsigned int attempt = 0; access("/dev/hvc0", R_OK | W_OK) < 0;
	     attempt++) {
		if (attempt == 500)
			stop("virtio diagnostic console did not appear");
		sleep_milliseconds(10);
	}
	if (symlink("/dev/hvc0", "/dev/ttyGS0") < 0)
		stop("cannot create diagnostic tty alias");
	sleep_milliseconds(400);

	make_directory("/run/initramfs");
	make_directory("/run/initramfs/sbin");
	bind_file(REPORTER, RETAINED_REPORTER);
	if (access("/systemd-root/usr/lib/systemd/systemd", X_OK) < 0)
		stop("systemd runtime root is absent");
	if (mount("/systemd-root", "/newroot", NULL, MS_BIND | MS_REC,
		  NULL) < 0)
		stop("cannot bind systemd runtime root");
	make_directory("/newroot/dev");
	make_directory("/newroot/proc");
	make_directory("/newroot/run");
	make_directory("/newroot/sys");
	move_handoff_mount("/dev", "/newroot/dev");
	move_handoff_mount("/proc", "/newroot/proc");
	move_handoff_mount("/sys", "/newroot/sys");
	move_handoff_mount("/run", "/newroot/run");
	require_emit("120");
	sleep_milliseconds(400);
	detach_controlling_terminal();
	if (setenv("LD_PRELOAD", "/usr/lib/rog5-abort-trace.so", 1) < 0)
		stop("cannot enable QEMU abort tracing");
	enter_new_root("/newroot", SYSTEMD);
}

int main(int argc, char **argv)
{
	if (argc == 2 && strcmp(argv[1], "systemd-success") == 0)
		systemd_success();
	if (argc == 2 && strcmp(argv[1], "sshd-stub") == 0) {
		sleep_milliseconds(PUBLICATION_SETTLE_MS);
		console_write("PASS systemd activated the sshd dependency\n");
		return EXIT_SUCCESS;
	}
	if (argc != 1)
		return EXIT_FAILURE;
	initial_init();
}
