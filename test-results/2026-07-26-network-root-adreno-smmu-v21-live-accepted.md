# Network-root Adreno SMMU v21 — live acceptance

Date: 2026-07-26

Result: **PASS for the idle Adreno SMMU foundation. The one permitted v21
RAM-only cycle loaded the already accepted GPUCC module, issued exactly one
exact-device platform reprobe, bound `3da0000.iommu` to `arm-smmu`, reached
runtime suspend, and retained zero firmware, render nodes, physical storage,
block-backed mounts, and failed units. No new warning, fault, or fatal
signature appeared. Normal reboot restored the exact persistent Alpine
fallback, and complete host cleanup passed. Nothing was flashed.**

V21 is consumed and must not be rerun. This accepts only idle Adreno SMMU
registration and runtime suspend. It does not yet accept A660 registration,
firmware, first DRM open, rendering, display, suspend, remote Plasma, or a
persistent installation.

## Reviewed checkpoint

The live cycle started from repository checkpoint:

`327dfb12142fabb616ffa91fdcf84dc74654e4ba`

The exact temporary-boot image was:

`artifacts/network-root-v18-adreno-smmu-diagnostic/boot-5.4.210-network-root-stage.avb.img`

Size: `100663296`

SHA-256:

`37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf`

The root-owned mode-`0555` v21 export independently verified immediately
before the cycle with 1,008 modules, zero A660 firmware, preserved credentials,
an unchanged accepted base, and exact
`driver_override=unset-null-representation` control-plane hashes.

Git was clean and synchronized with the remote branch. The persistent fallback
preflight passed its exact kernel, BusyBox init, compatible, ext4 root, zero
project modules, zero pstore records, zero current fatal signatures, and safe
thermal checks. Firewalld and ModemManager were active, NFS was inactive, and
all temporary network/firewall state was absent.

## Atomic transition

One guarded `RESTART2("bootloader")` request reached the exact fastboot
device. Manifest and product preflight passed. ModemManager was stopped only
for the attended ACM window, and the v21-only exact-peer NFSv4.2 server started.

Exactly one temporary `fastboot boot` was issued; no flash command was used.
Recovery ACM became ready. The `confirm-gpucc` helper was invoked once:

1. the known missing-marker race caused the one tested, identical load replay;
2. the payload hashes passed;
3. execute remained non-retryable; and
4. exactly one `kexec -e` was transmitted.

Linux `7.1.4-g7a5cef0db479`, systemd, the exact USB/NFS network root, and
strict pinned SSH then passed read-only checks with OverlayFS, zero physical
storage, and zero failed units.

## Read-only baseline

The compound gate was invoked exactly once. Before handoff it reported:

`PASS Adreno-SMMU baseline storage=0 mounts=0 firmware=0 render=0 failed_units=0 thermal_zones=29 thermal_max_mC=37100 module_files=1008 pstore_records=1 watchdog=armed smmu=unbound smmu_name=3da0000.iommu driver_override=unset-null-representation waiting_for_supplier=0 deferred_entries=0 supplier_links=2 drivers_probe=locked`

The one pstore record was already present before GPUCC or SMMU action. The
current kernel log had no fatal or IOMMU-fault signature, and the persistent
fallback exposed zero pstore records after the cycle.

The exact seven-byte override checker passed. The SMMU was unbound, platform
autoprobe was enabled, the exact root-owned mode-`0200` `drivers_probe` control
was available, and ARM SMMU force-bind files remained absent.

## Watchdog handoff and GPUCC

After baseline acceptance:

1. the 150-second transition watchdog armed;
2. the original network-root watchdog was frozen, terminated, and marked
   disarmed;
3. the independent 90-second probe watchdog armed; and
4. the exact external GPUCC module loaded once.

GPUCC completed its accepted bounded sequence:

| Target time | Marker |
|---:|---|
| 218.534663 | `map-complete` |
| 218.542861 | `pll0-begin` |
| 218.550878 | `pll0-complete` |
| 218.559142 | `pll1-begin` |
| 218.567155 | `pll1-complete` |
| 218.575417 | `registration-begin` |
| 218.591813 | `registration-complete ret=0` |
| 218.602439 | `insmod returned` |

Five seconds of ordinary autoprobe left the exact SMMU unbound:

`EVIDENCE dependency phase=after-gpucc-auto smmu_name=3da0000.iommu driver=unbound driver_override=unset-null-representation waiting_for_supplier=0 deferred_entries=0 supplier_links=2 exact_reprobe=0`

## Exact-device reprobe result

At target time 223.811172 the probe issued its only allowed request:

`3da0000.iommu`

to platform `drivers_probe`. It returned at 223.877395. The immediate state
was:

`EVIDENCE dependency phase=after-exact-reprobe smmu_name=3da0000.iommu driver=arm-smmu driver_override=unset-null-representation waiting_for_supplier=unavailable deferred_entries=0 supplier_links=1 exact_reprobe=1`

After the full 30-second settle, the device remained bound to `arm-smmu`.
The exact bind count was one, and its runtime status was `suspended`.

Final direct evidence was:

`EVIDENCE safety phase=success storage=0 mounts=0 render=0 firmware_requests=0 failed_units=0 system=running`

The accepted probe marker was:

`PASS Adreno-SMMU probe GPUCC=1 SMMU=1 runtime=suspended firmware=0 render=0 storage=0 mounts=0 failed_units=0 thermal_zones=29 thermal_max_mC=36200 exact_reprobe=1 driver_override=unset-null-representation watchdog=disarmed`

The probe also verified:

- disabled GPU and GMU consumers stayed unbound and outside IOMMU groups;
- no A660 SQE, GMU, or ZAP firmware request occurred;
- no render node appeared;
- the NFS lower stayed read-only and USB carrier stayed up;
- systemd remained `running`;
- maximum target temperature was 36.2 C; and
- no new warning, call trace, page fault, IOMMU fault, or fatal signature
  appeared.

The probe watchdog was safely disarmed. The transition watchdog remained the
rollback authority while normal systemd reboot was requested.

## Fallback and host cleanup

The network-root gadget departed normally. The bounded server removed its
export, NFS listener and threads, mount daemon, read-only bind mount,
diagnostic `/30`, temporary firewall rules, and restored
`ip_nonlocal_bind=0`.

The exact persistent fallback returned. Its ordinary `/16` profile was
reactivated with autoconnect still disabled, and ModemManager was restored.
Pinned fallback preflight passed. The redacted phone health result was:

`PASS fallback health thermal_zones=70 thermal_max_mC=39100 pstore_records=0 project_modules=0`

Final host checks proved:

- NFS inactive;
- zero exports, listeners, mount daemon, NFS runtime, or export mount;
- firewalld and ModemManager active;
- no temporary rich rule in any firewall zone;
- an empty drop zone with no interface, source, service, port, rule, or
  masquerade state;
- exact fallback `169.254.77.1/16` and zero diagnostic `/30` addresses;
- zero fastboot and ADB devices; and
- private evidence directory mode `0700` with both evidence logs mode `0600`.

No private identifier, credential, binary artifact, or private live evidence
is committed.

## Acceptance and next gate

GPUCC/CCF and the idle Adreno SMMU foundation are now live-accepted. V21 is
consumed and must not be served or retried.

After recording the result, the generic host NFS server was changed to reject
both consumed v20 and v21 roots. Its host and export contract tests pass; the
v21 root remains preserved only as independently verifiable evidence.

The next possible tier is the already built A660 **registration-only**
candidate. Before any live use it must be rebuilt or resealed against this
exact accepted SMMU result, rerun its complete source/binary/root verifier,
retain modular DRM/MSM and GPUCC ordering, keep display and UFS disabled,
embed no firmware, prevent automatic DRM opens, and preserve independent
watchdog/fallback gates.

Registration attaches IOMMU contexts and performs GMU RSCC/PDC setup; it is a
new hardware boundary. Firmware loading, GPU power-up, GMU resume/HFI,
ZAP/SCM authentication, first DRM open, rendering, display, suspend, and
accelerated desktop remain separately locked.
