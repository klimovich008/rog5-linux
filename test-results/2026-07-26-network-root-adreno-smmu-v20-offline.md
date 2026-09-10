# Network-root Adreno SMMU v20 offline acceptance

Date: 2026-07-26
Status: **offline accepted; eligible for at most one attended RAM-only live
cycle; SMMU and GPU acceleration are not yet accepted**

## Purpose

V19 proved that trace-free GPUCC registration completes, but the built-in
Adreno SMMU did not bind after a 30-second settle. V20 keeps every binary bit
from the reproducible v18 artifact and changes only the external diagnostic
control plane. Its single new live action is one exact-name platform-device
probe request after normal deferred probing has already been allowed to run.

V18 and v19 are consumed and remain prohibited from retry.

## Fail-first result

Before implementation, seven targeted contracts failed for the expected
reasons:

- the platform-reprobe source verifier did not exist;
- baseline and probe did not capture the exact `3da0000.iommu` identity;
- the transition watchdog was still 120 seconds;
- the binary bundle did not lock the reprobe source contract; and
- export/server/launcher paths still selected consumed v19.

After implementation, all seven contracts pass, together with the general NFS
host contract and the mocked one-shot launcher test.

## Pinned source proof

The source verifier accepts only Linux commit
`d9ac316489f4258d389d6298659d5e9c22183400`, tree
`c796deb1cc54e942f8bb46a2c76a7199e19e5c92`, and the exact accepted kernel
config. It hash-locks and checks:

- `drivers/base/bus.c`;
- `drivers/base/core.c`;
- `drivers/base/dd.c`;
- `include/linux/device/bus.h`;
- `drivers/iommu/arm/arm-smmu/arm-smmu.c`; and
- `config-7.1.4-network-root`.

The reviewed driver-core path resolves one device with
`bus_find_device_by_name()`, matches its exact name with `sysfs_streq()`, and
calls `device_attach()` only for that unbound device. The verifier rejects a
bus-wide scan, detach/reprobe path, and force attach. The built-in `arm-smmu`
driver has `suppress_bind_attrs=true`, so driver `bind` and `unbind` controls
must remain absent. The accepted config still has a ten-second deferred-probe
timeout; v20 does not alter or extend it.

## Guarded runtime contract

The read-only baseline now requires exactly one unbound platform device named
`3da0000.iommu`, an empty `driver_override`, enabled platform autoprobe, the
root-owned mode-0200 `drivers_probe` endpoint, and absent ARM SMMU force-bind
controls. Without mounting debugfs, it records:

- `waiting_for_supplier` when exposed;
- the exact device's `devices_deferred` entry count when already readable;
- supplier-link count;
- driver state; and
- the existing zero-storage, zero-firmware, zero-render and watchdog state.

The attended probe retains the original rollback watchdog handoff and uses a
90-second independent probe watchdog inside a 150-second transition watchdog.
After exact GPUCC registration succeeds, it waits five seconds for normal
automatic binding. Only if the exact SMMU is still unbound does it write
`3da0000.iommu` once to `/sys/bus/platform/drivers_probe`. There is no global
timeout extension, broad rescan, force bind, unload, retry, firmware, render,
or storage path.

Before any rejection, the probe now directly records dependency state plus
physical-storage count, block-backed mounts, render nodes, A660 firmware
requests, failed units, system state, thermals, and new kernel log lines. A
successful result still requires the one exact ARM SMMU bind, runtime suspend,
disabled GPU/GMU consumers, zero firmware/render/storage/mounts/failed units,
safe thermals, and no new warning or fault.

## Artifact and root verification

The full exact verifier passed:

```text
PASS exact v18 binary with v20 GPUCC plus exact-device Adreno SMMU control plane; consumer-disabled, firmware-free, zero-storage, reproducible, and offline-only
```

The temporary boot image remains unchanged:

```text
SHA256 37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf
```

PolicyKit created and independently verified
`/var/lib/rog5-network-root-adreno-smmu-v20`:

```text
module_files=1008
firmware=0
credentials=preserved
base=unchanged
reprobe=exact-once
```

The root is `root:root:0555`; its
`/etc/rog5/adreno-smmu-v20-export` seal is `root:root:0444`. The NFS allowlist
now accepts only the general v1 root and v20; consumed v18 and v19 are
rejected. NFS remained inactive, firewalld remained active, and the phone was
not contacted.

## Decision

V20 meets the offline prerequisites for exactly one attended temporary-boot
cycle after this checkpoint is committed and pushed. That live cycle remains
non-retryable, must never flash storage, must use a new private evidence
directory, and must end in verified persistent fallback plus complete host
cleanup. A no-bind, warning, fault, unsafe thermal, identity mismatch, storage
appearance, or cleanup failure rejects v20 and keeps A660 registration locked.
