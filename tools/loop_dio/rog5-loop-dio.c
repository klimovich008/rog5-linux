// SPDX-License-Identifier: MIT

/*
 * Minimal AArch64 helper for the persistent-root init: switch an attached,
 * not yet mounted loop device to direct I/O on its backing file.
 *
 *   rog5-loop-dio /dev/loopN BYTES
 *
 * LOOP_SET_BLOCK_SIZE BYTES (the backing filesystem's direct-I/O alignment,
 * 4096 on the phone's UFS), then LOOP_SET_DIRECT_IO 1. The kernel refuses
 * direct I/O while the loop's logical block size is below that alignment,
 * and refuses a block size change while the device is claimed (mounted).
 *
 * Exit status: 0 done, 2 usage, 3 open failed, 4 block size refused,
 * 5 direct I/O refused (the block size change stays; the loop stays
 * buffered and remains usable).
 */

#define NR_IOCTL 29UL
#define NR_OPENAT 56UL
#define NR_EXIT 93UL
#define AT_FDCWD (-100L)
#define O_RDONLY 0L
#define O_CLOEXEC 02000000L
#define LOOP_SET_DIRECT_IO 0x4C08UL
#define LOOP_SET_BLOCK_SIZE 0x4C09UL

static long syscall3(unsigned long number, long a, long b, long c)
{
	register long x0 __asm__("x0") = a;
	register long x1 __asm__("x1") = b;
	register long x2 __asm__("x2") = c;
	register unsigned long x8 __asm__("x8") = number;

	__asm__ volatile("svc #0"
			 : "+r"(x0)
			 : "r"(x1), "r"(x2), "r"(x8)
			 : "memory");
	return x0;
}

static long syscall4(unsigned long number, long a, long b, long c, long d)
{
	register long x0 __asm__("x0") = a;
	register long x1 __asm__("x1") = b;
	register long x2 __asm__("x2") = c;
	register long x3 __asm__("x3") = d;
	register unsigned long x8 __asm__("x8") = number;

	__asm__ volatile("svc #0"
			 : "+r"(x0)
			 : "r"(x1), "r"(x2), "r"(x3), "r"(x8)
			 : "memory");
	return x0;
}

static __attribute__((noreturn)) void exit_status(long status)
{
	syscall3(NR_EXIT, status, 0, 0);
	for (;;)
		__asm__ volatile("wfe");
}

/* "/dev/loop" followed by 1-4 decimal digits. */
static int loop_path(const char *path)
{
	static const char prefix[] = "/dev/loop";
	unsigned long i, digits = 0;

	for (i = 0; prefix[i]; i++)
		if (path[i] != prefix[i])
			return 0;
	for (; path[i]; i++) {
		if (path[i] < '0' || path[i] > '9' || ++digits > 4)
			return 0;
	}
	return digits > 0;
}

/* A power of two from 512 to 65536, plain decimal. */
static long block_bytes(const char *text)
{
	long value = 0;
	unsigned long i;

	for (i = 0; text[i]; i++) {
		if (text[i] < '0' || text[i] > '9' || i >= 5)
			return -1;
		value = value * 10 + (text[i] - '0');
	}
	if (i == 0 || value < 512 || value > 65536 || (value & (value - 1)))
		return -1;
	return value;
}

__attribute__((noreturn, used)) void rog5_main(long *stack)
{
	long argc = stack[0];
	char **argv = (char **)(stack + 1);
	long bytes, fd;

	if (argc != 3 || !loop_path(argv[1]))
		exit_status(2);
	bytes = block_bytes(argv[2]);
	if (bytes < 0)
		exit_status(2);
	fd = syscall4(NR_OPENAT, AT_FDCWD, (long)argv[1], O_RDONLY | O_CLOEXEC, 0);
	if (fd < 0)
		exit_status(3);
	if (syscall3(NR_IOCTL, fd, LOOP_SET_BLOCK_SIZE, bytes) < 0)
		exit_status(4);
	if (syscall3(NR_IOCTL, fd, LOOP_SET_DIRECT_IO, 1) < 0)
		exit_status(5);
	exit_status(0);
}

__asm__(".text\n"
	".global _start\n"
	".type _start, %function\n"
	"_start:\n"
	"\tmov x0, sp\n"
	"\tb rog5_main\n");
