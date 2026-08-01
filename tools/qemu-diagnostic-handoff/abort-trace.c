// SPDX-License-Identifier: MIT
#define _GNU_SOURCE

#include <execinfo.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void write_all(int descriptor, const char *value)
{
	size_t remaining = strlen(value);

	while (remaining > 0) {
		ssize_t written = write(descriptor, value, remaining);

		if (written > 0) {
			value += written;
			remaining -= (size_t)written;
			continue;
		}
		if (written < 0 && errno == EINTR)
			continue;
		_exit(122);
	}
}

__attribute__((noreturn)) static void trace_failure(
	const char *kind, const char *text, const char *file, const char *function)
{
	void *frames[32];
	int descriptor;
	int count;

	descriptor = open("/dev/console", O_WRONLY | O_CLOEXEC | O_NOCTTY);
	if (descriptor >= 0) {
		write_all(descriptor, "ROG5_QEMU_ASSERT kind=");
		write_all(descriptor, kind);
		write_all(descriptor, " text=");
		write_all(descriptor, text ?: "none");
		write_all(descriptor, " file=");
		write_all(descriptor, file ?: "none");
		write_all(descriptor, " function=");
		write_all(descriptor, function ?: "none");
		write_all(descriptor, "\n");
		count = backtrace(frames, (int)(sizeof(frames) / sizeof(frames[0])));
		if (count > 0)
			backtrace_symbols_fd(frames, count, descriptor);
		(void)close(descriptor);
	}
	_exit(121);
}

__attribute__((constructor)) static void announce_load(void)
{
	static const char marker[] = "ROG5_QEMU_ABORT_TRACE_LOADED\n";
	int descriptor;
	ssize_t written;

	descriptor = open("/dev/console", O_WRONLY | O_CLOEXEC | O_NOCTTY);
	if (descriptor < 0)
		return;
	written = write(descriptor, marker, sizeof(marker) - 1);
	(void)close(descriptor);
	if (written != (ssize_t)(sizeof(marker) - 1))
		_exit(123);
}

__attribute__((noreturn)) void abort(void)
{
	static int entered;
	void *frames[32];
	int descriptor;
	int count;

	if (entered)
		_exit(125);
	entered = 1;
	descriptor = open("/dev/console", O_WRONLY | O_CLOEXEC | O_NOCTTY);
	if (descriptor >= 0) {
		static const char marker[] = "ROG5_QEMU_ABORT_BACKTRACE\n";
		ssize_t written;

		written = write(descriptor, marker, sizeof(marker) - 1);
		if (written != (ssize_t)(sizeof(marker) - 1))
			_exit(124);
		count = backtrace(frames, (int)(sizeof(frames) / sizeof(frames[0])));
		if (count > 0)
			backtrace_symbols_fd(frames, count, descriptor);
		(void)close(descriptor);
	}
	_exit(126);
}

__attribute__((noreturn)) void __assert_fail(
	const char *assertion, const char *file, unsigned int line,
	const char *function)
{
	(void)line;
	trace_failure("glibc-assert", assertion, file, function);
}

__attribute__((noreturn)) void __stack_chk_fail(void)
{
	trace_failure("stack-check", "none", "none", "none");
}

__attribute__((noreturn)) void log_assert_failed(
	const char *text, const char *file, int line, const char *function)
{
	(void)line;
	trace_failure("systemd-assert", text, file, function);
}

void log_assert_failed_return(
	const char *text, const char *file, int line, const char *function)
{
	(void)line;
	trace_failure("systemd-assert-return", text, file, function);
}

__attribute__((noreturn)) void log_assert_failed_unreachable(
	const char *file, int line, const char *function)
{
	(void)line;
	trace_failure("systemd-unreachable", "none", file, function);
}
