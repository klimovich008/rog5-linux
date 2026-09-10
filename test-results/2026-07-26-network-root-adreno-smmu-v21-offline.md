# Network-root Adreno SMMU v21 offline acceptance

Date: 2026-07-26

Result: **v21 corrects the consumed v20 baseline without changing any kernel,
DTB, initramfs, module, wrapper, or boot-image bit. Pinned Linux 7.1.4 source
proves that the exact OF platform device begins with a NULL override pointer,
sysfs emits that pointer as the seven-byte text `(null)\n`, and normal OF
matching remains enabled. A new read-only checker accepts only that exact
representation; empty, malformed, linked, and nonempty inputs fail. No v21
path writes `driver_override`. The full unchanged-binary verifier and a new
independently verified v21 root pass offline. The phone was not contacted.**

The Adreno SMMU remains **not accepted**. V21 is eligible for at most one
attended RAM-only live cycle with the existing exact-device and rollback
boundaries; it must never be flashed or retried.

## V20 correction

V20 stopped before handoff because its baseline assumed that an unset
`driver_override` would read as an empty line. The live value was `(null)`.
No GPUCC load, `drivers_probe` write, or SMMU operation occurred in that
cycle.

V21 retains the exact one-device reprobe design but replaces the invalid
assumption with a source-pinned and mutation-tested representation check. It
never attempts to clear or alter the override.

## Pinned source contract

Source remains the clean Linux `7.1.4` tree:

- commit: `d9ac316489f4258d389d6298659d5e9c22183400`
- tree: `c796deb1cc54e942f8bb46a2c76a7199e19e5c92`

Newly explicit source identities are:

| Source | SHA-256 |
|---|---|
| `drivers/base/platform.c` | `c1967f53f66da20c515d32ca3242bd6f365b31f2678f7125bf71cc16ed56a258` |
| `include/linux/device.h` | `68ad17f3670b7fcedbfa70e8cab1b2044dff1e7525697efc953527fec2825fbe` |
| `lib/vsprintf.c` | `314241c733f99bf8b45e64c173d78b1449b4da3fdad90a63500166376d2774eb` |
| `drivers/of/platform.c` | `821937acef295d986caa4470166571b0d18cef2a2f9d1a730e1d0cb4cec70131` |

Together with the existing driver-core and ARM SMMU pins, the verifier proves:

1. `of_device_alloc()` obtains the device through
   `platform_device_alloc()`;
2. `platform_device_alloc()` uses `kzalloc()`, leaving the override name
   pointer NULL;
3. `driver_override_show()` passes that pointer to `%s`;
4. the exact kernel formatter maps a NULL string pointer to `(null)`;
5. `device_has_driver_override()` is false for the NULL pointer;
6. `device_match_driver_override()` returns `-1` when no override exists;
7. `platform_match()` then continues to OF matching; and
8. platform `drivers_probe` still resolves one exact device name and calls
   only unbound-device `device_attach()`.

The source verifier and test hashes are:

- verifier:
  `94ae43da4033daec9e6d80cdb0b0c3d0ff9436e6e873241ac97cf7884c86eff4`
- test:
  `9dfdd5b553ff3569d5a3177ca667b92d38f7e5ee51e3775df9565f9f5853d833`

## Fail-first representation suite

The new pure read-only checker is:

`scripts/device/check-adreno-smmu-driver-override-state.sh`

SHA-256:

`884dfcd287dd892ec0698bedaa4475045967459282811da640e48f5f7d503e45`

Its test first failed while the checker did not exist, then passed after the
implementation. It accepts exactly seven bytes, `(null)\n`, and emits
`unset-null-representation`. It rejects:

- an empty file;
- an empty line;
- `(null)` without the newline;
- `(null)` with an extra newline;
- a literal driver name;
- a whitespace-prefixed lookalike; and
- a symlink.

The test SHA-256 is:

`5348d98000865dd52a47ac5eacd4d04d16d2a92da719776e79971a2b040e2703`

Static baseline and probe tests reject the former empty-line check and any
redirection or `tee` path that could alter `driver_override`.

## Target and host boundary

The v21 baseline and probe both invoke the same hash-pinned checker and record:

`driver_override=unset-null-representation`

Their accepted hashes are:

| Control | SHA-256 |
|---|---|
| baseline | `a2eb74c66815a38e2ad3476a80d1fe5ffbc5de2f32a50429a84f2d4c9f3f4e51` |
| probe | `ae5d3f57d8411cd35b0c6265ec7a3f53b826cf1bb96ba651743c694b79c64c07` |
| compound gate | `7d15f897fd7e0beef6089bd20b3de0bce3fc68b6fdc5b832644ccf3bb583fb62` |

All v20 safety properties remain:

- the read-only baseline runs under the original watchdog;
- a 150-second transition watchdog must arm before handoff;
- the independent 90-second probe watchdog must arm before GPUCC and reprobe;
- five seconds of ordinary autoprobe precede any explicit request;
- at most one exact `3da0000.iommu` write to platform `drivers_probe` is
  possible; and
- global timeout extension, broad rescan, force bind, unload, retry, firmware,
  render, and storage paths remain absent.

The host runner stages six exact tmpfs inputs, uses strict pinned SSH, invokes
the compound gate once, logs privately, and never retries. The NFS server
allowlist accepts only the general v1 root and v21; consumed v20 is rejected.

## Unchanged binary verification

The exact temporary-boot image remains:

`artifacts/network-root-v18-adreno-smmu-diagnostic/boot-5.4.210-network-root-stage.avb.img`

Size: `100663296`

SHA-256:

`37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf`

The complete verifier returned:

`PASS exact v18 binary with v21 GPUCC plus exact-device Adreno SMMU control plane; NULL-override exact, consumer-disabled, firmware-free, zero-storage, reproducible, and offline-only`

## Isolated v21 export

PolicyKit created and a separate invocation independently verified:

`/var/lib/rog5-network-root-adreno-smmu-v21`

The root is `root:root:0555`. Its
`/etc/rog5/adreno-smmu-v21-export` seal is `root:root:0444` with SHA-256:

`d5d51ebbbc7d3698da788a9f2de8cc9fa97318059dc68c90993ad0406a64faca`

Verification proves:

- 1,008 module files, matching the accepted base;
- zero A660 SQE, GMU, or ZAP firmware files;
- preserved client authorization and SSH host identity;
- every other accepted-base file and metadata entry unchanged;
- `driver_override_state=UNSET_NULL_REPRESENTATION`;
- `driver_override_write=FORBIDDEN`;
- `smmu_reprobe=EXACT_PLATFORM_DEVICE_ONCE`; and
- `smmu_acceptance=NOT_ACCEPTED`.

The consumed v20 root remains separately preserved as `root:root:0555`, and
its seal remains `root:root:0444`. NFS remained inactive with no export or
mount daemon.

## Live decision

The v20 failure mode is now directly explained by pinned source, reproduced by
the live text, corrected through one read-only helper, and covered by negative
tests. The binary and hardware boundary are otherwise unchanged. This is
sufficient for **at most one new attended v21 RAM-only cycle** under the
existing exact fallback, private evidence, watchdog, and cleanup preflights.

Passing v21 would accept only idle Adreno SMMU registration/runtime suspend.
It would not accept A660 registration, firmware, first DRM open, rendering,
display, suspend, remote Plasma, or persistent installation.
