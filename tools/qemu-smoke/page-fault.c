// SPDX-License-Identifier: GPL-2.0-only
/* Bounded anonymous/file-backed COW probe for a generic QEMU kernel, never a phone.
 * Raw syscall adapter follows tools/qemu-smoke/init.c. PROBE_USER_TEST exercises
 * the same data checks under qemu-user; it cannot qualify the guest kernel.
 */
#define PAGES 8192
#define PAGE_SIZE 4096
#define ROUNDS 8
/* arch/arm64/include/uapi/asm/fcntl.h overrides the generic flag value. */
#define ARM64_O_NOFOLLOW 0100000
#ifndef PROBE_BACKING_PATH
#define PROBE_BACKING_PATH "/backing/pages.bin"
#endif
static volatile unsigned char *memory;

static long call(long n, long a, long b, long c, long d, long e)
{
	register long x0 __asm__("x0") = a;
	register long x1 __asm__("x1") = b;
	register long x2 __asm__("x2") = c;
	register long x3 __asm__("x3") = d;
	register long x4 __asm__("x4") = e;
	register long x5 __asm__("x5") = 0; /* mmap file offset; unused otherwise. */
	register long x8 __asm__("x8") = n;
	__asm__ volatile("svc 0" : "+r"(x0)
		: "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5), "r"(x8)
		: "memory", "cc");
	return x0;
}

static void say(const char *s)
{
	long size = 0, done = 0, n;
	while (s[size]) size++;
	while (done < size) {
		n = call(64, 1, (long)s + done, size - done, 0, 0);
		if (n == -4) continue;
		if (n <= 0) return; /* Missing output makes the host oracle fail. */
		done += n;
	}
}

static void number(unsigned long value)
{
	char buf[24];
	unsigned int pos = sizeof(buf) - 1;
	buf[pos] = 0;
	do {
		buf[--pos] = '0' + value % 10;
		value /= 10;
	} while (value);
	say(buf + pos);
}

static unsigned long millis(void)
{
	struct { long seconds, nanos; } now;
	if (call(113, 1, (long)&now, 0, 0, 0) < 0) return 0;
	return now.seconds * 1000UL + now.nanos / 1000000UL;
}

static __attribute__((noreturn)) void end(int status)
{
#ifndef PROBE_USER_TEST
	if (call(172, 0, 0, 0, 0, 0) == 1)
		call(142, 0xfee1dead, 0x28121969, 0x4321fedc, 0, 0);
#endif
	call(94, status, 0, 0, 0, 0);
	for (;;) __asm__ volatile("wfe");
}

static __attribute__((noreturn)) void fail(const char *stage)
{
	say("FAIL page-fault-probe "); say(stage); say("\n"); end(1);
}

#ifdef PROBE_FILE_BACKED
static int original_page(volatile unsigned char *data, unsigned int page)
{
	unsigned long off = page * PAGE_SIZE;
	return data[off] == 0x31 && data[off + 1] == page % 251 &&
		data[off + 2048] == 0x5c && data[off + 4095] == 0xc5;
}
#endif

static void phase(unsigned int round, const char *name)
{
	say("OBSERVE page-fault-round="); number(round + 1);
	say(" phase="); say(name); say(" monotonic_ms=");
	number(millis()); say("\n");
}

void _start(void)
{
	unsigned long started, finish;
	long pid, waited, mapped;
	int status;
#ifdef PROBE_FILE_BACKED
	long backing;
#endif
#ifndef PROBE_USER_TEST
	long fd;
	if (call(172, 0, 0, 0, 0, 0) != 1) end(1);
	if (call(40, (long)"devtmpfs", (long)"/dev",
		 (long)"devtmpfs", 0, 0) < 0) fail("mount-console");
	fd = call(56, -100, (long)"/dev/console", 2, 0, 0);
	if (fd < 0) fail("open-console");
	for (long i = 0; i < 3; i++)
		if (fd != i && call(24, fd, i, 0, 0, 0) < 0)
			fail("dup-console");
#endif
#ifdef PROBE_FILE_BACKED
#ifndef PROBE_USER_TEST
	if (call(40, (long)"probe", (long)"/backing", (long)"9p", 1,
		 (long)"trans=virtio,version=9p2000.L,msize=262144") < 0)
		fail("mount-backing-readonly");
#endif
	backing = call(56, -100, (long)PROBE_BACKING_PATH, ARM64_O_NOFOLLOW, 0, 0);
	if (backing < 0) fail("open-backing"); /* O_RDONLY | O_NOFOLLOW */
	if (call(62, backing, 0, 2, 0, 0) != PAGES * PAGE_SIZE)
		fail("backing-size");
	say("OBSERVE page-fault-backing=file-private\n");
#else
	say("OBSERVE page-fault-backing=anonymous\n");
#endif
	started = millis();
	if (!started) fail("clock-start");
	say("BEGIN page-fault-probe pages=8192 rounds=8\n");
	for (unsigned int round = 0; round < ROUNDS; round++) {
		phase(round, "private-write");
#ifdef PROBE_FILE_BACKED
		mapped = call(222, 0, PAGES * PAGE_SIZE, 3, 2, backing);
#else
		/* Fresh private anonymous pages. The retained minimal kernel disables
		 * CONFIG_ADVISE_SYSCALLS, so do not depend on MADV_DONTNEED.
		 */
		mapped = call(222, 0, PAGES * PAGE_SIZE, 3, 0x22, -1);
#endif
		if (mapped < 0) fail("map-pages");
		memory = (volatile unsigned char *)mapped;
		for (unsigned int p = 0; p < PAGES; p++) {
			unsigned long off = p * PAGE_SIZE;
#ifdef PROBE_FILE_BACKED
			if (!original_page(memory, p)) fail("file-page");
#else
			if (memory[off] || memory[off + 1] ||
			    memory[off + 2048] || memory[off + 4095])
				fail("anonymous-zero");
#endif
			memory[off] = 1 + p % 127;
			memory[off + 1] = 0;
			memory[off + 2048] = 0x55;
			memory[off + 4095] = 0xaa;
		}
		phase(round, "fork-cow");
		pid = call(220, 17, 0, 0, 0, 0); /* clone(SIGCHLD), private VM. */
		if (pid < 0) fail("clone");
		if (!pid) {
			for (unsigned int p = 0; p < PAGES; p++) {
				unsigned long off = p * PAGE_SIZE;
				if (memory[off] != 1 + p % 127) fail("child-before");
				memory[off] = 0xfe; /* Forces copy-on-write. */
				if (memory[off] != 0xfe || memory[off + 1] ||
				    memory[off + 2048] != 0x55 ||
				    memory[off + 4095] != 0xaa)
					fail("child-copy");
			}
			end(0);
		}
		status = -1;
		do { waited = call(260, pid, (long)&status, 0, 0, 0); }
		while (waited == -4);
		if (waited != pid || status != 0) fail("child-exit");
#ifdef PROBE_CORRUPT_PARENT
		memory[0] = 0xfe; /* Oracle mutation, only in the user-mode test. */
#endif
		for (unsigned int p = 0; p < PAGES; p++) {
			unsigned long off = p * PAGE_SIZE;
			if (memory[off] != 1 + p % 127 || memory[off + 1] ||
			    memory[off + 2048] != 0x55 || memory[off + 4095] != 0xaa)
				fail("parent-isolation");
		}
		if (call(215, (long)memory, PAGES * PAGE_SIZE, 0, 0, 0) < 0)
			fail("unmap-pages");
#ifdef PROBE_FILE_BACKED
		phase(round, "backing-check");
		mapped = call(222, 0, PAGES * PAGE_SIZE, 1, 2, backing);
		if (mapped < 0) fail("remap-backing");
		for (unsigned int p = 0; p < PAGES; p++)
			if (!original_page((volatile unsigned char *)mapped, p))
				fail("backing-isolation");
		if (call(215, mapped, PAGES * PAGE_SIZE, 0, 0, 0) < 0)
			fail("unmap-backing");
#endif
		say("PASS page-fault-round="); number(round + 1); say("\n");
	}
#ifdef PROBE_FILE_BACKED
	if (call(57, backing, 0, 0, 0, 0) < 0) fail("close-backing");
#endif
	finish = millis();
	if (finish < started || !finish) fail("clock-end");
	say("PASS page-fault-probe pages=8192 rounds=8 elapsed_ms=");
	number(finish - started); say("\n");
	end(0);
}
