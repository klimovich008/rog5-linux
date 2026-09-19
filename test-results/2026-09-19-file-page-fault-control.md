# Read-only 9P page-fault control — 2026-09-19

**Both file-backed kernel controls PASS; full startup stall NOT REPRODUCED.**
This is generic ARM64 VM evidence, not Denial rendering or ROG5 hardware proof.
S06/R01 FAIL and mobile physical NOT RUN remain unchanged. No phone operation,
candidate, signing, admission, claim or protected-storage mutation occurred.

Starting source/tree: `9603751563933b9dab8233d8310bae7827f0b2dd` /
`d10bb936377af1583c749e7383d3c0f494f19f48`. The community audit was committed
separately as `ac09b52f`. Compiled and tested source is
`11b40249f5fd3212dd9f6d794284d01a58802bd6`; its exact tree and tool identities
are in the [qualification record](2026-09-19-file-page-fault-control-qualification.json).
The original dirty checkout and previously compiled phone artifacts were preserved.

## Executed behavior

`tools/qemu-smoke/page-fault.c` now supports a read-only synthetic backing file.
Each of eight rounds privately maps 32 MiB, checks four sentinels per 4 KiB page,
writes private data, forks one child, checks child copying and parent isolation,
unmaps, and remaps the backing file read-only to check the original sentinels.
These guest checks sample bytes; the host additionally streams a SHA256 over
all backing-file bytes before and after execution and compares metadata excluding
access time. The backing directory contains no newly created server metadata.

The first negative test failed: opening a symlink unexpectedly succeeded.
The raw flag was the generic `O_NOFOLLOW` value, which ARM64 interprets as
`O_LARGEFILE`. The exact pinned kernel's `arch/arm64/include/uapi/asm/fcntl.h`
defines `O_NOFOLLOW` as octal `0100000`. Correcting that value makes the actual
ARM64 user-mode program refuse the symlink. Initial failing source and logs are
retained under private `rog5-file-page-fault-control-20260919-r1`.

Final user-mode checks pass anonymous and file-backed positive cases; intentional
parent corruption, missing file, truncated file and symlink each produce the
expected failure stage and exit1. Seven clang/LLD variants compile with
`-Werror -Wall -Wextra`; six user-mode invocations execute. qemu-user exercises
the host kernel and is distinct from the following full-system executions.

| Kernel control | Guest workload | Host command plus cleanup | Result |
| --- | --- | --- | --- |
| Normal | 4372 ms | 5.750 s | Eight rounds; MOPS advertised; no RCU/panic; normal poweroff |
| `arm64.nomops` | 4585 ms | 5.948 s | Eight rounds; MOPS absent; no RCU/panic; normal poweroff |

Both use the same retained Linux7.1.4 Image, QEMU8.2.2 container, max CPU,
two guest CPUs, 1GiB guest RAM and single-thread TCG. Limits remain 2GiB host
container memory/no swap allowance, two-CPU quota, 64 tasks, 120-second command
deadline and 8MiB serial-log bound. Network is disabled. Inputs and the 9P export
are read-only. This adds one virtio-9P export and explicitly uses modern virtio
MMIO, matching the full harness setting. No render node or Arch runtime is
exposed: the 32MiB file is a deterministic synthetic fixture, not a runtime file.
One run per mode is not a performance comparison or general correctness proof.

## Identities and reproduction

- Linux source: `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`, clean on recheck.
- Image SHA256: `2b1c8d95f54dda28e772df82be54af7508b2ce84183f1b0024a7f14e3d5ce0fc`.
- Probe executable, 5384 bytes: `4cb080c8251ca4421db74862378560a578badfb9ca291a31028f3cdaa68f597f`.
- Backing file, 33554432 bytes: `84fea915b6ccd6f7a5ceadac35c9223a5fcde8d97b90cdc230a7b1f74e806c62`.

The qualification JSON records every compile and VM command, time, output hash,
preflight result, exact source and tool identities. Private final evidence is
`rog5-file-page-fault-control-20260919-r2`; use fresh output directories rather
than replaying retained wrappers. Compile with `PROBE_FILE_BACKED` and the
recorded freestanding ARM64 flags. The default guest file is `/backing/pages.bin`;
include empty `/dev` and `/backing` directories in the initramfs. The synthetic
file contains 8192 initially zeroed pages, with offsets0/1/2048/4095 set to
0x31, page-index modulo251, 0x5c, 0xc5 respectively. `PROBE_USER_TEST` omits
VM-only mount/poweroff behavior; `PROBE_BACKING_PATH` selects a host fixture.
The wrapper uses the existing bounded executor, cleanup and RCU/poweroff oracle.

## Interpretation and next action

The small anonymous and file-backed controls both pass in both MOPS modes.
They do not repair or explain the retained full-runtime RCU self-stall, and
must not be used to justify disabling MOPS by default. The next discriminating
experiment is a bounded full-runtime startup-only comparison with explicit
nomops control, preserving kernel, runtime bytes, resources and deadlines.
Interactive Denial, portals and application acceptance remain incomplete.

This turn is progress: actual read-only 9P/COW execution now narrows the failure
boundary, and a caught ARM64 ABI error is corrected. Reuse this fast control for
future mapping changes; do not repeatedly rebuild Denial/Flutter or run a broad
tier to discover basic syscall/ABI problems. Focused executions preceded the
single final active tier. Historical failures remain unchanged.

Final local active tier: **111 PASS, 0 FAIL/BLOCKED/SKIPPED, 255 NOT_SELECTED**,
181.819s; service-reported peak490.9MiB and0swap. Three optional
historical subchecks are skipped separately. These are personally executed host
checks on source11b40249, not imported CI or phone results.
