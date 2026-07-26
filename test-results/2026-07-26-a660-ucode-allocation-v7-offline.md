# A660 ucode-allocation v7 — corrected raw-size offline acceptance

Date: 2026-07-26

Decision: **HOLD. The source-pinned raw-size correction, immutable v6
predecessor, reproducible runtime, compound watchdog gate, protected
copy-on-write root, whole-tree verification, and negative mutation suite pass
offline. This report does not authorize a phone boot or live probe.**

The phone was not contacted. NFS was not started, no SSH credential was used,
no ADB, fastboot, boot, reboot, or flash command ran, and no phone storage was
exposed. The v7 root has no bounded-server case and no live host runner.

## Fail-first and implementation checkpoints

Fail-first commit
`78aa31ded30c8e3062bb449d61d18235a7625822` added the v7 umbrella
contract before its implementation. The contract rejected the absent v7
runtime/export/report path.

Runtime implementation commit
`fadb6d468e374b6cb95744a4ccb489dfb545d2be` added the immutable-v6
derivation, source/relocation verifier, semantic mutation suites, corrected
target baseline and probe, and compound watchdog gate.

Protected-export commit
`a177577a1b28fc11c9ed7eaf9fa4c2a3ce12f49f` added a PolicyKit-only
builder, complete predecessor and candidate verifier, exact-delta tree
comparison, offline non-runnable contract, and two changed-seal negative
tests.

## Why v7 does not rebuild the kernel

The sole v6 cycle reached the exact diagnostic, requested both firmware
files, created all three GEM objects, emitted the kernel's successful
allocation-and-rollback marker, and traced complete rollback. Its userspace
gate rejected a value-layer mismatch: a function-entry kprobe observes raw
arguments, while the expected set contained page-rounded object sizes.

The immutable rejection report is pinned by SHA-256:

```text
cfdd0837e6da7d06ba74e0557c6abeea396f12f02e345d9ab87ba1a47ade89e6
```

V7 therefore changes only the userspace oracle and diagnostic generation. It
reuses the exact accepted MSM module:

```text
fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45  msm.ko
```

The compiler-relocation verifier remains:

```text
56d63a17b6c89454691dbd74539c299d99e99b341831358d6f673f128a3181ae
```

It still requires three logical gets inlined into
`msm_gem_kernel_new()`, two logical puts inlined into
`msm_gem_kernel_put()`, public wrapper counts `get=1, put=2`, and logical
vmap balance `4/4`. A changed module or relocation layout fails closed.

## Two explicit size layers

The immutable source-boundary report SHA-256 is:

```text
a17847d18c21d5b2c039df4353a899abce37159ec0009b5afaa0dda6067d146f
```

It proves both layers independently:

| Allocation | Raw `msm_gem_kernel_new()` entry argument | Page-rounded GEM object |
|---|---:|---:|
| SQE firmware (`fw->size - 4`) | 43,288 | 45,056 |
| one-ring RPTR shadow (`sizeof(u32)`) | 4 | 4,096 |
| power-up register list (`PAGE_SIZE`) | 4,096 | 4,096 |

The v7 seal and verifier therefore require:

```text
size_policy=RAW_KERNEL_NEW_ENTRY_ARGUMENTS
raw_size_contract=4,4096,43288
object_size_policy=SOURCE_PINNED_PAGE_ALIGN
object_size_contract=4096,4096,45056
```

The live entry oracle is only the sorted raw set `4`, `4096`, `43288`.
Page-rounded sizes remain source-pinned as a separate invariant and are not
substituted into the kprobe observation.

## Reproducible runtime

V7 derives from the immutable generated v6 runtime with two zero-fuzz
patches. It never edits or relabels the consumed v6 files.

| Runtime input/output | SHA-256 |
|---|---|
| v7 baseline patch | `6a2e3d5d5d54fc18cc6422052aeee25c9533f219bf2b6b2e5b14eace21d8aeb9` |
| v7 probe patch | `605f88b8f34eed6018a97d063fb496212fe04cb11c029d02424060318336c9a5` |
| v7 runtime builder | `ac4412f6710b1c6bb1d6f87bb6850157aa136a55301db84884843784bae6bf7c` |
| v7 source verifier | `7f73923dd8d1a3b30a0bfd3a76bc8eb51e262ad5dc6a72fc69620e5b9729540a` |
| generated v7 baseline | `d8c2d697d20c213f3528d6a4cf99ca7d0243bf83222a34ff6f665ab22fc27386` |
| generated v7 probe | `01a681bdf9fc17b3c676797cafadc43338eee49f2a5e3b7c6789edc1c7056cf0` |

Generation uses:

```text
patch --batch --fuzz=0 --no-backup-if-mismatch
```

The runtime suite reproduced both outputs and rejected mutations to raw and
page-rounded size layers, trace counts/order, PID filtering, logical object
balance, settled snapshot equality, predecessor/report identity, firmware,
watchdog handling, storage isolation, and stale v6 controls.

## Retained live evidence contract

A future single diagnostic must still establish every v6 rollback invariant:

| Evidence | Required result |
|---|---:|
| diagnostic entry / successful return | 1 / 1 |
| firmware request / release | 2 / 2 |
| VMA map entry / successful return | 3 / 3 |
| VMA unmap / close | 3 / 3 |
| GEM unpin / free | 3 / 3 |
| successful `msm_gem_kernel_new` returns | 3 |
| `msm_gem_kernel_put` | 2 |
| public get / put wrappers | 1 / 2 |
| logical vmap gets / puts | 4 / 4 |
| helper invocation / result | 1 / exact `EUCLEAN` |
| post-run settling | 20 seconds |
| pre/post MSM GEM snapshot | byte-identical |

The three successful kernel-new pointers must be unique. Public-wrapper,
kernel-put, unpin, and free object sets must satisfy the pinned union
relationships. Power/runtime-resume, GMU/HFI, hardware initialization,
ZAP/SCM, surviving DRM descriptors, storage, mounts, failed systemd units,
new warnings/faults, and thermal-limit violations remain forbidden.

## Compound target gate

The target gate SHA-256 is:

```text
f7f223b62521306007c9ac224f008c0a9e6f85fdbdcac1529bf7c8e3a9ea3d1e
```

It requires both exact future authorization values:

```text
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_GATE=1
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_REBOOT=1
```

It verifies the storage-free OverlayFS/read-only-NFS environment and exact
runtime hashes, keeps the initial SysRq watchdog armed through the baseline,
starts an independent 240-second transition watchdog, hands off the initial
watchdog, invokes the corrected probe once, and requests a normal reboot only
after the complete probe passes. Its mutation suite proves guard, ordering,
hash, one-invocation, overlapping-watchdog, and reboot-bypass constraints.

This gate is not installed in a host runner and v7 is absent from the bounded
NFS server. It cannot currently be launched against hardware.

## Protected copy-on-write root

PolicyKit created:

```text
/var/lib/rog5-network-root-a660-ucode-allocation-v7
```

It is root-owned mode `0555` and derives only from the immutable consumed v6
root using `cp -a --reflink=always`. Before copying, the builder reverified
the entire v6 root against accepted registration-v3, required its permanent
server lockout, and pinned:

```text
e9a9bf460b62d91c44fa15b8258ae5a5660ef387846530e8cf93fce67f7f17ea  v6 predecessor seal
```

The derivation removed only the v6 helper, baseline, probe, and seal, then
installed their v7 counterparts. The verifier compared all undeclared file
content, metadata, symlink targets, module/firmware identities, registration
marker, both authorized-key files, and SSH host identity against v6.

Exact installed v7 controls are:

| Export input | Mode | Size | SHA-256 |
|---|---:|---:|---|
| v7 export seal | `0444` | 2,224 | `c679ff6cbed6aefb28b7537cd30c561948e4d4672cd9320a8e70fd3d79b4f046` |
| one-open helper | `0755` | 896 | `d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae` |
| generated baseline | `0755` | 11,469 | `d8c2d697d20c213f3528d6a4cf99ca7d0243bf83222a34ff6f665ab22fc27386` |
| generated probe | `0755` | 32,964 | `01a681bdf9fc17b3c676797cafadc43338eee49f2a5e3b7c6789edc1c7056cf0` |

The inherited accepted payload remains:

| Export input | Mode | SHA-256 |
|---|---:|---|
| `msm.ko` | `0644` | `fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45` |
| `qcom/a660_sqe.fw` | `0644` | `d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76` |
| `qcom/a660_gmu.bin` | `0644` | `8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7` |
| `qcom/sm8350/a660_zap.mbn` | absent | pinned reference `5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d` |

Current Btrfs accounting confirms the derivation shares the payload:

| Root | Total | Exclusive | Set shared |
|---|---:|---:|---:|
| consumed v6 | 5.21 GiB | 48.00 KiB | 2.80 GiB |
| corrected v7 | 5.21 GiB | 48.00 KiB | 2.80 GiB |

The protected verifier passed during preparation and again independently:

```text
PASS A660 ucode-allocation v7 export modules=7 firmware=2 zap=absent helper=exact raw_sizes=4,4096,43288 object_sizes=4096,4096,45056 compiler=relocations logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=consumed-v6 root-owned mode 0555
```

Two separate reflink mutation roots changed only:

1. consumed predecessor to unconsumed; and
2. the raw-size contract to the page-rounded set.

The exact verifier rejected both. The mutation roots and every partial export
were removed; the protected original remained unchanged.

## Unchanged boot package

No kernel or boot package was rebuilt. The existing RAM-only temporary image
remains:

| Input | Size | SHA-256 |
|---|---:|---|
| temporary-boot AVB image | 100,663,296 | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |

Nothing in this offline checkpoint authorizes using that image.

## Consolidated offline result

All v7 shell tools pass POSIX/Bash syntax, ShellCheck 0.11.0, reproducible
generation, source/relocation checks, semantic runtime mutations,
independent probe mutations, compound-gate ordering/guard tests, protected
root verification, exact-delta tree comparison, changed-seal mutations,
consumed-v6 lockout, non-runnable enforcement, and `git diff --check`.

The umbrella suite ends with:

```text
PASS A660 ucode-allocation v7 is raw-size-pinned, compiler-pinned, logical-vmap-balanced, snapshot-guarded, storage-isolated, non-runnable, and offline-only
```

After root construction and testing:

- `nfs-server.service`, `rpcbind.service`, and `rpcbind.socket` were inactive;
- there were zero NFS exports, port 111/2049 listeners, export mounts,
  `rpc.mountd`, or `rpc.nfsd` processes;
- `net.ipv4.ip_nonlocal_bind` was zero;
- the v7 root had zero bounded-server cases and zero live host runners;
- zero partial or mutation roots remained; and
- the phone had not been contacted.

No credential, private key, phone identifier, or private evidence path is
committed.

## HOLD boundary

Offline v7 preparation is accepted. Hardware use is not.

Before any phone boot, a separate checkpoint must:

1. fail-first test and implement an exact one-invocation v7 host runner with
   strict SSH identity, immutable inputs, private evidence, no retry, and no
   NFS/boot/flash authority;
2. retain **HOLD** and verify the runner independently;
3. in a later attended review, require clean synchronized Git, exact
   fallback, credentials, package/root/gate/runner hashes, and inactive host
   services;
4. add only one verifier-first, explicit-opt-in v7 NFS case;
5. prove an actual unarmed invocation refuses with zero residue;
6. authorize at most one RAM-only cycle under both watchdogs, never flash;
7. require the complete raw-size, pointer-union, logical `4/4`, rollback, and
   equal settled-snapshot contract before normal reboot; and
8. restore exact fallback, prove complete host cleanup, then consume v7
   regardless of pass or rejection.

No v5 or v6 authorization, server case, credential decision, or live result
may be inherited.
