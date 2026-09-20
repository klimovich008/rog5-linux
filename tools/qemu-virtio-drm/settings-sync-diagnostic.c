/* VM-only probe: observe the real call; never replace or time-limit it. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#if defined(ROG5_WINDOW_PROBE) && !defined(ROG5_NO_UNREF_PROBE)
#error "window observation requires the no-unref control to retain record limits"
#endif

static int log_fd = -1;
static void (*real_sync)(void);
static pthread_mutex_t log_lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned int records;
#ifndef ROG5_NO_UNREF_PROBE
/* Explicit experimental control: omit the symbol entirely, rather than
 * forwarding through a supposedly cheap wrapper on every object release.
 * Run/shutdown/settings observation and all log guards remain available.
 */
static _Atomic(void *) pending_unref;
#endif
static _Atomic int application_observed;
#ifndef ROG5_NO_UNREF_PROBE
static void (*real_unref)(void *);
static pthread_once_t unref_once = PTHREAD_ONCE_INIT;
#endif

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

/* Observe only the first direct unref of the exact application after its run
 * and our disconnects returned. Other references/callees retain their behavior.
 * Resolving once also covers legitimate unrefs before g_application_run().
 */
#ifndef ROG5_NO_UNREF_PROBE
static void resolve_unref(void)
{
	dlerror();
	real_unref = (void (*)(void *))dlsym(RTLD_NEXT, "g_object_unref");
	if (dlerror() || !real_unref)
		fail();
}

void g_object_unref(void *object)
{
	int entry_errno = errno, result_errno;
	void *expected = object;
	int observe;
	if (pthread_once(&unref_once, resolve_unref))
		fail();
	observe = object && atomic_compare_exchange_strong(&pending_unref,
							 &expected, NULL);
	if (observe)
		record("APP_UNREF_BEGIN");
	errno = entry_errno;
	real_unref(object);
	result_errno = errno;
	if (observe)
		record("APP_UNREF_END");
	errno = result_errno;
}
#endif

__attribute__((destructor)) static void finalize_probe(void)
{
	int saved_errno = errno;
	/* Reaching this DSO destructor is not proof that process exit completed. */
	if (atomic_load(&application_observed))
		record("DSO_FINI");
	errno = saved_errno;
}

/* Opaque public API types: the probe never inspects or replaces object layout.
 * Resolve these only when an application actually runs, so the sync-only probe
 * remains usable without a GApplication. Signatures and G_CONNECT_AFTER=1 are
 * from the retained GLib 2.88.3 headers. Its shutdown signal is RUN_LAST.
 */
struct _GApplication;

#ifdef ROG5_WINDOW_PROBE
static void *(*window_list)(void *);

/* GtkApplication::window-removed is RUN_FIRST in the retained GTK3 source.
 * This AFTER handler observes the public list after the default handler and
 * ordinary handlers; it does not bracket removal or inspect private use_count.
 * The explicit one-window diagnostic retains the existing record/byte limits.
 */
static void window_removed(void *application, void *window, void *data)
{
	int saved_errno = errno;
	(void)window;
	(void)data;
	record(window_list(application) ? "WINDOW_REMOVED_NONZERO" : "WINDOW_REMOVED_ZERO");
	errno = saved_errno;
}
#endif

static void shutdown_before(struct _GApplication *application, void *data)
{
	int saved_errno = errno;
	(void)application;
	(void)data;
	record("SHUTDOWN_BEFORE");
	errno = saved_errno;
}

static void shutdown_after(struct _GApplication *application, void *data)
{
	int saved_errno = errno;
	(void)application;
	(void)data;
	record("SHUTDOWN_AFTER");
	errno = saved_errno;
}

int g_application_run(struct _GApplication *application, int argc, char **argv)
{
	int entry_errno = errno, result_errno, result, disconnect_errno;
	int (*run)(struct _GApplication *, int, char **);
	unsigned long (*connect)(void *, const char *, void (*)(void), void *,
				 void (*)(void *, void *), int);
	void (*disconnect)(void *, unsigned long);
	unsigned long before, after;
#ifdef ROG5_WINDOW_PROBE
	unsigned long removed;
#endif

	dlerror();
	run = (int (*)(struct _GApplication *, int, char **))
		dlsym(RTLD_NEXT, "g_application_run");
	connect = (unsigned long (*)(void *, const char *, void (*)(void), void *,
				     void (*)(void *, void *), int))
		dlsym(RTLD_NEXT, "g_signal_connect_data");
	disconnect = (void (*)(void *, unsigned long))
		dlsym(RTLD_NEXT, "g_signal_handler_disconnect");
	if (dlerror() || !run || !connect || !disconnect) {
		record("app-resolve-failed");
		fail();
	}
	before = connect(application, "shutdown", (void (*)(void))shutdown_before,
			 NULL, NULL, 0);
	after = connect(application, "shutdown", (void (*)(void))shutdown_after,
			NULL, NULL, 1); /* G_CONNECT_AFTER */
	if (!before || !after)
		fail();
#ifdef ROG5_WINDOW_PROBE
	dlerror();
	window_list = (void *(*)(void *))dlsym(RTLD_NEXT, "gtk_application_get_windows");
	if (dlerror() || !window_list) {
		record("window-resolve-failed");
		fail();
	}
	removed = connect(application, "window-removed", (void (*)(void))window_removed,
			  NULL, NULL, 1); /* G_CONNECT_AFTER; no extra application ref */
	if (!removed)
		fail();
#endif
	atomic_store(&application_observed, 1);
	record("APP_RUN_BEGIN");
	errno = entry_errno;
	result = run(application, argc, argv);
	result_errno = errno;
	record("APP_RUN_END");
	/* Disconnect while the caller still owns the application; no extra ref or
	 * weak-ref callback changes its lifetime. These are signal-observer bounds,
	 * not exact subclass instruction boundaries. No main-context iteration.
	 */
	disconnect(application, before);
	disconnect_errno = errno;
	record("APP_DISCONNECT_ONE_END");
	errno = disconnect_errno;
	disconnect(application, after);
#ifdef ROG5_WINDOW_PROBE
	disconnect(application, removed);
#endif
	record("APP_OBSERVERS_REMOVED");
#ifndef ROG5_NO_UNREF_PROBE
	atomic_store(&pending_unref, application);
#endif
	errno = result_errno;
	return result;
}
