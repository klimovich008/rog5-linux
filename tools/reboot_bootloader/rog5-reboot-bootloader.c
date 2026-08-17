// SPDX-License-Identifier: MIT

/* Minimal AArch64 restart2("bootloader") helper for the sealed rescue. */

#define LINUX_REBOOT_MAGIC1 0xFEE1DEADUL
#define LINUX_REBOOT_MAGIC2 672274793UL
#define LINUX_REBOOT_CMD_RESTART2 0xA1B2C3D4UL
#define NR_REBOOT 142UL
#define NR_EXIT 93UL

static __attribute__((noreturn)) void exit_status(unsigned long status)
{
	register unsigned long x0 __asm__("x0") = status;
	register unsigned long x8 __asm__("x8") = NR_EXIT;

	__asm__ volatile("svc #0" : : "r"(x0), "r"(x8) : "memory");
	for (;;)
		__asm__ volatile("wfe");
}

void _start(void)
{
	static const char command[] = "bootloader";
	register unsigned long x0 __asm__("x0") = LINUX_REBOOT_MAGIC1;
	register unsigned long x1 __asm__("x1") = LINUX_REBOOT_MAGIC2;
	register unsigned long x2 __asm__("x2") = LINUX_REBOOT_CMD_RESTART2;
	register const char *x3 __asm__("x3") = command;
	register unsigned long x8 __asm__("x8") = NR_REBOOT;

	__asm__ volatile(
		"svc #0"
		: "+r"(x0)
		: "r"(x1), "r"(x2), "r"(x3), "r"(x8)
		: "memory");

	/* Success never returns. Any return leaves PID 1's fail-closed loop armed. */
	exit_status(111);
}
