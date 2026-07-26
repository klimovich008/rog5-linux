# A660 SQE/GMU request-only v4 — offline root and gate acceptance

Date: 2026-07-26

Result: **the source-locked one-open helper, root-owned SQE/GMU-only export,
target baseline/probe, overlapping-watchdog gate, strict host runner, and
unchanged temporary-boot package pass their complete offline contracts**. The
new export contains exactly seven reviewed modules, exact SQE and GMU
firmware, no ZAP image, one 896-byte static AArch64 helper, preserved SSH
credentials, and the accepted registration-v3 marker.

This is not a live firmware-request result. The phone was not contacted, NFS
stayed inactive, no boot command ran, and nothing was flashed.

## Fail-first boundary

Commit `7c5ab07fb328358ea4afab81f6ff0d80646fb16d` records the missing v4
helper/runtime/export/host-control contract before implementation. The
contract requires:

- the exact accepted registration-v3 export and live marker;
- the accepted request-only module archive and changed `msm.ko`;
- exact SQE and GMU firmware mode `0644`, with ZAP absent;
- one fixed `/dev/dri/renderD128` open and exact `EUCLEAN` result 117;
- zero surviving DRM descriptors;
- zero ucode, runtime-power, HFI, ZAP/SCM, storage, display, warning, or fault
  evidence;
- independent probe and transition/reset watchdogs;
- immediate normal fallback reboot;
- strict SSH identity, private evidence, one invocation, and no retry; and
- reuse only of the exact unchanged Image/DT/wrapper/AVB package.

Before the implementation existed, it returned:

```text
FAIL missing A660 firmware-request-only open-helper source
```

## Freestanding one-open helper

`tools/diagnostics/a660-firmware-request-only-open.c` is a libc-free AArch64
program with source SHA-256
`68f7dbb0669b2b386fba2434c58aeb039917ba1ca229479c53a1d729f124f3ef`.
It has no path argument, loop, retry, dynamic loader, or storage path. It
issues exactly one raw `openat(AT_FDCWD, "/dev/dri/renderD128",
O_RDWR|O_CLOEXEC)` and reports `OPEN_ERRNO=117` only for the required
`EUCLEAN` result.

The source verifier rejects six mutations:

- syscall 57 instead of AArch64 `openat` 56;
- `renderD129` instead of the exact first render node;
- errno 116 instead of 117;
- wrong output;
- a second `openat`; and
- a retry loop.

Two empty, isolated, rootless Podman builds used the same network-disabled,
read-only Ubuntu 24.04 builder image as the kernel build. Their binary and
metadata outputs are byte-identical:

| Output | Size | Mode | SHA-256 |
|---|---:|---:|---|
| `rog5-a660-firmware-request-only-open` | 896 | `0755` | `d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae` |
| `build-meta.txt` | 253 | `0644` | `ffb57737611ecea9a5f7d17ab74bc2b37c3d80f792e763061e902016785fff59` |

The binary is stripped, statically linked AArch64 ELF64 with no interpreter,
dynamic segment, relocation, or executable stack. Its only relevant strings
are the exact render path, expected errno result, and bounded unexpected-error
result.

## Runtime source and mutation suite

The immutable-lower runtime inputs are:

| Input | SHA-256 |
|---|---|
| request-only baseline | `88db9503be4c4ee58639bc1afdfdf2958a419c4c2a7d5d6db966a255264026ff` |
| request-only probe | `17a8d45e6dec02f1977800eab8562c12f7ef3841a92d7797b0ffc4d86313c25e` |
| compound target gate | `dc0659d5e103c7685335f97565a9b977aab4d2ed0619cd55c4d7b4896f2f54d6` |
| one-shot host runner | `409c5e9cd2d4590d92700f86fab7c300407b641d0ed23cdd95eba6a57836e805` |

The baseline begins with the original network-root rollback watchdog armed.
It verifies storage isolation, immutable NFS lower, accepted v3 marker, seven
unloaded modules, two exact firmware files, ZAP absence, exact helper, unbound
GPU graph, zero render nodes/descriptors/firmware requests, safe thermals, and
a quiet kernel log.

After watchdog handoff, the probe uses the accepted exact SMMU reprobe and
seven-module registration sequence. It inserts MSM once with
`separate_gpu_kms=1 firmware_request_only=1`, requires one headless
`renderD128`, then runs the source-locked helper once. Acceptance requires
status 117, output `OPEN_ERRNO=117`, exactly one bounded kernel success marker,
zero failure markers, zero DRM descriptors, suspended SMMU/GMU runtime state,
and no later hardware, storage, display, warning, or fault evidence through
the settle interval.

The runtime verifier rejects:

- an unarmed request-only parameter;
- a second helper invocation;
- a wrong expected errno;
- removal of the ZAP/SCM boundary;
- a wrong SQE hash;
- removal of repeated DRM-descriptor checks; and
- a probe-level reboot bypass.

The compound gate runs the baseline before arming a 180-second transition
watchdog, disarms the original rollback watchdog only after overlap, invokes
the probe exactly once, and immediately requests normal reboot. Static guard
tests reject missing or malformed authorization variables.

The host runner requires a clean synchronized Git checkpoint, exact
credentials and known-host identity, a root-owned verified export, exact
unchanged AVB image, two mode-`0500` tmpfs control inputs, one SSH invocation,
mode-`0600` evidence, the exact target PASS records, and the expected reboot
disconnect. Its mock transport test proves one prepare, copy, verify, and gate
call with no retry.

## Root-owned v4 export

PolicyKit created
`/var/lib/rog5-network-root-a660-firmware-request-only-v4` as root-owned mode
`0555`, derived by Btrfs reflink from the accepted, consumed registration-v3
root. It shares about 2.80 GiB of extents with its predecessor and reports
about 11.80 MiB exclusive in the paired Btrfs accounting view.

The builder removes the consumed v3 baseline, probe, and seal. It changes only
the MSM module; installs the new baseline, probe, helper, and v3 acceptance
marker; and adds two firmware files. The existing exact SMMU checker,
remaining six modules, credentials, host identity, distro userspace, and every
undeclared file remain equal to registration v3.

| Export input | Mode | SHA-256 |
|---|---:|---|
| export seal | `0444` | `2b615c6acb96b76384e741798e67e86322fce228cab1f78e01494227509f0dc8` |
| registration-v3 marker | `0444` | `8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f` |
| request-only MSM module | `0644` | `eb2df946472603d932d63a25f5350535b104303e5db6ac8dc66273647460b082` |
| one-open helper | `0755` | `d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae` |
| `qcom/a660_sqe.fw` | `0644` | `d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76` |
| `qcom/a660_gmu.bin` | `0644` | `8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7` |
| `qcom/sm8350/a660_zap.mbn` | absent | host-side pin `5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d` |

The first complete export verification rejected the retained candidate because
the metadata comparator treated the expected new/removed entries' parent
directory sizes as unchanged payload. A fail-first regression now excludes
only those four parent directory entries while still comparing every child
entry and undeclared file hash. The retained candidate then passed, was
promoted atomically to the exact v4 path, and passed again there:

```text
PASS A660 firmware-request-only v4 export modules=7 firmware=2 zap=absent helper=exact credentials=preserved base=registration-v3
```

The generic NFS server now accepts this one exact v4 path through its complete
export verifier. It still rejects registration v1-v3 and consumed SMMU v20/v21
roots. No NFS export, listener, mount, or `rpc.mountd` process is active.

## Unchanged boot package

The accepted request-only build has the same Image SHA-256 as registration:
`52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db`.
Therefore no new wrapper or boot image was built. The complete existing
registration verifier rechecked the exact DT, nested stage, ASUS wrapper,
header-v3 image, AVB footer, fourteen-file manifest, accepted predecessors,
source, and storage/display containment.

The reused temporary-boot image SHA-256 is
`c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c`;
the manifest SHA-256 is
`c4b9a2ec5afdd73a555031425a5eaedf5ab97a36a69eeefdcfede279ad7ffcd0`.
The full verifier returned:

```text
PASS exact live-accepted A660 registration bundle; exact SMMU reprobe, four nodes, seven modules, unopened render, zero firmware/storage/display, consumed and reproducible
PASS A660 registration bundle contract pins predecessor, source, DT, modules, wrappers, package, and source lock
```

## Consolidated result and live boundary

All 17 new shell tools pass syntax, ShellCheck 0.11.0, and
`git diff --check`. With both helper builds, both request-only kernel builds,
the real kernel verifier/comparator, and full package verifier enabled, the
umbrella suite ends with:

```text
PASS A660 firmware-request-only v4 contract is exact-root, SQE/GMU-only, one-open, watchdog-guarded, storage-isolated, and non-flashing
```

Offline preparation is complete, but nothing here proves a firmware request
on hardware. Before any live cycle, the repository and draft PR must be clean
and synchronized, the root must pass its privileged verifier again, host
preflight must prove exact persistent fallback and inactive NFS state, and an
attended go/no-go decision must be recorded. A permitted cycle remains
RAM-only `fastboot boot`, one invocation, immediate reboot, exact fallback,
full host cleanup, and permanent consumption of v4 regardless of result.

The subsequent
[request-only v4 live acceptance](2026-07-26-a660-firmware-request-only-v4-live-accepted.md)
records the sole permitted cycle: exact SQE/GMU requests, deliberate
`EUCLEAN`, zero later hardware/storage/fault evidence, exact fallback,
complete cleanup, and consumed-root lockout.
