// SPDX-License-Identifier: GPL-2.0-only

#define _GNU_SOURCE

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define REPORTER "/sbin/rog5-early-target-diag"
#define RETAINED_REPORTER "/run/initramfs/sbin/rog5-early-target-diag"
#define CANDIDATE "headless-netroot-early-diag-v2"
#define SYSTEMD "/usr/lib/systemd/systemd"
#define SSH_PROOF_COMMAND "rog5-qemu-openssh-proof-v1"
#define SSH_PASSWORD_ASKPASS "rog5-qemu-password-askpass"
#define SSH_PASSWORD_PROBE "rog5-qemu-password"
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

static void bind_file(const char *source, const char *target)
{
	make_file(target);
	if (mount(source, target, NULL, MS_BIND, NULL) < 0)
		stop("cannot bind handoff executable");
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

static int run_ssh(bool with_key)
{
	pid_t child = fork();

	if (child < 0)
		return -1;
	if (child == 0) {
		if (with_key) {
			execl("/usr/bin/ssh", "ssh", "-F", "/dev/null", "-T",
			      "-p", "2222", "-o", "BatchMode=yes", "-o",
			      "ConnectTimeout=2", "-o", "ConnectionAttempts=1",
			      "-o", "IdentitiesOnly=yes", "-o",
			      "StrictHostKeyChecking=yes", "-o",
			      "UserKnownHostsFile=/etc/ssh/ssh_known_hosts",
			      "-o", "GlobalKnownHostsFile=/dev/null", "-i",
			      "/etc/ssh/client_ed25519_key",
			      "root@127.0.0.1", SSH_PROOF_COMMAND,
			      (char *)NULL);
		} else {
			execl("/usr/bin/ssh", "ssh", "-F", "/dev/null", "-T",
			      "-p", "2222", "-o", "BatchMode=yes", "-o",
			      "ConnectTimeout=2", "-o", "ConnectionAttempts=1",
			      "-o", "IdentitiesOnly=yes", "-o",
			      "PubkeyAuthentication=no", "-o",
			      "PasswordAuthentication=no", "-o",
			      "KbdInteractiveAuthentication=no", "-o",
			      "StrictHostKeyChecking=yes", "-o",
			      "UserKnownHostsFile=/etc/ssh/ssh_known_hosts",
			      "-o", "GlobalKnownHostsFile=/dev/null",
			      "root@127.0.0.1", SSH_PROOF_COMMAND,
			      (char *)NULL);
		}
		_exit(127);
	}
	return wait_child(child);
}

static int run_password_ssh(void)
{
	pid_t child = fork();

	if (child < 0)
		return -1;
	if (child == 0) {
		if (setenv("SSH_ASKPASS", "/usr/bin/" SSH_PASSWORD_ASKPASS,
			   1) < 0 ||
		    setenv("SSH_ASKPASS_REQUIRE", "force", 1) < 0 ||
		    setenv("DISPLAY", "rog5-qemu", 1) < 0)
			_exit(126);
		execl("/usr/bin/ssh", "ssh", "-F", "/dev/null", "-T",
		      "-p", "2222", "-o", "BatchMode=no", "-o",
		      "ConnectTimeout=2", "-o", "ConnectionAttempts=1",
		      "-o", "IdentitiesOnly=yes", "-o",
		      "PreferredAuthentications=password", "-o",
		      "PubkeyAuthentication=no", "-o",
		      "KbdInteractiveAuthentication=no", "-o",
		      "NumberOfPasswordPrompts=1", "-o",
		      "StrictHostKeyChecking=yes", "-o",
		      "UserKnownHostsFile=/etc/ssh/ssh_known_hosts", "-o",
		      "GlobalKnownHostsFile=/dev/null",
		      "password-probe@127.0.0.1", SSH_PROOF_COMMAND,
		      (char *)NULL);
		_exit(127);
	}
	return wait_child(child);
}

static int ssh_proof(void)
{
	int status = -1;

	for (unsigned int attempt = 0; attempt < 100; attempt++) {
		status = run_ssh(true);
		if (status == 0)
			break;
		sleep_milliseconds(50);
	}
	if (status != 0) {
		console_write("FAIL real OpenSSH key login was not accepted\n");
		return EXIT_FAILURE;
	}
	if (run_ssh(false) == 0) {
		console_write("FAIL OpenSSH accepted a keyless login\n");
		return EXIT_FAILURE;
	}
	if (run_password_ssh() == 0) {
		console_write("FAIL OpenSSH accepted a password login\n");
		return EXIT_FAILURE;
	}
	console_write("PASS real key-only OpenSSH login completed\n");
	return EXIT_SUCCESS;
}

__attribute__((noreturn)) static void sshd_check(void)
{
	int console_descriptor = open("/dev/console", O_WRONLY | O_CLOEXEC);

	if (console_descriptor >= 0) {
		(void)dup2(console_descriptor, STDOUT_FILENO);
		(void)dup2(console_descriptor, STDERR_FILENO);
		(void)close(console_descriptor);
	}
	execl("/usr/bin/sshd", "/usr/bin/sshd", "-t", "-e", "-f",
	      "/etc/ssh/sshd_config", (char *)NULL);
	_exit(127);
}

__attribute__((noreturn)) static void sshd_server(void)
{
	int console_descriptor = open("/dev/console", O_WRONLY | O_CLOEXEC);

	if (console_descriptor >= 0) {
		(void)dup2(console_descriptor, STDOUT_FILENO);
		(void)dup2(console_descriptor, STDERR_FILENO);
		(void)close(console_descriptor);
	}
	execl("/usr/bin/sshd", "/usr/bin/sshd", "-D", "-e", "-f",
	      "/etc/ssh/sshd_config", (char *)NULL);
	_exit(127);
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

static void require_systemd_pid_one(void)
{
	char pid_one[128];
	ssize_t length;

	length = readlink("/proc/1/exe", pid_one, sizeof(pid_one) - 1);
	if (length < 1 || (size_t)length >= sizeof(pid_one))
		stop("cannot inspect systemd PID 1");
	pid_one[length] = '\0';
	if (strcmp(pid_one, SYSTEMD) != 0)
		stop("generated units did not run under systemd PID 1");
}

static bool mount_option_present(const char *options, const char *required)
{
	size_t required_length = strlen(required);
	const char *cursor = options;

	while (*cursor != '\0') {
		const char *end = strchr(cursor, ',');
		size_t length = end == NULL ? strlen(cursor) :
			(size_t)(end - cursor);

		if (length == required_length &&
		    strncmp(cursor, required, length) == 0)
			return true;
		if (end == NULL)
			break;
		cursor = end + 1;
	}
	return false;
}

static bool mountinfo_has(const char *required_mountpoint,
			  const char *required_type,
			  const char *required_source,
			  const char *required_option)
{
	char *line = NULL;
	size_t capacity = 0;
	unsigned int matches = 0;
	FILE *stream;

	stream = fopen("/proc/self/mountinfo", "re");
	if (stream == NULL)
		stop("cannot open network-root mountinfo");
	while (getline(&line, &capacity, stream) >= 0) {
		char mountpoint[256];
		char mount_options[512];
		char filesystem_type[64];
		char source[256];
		char *separator = strstr(line, " - ");

		if (separator == NULL)
			continue;
		*separator = '\0';
		if (sscanf(line, "%*s %*s %*s %*s %255s %511s",
			   mountpoint, mount_options) != 2 ||
		    sscanf(separator + 3, "%63s %255s",
			   filesystem_type, source) != 2)
			continue;
		if (strcmp(mountpoint, required_mountpoint) == 0 &&
		    strcmp(filesystem_type, required_type) == 0 &&
		    strcmp(source, required_source) == 0 &&
		    mount_option_present(mount_options, required_option))
			matches++;
	}
	if (ferror(stream)) {
		free(line);
		(void)fclose(stream);
		stop("cannot read network-root mountinfo");
	}
	free(line);
	if (fclose(stream) != 0)
		stop("cannot close network-root mountinfo");
	return matches == 1;
}

static bool exact_file(const char *path, const char *expected)
{
	char content[128];
	size_t expected_length = strlen(expected);
	ssize_t length;
	int descriptor;

	if (expected_length >= sizeof(content))
		stop("network-root expected record is too long");
	descriptor = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
	if (descriptor < 0)
		return false;
	length = read(descriptor, content, sizeof(content));
	if (close(descriptor) < 0)
		return false;
	return length == (ssize_t)expected_length &&
		memcmp(content, expected, expected_length) == 0;
}

static void require_no_block_devices(void)
{
	struct dirent *entry;
	DIR *directory;
	bool found = false;
	int read_error;

	directory = opendir("/sys/class/block");
	if (directory == NULL && errno == ENOENT)
		return;
	if (directory == NULL)
		stop("cannot inspect live block topology");
	errno = 0;
	while ((entry = readdir(directory)) != NULL) {
		if (strcmp(entry->d_name, ".") == 0 ||
		    strcmp(entry->d_name, "..") == 0)
			continue;
		found = true;
		break;
	}
	read_error = errno;
	if (closedir(directory) < 0)
		stop("cannot close live block topology");
	if (read_error != 0)
		stop("cannot read live block topology");
	if (found)
		stop("live block device appeared in network-root gate");
}

static void require_network_root_state(void)
{
	struct stat metadata;

	require_no_block_devices();
	if (!mountinfo_has("/", "overlay", "overlay", "rw"))
		stop("PID 1 root is not the production overlay");
	if (!mountinfo_has("/.rog5/root-ro", "nfs4", "169.254.77.1:/",
			   "ro"))
		stop("production NFS lower identity changed after handoff");
	if (!mountinfo_has("/.rog5/state", "tmpfs", "tmpfs", "rw"))
		stop("production tmpfs state identity changed after handoff");
	if (!exact_file("/run/rog5-physical-block-count", "0\n"))
		stop("production physical-storage record changed");
	if (!exact_file("/run/rog5-network-root-source",
			"169.254.77.1:/\n"))
		stop("production network-root source record changed");
	if (lstat("/run/rog5-network-root-mounted", &metadata) < 0 ||
	    !S_ISREG(metadata.st_mode) || metadata.st_size != 0)
		stop("production network-root marker changed");
	if (access("/overlay-write", F_OK) < 0 ||
	    access("/.rog5/state/upper/overlay-write", F_OK) < 0)
		stop("production overlay upper write did not survive handoff");
	errno = 0;
	if (access("/.rog5/root-ro/overlay-write", F_OK) == 0 || errno != ENOENT)
		stop("production overlay write reached the NFS lower");
}

__attribute__((noreturn)) static void finish_systemd_gate(const char *message)
{
	char pid_text[32];
	char *end = NULL;
	long reporter_pid;
	int descriptor;
	ssize_t length;

	sleep_milliseconds(PUBLICATION_SETTLE_MS);
	console_write(message);
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

__attribute__((noreturn)) static void systemd_success(void)
{
	require_systemd_pid_one();
	finish_systemd_gate(
		"PASS generated diagnostic units ran under ARM64 systemd\n");
}

__attribute__((noreturn)) static void network_root_success(void)
{
	require_systemd_pid_one();
	require_network_root_state();
	finish_systemd_gate(
		"PASS production NFS/OverlayFS root reached ARM64 systemd and key-only OpenSSH\n");
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
	enter_new_root("/newroot", SYSTEMD);
}

int main(int argc, char **argv)
{
	const char *program = strrchr(argv[0], '/');

	program = program == NULL ? argv[0] : program + 1;
	if (strcmp(program, SSH_PASSWORD_ASKPASS) == 0) {
		static const char password[] = SSH_PASSWORD_PROBE "\n";

		if (argc != 2 || write(STDOUT_FILENO, password,
				       sizeof(password) - 1) !=
				(ssize_t)(sizeof(password) - 1))
			return EXIT_FAILURE;
		return EXIT_SUCCESS;
	}
	if (argc == 3 && strcmp(argv[1], "-c") == 0 &&
	    strcmp(argv[2], SSH_PROOF_COMMAND) == 0) {
		if (getenv("SSH_CONNECTION") == NULL || getenv("SSH_CLIENT") == NULL)
			return EXIT_FAILURE;
		console_write("PASS OpenSSH executed the authenticated command\n");
		return EXIT_SUCCESS;
	}
	if (argc == 2 && strcmp(argv[1], "systemd-success") == 0)
		systemd_success();
	if (argc == 2 && strcmp(argv[1], "network-root-success") == 0)
		network_root_success();
	if (argc == 2 && strcmp(argv[1], "ssh-proof") == 0)
		return ssh_proof();
	if (argc == 2 && strcmp(argv[1], "sshd-check") == 0)
		sshd_check();
	if (argc == 2 && strcmp(argv[1], "sshd-server") == 0)
		sshd_server();
	if (argc != 1)
		return EXIT_FAILURE;
	initial_init();
}
