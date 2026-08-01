// SPDX-License-Identifier: MIT
#define _GNU_SOURCE

#include <execinfo.h>
#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>

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
