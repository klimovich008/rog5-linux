# A660 ucode-allocation v6 — offline root and gate acceptance

Date: 2026-07-26

Decision: **HOLD. The fresh compiler-pinned root, logical-vmap oracle,
mutation-tested gate, and unchanged temporary-boot package pass offline, but
this report does not authorize a phone cycle.**

The phone was not contacted. NFS was not started, no SSH credential was used,
no boot or reboot command ran, and nothing was flashed. The v6 root is absent
from the bounded NFS allowlist, and no v6 live host runner exists.

## Fail-first checkpoint

Commit `8beb7a584e5ab4b300efb87f0575119a2dcdb673` recorded the missing
v6 implementation before any new runtime, export, or gate tool existed. The
umbrella contract failed at its first missing input:

```text
FAIL missing executable A660 ucode-allocation v6 tool: .../build-a660-ucode-allocation-v6-runtime.sh
```

Implementation commit `b4a68e53e758bbb306aedd11a27adcd19a5b00aa`
adds the generated runtime, compiler-aware verifier, root preparation and
whole-tree verification, target compound gate, static/mutation tests, and
non-runnable HOLD enforcement.

## Why v6 does not rebuild the kernel

The v5 kernel completed its intended three-object allocation and rollback.
The rejection was a userspace trace-oracle error caused by Clang inlining,
not a changed kernel path. V6 therefore reuses the exact accepted module:

```text
fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45  msm.ko
```

The pinned relocation verifier SHA-256 is:

```text
56d63a17b6c89454691dbd74539c299d99e99b341831358d6f673f128a3181ae
```

It proves this exact module has:

- three logical `msm_gem_get_vaddr()` acquisitions inlined into
  `msm_gem_kernel_new()`;
- two logical `msm_gem_put_vaddr()` releases inlined into
  `msm_gem_kernel_put()`;
- one remaining public get-wrapper relocation;
- two remaining public put-wrapper relocations; and
- callable, unique `msm_gem_kernel_new` and `msm_gem_kernel_put` symbols for
  direct tracing.

That yields the compiler-specific live expectation `kernel_new=3`,
`kernel_put=2`, wrapper `get=1, put=2`, and logical balance `4/4`. A different
module or relocation layout fails closed.

## Reproducible runtime correction

V6 does not edit or relabel the consumed v5 runtime evidence. It derives two
new scripts from the immutable v5 sources using zero-fuzz patches:

| Input/output | SHA-256 |
|---|---|
| accepted v5 baseline | `4f2e50fd492c9fff06198396c1fd80fa877b1447f18920d9895ad82c4034e041` |
| accepted v5 probe | `63adc85bdd3b4f5b08130722d30615fad1a439eb3aa2a43a4b161e826c36c3ef` |
| v6 baseline patch | `02a61e41b20ae9974fa50f7bd602b4ebc4665d66c435a90a0edbfb81cf3ca5f8` |
| v6 probe patch | `f6458d465873a6d69c84f2bd12ae12bf482f342e6abd006bf10f3e1b898f2812` |
| generated v6 baseline | `5ad24829bd347fcc22239d761029f3c0f8064efa1b16e9f01b6cf745902df854` |
| generated v6 probe | `b90e33524da2558659a733c48d5670d2136208a9186d5abb3ecd79f1e28f2725` |

Generation uses:

```text
patch --batch --fuzz=0 --no-backup-if-mismatch
```

and refuses changed sources, patches, pre-existing outputs, aliased output
paths, missing parents, or output-hash drift. Duplicate generation produced
byte-identical scripts.

The runtime verifier also pins the immutable v5 rejection report SHA-256
`0c65c98cc03a49d9e5c8a15b391dbe2b6014b5e791a8659c06cd7c2d0bf52fb9`
and requires `predecessor=v5_live_rejected_consumed` plus
`v5_reuse=FORBIDDEN`.

## Corrected trace and state oracle

The one stopped helper remains PID-filtered through tracefs before it is
continued into exactly one `openat()` of `/dev/dri/renderD128`. A future
single probe must establish all of the following:

| Evidence | Required result |
|---|---:|
| `adreno_load_ucode_only` entry / successful return | 1 / 1 |
| `msm_gem_vma_map` entry / successful return | 3 / 3 |
| `msm_gem_vma_unmap` / `msm_gem_vma_close` | 3 / 3 |
| `msm_gem_unpin_iova` / `msm_gem_free_object` | 3 / 3 |
| successful `msm_gem_kernel_new` returns | 3 |
| `msm_gem_kernel_put` | 2 |
| public `msm_gem_get_vaddr` / `msm_gem_put_vaddr` | 1 / 2 |
| logical vmap gets / puts | 4 / 4 |
| `request_firmware_direct` / `release_firmware` | 2 / 2 |
| helper status/output | exact `EUCLEAN` / `OPEN_ERRNO=117` |
| pre/post settled MSM GEM snapshot | byte-identical |

The three `kernel_new` sizes must sort exactly to 4,096, 4,096, and 45,056
bytes, and their three successful return pointers must be unique. The one
public get object must equal both public put objects. The two `kernel_put`
objects must be distinct, and their union with the public get object must
equal the three-object unpin/free set. Existing VMA, firmware-reference,
runtime-suspend, no-surviving-DRM-FD, warning/fault, display, and storage
relationships remain mandatory.

Nine PID-filtered forbidden probes remain fixed at zero:

- `msm_gpu_pm_resume`;
- `adreno_runtime_resume`;
- `a6xx_pm_resume`;
- `a6xx_gmu_resume`;
- `adreno_hw_init`;
- `a6xx_hw_init`;
- `a6xx_zap_shader_init`;
- `qcom_scm_pas_auth_and_reset`; and
- `qcom_scm_set_gpu_smmu_aperture`.

The verifier rejects the old four-public-wrapper oracle, missing direct
kernel-new/kernel-put probes, changed counts, missing logical object-set
equality, missing GEM snapshot equality, wrong firmware or predecessor,
unfiltered traces, a second open, wrong errno, mixed diagnostic modes, and
probe-level reboot bypass.

## Compound watchdog gate

The target gate requires both exact authorization values:

```text
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V6_GATE=1
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V6_REBOOT=1
```

It verifies the storage-free OverlayFS/NFS-lower environment, exact generated
runtime hashes, and exact initial-watchdog disarm helper SHA-256
`733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc`.
It runs the zero-action baseline while the initial SysRq watchdog remains
armed, starts an independent 240-second SysRq transition watchdog, hands off
the initial watchdog, invokes the corrected probe exactly once, and requests
an immediate normal reboot only after a complete probe PASS.

The gate tests prove this ordering, both guards, exact one-invocation counts,
watchdog overlap, and rejection of host/device transport, module removal,
physical-storage write, or mount paths. It is intentionally not exposed by a
host runner or NFS server case.

## Root-owned export

PolicyKit created:

```text
/var/lib/rog5-network-root-a660-ucode-allocation-v6
```

It is root-owned mode `0555`, derives only from the accepted registration-v3
root by Btrfs reflink, and passed the complete protected verifier before its
atomic rename and twice afterward. The whole-tree verifier compares all
undeclared metadata and file hashes against the base and preserves both
authorized-key files and the SSH host identity.

Its Btrfs accounting is:

| Root | Logical bytes | Exclusive bytes | Set-shared bytes |
|---|---:|---:|---:|
| registration v3 | 5,593,767,936 | 12,374,016 | 3,004,542,976 |
| ucode-allocation v6 | 5,593,903,104 | 12,439,552 | 3,004,596,224 |

Exact installed inputs are:

| Export input | Mode | SHA-256 |
|---|---:|---|
| v6 export seal | `0444` | `e9a9bf460b62d91c44fa15b8258ae5a5660ef387846530e8cf93fce67f7f17ea` |
| registration-v3 marker | `0444` | `8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f` |
| ucode-allocation `msm.ko` | `0644` | `fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45` |
| one-open helper | `0755` | `d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae` |
| generated baseline | `0755` | `5ad24829bd347fcc22239d761029f3c0f8064efa1b16e9f01b6cf745902df854` |
| generated probe | `0755` | `b90e33524da2558659a733c48d5670d2136208a9186d5abb3ecd79f1e28f2725` |
| `qcom/a660_sqe.fw` | `0644` | `d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76` |
| `qcom/a660_gmu.bin` | `0644` | `8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7` |
| `qcom/sm8350/a660_zap.mbn` | absent | pinned input `5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d` |

The protected verifier returned:

```text
PASS A660 ucode-allocation v6 export modules=7 firmware=2 zap=absent helper=exact compiler=relocations logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=registration-v3 root-owned mode 0555
```

A copy-on-write mutation changed only the predecessor seal from consumed to
unconsumed. The same verifier rejected that root; the temporary mutation root
was then removed. No failed partial export remains.

## Unchanged kernel build and boot package

V6 changes only the evidence oracle. The two accepted ucode-allocation kernel
builds remain byte-identical, and the build contract still reports an
unchanged Image with the exact MSM-only predecessor delta:

```text
PASS A660 ucode-allocation kernel build is exact-stack, unchanged-Image, modular, firmware-clean, rollback-safe, and reproducible by contract
PASS two clean A660 ucode-allocation builds are byte-identical and the ucode-allocation MSM module differs only from its accepted firmware-only predecessor
```

No boot package was rebuilt. The existing temporary AVB image remains exactly
100,663,296 bytes with SHA-256
`c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c`.
Its fourteen-file `SHA256SUMS` manifest remains
`c4b9a2ec5afdd73a555031425a5eaedf5ab97a36a69eeefdcfede279ad7ffcd0`.
The registration package contract re-passed.

## Consolidated offline result

All new shell tools pass Bash/POSIX syntax, ShellCheck 0.11.0, runtime and
semantic mutation suites, target-gate ordering tests, compiler-relocation
tests, root/export tests, consumed-v5 lockout, and `git diff --check`. The
umbrella suite ends with:

```text
PASS A660 ucode-allocation v6 is compiler-pinned, logical-vmap-balanced, snapshot-guarded, storage-isolated, non-runnable, and pre-live HOLD
```

At the implementation checkpoint, branch `agent/linux-recovery-host` was
clean, synchronized with GitHub at
`b4a68e53e758bbb306aedd11a27adcd19a5b00aa`, and contained no credential
material.

After all root tests:

- `nfs-server.service`, `rpcbind.service`, and `rpcbind.socket` were inactive;
- there were zero NFS exports, mounts, port 111/2049 listeners, or
  `rpc.mountd`/`rpc.nfsd` processes;
- `net.ipv4.ip_nonlocal_bind` remained zero;
- the v6 root had zero server allowlist cases and no live host runner;
- zero partial or mutation roots remained; and
- the phone had not been contacted.

## HOLD boundary

Offline preparation is accepted. Hardware use is not.

Before any phone boot, a separate attended review must:

1. fail-first test and implement a new exact one-invocation v6 host runner;
2. recheck a clean synchronized Git checkpoint, exact root/package/gate
   hashes, inactive NFS, credentials, and persistent fallback health;
3. add only an explicit verifier-first v6 NFS case for that bounded window;
4. create fresh private evidence storage and prove unarmed refusal;
5. use only the accepted RAM-only temporary boot path, never flash;
6. invoke v6 at most once and require the full corrected trace plus equal
   post-settle GEM snapshot before reboot; and
7. prove exact fallback and complete host cleanup, then consume v6 regardless
   of pass or rejection.

V5 authorization cannot be inherited or reused.
