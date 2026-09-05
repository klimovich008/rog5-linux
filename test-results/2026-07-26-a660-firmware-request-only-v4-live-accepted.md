# A660 SQE/GMU request-only v4 — live acceptance

Date: 2026-07-26

Result: **PASS for the isolated A660 firmware-request boundary. The one
permitted RAM-only v4 cycle loaded the seven reviewed modules, performed one
exact Adreno SMMU reprobe, attached the GPU and GMU to two IOMMU groups,
created one headless render node, and invoked one fixed open helper. The
kernel requested exactly `a660_sqe.fw` and `a660_gmu.bin`, emitted one bounded
success marker, and rejected the open with `EUCLEAN` before ucode mapping,
runtime power, GPU hardware initialization, GMU firmware/HFI startup, or
ZAP/SCM authentication. No DRM descriptor survived. Storage, block-backed
mounts, display connectors, failed units, warnings, call traces, page faults,
IOMMU faults, and fatal signatures stayed zero. Normal reboot restored the
exact persistent Alpine fallback, and complete privileged host cleanup
passed. Nothing was flashed.**

V4 is consumed and must never be served or retried. This accepts only exact
SQE/GMU firmware requests followed by a deliberately failed first open. It
does not accept ucode buffer creation, GPU or GX power, regulator or
interconnect votes, GMU resume, GMU firmware/HFI, ZAP/SCM authentication, a
successful DRM open, command submission, rendering, display, suspend, remote
Plasma, or persistent installation.

## Reviewed checkpoint

The live cycle started from the clean synchronized repository checkpoint:

`2cb3d85439b1bc72f96b8d401207c53d9d77cf1e`

The exact temporary-boot image was:

`artifacts/network-root-a660-registration/boot-5.4.210-network-root-stage.avb.img`

Size: `100663296`

SHA-256:

`c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c`

The accepted Image remained unchanged at:

`52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db`

The root-owned mode-`0555`
`/var/lib/rog5-network-root-a660-firmware-request-only-v4` export verified
immediately before the cycle with:

- the exact consumed registration-v3 base and acceptance marker;
- exactly seven `7.1.4-rog5-a660reg1` modules;
- only the changed request-only `msm.ko`;
- exact mode-`0644` SQE and GMU firmware;
- no ZAP image anywhere in the immutable lower;
- the exact 896-byte static one-open helper;
- preserved SSH client authorization and server host identity; and
- complete equality for every undeclared base file.

Its exact identities were:

| Input | SHA-256 |
|---|---|
| export seal | `2b615c6acb96b76384e741798e67e86322fce228cab1f78e01494227509f0dc8` |
| request-only MSM module | `eb2df946472603d932d63a25f5350535b104303e5db6ac8dc66273647460b082` |
| one-open helper | `d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae` |
| `qcom/a660_sqe.fw` | `d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76` |
| `qcom/a660_gmu.bin` | `8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7` |

The complete source, patch, duplicate kernel builds, duplicate helper builds,
DT, nested initramfs, ASUS wrapper, header-v3/AVB package, export, target gate,
host runner, mutation suites, and exact package verifier passed before the
cycle.

## Read-only preflight

The persistent fallback passed its exact kernel, BusyBox init, compatible,
ext4 root, zero project modules, zero pstore records, zero current fatal
signatures, safe thermals, and dedicated strict-host-key SSH identity.

The host preflight proved:

- local and remote-tracking Git checkpoints were identical and clean;
- both SSH host aliases were already pinned;
- the private key and known-hosts file had safe owner/write modes;
- firewalld, NetworkManager, and ModemManager were active;
- NFS, mountd, exports, listeners, export mounts, and kernel NFS threads were
  absent;
- the dedicated drop zone was empty and drop-by-default;
- no temporary NFS/firewall rule existed;
- the ordinary fallback profile was the exact non-autoconnecting `/16`; and
- `ip_nonlocal_bind=0`.

One additional read-only preflight used `firewall-cmd --get-target`, which
this firewalld version permits only for permanent state. It stopped without a
state change. The accepted check reused the server's tested runtime
`--list-all` parser and passed.

## Bounded NFS server

The first server invocation refused before creating any export, listener,
mount, firewall rule, interface change, or sysctl change. Reboot had recreated
the root-owned, non-linked, empty `/var/lib/nfs/etab` as mode `0600`, while
the old host contract expected only `0644`. After confirming zero NFS state,
the empty file was temporarily normalized to `0644` and the same exact server
was invoked again.

The accepted 1,200-second NFS window exceeded the target's 900-second original
rollback deadline. Before the phone transition, the host proved:

`PASS v4 NFS ready listener=169.254.77.1:2049 peer=169.254.77.2 export=ro protocol=4.2 threads=4 firewall=exact nonlocal=1`

The server exposed one NFSv4.2/TCP listener only on the USB host address,
exported the verified root read-only only to the exact `/30` peer, used the
built-in drop zone, and blocked its NFS/mountd ports in every pre-existing
active zone. The system NFS service stayed inactive.

Two extra readiness reads initially lacked permission for the kernel NFS
thread count and `exportfs` lock. Both stopped without state changes and then
passed through PolicyKit. Final cleanup recreated the empty `etab` at its
native mode `0600`; the host contract now accepts root-owned mode `0600` or
`0644` while retaining all type, ownership, export, and inactive-state checks.

## Atomic transition

ModemManager alone was stopped to release the recovery ACM. Firewalld and
NetworkManager remained active.

One identity-pinned `RESTART2("bootloader")` request reached exactly one
fastboot device. Product preflight returned `lahaina`.

Exactly one temporary `fastboot boot` was issued; no flash, erase, or partition
write command was used. The ASUS wrapper exposed the exact recovery ACM
identity. The fixed `confirm-gpucc` process was invoked once:

1. the known missing-marker race caused its one tested, identical load-only
   rediscovery;
2. Image, DT, and initramfs hashes passed;
3. execute remained non-retryable; and
4. exactly one `kexec -e` was transmitted.

Linux `7.1.4-rog5-a660reg1`, systemd, strict SSH, and the exact USB/NFS root
then passed readiness with a read-only NFS lower, volatile OverlayFS upper,
zero physical storage, zero block-backed mounts, zero loaded project modules,
zero render nodes, the exact v4 seal, and the original rollback watchdog
armed.

## Read-only baseline and watchdog handoff

The one-shot host runner invoked the compound target gate exactly once.
Before any module load or firmware request, it reported:

`PASS A660-firmware-request-only baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 zap=absent render=0 drm_fds=0 failed_units=0 thermal_zones=29 thermal_max_mC=38100 module_files=7 helper=exact watchdog=armed`

After baseline acceptance:

1. an independent 180-second transition/reset watchdog armed;
2. the original 900-second network-root watchdog was frozen, terminated, and
   marked disarmed by the accepted A660-release helper;
3. an independent 90-second request-only probe watchdog armed; and
4. the probe remained the sole hardware-action invocation.

The transition watchdog remained reset authority through the probe and normal
reboot request.

## GPUCC and exact SMMU reprobe

GPUCC completed its accepted bounded registration:

| Target time | Marker |
|---:|---|
| 279.894551 | GPUCC diagnostic begin |
| 279.902149 | `map-complete` |
| 279.910318 | `pll0-begin` |
| 279.918300 | `pll0-complete` |
| 279.926543 | `pll1-begin` |
| 279.934521 | `pll1-complete` |
| 279.942768 | `registration-begin` |
| 279.956710 | `registration-complete ret=0` |

Five seconds of ordinary autoprobe left the exact SMMU unbound. The probe
wrote only `3da0000.iommu` once to platform `drivers_probe`.
`arm-smmu` reported stage-1 translation, coherent table walk, six
stream-matching groups, seven context banks, a 48-bit VA to 36-bit IPA path,
and zero preserved boot mappings. The GPU and GMU then attached to exactly two
IOMMU groups, and `exact_reprobe=1`.

No broad rescan, override write, force-bind, unload, or retry occurred.

## Exact firmware-request result

Only after the accepted SMMU bind, the probe loaded `drm_exec`, `drm_gpuvm`,
`gpu_sched`, `mdt_loader`, `ubwc_config`, and the request-only MSM module with:

`separate_gpu_kms=1 firmware_request_only=1`

Together with GPUCC, exactly seven reviewed modules remained loaded. The A660
bound to `adreno`; the GMU did not acquire a separate platform driver; and the
SMMU and GMU runtime states reached `suspended`.

MSM created exactly one headless `/dev/dri/renderD128` and no display
connector. Repeated scans found zero process descriptors referring to
`/dev/dri/*` before the helper.

At target time 297.668229, the fixed static helper issued its only raw
`openat()`:

| Target time | Kernel evidence |
|---:|---|
| 297.690689 | loaded `qcom/a660_sqe.fw` from the reviewed location |
| 297.702607 | loaded `qcom/a660_gmu.bin` from the reviewed location |
| 297.712479 | `A660 firmware-only passed; reject open` |

The helper returned status 117 with exact output `OPEN_ERRNO=117`. The gate
observed one helper invocation, two firmware requests, one success marker,
zero failure markers, and no surviving DRM descriptor. ZAP remained absent.

During the 20-second settle:

- the success marker count remained one;
- no second firmware request or open appeared;
- SMMU and GMU runtime states remained `suspended`;
- ucode, GPU/GX power, hardware initialization, GMU firmware/HFI, and ZAP/SCM
  markers remained zero;
- physical storage, block mounts, display connectors, and failed units
  remained zero;
- no warning, call trace, page fault, IOMMU fault, or fatal signature
  appeared; and
- the maximum target temperature was 38.5 C.

The accepted target result was:

`PASS A660 firmware-request-only open_invocations=1 open_errno=117 firmware_requests=2 success_markers=1 zap=absent ucode=0 power=0 hfi=0 scm=0 drm_fds=0 storage=0 mounts=0 failed_units=0 iommu=2 render=1 thermal_zones=29 thermal_max_mC=38500 exact_reprobe=1 driver_override=unset-null-representation watchdog=disarmed`

The compound gate then reported:

`PASS compound A660 firmware-request-only gate open_errno=117 transition_watchdog=armed reboot=requested`

The expected SSH disconnect followed the normal nonblocking systemd reboot
request.

## Fallback and host cleanup

The network-root gadget departed normally. The bounded server removed its:

- export;
- NFS listener and kernel threads;
- mount daemon;
- read-only bind mount;
- diagnostic `/30`;
- temporary firewall interface and rich rules; and
- temporary `ip_nonlocal_bind=1`.

The exact persistent Alpine gadget returned. Because its ordinary
`rog5-usb-temporary` profile intentionally has autoconnect disabled, the host
validated that profile's exact wired `/16` settings and reactivated it once.
Autoconnect remained disabled.

The pinned fallback preflight passed. The redacted phone health result was:

`PASS fallback health thermal_zones=70 thermal_max_mC=38500 pstore_records=0 project_modules=0`

ModemManager was restored. Final privileged host checks proved:

- NFS and mountd inactive;
- zero exports, listeners, kernel NFS threads, export mounts, or temporary
  NFS state;
- firewalld, NetworkManager, and ModemManager active;
- no temporary NFS rich rule in any firewall zone;
- an empty dedicated drop zone;
- `ip_nonlocal_bind=0`;
- exact fallback `169.254.77.1/16` and zero diagnostic `/30` addresses;
- zero fastboot and ADB devices;
- a clean synchronized candidate checkpoint; and
- private evidence directory mode `0700` with all 20 evidence files mode
  `0600`.

The exact final host markers were:

`PASS privileged host cleanup NFS=0 exports=0 listeners=0 mounts=0 firewall-temp=0 nonlocal=0 services=restored etab_mode=600`

`PASS exact fallback link/profile, no fastboot/ADB, clean synchronized checkpoint, private gate evidence`

No private identifier, credential, binary artifact, or private live evidence
is committed.

## Acceptance and next gate

The post-live fail-first acceptance contract is commit
`68607c37dfa9558c8d0d77477c0ab973bf623da3`. It initially rejected the
missing exact report/verifier/marker, the still-runnable v4 path, and the
server's mode-`0644`-only `etab` assumption.

Exact SQE/GMU request and deliberate failed-open isolation are now
live-accepted. V4 is consumed and must not be served or retried. The generic
NFS server rejects v4 and every consumed A660/SMMU root; the root remains
preserved as independently verifiable offline evidence only.

The next permissible GPU tier is offline source and allocation-path work:
prove whether A660 ucode buffer creation can be isolated after the accepted
firmware objects and before runtime power or hardware access. Only after a
new fail-first contract, duplicate builds, fresh versioned export, independent
rollback, and explicit one-shot review may that boundary be considered on
hardware. GPU/GX power, GMU resume/HFI, ZAP/SCM authentication, successful DRM
open, command submission, rendering, display, suspend, remote Plasma, and
persistent deployment remain separate gated milestones.
