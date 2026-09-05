# Network-root v20 Adreno SMMU — safe baseline rejection

Date: 2026-07-26

Result: **the one permitted v20 cycle stopped at its read-only baseline
because the verifier treated the kernel's textual `(null)` representation of
an unset platform `driver_override` as a nonempty override. No handoff or
probe action occurred: GPUCC was not loaded, `drivers_probe` was not written,
the SMMU remained unbound, and no firmware, render, or storage path appeared.
Normal fallback reboot and complete host cleanup passed. V20 is consumed and
must not be retried.**

## Exact attended boundary

The cycle used the unchanged manifest-pinned v18-v20 binary through one
temporary `fastboot boot`; nothing was flashed. The image was:

`artifacts/network-root-v18-adreno-smmu-diagnostic/boot-5.4.210-network-root-stage.avb.img`

Size: `100663296`

SHA-256:

`37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf`

The guarded fallback request reached the exact fastboot device, the manifest
and artifact preflight passed, and the isolated v20 NFS service started with
its exact-peer policy. Recovery ACM then accepted one atomic
`confirm-gpucc` request. The known missing-marker race caused the one allowed
identical staging-load replay; execute remained non-retryable and was
transmitted exactly once.

The target reached its exact USB/NFS network root. Strict pinned SSH verified
Linux `7.1.4-g7a5cef0db479`, systemd, OverlayFS, and zero failed units before
the host invoked the compound v20 gate exactly once.

## Baseline stop

The gate stopped immediately with:

`FAIL Adreno SMMU driver_override is not empty`

The original network-root watchdog was still armed. The transition and probe
watchdogs were not armed because the handoff boundary was never reached. The
gate did not:

- disarm the original watchdog;
- load the GPUCC module;
- write `3da0000.iommu` to platform `drivers_probe`;
- bind, reprobe, or otherwise operate the Adreno SMMU;
- request firmware or expose a render node; or
- access a storage path.

A separate read-only diagnosis on that same boot reported:

`PASS v20 baseline diagnosis driver_override=null-representation smmu=unbound gpucc=absent watchdog=armed waiting=0 deferred=0 suppliers=2 storage=0 mounts=0 render=0 firmware=0 failed_units=0 system=running thermal_zones=29 thermal_max_mC=36500`

The complete private gate output remains outside Git in a caller-owned
mode-`0600` evidence file inside a mode-`0700` directory. Device serials,
MAC addresses, boot IDs, credentials, and private evidence are not included
here.

## Source diagnosis

The v20 assumption that an unset `driver_override` reads as an empty line was
wrong for this exact kernel. Pinned Linux `7.1.4` source and the live value
show:

- `driver_override_show()` formats `dev->driver_override.name` with `%s`;
- the kernel formatter emits `(null)` when that pointer is `NULL`;
- `platform_device_alloc()` uses `kzalloc()`, so a fresh platform device
  begins with a `NULL` override pointer;
- `device_has_driver_override()` is false for that `NULL` pointer;
- `device_match_driver_override()` returns `-1` when no override exists; and
- `platform_match()` then continues to normal OF matching.

The observed `(null)` therefore represented the unset, zero-initialized
state, not a driver selection. No v20 control-plane script wrote
`driver_override`.

This is a baseline-verifier defect, not evidence that the SMMU probe failed
or that the device had an unsafe override. The exact-device reprobe path was
never exercised, so v20 neither accepts nor rejects SMMU binding.

## Fallback and cleanup

Because the gate stopped before handoff, the original watchdog remained the
rollback authority. A normal systemd fallback reboot was requested once. The
network-root gadget departed, the bounded NFS service exited, and all of its
runtime state was removed.

The persistent Alpine fallback returned with its exact vendor
kernel/init/ext4 and USB identity. A redacted health query reported:

`PASS fallback health thermal_zones=70 thermal_max_mC=39100 pstore_records=0 project_modules=0`

The privileged host cleanup verifier also passed:

- NFS inactive, with zero exports, listeners, mount daemon, export mount, and
  active NFS threads;
- `ip_nonlocal_bind=0`;
- firewalld and ModemManager active;
- no temporary firewall interface, source, service, port, rich rule, or
  masquerade state;
- the ordinary fallback `/16` profile restored and no diagnostic `/30`
  retained; and
- zero fastboot and ADB devices.

## V21 correction boundary

V20 is consumed and must not be served or retried. A separately versioned v21
control plane must be completed offline before another live decision. It
must:

1. source-pin the platform allocation, override display, kernel string
   formatting, and platform match semantics;
2. accept only the reviewed exact `(null)` representation as the unset state
   on this fresh device;
3. reject every other nonempty override value;
4. never write `driver_override` to clear or alter it;
5. retain the exact one-device `drivers_probe` request and all v20
   watchdog/safety constraints;
6. use a new independently verified root and seal while preserving v20; and
7. disable v20 in every runnable host allowlist before v21 can become
   live-eligible.

GPUCC/CCF remains live-accepted from v17. The Adreno SMMU remains **not
accepted**. A660 registration, first DRM open, firmware loading, GMU resume,
ZAP/SCM authentication, rendering, Mesa/Freedreno, display, suspend, and
accelerated desktop remain locked.
