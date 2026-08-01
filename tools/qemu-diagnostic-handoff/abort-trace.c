// SPDX-License-Identifier: MIT
#define _GNU_SOURCE

#include <dlfcn.h>
#include <execinfo.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <ucontext.h>
#include <unistd.h>

static int (*real_sigaction)(int, const struct sigaction *,
			     struct sigaction *);

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

#if defined(__aarch64__)
static void write_hex(int descriptor, uintptr_t value)
{
	static const char digits[] = "0123456789abcdef";
	char encoded[2 + sizeof(value) * 2 + 2];
	size_t index = sizeof(encoded);

	encoded[--index] = '\0';
	encoded[--index] = '\n';
	for (size_t count = 0; count < sizeof(value) * 2; count++) {
		encoded[--index] = digits[value & 0xfU];
		value >>= 4;
	}
	encoded[--index] = 'x';
	encoded[--index] = '0';
	write_all(descriptor, encoded + index);
}
#endif

static void trace_trap(int signal_number, siginfo_t *information, void *context)
{
	int descriptor;

	(void)signal_number;
	(void)information;
	descriptor = open("/dev/console", O_WRONLY | O_CLOEXEC | O_NOCTTY);
	if (descriptor >= 0) {
		write_all(descriptor, "ROG5_QEMU_TRAP_CONTEXT\n");
#if defined(__aarch64__)
		ucontext_t *machine = context;
		uintptr_t frame = (uintptr_t)machine->uc_mcontext.regs[29];

		write_all(descriptor, "pc=");
		write_hex(descriptor, (uintptr_t)machine->uc_mcontext.pc);
		write_all(descriptor, "lr=");
		write_hex(descriptor, (uintptr_t)machine->uc_mcontext.regs[30]);
		write_all(descriptor, "fp=");
		write_hex(descriptor, frame);
		for (unsigned int depth = 0; depth < 24 && frame != 0; depth++) {
			const uintptr_t *record = (const uintptr_t *)frame;
			uintptr_t previous = record[0];

			write_hex(descriptor, record[1]);
			if (previous <= frame || previous - frame > 1024 * 1024)
				break;
			frame = previous;
		}
#else
		(void)context;
#endif
		(void)close(descriptor);
	}
	_exit(120);
}

int sigaction(int signal_number, const struct sigaction *action,
	      struct sigaction *previous)
{
	int result;

	if (real_sigaction == NULL)
		_exit(117);
	result = real_sigaction(signal_number, action, previous);
	if (result < 0)
		return -1;
	if (signal_number == SIGTRAP && action != NULL &&
	    action->sa_handler == SIG_DFL) {
		struct sigaction tracing = {
			.sa_sigaction = trace_trap,
			.sa_flags = SA_SIGINFO | SA_RESETHAND,
		};

		if (sigemptyset(&tracing.sa_mask) < 0 ||
		    real_sigaction(SIGTRAP, &tracing, NULL) < 0)
			_exit(119);
	}
	return 0;
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
	void *resolved;
	int descriptor;
	ssize_t written;

	resolved = dlsym(RTLD_NEXT, "sigaction");
	if (resolved == NULL || sizeof(resolved) != sizeof(real_sigaction))
		_exit(118);
	memcpy(&real_sigaction, &resolved, sizeof(real_sigaction));
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
