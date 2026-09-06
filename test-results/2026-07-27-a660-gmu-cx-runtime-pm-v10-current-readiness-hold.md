# A660 GMU/CX runtime-PM v10 — current-branch readiness HOLD

Date: 2026-07-27

Decision: **PASS CURRENT READINESS; HOLD FOR LIVE USE. V10 is selected as the
next attended candidate because it advances the critical GPU-acceleration
path. No NFS window or RAM-only cycle is authorized by this checkpoint.**

No NFS, RPC, firewall, interface, listener, mount, boot, kexec, reboot,
fastboot, flash, module load, DRM open, phone write, or external-service
action ran. PolicyKit performed one complete read-only protected-root
verification and one deliberately unarmed server invocation. Pinned fallback
SSH was used only for the read-only recovery preflight.

This refresh builds on the original
[v10 kernel acceptance](2026-07-27-a660-gmu-cx-runtime-pm-v10-offline.md),
[runtime acceptance](2026-07-27-a660-gmu-cx-runtime-pm-v10-runtime-offline.md),
and
[protected-root/pre-live HOLD](2026-07-27-a660-gmu-cx-runtime-pm-v10-prelive-hold.md).
It does not replace those source, build, mutation, and recursive-root
arguments.

## Why v10 is next

Two independently prepared candidates are available:

| Candidate | What one cycle can prove | What it cannot prove |
|---|---|---|
| A660 GMU/CX runtime-PM v10 | the next bounded mainline GPU power-domain transition, exact rollback, and the first evidence needed before v11 clock preparation | rendering, Plasma, Wi-Fi, VPN/hotspot, or persistent installation |
| Arch successor v2 | modern headless systemd/SSH/server userspace, screen-off state, and a normal reboot from volatile OverlayFS | GPU acceleration or hardware rendering |

The persistent Alpine fallback already supplies a usable software-rendered
remote-server baseline, while GPU acceleration remains a hard blocker for the
requested final system. V10 therefore has higher critical-path value. The
Arch successor-v2 trial remains separately ready and is not consumed or
invalidated by this choice.

V11 remains deliberately non-runnable until v10 is live-tested and consumed.
The following current-state checks pass:

```text
v11_root=absent
v11_live_controls=absent
```

## Current synchronized checkpoint

The worktree was clean and local/remote heads were identical:

```text
branch=agent/linux-recovery-host
head=603a6be23f472648b2fc71602f30eaba7f27dc04
remote=603a6be23f472648b2fc71602f30eaba7f27dc04
```

The original v10 report recorded an earlier shared-server hash. The shared
server later gained the accepted successor-v1 path, so its whole-file identity
changed. The v10 guard, exact root, verifier-before-state order, consumed-root
exclusions, and common NFS/firewall runtime remain covered by the current
v10 server test. This refresh pins the current accepted server identity:

```text
serve-network-root.sh=e3961cc441ae6cb75f1a3dcbbd5e4ccc99b31c67018159ac10f61c11f1548769
```

No v10 target, runner, verifier, runtime builder, runtime verifier, or trace
oracle identity changed from the original HOLD.

## Current offline and control revalidation

The current branch returned:

```text
PASS A660 GMU/CX runtime-PM boundary is accepted-v9-dependent, source-pinned, get-error-balanced, synchronously rolled back, CX-only, and pre-GX
PASS A660 GMU/CX runtime-PM diagnostic patch is mutation-tested, exact-chip, atomic-stateful, get-error-balanced, synchronously rolled back, CX-only, and pre-GX
PASS A660 GMU/CX runtime-PM kernel build is exact-stack, unchanged-Image, modular, firmware-clean, rollback-safe, offline-only, and reproducible by contract
PASS A660 GMU/CX runtime-PM v10 runtime is reproducibly generated and rejects authorization, mode, trace, device, order, GX, state, snapshot, errno, module, predecessor, and parameter mutations
PASS A660 GMU/CX runtime-PM v10 trace oracle accepts exact balanced GMU/index-0-CX PM and rejects identity, order, state, rollback, or boundary mutations
PASS A660 GMU/CX runtime-PM v10 root is consumed-v9-derived, exact-delta, runtime-mutation-tested, storage-free, target-gated, one-shot, and server-inactive
PASS compound A660 GMU/CX runtime-PM v10 gate overlaps watchdogs, invokes one exact GMU/CX probe, and immediately reboots
PASS A660 GMU/CX runtime-PM v10 NFS window is exact-root, opt-in, verifier-first, bounded, and non-flashing
PASS host A660 GMU/CX runtime-PM v10 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries
```

The complete protected-root verifier then returned:

```text
PASS A660 GMU/CX runtime-PM v10 export modules=7 firmware=2 zap=absent helper=exact oracle=gmu-linked-cx module=v10-msm-only gmu_runtime_pm=1/1 cx_runtime_pm=1/1 gx_runtime_pm=0 clocks=0 secure=0 mmio=0 irq=0 firmware_start=0 hfi=0 logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=consumed-v9 root-owned mode 0555
```

One initial verifier command used a relative script path after PolicyKit
changed the working directory and returned status 127 before the verifier ran.
The absolute-path invocation above then completed successfully. Neither
invocation changed host or phone state.

## Actual current unarmed refusal

The current shared server was invoked through PolicyKit against:

```text
/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10
```

with `ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_NFS` explicitly absent. It
returned status 1:

```text
FAIL set ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_NFS=1 for the attended v10 window
```

Normalized before/after state was byte-identical:

```text
before_sha256=ecf4b906e413a67c17a15e91fa27c311360a6c644cdc6771a6553460a71f6221
after_sha256=ecf4b906e413a67c17a15e91fa27c311360a6c644cdc6771a6553460a71f6221
```

Normalization covered NFS/rpcbind/firewalld units, exports, listeners on
111/2049/32767, the temporary mount, mountd, NFS threads,
`ip_nonlocal_bind`, all runtime firewall zones, IPv4 interface/prefix
identity, v10 root metadata and seal, and v11-root absence.

Final host state remained:

```text
nfs-server=inactive
rpcbind=inactive
exports=0
listeners=0
temporary_mount=absent
```

## Connected fallback preflight

The exact guarded preflight passed through caller-owned pinned SSH material:

```text
PASS exact persistent fallback ready for guarded bootloader reboot
```

It verifies the exact `5.4.134-qgki-perf-00001-g6c308144c23e` fallback
kernel, BusyBox PID 1, `qcom,lahaina-mtp`, ext4 root, zero project modules,
empty pstore, no fatal kernel signatures, safe thermal telemetry, and Python
availability. A separate read-only check reported:

```text
id=alpine
version_id=3.24.0
brightness=0
```

The preflight action did not reboot the phone.

## Current control identities

| Input | SHA-256 |
|---|---|
| shared bounded NFS server | `e3961cc441ae6cb75f1a3dcbbd5e4ccc99b31c67018159ac10f61c11f1548769` |
| v10 NFS-window test | `82507ed29a555e01218fbe774d6ed6864bd9ce054bfc0e5d55557622a820fa21` |
| target compound gate | `785827f58cfde18130b4e36d5b201b93ed1232f5f4d9a41e8441cbcdcde937f4` |
| target-gate test | `607766dea103d74c020e837afd69d9df2a25eea09cd05cf3cc0f8df753c69162` |
| one-shot host runner | `c84f66f626c1e70c8dd28292eb42fc249d19e6f0e02479e80ceec5e5025c035d` |
| host-runner test | `9db350ea0727114d9e10bdfdec01a49264c22acc275ab2c82323f325b5d38bc4` |
| protected-root verifier | `f26d67a3267f34153fb672b30bcc9cede8bc4b5bef4f011fa2a3028473601743` |
| runtime builder | `a0bd091b1304581fe41bfcf1ceaa77a84fbbdd606d3797144a1e6685e1179942` |
| runtime-source verifier | `7141c437962b49a90574dc8e14987fad9d291b5d8ea8b9c3371ebf0c8af187b3` |
| exact trace oracle | `33ccadc6ae1e5f6f12ed83de0ddc192d30d204e229ec1b97aa813e1d0ac9c7e6` |

The protected-root seal remains:

```text
eaa44f2a7cef85e14d1b9dd0359b47d3cf10a5d5b05dafee77c085ce12a45cb4
```

## Remaining authorization boundary

This report selects a candidate; it does not authorize the candidate. A
fresh attended review must repeat the synchronized-Git, exact-input,
protected-root, private-credential/evidence, fallback, and host-zero-state
checks immediately before action.

Only a new explicit user instruction such as:

```text
GO A660 GMU/CX runtime-PM v10 one-cycle RAM-only diagnostic
```

may authorize opening the bounded NFS window and running exactly one
non-flashing v10 cycle. There is no retry. V10 must be consumed regardless of
pass, rejection, or ambiguous evidence, followed by exact fallback and host
cleanup verification.
