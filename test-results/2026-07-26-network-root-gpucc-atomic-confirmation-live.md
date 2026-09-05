# Network-root v17 atomic GPUCC confirmation — live result

Date: 2026-07-26

Result: **PASS for the isolated GPUCC/CCF foundation**. The one permitted
RAM-only v17 cycle reached complete SM8350 GPUCC registration, bound exactly
one platform device, remained stable for 30 seconds, rebooted normally, and
restored the exact persistent fallback with complete host cleanup. Nothing
was flashed.

This is not GPU acceleration evidence. GPU, GMU, the Adreno SMMU, firmware,
DRM/MSM consumers, and render nodes remained disabled throughout the test.

## Reviewed inputs

The live cycle started from repository checkpoint
`f4880f4f7c761c5a07a117b46015e26ec85c318e` and the exact artifacts accepted
by the v15–v17 offline gates:

| Input | SHA-256 |
|---|---|
| Linux 7.1.4 Image | `d30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b` |
| module archive | `9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2560231067d2a` |
| external `gpucc-sm8350.ko` | `9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a` |
| USB2/UFS-disabled DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| staging initramfs | `68b8729c5aef7f9a3eacba07685fe952f4df6cac29eb8c35d9559fda98722fab` |
| temporary-boot AVB image | `bb4a6e34c98475f991a9575defe57c52ac732da0cea96a10585ee0bb92ae7730` |
| fourteen-file manifest | `a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc` |

The complete exact-bundle verifier passed again immediately before the live
transition. The host branch was synchronized and clean, the fallback stock
kernel/ext4 identity passed through pinned key-only SSH, standard pstore and
current fatal signatures were zero, no project diagnostic module was loaded,
and the maximum fallback temperature was 39.8 C.

The attended NFS server initially failed closed because its existing empty
state file had an unexpected restrictive mode. After proving it was a
root-owned regular empty file and that there were zero exports, listeners,
threads, mounts, or rules, the mode was corrected to `0644`. The second start
passed the exact-peer, read-only NFSv4.2 gate.

## Atomic staging transport

Exactly one `fastboot boot` was used; no flash command was issued. One
guarded `confirm-gpucc` process then:

1. checked both explicit guards before device discovery;
2. sent the trace-free `load-gpucc-confirmation` action;
3. replayed that identical idempotent load once after the known marker race;
4. immediately entered the existing non-retryable execute path; and
5. transmitted exactly one `kexec -e`.

Linux `7.1.4-g7a5cef0db479`, systemd, the exact USB network gadget, and strict
target SSH all became reachable. There was no operator-controlled gap between
load and execute.

## Target baseline

Before disarming the original 900-second target watchdog, the hash-pinned
baseline passed:

- all three high-volume core trace arguments were absent and their read-only
  parameters were `N`;
- OverlayFS used the exact read-only NFS lower;
- physical storage and block-backed mounts were both zero;
- GPU, GMU, and the Adreno SMMU were explicitly disabled and unbound;
- no render node or GPUCC module was present;
- systemd was running with zero failed units;
- the USB carrier remained up; and
- 29 thermal zones were readable with a 37.5 C maximum.

One inherited pstore record contained only known staging/fallback warnings,
with no panic, oops, fault, or watchdog-bite signature. A pre-existing
PMIC-arb warning was captured before the probe; acceptance rejected any new
warning or fault after that snapshot.

## One-shot GPUCC result

The exact module, disarm helper, baseline, and guarded probe were staged only
under target tmpfs. The original watchdog was frozen, terminated, and marked
disarmed immediately before a separate 75-second process-group watchdog was
armed. The probe was executed once and was not retried.

All eight bounded outer markers returned:

| Target time | Marker |
|---:|---|
| 403.980536 | `begin` |
| 403.988139 | `map-complete` |
| 403.996305 | `pll0-begin` |
| 404.004288 | `pll0-complete` |
| 404.012533 | `pll1-begin` |
| 404.020512 | `pll1-complete` |
| 404.028746 | `registration-begin` |
| 404.042766 | `registration-complete ret=0` |

The module load returned at target time 404.055105. After the required
30-second stability interval:

- `gpucc_sm8350` remained loaded;
- its read-only diagnostic parameter remained enabled;
- the `sm8350-gpucc` driver had exactly one bound platform device;
- GPU, GMU, and Adreno SMMU consumers remained disabled and unbound;
- render nodes, physical storage, and block-backed mounts remained zero;
- the NFS lower remained read-only and USB carrier stayed up;
- systemd still reported running with zero failed units;
- no new warning, fault, or fatal signature appeared; and
- the independent watchdog was safely disarmed.

A separate post-probe check repeated those gates at a 36.5 C maximum.

## Reboot and cleanup

`systemctl reboot --no-block` entered the retained exitrd path, the target
gadget departed, and the attended NFS harness removed its export, listener,
threads, mounts, address, and temporary firewall rules. The persistent
fallback returned with a changed private boot identity.

Two host-side observations initially looked like rollback failures but were
control-check defects, not phone failures:

- the first endpoint detector expected the temporary staging product label
  instead of the distinct persistent fallback gadget; and
- the first strict-SSH command used `findmnt`, which the minimal fallback
  userspace does not contain.

After checking the correct persistent endpoint and `/proc/mounts`, pinned
key-only SSH proved the exact stock kernel and ext4 root. Final phone checks
reported zero retained pstore records, zero current fatal signatures, zero
project diagnostic modules, and 73 readable thermal zones with a 38.5 C
maximum.

One runtime firewalld interface assignment survived because the NFS cleanup
guard removed it only while the target sysfs interface still existed. The
exact assignment was removed after proving it was the single phone NCM
interface and that the zone had no source, service, port, rule, or
masquerading state. The host cleanup now removes the runtime assignment even
after USB departure, and its static host test rejects the old ordering.

Final host checks passed:

- inactive NFS service and mount daemon;
- zero exports, listeners, NFS threads, NFS mounts, or runtime directories;
- restored `ip_nonlocal_bind`;
- zero target `/30` addresses or temporary firewall state;
- active firewalld and ModemManager;
- exact active fallback `/16` profile with autoconnect disabled;
- zero Fastboot and ADB targets;
- no project sleep inhibitor; and
- private evidence directory mode `0700` with every evidence file mode
  `0600`.

No private identifier, credential, binary artifact, or private live evidence
is committed.

## Decision and next gate

V17 passes and must not be rerun. The experimental CCF runtime-PM ordering
candidate is accepted only as the isolated SM8350 GPUCC registration
foundation: under a zero-storage network root, with every real consumer
disabled, it completes registration and remains stable without a new warning.

It is not yet approved as a general CCF change or a production phone kernel.
The single 30-second bind does not validate GPU power domains, regulators,
interconnects, the Adreno SMMU, GMU firmware, DRM/MSM, Mesa/Freedreno,
rendering, suspend/resume, unbind, sustained load, or battery impact.

The next GPU tier is offline-first:

1. source-test the exact SM8350 GPU/GX, regulator, interconnect, Adreno SMMU,
   GMU, reserved-memory, and firmware dependency graph;
2. keep UFS, RMTFS, unrelated remote processors, display consumers, and
   persistent storage outside the candidate;
3. reproduce the kernel, DTB, modules, wrapper, and package twice;
4. bring up the Adreno SMMU and power prerequisites before GPU/GMU consumers;
   and
5. permit one attended RAM-only probe only after an independent watchdog and
   fail-closed warning, fault, storage, thermal, reboot, and cleanup tests
   pass offline.
