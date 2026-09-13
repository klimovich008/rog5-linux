/* VM-only probe: observe the real call; never replace or time-limit it. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static int log_fd = -1;
static void (*real_sync)(void);
static pthread_mutex_t log_lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned int records;

/* Do not report failure through stderr: it may be a stalled evidence FIFO. */
static void fail(void)
{
	_exit(125);
}

static void check_log(void)
{
	struct stat st;
	if (fstat(log_fd, &st) || !S_ISREG(st.st_mode) ||
	    st.st_uid != geteuid() || (st.st_mode & 07777) != 0600 ||
	    st.st_nlink != 1 || st.st_size < 0 || st.st_size > 1536 - 128)
		fail();
}

static void record(const char *stage)
{
	struct timespec now;
	char line[128];
	int length;
	if (pthread_mutex_lock(&log_lock))
		fail();
	check_log();
	if (++records > 12 || clock_gettime(CLOCK_MONOTONIC, &now))
		fail();
	length = snprintf(line, sizeof(line),
		"ROG5_SETTINGS_SYNC phase=%s pid=%ld clock=CLOCK_MONOTONIC seconds=%lld.%09ld\n",
		stage, (long)getpid(), (long long)now.tv_sec, now.tv_nsec);
	if (length < 0 || (size_t)length >= sizeof(line) ||
	    write(log_fd, line, (size_t)length) != length)
		fail();
	if (pthread_mutex_unlock(&log_lock))
		fail();
}

__attribute__((constructor)) static void initialize(void)
{
	int saved_errno = errno;
	const char *path = getenv("ROG5_SETTINGS_SYNC_LOG");
	if (!path || !*path)
		fail();
	log_fd = open(path, O_WRONLY | O_NOFOLLOW | O_NONBLOCK | O_APPEND | O_CLOEXEC);
	if (log_fd < 0)
		fail();
	check_log();
	dlerror();
	/* POSIX specifies this dlsym conversion for a function symbol. */
	real_sync = (void (*)(void))dlsym(RTLD_NEXT, "g_settings_sync");
	if (dlerror() || !real_sync) {
		record("resolve-failed");
		fail();
	}
	/* The launcher admits only our preload. Keep it out of exec'ed helpers,
	 * which need not link GIO; the current process retains the interposer.
	 */
	if (unsetenv("LD_PRELOAD") || unsetenv("ROG5_SETTINGS_SYNC_LOG"))
		fail();
	record("loaded resolved=true");
	errno = saved_errno;
}

void g_settings_sync(void)
{
	int entry_errno = errno;
	int result_errno;
	if (!real_sync)
		fail();
	record("BEGIN");
	errno = entry_errno;
	real_sync();
	result_errno = errno;
	record("END");
	errno = result_errno;
}
