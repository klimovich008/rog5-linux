// SPDX-License-Identifier: MIT
#define _GNU_SOURCE
#include <fcntl.h>
#include <signal.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <termios.h>
#include <unistd.h>

#ifndef ROG5_EXITRD_LOG_DEVICE
#define ROG5_EXITRD_LOG_DEVICE "/dev/ttyGS0"
#endif

/* Interrupt u_serial's close-drain wait; O_NONBLOCK alone does not bound it.
 * Keep this periodic until close has returned, even if an earlier call used a
 * tick. A wedged/uninterruptible kernel is not bounded by a userspace timer.
 */
#define LOG_TICK_USEC 250000
static void interrupt_wait(int signo)
{
	(void)signo;
}

/* Advisory output only: no reader, retry, file creation or storage write. */
int main(int argc, char **argv)
{
	static const char prefix[] = "ROG5_EXITRD ";
	char line[256];
	struct stat st;
	struct termios attributes;
	struct sigaction action = { .sa_handler = interrupt_wait };
	struct itimerval timer = {
		.it_value.tv_usec = LOG_TICK_USEC,
		.it_interval.tv_usec = LOG_TICK_USEC,
	};
	sigset_t signals;
	size_t length;
	int fd;
	ssize_t written;

	if (argc != 2)
		return 0;
	length = strnlen(argv[1], sizeof(line));
	if (!length || length > sizeof(line) - sizeof(prefix))
		return 0;
	for (size_t i = 0; i < length; i++)
		if ((unsigned char)argv[1][i] < 32 ||
		    (unsigned char)argv[1][i] > 126)
			return 0;
	memcpy(line, prefix, sizeof(prefix) - 1);
	memcpy(line + sizeof(prefix) - 1, argv[1], length);
	length += sizeof(prefix) - 1;
	line[length++] = '\n';
	sigemptyset(&signals);
	sigaddset(&signals, SIGALRM);
	if (sigaction(SIGALRM, &action, NULL) != 0 ||
	    sigprocmask(SIG_UNBLOCK, &signals, NULL) != 0 ||
	    setitimer(ITIMER_REAL, &timer, NULL) != 0)
		return 0;
	fd = open(ROG5_EXITRD_LOG_DEVICE,
		  O_WRONLY | O_NOCTTY | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW);
	if (fd < 0)
		return 0;
	if (fstat(fd, &st) == 0 && S_ISCHR(st.st_mode) &&
	    tcgetattr(fd, &attributes) == 0) {
		cfmakeraw(&attributes);
		attributes.c_cflag |= CLOCAL | CREAD;
		if (tcsetattr(fd, TCSANOW, &attributes) == 0) {
			written = write(fd, line, length);
			(void)written; /* Partial evidence is advisory; never retry. */
		}
	}
	close(fd);
	return 0;
}
