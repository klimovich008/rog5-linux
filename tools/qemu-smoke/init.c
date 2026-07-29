// SPDX-License-Identifier: GPL-2.0-only

#define AT_FDCWD (-100)
#define O_WRONLY 1
#define SYS_OPENAT 56
#define SYS_WRITE 64
#define SYS_REBOOT 142
#define REBOOT_MAGIC1 0xfee1dead
#define REBOOT_MAGIC2 0x28121969
#define REBOOT_POWER_OFF 0x4321fedc

static long syscall4(long number, long first, long second, long third,
		     long fourth)
{
	register long x0 __asm__("x0") = first;
	register long x1 __asm__("x1") = second;
	register long x2 __asm__("x2") = third;
	register long x3 __asm__("x3") = fourth;
	register long x8 __asm__("x8") = number;

	__asm__ volatile("svc 0"
			 : "+r"(x0)
			 : "r"(x1), "r"(x2), "r"(x3), "r"(x8)
			 : "memory");
	return x0;
}

void _start(void)
{
	static const char console[] = "/dev/console";
	static const char message[] =
		"PASS qemu-system arm64 initramfs boot\n";
	long descriptor;

	descriptor = syscall4(SYS_OPENAT, AT_FDCWD, (long)console,
			      O_WRONLY, 0);
	if (descriptor < 0)
		descriptor = 1;
	syscall4(SYS_WRITE, descriptor, (long)message, sizeof(message) - 1, 0);
	syscall4(SYS_REBOOT, REBOOT_MAGIC1, REBOOT_MAGIC2,
		 REBOOT_POWER_OFF, 0);
	for (;;)
		__asm__ volatile("wfe");
}
