// SPDX-License-Identifier: MIT

/* Execute an already loaded kernel after systemd/exitramfs storage teardown.
 * No libc, filesystem, dynamic loader, image loading or retry is involved.
 */
#define LINUX_REBOOT_MAGIC1 0xFEE1DEADUL
#define LINUX_REBOOT_MAGIC2 672274793UL
#define LINUX_REBOOT_CMD_KEXEC 0x45584543UL
#define NR_REBOOT 142UL
#define NR_EXIT 93UL

void _start(void)
{
	register unsigned long x0 __asm__("x0") = LINUX_REBOOT_MAGIC1;
	register unsigned long x1 __asm__("x1") = LINUX_REBOOT_MAGIC2;
	register unsigned long x2 __asm__("x2") = LINUX_REBOOT_CMD_KEXEC;
	register unsigned long x3 __asm__("x3") = 0;
	register unsigned long x8 __asm__("x8") = NR_REBOOT;

	__asm__ volatile("svc #0" : "+r"(x0)
			 : "r"(x1), "r"(x2), "r"(x3), "r"(x8) : "memory");
	/* A successful handoff never returns. Preserve common errno values for
	 * exitramfs evidence; 111 also denotes other/invalid returns. Never retry.
	 */
	long result = (long)x0;
	x0 = result < 0 && result >= -125 ? (unsigned long)-result : 111;
	x8 = NR_EXIT;
	__asm__ volatile("svc #0" : : "r"(x0), "r"(x8) : "memory");
	for (;;)
		__asm__ volatile("wfe");
}
