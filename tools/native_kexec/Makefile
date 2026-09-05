CC = clang
OUT ?= rog5-kexec-exec
SOURCE := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))rog5-kexec-exec.c
CFLAGS = --target=aarch64-linux-gnu -fuse-ld=lld -nostdlib -static \
 -fno-builtin -Wall -Wextra -Werror -fno-pic -fno-pie \
 -fno-stack-protector -Wl,-e,_start -Wl,--build-id=none -Wl,-z,noexecstack

$(OUT): $(SOURCE)
	$(CC) $(CFLAGS) $< -o $@

LOG_CC ?= cc
LOG_OUT ?= rog5-exitrd-log
LOG_SOURCE := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))rog5-exitrd-log.c
.PHONY: exitrd-log
exitrd-log:
	$(LOG_CC) -std=c11 -O2 -static -Wall -Wextra -Werror \
	 -fstack-protector-strong -Wl,--build-id=none -Wl,-z,noexecstack \
	 $(LOG_SOURCE) -o $(LOG_OUT)
