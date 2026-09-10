# A660 GMU/CX runtime-PM v10 — protected-root and pre-live HOLD

Date: 2026-07-27

Decision: **HOLD. The source-pinned v10 runtime oracle, protected root,
target gate, watchdog, one-shot host runner, and verifier-first bounded NFS
case all pass offline. The connected persistent Alpine fallback also passes
the strict read-only identity and health preflight. No v10 live cycle is
authorized by this checkpoint.**

No NFS window was opened. No boot, reboot, flash, module load, DRM open, or
phone write occurred.

## Protected root

The root at
`/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10` is an exact
copy-on-write delta from the permanently consumed v9 root. It is root-owned,
mode `0555`, and contains:

- the unchanged Linux release, Image, six dependency modules, two firmware
  files, rootfs, and SSH credentials from v9;
- the accepted v10 `msm.ko` as the only kernel/module delta;
- separately generated baseline and probe controls;
- the exact GMU/linked-CX trace oracle and static one-open helper; and
- no ZAP firmware or retained v9 runtime control.

The complete verifier recursively compared the protected root with consumed
v9 and passed:

```text
PASS A660 GMU/CX runtime-PM v10 export modules=7 firmware=2 zap=absent helper=exact oracle=gmu-linked-cx module=v10-msm-only gmu_runtime_pm=1/1 cx_runtime_pm=1/1 gx_runtime_pm=0 clocks=0 secure=0 mmio=0 irq=0 firmware_start=0 hfi=0 logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=consumed-v9 root-owned mode 0555
```

The root seal SHA-256 is
`eaa44f2a7cef85e14d1b9dd0359b47d3cf10a5d5b05dafee77c085ce12a45cb4`.
The installed v10 `msm.ko` SHA-256 is
`c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d`.
Exactly seven project modules are installed.

## Runtime oracle and one-shot controls

The source-pinned runtime suite regenerates the baseline and probe twice and
rejects fourteen mutations. The diagnostic accepts only:

- one deliberate `EUCLEAN` DRM-open failure;
- one exact `3d6a000.gmu` resume/suspend pair;
- one linked `genpd:0:3d6a000.gmu` CX resume/suspend pair;
- suspended GMU and CX state after settling;
- two balanced SQE/GMU firmware requests;
- exact allocation, mapping, logical-vmap, and GEM-snapshot rollback; and
- zero GX runtime PM, clocks, secure init, MMIO, IRQ, firmware start, HFI,
  hardware init, ZAP/SCM, storage access, or retained DRM descriptors.

The CX explicit-suspend result may be `0` or already-suspended `1`. Generic
runtime-PM events are PID-filtered and device-classified; they are not treated
as a process-global count.

The compound target gate requires both one-shot authorization variables,
arms an overlapping reboot watchdog, runs baseline then probe exactly once,
requires every oracle marker, and requests immediate fallback. The host
runner requires separate live-gate and reboot variables, strict pinned SSH
identity, a private evidence directory, exact two-file tmpfs staging, and no
retry.

## Fail-first bounded NFS case

Commit `f716d4eb60ad74dd9da0ae916e7dda961f54d680` records the missing
v10 server case:

```text
FAIL bounded NFS server omits v10 live-window contract: /var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10)
```

Commit `780b1b8857f3940a81e07885e85a56dc6f2fae63` adds only one
exact-root case. It requires:

```text
ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_NFS=1
```

That guard precedes the complete v10 root verifier, and the verifier precedes
the first export-table, NFS, firewall, bind-mount, interface, or sysctl state
line. The v10 root is checked against immutable consumed v9. Every consumed
SMMU/A660 root through v9 remains absent from the server.

An actual PolicyKit invocation against the exact v10 root without the token
returned:

```text
FAIL set ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_NFS=1 for the attended v10 window
```

Normalized before/after state was byte-identical across NFS and rpcbind
units, exports, NFS mounts and processes, ports 111/2049/32767, runtime
firewall state, IPv4 addresses, `ip_nonlocal_bind`, NFS threads, and the
temporary export mount. Final state remained:

```text
nfs-server=inactive
rpcbind-service=inactive
rpcbind-socket=inactive
exports=0
listeners=0
mount=absent
nonlocal=0
```

The server remains runtime-only, read-only, NFSv4.2-only, bound to the USB
host address and exact phone peer, and bounded to 60–86,400 seconds. It has no
ADB, fastboot, boot, flash, or phone-storage command.

## Revalidation

At clean synchronized checkpoint
`780b1b8857f3940a81e07885e85a56dc6f2fae63`:

```text
PASS A660 GMU/CX runtime-PM boundary is accepted-v9-dependent, source-pinned, get-error-balanced, synchronously rolled back, CX-only, and pre-GX
PASS A660 GMU/CX runtime-PM diagnostic patch is mutation-tested, exact-chip, atomic-stateful, get-error-balanced, synchronously rolled back, CX-only, and pre-GX
PASS A660 GMU/CX runtime-PM kernel build is exact-stack, unchanged-Image, modular, firmware-clean, rollback-safe, offline-only, and reproducible by contract
PASS A660 GMU/CX runtime-PM v10 root is consumed-v9-derived, exact-delta, runtime-mutation-tested, storage-free, target-gated, one-shot, and server-inactive
PASS host gate is exact-peer, runtime-only, read-only, and fail-closed
PASS A660 GMU/CX runtime-PM v10 NFS window is exact-root, opt-in, verifier-first, bounded, and non-flashing
PASS host A660 GMU/CX runtime-PM v10 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries
```

Shell syntax, ShellCheck, and `git diff --check` also pass.

Important control identities are:

| Input | SHA-256 |
|---|---|
| bounded NFS server | `bd223caa78b6d8975194f65b35e3bd54a7194c014ad65ddd1961a66aaee2707b` |
| v10 NFS-window test | `82507ed29a555e01218fbe774d6ed6864bd9ce054bfc0e5d55557622a820fa21` |
| protected-root builder | `d679679dbb1590e23f7cae36e9cbb6767dc8cb3277600e09e722c8d502e707f1` |
| protected-root verifier | `f26d67a3267f34153fb672b30bcc9cede8bc4b5bef4f011fa2a3028473601743` |
| target compound gate | `785827f58cfde18130b4e36d5b201b93ed1232f5f4d9a41e8441cbcdcde937f4` |
| one-shot host runner | `c84f66f626c1e70c8dd28292eb42fc249d19e6f0e02479e80ceec5e5025c035d` |
| runtime builder | `a0bd091b1304581fe41bfcf1ceaa77a84fbbdd606d3797144a1e6685e1179942` |
| runtime verifier | `7141c437962b49a90574dc8e14987fad9d291b5d8ea8b9c3371ebf0c8af187b3` |
| exact trace oracle | `33ccadc6ae1e5f6f12ed83de0ddc192d30d204e229ec1b97aa813e1d0ac9c7e6` |
| accepted module archive | `87e5c3bae7d5034b64aea7212be8372506bf8b28cbdca7fb1b79bb20db50b9d0` |

## Connected fallback

The phone is reachable through its pinned fallback SSH identity. The strict
read-only preflight passed the exact vendor kernel, BusyBox PID 1,
`qcom,lahaina-mtp`, ext4 root, zero project diagnostic modules, empty pstore,
zero fatal kernel signatures, safe thermal telemetry, and Python
availability:

```text
PASS exact persistent fallback ready for guarded bootloader reboot
```

Its display backlight remains at zero. This confirms recovery readiness; it
does not authorize a v10 transition.

## Requirement for a future GO review

A later review must recheck clean synchronized Git, the complete root,
runtime, package, server, credential, fallback, and host gates immediately
before deciding GO. V9 authorization and evidence cannot be inherited.

Only a fresh explicit decision may authorize one attended RAM-only v10 cycle.
That cycle must have no retry and no flash, require the exact compound result,
reboot immediately to fallback, prove fallback health and complete host
cleanup, and consume v10 regardless of outcome. Any failed or ambiguous
prerequisite keeps the decision at HOLD.
