// SPDX-License-Identifier: GPL-2.0-only
/* Offline QEMU guest PID 1. Never execute on a physical device. */
#define AT_FDCWD (-100)

static long call(long n, long a, long b, long c, long d, long e)
{
	register long x0 __asm__("x0") = a;
	register long x1 __asm__("x1") = b;
	register long x2 __asm__("x2") = c;
	register long x3 __asm__("x3") = d;
	register long x4 __asm__("x4") = e;
	register long x8 __asm__("x8") = n;

	__asm__ volatile("svc 0" : "+r"(x0)
		: "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x8)
		: "memory");
	return x0;
}

static void say(const char *s)
{
	long n = 0;

	while (s[n])
		n++;
	call(64, 1, (long)s, n, 0, 0);
}

static void poweroff(void)
{
	call(142, 0xfee1dead, 0x28121969, 0x4321fedc, 0, 0);
	for (;;)
		__asm__ volatile("wfe");
}

static void check(long result, const char *stage)
{
	if (result >= 0)
		return;
	say("FAIL guest-init: ");
	say(stage);
	say("\n");
	poweroff();
}

static void mountfs(const char *source, const char *target,
		    const char *type, long flags, const char *data)
{
	check(call(40, (long)source, (long)target, (long)type, flags,
		   (long)data), target);
}

void _start(void)
{
	static char *const argv[] = { "/usr/bin/bash", "/run/guest.sh", 0 };
	static char *const env[] = { "PATH=/usr/bin", "HOME=/tmp",
		"LANG=C", "TERM=linux", 0 };
	long pid, fd;
	int status = -1;

	fd = call(56, AT_FDCWD, (long)"/dev/console", 2, 0, 0);
	check(fd, "console");
	for (long i = 0; i < 3; i++)
		if (fd != i)
			check(call(24, fd, i, 0, 0, 0), "dup console");
	mountfs("rootfs", "/sysroot", "9p", 1,
		"trans=virtio,version=9p2000.L,msize=262144");
	mountfs("proc", "/sysroot/proc", "proc", 0, "");
	mountfs("sysfs", "/sysroot/sys", "sysfs", 0, "");
	mountfs("devtmpfs", "/sysroot/dev", "devtmpfs", 0, "");
	mountfs("tmpfs", "/sysroot/tmp", "tmpfs", 0, "mode=1777,size=256m");
	mountfs("/stage", "/sysroot/run", "", 4096, "");
	mountfs("payload", "/sysroot/run/payload", "9p", 1,
		"trans=virtio,version=9p2000.L,msize=262144");
	check(call(34, AT_FDCWD, (long)"/sysroot/dev/pts", 0755, 0, 0),
		"mkdir dev/pts");
	mountfs("devpts", "/sysroot/dev/pts", "devpts", 0,
		"newinstance,ptmxmode=0666,mode=0620");
	pid = call(220, 17, 0, 0, 0, 0); /* clone(SIGCHLD) */
	check(pid, "clone");
	if (!pid) {
		check(call(51, (long)"/sysroot", 0, 0, 0, 0), "chroot");
		check(call(49, (long)"/", 0, 0, 0, 0), "chdir");
		check(call(221, (long)argv[0], (long)argv, (long)env, 0, 0),
			"exec guest script");
	}
	check(call(260, pid, (long)&status, 0, 0, 0), "wait guest");
	say(status == 0 ? "PASS guest-script exited cleanly\n" :
		"FAIL guest-script exit status\n");
	poweroff();
}
