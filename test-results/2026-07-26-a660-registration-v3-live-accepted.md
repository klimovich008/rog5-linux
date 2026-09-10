# A660 registration v3 — live acceptance

Date: 2026-07-26

Result: **PASS for firmware-free A660/GMU registration. The one permitted v3
RAM-only cycle used the live-accepted exact Adreno SMMU reprobe, loaded the
seven reviewed modules in order, bound the A660 platform device, attached the
GPU and GMU to two IOMMU groups, created one headless render node, and settled
for 30 seconds with zero DRM descriptors, zero A660 firmware files or
requests, zero display connectors, zero physical storage, zero block-backed
mounts, and zero failed units. No new warning, call trace, page fault, IOMMU
fault, or fatal signature appeared. Normal reboot restored the exact
persistent Alpine fallback, and complete privileged host cleanup passed.
Nothing was flashed.**

Registration v3 is consumed and must not be rerun. This accepts only
firmware-free platform registration and idle IOMMU attachment. It does not
accept firmware loading, GPU power-up, GMU resume/HFI, ZAP/SCM
authentication, first DRM open, rendering, display, suspend, remote Plasma,
or persistent installation.

## Reviewed checkpoint

The live cycle started from the clean synchronized repository checkpoint:

`8b633fba764093071a829946858da02445606d14`

The exact temporary-boot image was:

`artifacts/network-root-a660-registration/boot-5.4.210-network-root-stage.avb.img`

Size: `100663296`

SHA-256:

`c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c`

The root-owned mode-`0555`
`/var/lib/rog5-network-root-a660-registration-v3` export independently
verified immediately before the cycle with:

- exact v21 report and acceptance-marker pins;
- exact unset-NULL `driver_override` checker;
- the exact-reprobe seal;
- exactly seven `7.1.4-rog5-a660reg1` modules;
- zero A660 SQE, GMU, or ZAP firmware;
- preserved client authorization and server host identity; and
- an unchanged accepted v1 base.

The complete source, kernel, DT, modules, nested initramfs, ASUS wrapper,
header-v3/AVB, export, target gate, and host runner verifier passed before the
cycle.

## Read-only preflight

The persistent fallback passed its exact kernel, BusyBox init, compatible,
ext4 root, zero project modules, zero pstore records, zero current fatal
signatures, and safe thermal checks. The separate preflight read 70 thermal
zones with a maximum of 38.5 C.

The host preflight proved:

- the local and remote-tracking Git checkpoints were identical and clean;
- both strict SSH host aliases were already pinned;
- the private key and known-hosts file had exact owner-only modes;
- firewalld, NetworkManager, and ModemManager were active;
- NFS, mountd, exports, listeners, export mounts, and kernel NFS threads were
  absent;
- the dedicated drop zone was empty and drop-by-default;
- no temporary NFS/firewall rule existed; and
- `ip_nonlocal_bind=0`.

The v3 export was then opened only through the bounded exact-peer NFSv4.2
server. Its 1,200-second host window exceeded the target's 900-second original
rollback deadline so target reset authority could not lose a timeout race.

## Atomic transition

One guarded `RESTART2("bootloader")` request reached exactly one fastboot
device. Product preflight returned `lahaina`.

Exactly one temporary `fastboot boot` was issued; no flash command was used.
The ASUS wrapper exposed the exact recovery ACM identity. The fixed
`confirm-gpucc` staging sequence was invoked once:

1. the known missing-marker race caused its one tested, identical load-only
   rediscovery;
2. Image, DT, and initramfs hashes passed;
3. execute remained non-retryable; and
4. exactly one `kexec -e` was transmitted.

Linux `7.1.4-rog5-a660reg1`, systemd, strict SSH, and the exact USB/NFS root
then passed readiness checks with read-only NFS lower, volatile OverlayFS,
zero physical storage, and the original watchdog armed.

## Read-only baseline

The compound A660 gate was invoked exactly once. Before handoff it reported:

`PASS A660-registration baseline storage=0 mounts=0 firmware=0 render=0 drm_fds=0 failed_units=0 thermal_zones=29 thermal_max_mC=37100 module_files=7 pstore_records=1 watchdog=armed modules=unloaded smmu_name=3da0000.iommu driver_override=unset-null-representation drivers_probe=locked`

The one pstore record was already present before GPUCC, SMMU, DRM dependency,
or MSM action. The current kernel log had no fatal or IOMMU-fault signature,
and persistent fallback exposed zero pstore records after the cycle.

Baseline also proved:

- all seven modules were present but unloaded;
- GPUCC, SMMU, GPU, and GMU each resolved to one exact unbound platform
  device;
- `3da0000.iommu` had the reviewed unset-NULL override representation;
- platform autoprobe was enabled;
- `drivers_probe` was root-owned mode `0200`;
- ARM SMMU force-bind controls were absent;
- firmware files, requests, render nodes, and DRM descriptors were absent;
- systemd was `running`; and
- the original rollback watchdog remained armed.

## Watchdog handoff

After baseline acceptance:

1. the independent 180-second transition/reset watchdog armed;
2. the original 900-second network-root watchdog was frozen, terminated, and
   marked disarmed by the A660-release-specific helper;
3. the independent 90-second registration watchdog armed; and
4. the registration probe remained the sole hardware-action invocation.

The transition watchdog stayed armed after probe success and remained reset
authority until normal reboot removed the network root.

## GPUCC and exact SMMU reprobe

GPUCC completed its already accepted bounded registration:

| Target time | Marker |
|---:|---|
| 194.423031 | GPUCC diagnostic begin |
| 194.430727 | `map-complete` |
| 194.438933 | `pll0-begin` |
| 194.446956 | `pll0-complete` |
| 194.455214 | `pll1-begin` |
| 194.463222 | `pll1-complete` |
| 194.471478 | `registration-begin` |
| 194.488773 | `registration-complete ret=0` |

Five seconds of ordinary autoprobe left the exact SMMU unbound. At target
time 199.624567, the probe wrote only:

`3da0000.iommu`

to platform `drivers_probe`. `arm-smmu` reported stage-1 translation,
coherent table walk, six stream-matching groups, seven context banks, a
48-bit VA to 36-bit IPA path, and zero preserved boot mappings.

The single request returned at target time 199.700644 with:

- `3da0000.iommu` bound to `arm-smmu`;
- the GPU attached to one IOMMU group;
- the GMU attached to a second IOMMU group; and
- `exact_reprobe=1`.

No broad rescan, override write, force-bind, unload, or retry occurred.

## A660 registration result

Only after the accepted SMMU bind, the probe loaded:

1. `drm_exec`;
2. `drm_gpuvm`;
3. `gpu_sched`;
4. `mdt_loader`;
5. `ubwc_config`; and
6. `msm` with the read-only `separate_gpu_kms=1` parameter.

Together with GPUCC, exactly seven reviewed modules remained loaded. The
Adreno device bound, the GMU did not acquire a separate platform driver, and
the SMMU and GMU runtime paths reached `suspended`.

MSM initialized one headless DRM minor and exactly one render node. No display
connector appeared, and repeated scans before and after the 30-second settle
found zero process descriptors referring to `/dev/dri/*`. The three A660
firmware files were absent from the root, and the kernel requested none.

The accepted probe marker was:

`PASS A660 registration GPUCC=1 SMMU=1 GPU=1 GMU=1 iommu=2 render=1 drm_fds=0 firmware=0 storage=0 mounts=0 failed_units=0 thermal_zones=29 thermal_max_mC=38100 exact_reprobe=1 driver_override=unset-null-representation watchdog=disarmed`

The probe additionally rechecked:

- read-only NFS lower and live USB carrier;
- zero physical block devices and block-backed mounts;
- zero systemd failures and system state `running`;
- zero A660 firmware request;
- zero new warning, call trace, page fault, IOMMU fault, or fatal signature;
  and
- a maximum target temperature of 38.1 C.

The probe watchdog was safely disarmed. The transition watchdog remained armed
while the compound gate requested immediate nonblocking systemd reboot.

## Fallback and host cleanup

The network-root gadget departed normally. The bounded server removed its:

- export;
- NFS listener and kernel threads;
- mount daemon;
- read-only bind mount;
- diagnostic `/30`;
- temporary firewall interface and rich rules; and
- temporary `ip_nonlocal_bind=1`.

The exact persistent Alpine fallback returned. Its ordinary
`rog5-usb-temporary` `/16` profile was reactivated with autoconnect still
disabled, and ModemManager was restored. The pinned fallback preflight passed.
The redacted phone health result was:

`PASS fallback health thermal_zones=70 thermal_max_mC=39100 pstore_records=0 project_modules=0`

Final privileged host checks proved:

- NFS and mountd inactive;
- zero exports, listeners, export mounts, or temporary NFS state;
- firewalld, NetworkManager, and ModemManager active;
- no temporary rich rule in any firewall zone;
- an empty dedicated drop zone;
- `ip_nonlocal_bind=0`;
- exact fallback `169.254.77.1/16` and zero diagnostic `/30` addresses;
- zero fastboot and ADB devices;
- a clean synchronized Git checkpoint; and
- private evidence directory mode `0700` with all twelve evidence files mode
  `0600`.

No private identifier, credential, binary artifact, or private live evidence
is committed.

## Acceptance and next gate

Firmware-free A660/GMU platform registration, two IOMMU attachments, and an
idle unopened render node are now live-accepted. V3 is consumed and must not
be served or retried.

The generic NFS server now rejects the old A660 root, v2, v3, and all consumed
SMMU diagnostic roots. The v3 root remains preserved only as independently
verifiable evidence.

The next possible tier is a **firmware provisioning without DRM open** gate.
It must pin this exact report and a mutation-tested nonsecret acceptance
marker, keep the render node unopened, request only the reviewed A660 SQE/GMU
and ZAP images, preserve zero storage/display activity, and remain under
independent rollback. Firmware loading, GMU resume/HFI, ZAP/SCM
authentication, first DRM open, rendering, display, suspend, remote Plasma,
and persistent deployment remain separate milestones until their own gates
pass.
