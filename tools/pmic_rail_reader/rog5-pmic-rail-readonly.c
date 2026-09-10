// SPDX-License-Identifier: GPL-2.0-only
/* Fixed PM8350 metadata/config snapshot via pread, never a whole register dump. */
#define NR_OPENAT 56
#define NR_CLOSE 57
#define NR_WRITE 64
#define NR_PREAD64 67
#define NR_EXIT 93
#define READ_FLAGS (0x20000 | 0x80000) /* O_RDONLY | O_NOFOLLOW | O_CLOEXEC */

#ifdef READER_TEST
extern long syscall4(long, long, long, long, long);
#else
static long syscall4(long number, long a, long b, long c, long d)
{
	register long x8 __asm__("x8") = number;
	register long x0 __asm__("x0") = a;
	register long x1 __asm__("x1") = b;
	register long x2 __asm__("x2") = c;
	register long x3 __asm__("x3") = d;
	__asm__ volatile("svc 0" : "+r"(x0) : "r"(x8), "r"(x1), "r"(x2),
			 "r"(x3) : "memory");
	return x0;
}
#endif

static const char hex[] = "0123456789abcdef";
static const char map[] = "/sys/kernel/debug/regmap/0-01/registers";

static unsigned int length(const char *s)
{
	unsigned int n = 0;
	while (s[n])
		n++;
	return n;
}

static int emit(const char *s, unsigned int n)
{
	while (n) {
		long ret = syscall4(NR_WRITE, 1, (long)s, n, 0);
		if (ret <= 0 || (unsigned long)ret > n)
			return -1;
		s += ret;
		n -= ret;
	}
	return 0;
}

static int metadata(const char *path, const char *expected, int nul_list)
{
	char buf[256];
	unsigned int n = length(expected), i;
	long fd, count;

	fd = syscall4(NR_OPENAT, -100, (long)path, READ_FLAGS, 0);
	if (fd < 0)
		return 0;
	count = syscall4(NR_PREAD64, fd, (long)buf, sizeof(buf), 0);
	syscall4(NR_CLOSE, fd, 0, 0, 0);
	if (count < (long)n || (!nul_list && count != (long)n))
		return 0;
	for (i = 0; i < n; i++)
		if (buf[i] != expected[i])
			return 0;
	return !nul_list || (count > (long)n && !buf[n]);
}

static int digit(char c)
{
	unsigned int i;
	for (i = 0; i < 16; i++)
		if (hex[i] == c)
			return i;
	return -1;
}

/* This exact kernel's 16-bit/8-bit contiguous regmap prints nine-byte lines.
 * pread never falls back to reading/discarding intervening PMIC registers.
 */
static int reg_byte(long fd, unsigned int reg)
{
	char line[9];
	int high, low;
	unsigned int i;
	long n = syscall4(NR_PREAD64, fd, (long)line, sizeof(line), reg * 9UL);

	if (n != (long)sizeof(line))
		return -2;
	for (i = 0; i < 4; i++)
		if (line[i] != hex[(reg >> (12 - 4 * i)) & 15])
			return -2;
	if (line[4] != ':' || line[5] != ' ' || line[8] != '\n')
		return -2;
	if (emit(line, sizeof(line)))
		return -2;
	if (line[6] == 'X' && line[7] == 'X')
		return -1; /* Read denied/error, not an absent or disabled regulator. */
	high = digit(line[6]);
	low = digit(line[7]);
	return high < 0 || low < 0 ? -2 : (high << 4) | low;
}

static int snapshot(void)
{
	static const unsigned int config[] = { 1, 3, 0x40, 0x41, 0x45, 0x46 };
	unsigned int base, i;
	int type, subtype, ret = 0;
	long fd;

	if (!metadata("/sys/firmware/devicetree/base/compatible", "asus,rog-phone5", 1) ||
	    !metadata("/proc/sys/kernel/osrelease", "7.1.4-g359318de534f\n", 0) ||
	    !metadata("/sys/firmware/devicetree/base/soc@0/spmi@c440000/pmic@1/compatible",
		      "qcom,pm8350", 1) ||
	    !metadata("/sys/kernel/debug/regmap/0-01/name", "pmic-spmi\n", 0) ||
	    !metadata("/sys/kernel/debug/regmap/0-01/range", "0-ffff\n", 0))
		return 2;
	fd = syscall4(NR_OPENAT, -100, (long)map, READ_FLAGS, 0);
	if (fd < 0)
		return 3;
	if (reg_byte(fd, 0x104) != 0x51 || reg_byte(fd, 0x105) < 0) {
		ret = 4;
		goto close;
	}
	for (base = 0x1400; base <= 0x3f00; base += 0x100) {
		type = reg_byte(fd, base + 4);
		subtype = reg_byte(fd, base + 5);
		if (type == -2 || subtype == -2) {
			ret = 5;
			goto close;
		}
		/* Only BUCK/HFSMPS_510: offsets from the exact kernel driver.
		 * These are programmed configuration values, not ADC measurements.
		 */
		if (type != 3 || subtype != 0x0a)
			continue;
		for (i = 0; i < sizeof(config) / sizeof(config[0]); i++)
			if (reg_byte(fd, base + config[i]) == -2) {
				ret = 5;
				goto close;
			}
	}
close:
	syscall4(NR_CLOSE, fd, 0, 0, 0);
	return ret;
}

#ifndef READER_TEST
__attribute__((noreturn)) void _start(void)
{
	int ret = snapshot();
	syscall4(NR_EXIT, ret, 0, 0, 0);
	__builtin_unreachable();
}
#endif
