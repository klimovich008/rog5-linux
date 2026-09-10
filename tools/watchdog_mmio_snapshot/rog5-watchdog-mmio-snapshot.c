// SPDX-License-Identifier: GPL-2.0-only
#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/mman.h>
#include <unistd.h>

#ifndef ROG5_MMIO_PATH
#define ROG5_MMIO_PATH "/dev/mem"
#endif

#ifndef ROG5_MMIO_BASE
#define ROG5_MMIO_BASE 0x17c10000
#endif

#define ROG5_MMIO_SIZE 0x1000
#define WDT_EN 0x08
#define WDT_STS 0x0c
#define WDT_BARK_TIME 0x10
#define WDT_BITE_TIME 0x14

static sigjmp_buf fault_return;
static volatile sig_atomic_t fault_signal;

static void fault_handler(int signal_number)
{
	fault_signal = signal_number;
	siglongjmp(fault_return, 1);
}

static int install_fault_handler(int signal_number)
{
	struct sigaction action = {
		.sa_handler = fault_handler,
	};

	sigemptyset(&action.sa_mask);
	return sigaction(signal_number, &action, NULL);
}

int main(int argc, char **argv)
{
	volatile uint32_t *registers;
	void *mapping;
	uint32_t en;
	uint32_t sts;
	uint32_t bark;
	uint32_t bite;
	int fd;

	(void)argv;
	if (argc != 1)
		return 64;

	fd = open(ROG5_MMIO_PATH, O_RDONLY | O_CLOEXEC | O_SYNC);
	if (fd < 0) {
		fprintf(stderr, "open:%d\n", errno);
		return 2;
	}

	mapping = mmap(NULL, ROG5_MMIO_SIZE, PROT_READ, MAP_SHARED, fd,
		       ROG5_MMIO_BASE);
	if (mapping == MAP_FAILED) {
		fprintf(stderr, "mmap:%d\n", errno);
		close(fd);
		return 3;
	}

	if (install_fault_handler(SIGBUS) || install_fault_handler(SIGSEGV)) {
		fprintf(stderr, "signal:%d\n", errno);
		munmap(mapping, ROG5_MMIO_SIZE);
		close(fd);
		return 5;
	}

	if (sigsetjmp(fault_return, 1)) {
		fprintf(stderr, "fault:%d\n", fault_signal);
		munmap(mapping, ROG5_MMIO_SIZE);
		close(fd);
		return 4;
	}

	registers = mapping;
	en = registers[WDT_EN / sizeof(*registers)];
	sts = registers[WDT_STS / sizeof(*registers)];
	bark = registers[WDT_BARK_TIME / sizeof(*registers)];
	bite = registers[WDT_BITE_TIME / sizeof(*registers)];

	printf("wdt-r32765-e%08" PRIx32 "-s%08" PRIx32
	       "-b%08" PRIx32 "-i%08" PRIx32 "\n",
	       en, sts, bark, bite);
	munmap(mapping, ROG5_MMIO_SIZE);
	close(fd);
	return 0;
}
