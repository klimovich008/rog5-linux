/*
 * One-purpose AArch64 helper for the ROG5 firmware-request-only gate.
 *
 * It performs exactly one openat() of the first render node.  The diagnostic
 * MSM module must reject that open with EUCLEAN after requesting SQE and GMU
 * firmware.  There is deliberately no libc, path argument, retry, or loop.
 */

typedef unsigned long size_t;

enum {
	SYS_OPENAT = 56,
	SYS_WRITE = 64,
	SYS_EXIT = 93,
	AT_FDCWD = -100,
	O_RDWR = 2,
	O_CLOEXEC = 0x80000,
	EUCLEAN = 117,
};

static long syscall1(long number, long argument)
{
	register long x0 __asm__("x0") = argument;
	register long x8 __asm__("x8") = number;

	__asm__ volatile("svc 0"
			 : "+r"(x0)
			 : "r"(x8)
			 : "memory", "cc");
	return x0;
}

static long syscall3(long number, long argument0, long argument1,
		     long argument2)
{
	register long x0 __asm__("x0") = argument0;
	register long x1 __asm__("x1") = argument1;
	register long x2 __asm__("x2") = argument2;
	register long x8 __asm__("x8") = number;

	__asm__ volatile("svc 0"
			 : "+r"(x0)
			 : "r"(x1), "r"(x2), "r"(x8)
			 : "memory", "cc");
	return x0;
}

static long syscall4(long number, long argument0, long argument1,
		     long argument2, long argument3)
{
	register long x0 __asm__("x0") = argument0;
	register long x1 __asm__("x1") = argument1;
	register long x2 __asm__("x2") = argument2;
	register long x3 __asm__("x3") = argument3;
	register long x8 __asm__("x8") = number;

	__asm__ volatile("svc 0"
			 : "+r"(x0)
			 : "r"(x1), "r"(x2), "r"(x3), "r"(x8)
			 : "memory", "cc");
	return x0;
}

static void write_message(const char *message, size_t length)
{
	(void)syscall3(SYS_WRITE, 1, (long)message, (long)length);
}

static __attribute__((noreturn)) void exit_with(long status)
{
	(void)syscall1(SYS_EXIT, status);
	__builtin_unreachable();
}

void _start(void)
{
	static const char render_node[] = "/dev/dri/renderD128";
	static const char expected[] = "OPEN_ERRNO=117\n";
	static const char unexpected[] = "OPEN_ERRNO=unexpected\n";
	long result;
	long error;

	result = syscall4(SYS_OPENAT, AT_FDCWD, (long)render_node,
			  O_RDWR | O_CLOEXEC, 0);
	if (result >= 0) {
		write_message(unexpected, sizeof(unexpected) - 1);
		exit_with(1);
	}

	error = -result;
	if (error == EUCLEAN) {
		write_message(expected, sizeof(expected) - 1);
		exit_with(EUCLEAN);
	}

	write_message(unexpected, sizeof(unexpected) - 1);
	exit_with(error > 0 && error < 256 ? error : 255);
}
