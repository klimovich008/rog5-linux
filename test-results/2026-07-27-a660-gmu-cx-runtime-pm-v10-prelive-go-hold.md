# A660 GMU/CX runtime-PM v10 — attended-GO review HOLD

Date: 2026-07-27

Decision: **PASS EVERY CURRENT TECHNICAL PREREQUISITE; HOLD FOR USER
AUTHORIZATION. V10 remains the selected next live GPU boundary. No NFS
window, reboot, Fastboot transition, RAM-only boot, module load, or DRM open
ran.**

This review was performed after the successor-v3 Arch root gained its
separate protected export and inert live controls. It refreshes current
technical readiness; it does not inherit or create live authority.

## Why v10 remains next

The persistent Alpine fallback already provides a usable software-rendered
screen-off remote server. Successor v3 now provides a protected modern Arch
userspace candidate with the confined power-button service, but booting it
cannot prove GPU acceleration.

V10 isolates the next unconsumed A660 dependency: one normal GMU consumer
runtime-PM transition and its linked index-0 CX supplier transition, followed
by synchronous rollback. That evidence is required before v11 can test clock
preparation. V11 remains non-runnable:

```text
v11_root=absent
v11_live_controls=absent
```

Any v10 authorization applies only to v10. It does not authorize successor
v3, v11, persistent installation, or flashing.

## Synchronized evidence checkpoint

The technical review started from a clean public checkpoint:

```text
branch=agent/linux-recovery-host
head=67a2b199e24a0488e1ec2aeeb3e24043347240ce
remote=67a2b199e24a0488e1ec2aeeb3e24043347240ce
```

The current control identities remain exactly those accepted by the earlier
[readiness HOLD](2026-07-27-a660-gmu-cx-runtime-pm-v10-current-readiness-hold.md):

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

The temporary staging boot image remains:

```text
sha256=c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c
```

## Current offline revalidation

All current suites passed:

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
PASS fallback reboot helper is identity-pinned, restart2-only, guarded, and fastboot-verifying
```

These cover the source boundary, twelve patch mutations, deterministic build
contract, fourteen runtime mutations, trace-oracle mutations, protected-root
contract, nested-watchdog ordering, verifier-first exact-root server case,
strict SSH, one invocation, one fallback reboot request, and no retry.

## Complete protected-root verification

PolicyKit performed the full recursive, read-only v10-to-consumed-v9
comparison:

```text
PASS A660 GMU/CX runtime-PM v10 export modules=7 firmware=2 zap=absent helper=exact oracle=gmu-linked-cx module=v10-msm-only gmu_runtime_pm=1/1 cx_runtime_pm=1/1 gx_runtime_pm=0 clocks=0 secure=0 mmio=0 irq=0 firmware_start=0 hfi=0 logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=consumed-v9 root-owned mode 0555
```

The protected root remains:

```text
path=/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10
owner_mode=0:0:0555
seal_sha256=eaa44f2a7cef85e14d1b9dd0359b47d3cf10a5d5b05dafee77c085ce12a45cb4
base=/var/lib/rog5-network-root-a660-gmu-resume-entry-v9
modules=7
firmware_files=2
zap=absent
delta=v10-msm-only
```

The verifier accepts only one deliberate `EUCLEAN` open rejection, one exact
GMU resume/suspend pair, one linked-CX resume/suspend pair, both domains
settled suspended, balanced firmware/allocation/mapping rollback, and equal
GEM snapshots. It rejects GX, clocks, secure setup, MMIO, IRQ, firmware
start, HFI, hardware initialization, ZAP/SCM, storage, retained DRM
descriptors, warnings, and faults.

## Actual unarmed refusal

The current shared server was invoked through PolicyKit against the exact v10
root with `ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_NFS` absent. It returned:

```text
FAIL set ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_NFS=1 for the attended v10 window
status=1
```

Normalized NFS/RPC/firewalld units, exports, listeners, temporary mount,
mount daemon, NFS threads, `ip_nonlocal_bind`, firewall zones, IPv4 interface
state, v10 root/seal, and v11-root absence were byte-identical:

```text
before_sha256=05732f01752ea0b6dfe19dec11dfab628e765c105c76550507e23897aa7514b3
after_sha256=05732f01752ea0b6dfe19dec11dfab628e765c105c76550507e23897aa7514b3
```

Final host state remained:

```text
nfs-server=inactive
rpcbind=inactive
exports=0
listeners=0
temporary_mount=absent
```

## Connected fallback preflight

The caller-owned SSH key and known-hosts files are both mode `0600`. Their
bodies were not printed, copied, or committed. The guarded action was
explicitly `preflight`, so its reboot/Fastboot branch was unreachable.

The exact fallback check returned:

```text
PASS exact persistent fallback ready for guarded bootloader reboot
id=alpine
version_id=3.24.0
brightness=0
```

It verifies the exact fallback kernel, BusyBox PID 1,
`qcom,lahaina-mtp`, ext4 root, zero project diagnostic modules, empty pstore,
zero fatal kernel signatures, safe thermal telemetry, and Python
availability. It did not reboot or write the phone.

## HOLD reason and sole authorization boundary

No technical prerequisite currently contradicts one attended v10 cycle. The
review remains HOLD because the required fresh user decision is absent.

Only this exact new user instruction may authorize the next live action:

```text
GO A660 GMU/CX runtime-PM v10 one-cycle RAM-only diagnostic
```

If supplied, it authorizes only:

- one attended, temporary, RAM-only v10 diagnostic;
- the exact verifier-first bounded NFS window and exact protected root;
- the exact compound target/runner invocation with nested watchdogs;
- immediate normal fallback and complete cleanup verification; and
- permanent consumption of v10 regardless of pass, rejection, or ambiguity.

It does not authorize retry, flashing, persistent storage changes, v11,
successor v3, credentials, accounts, or external services. Until that exact
instruction is supplied, no NFS start, reboot, boot, module load, or DRM open
may occur.
