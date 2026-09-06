# A660 GMU resume-entry v9 — protected-root offline acceptance

Date: 2026-07-26

Decision: **PASS offline / HOLD live. The consumed-v8-derived protected root,
signed/device-scoped trace oracle, exact-delta verifier, target compound gate,
and runtime mutation suite pass. This report does not authorize NFS, a phone
connection, a boot, a reboot, a live probe, a retry, GMU power preparation, or
flashing.**

The phone was not contacted. No SSH credential was used and no ADB, fastboot,
device-storage, or flash command ran. PolicyKit performed only the local
root-owned export operation without a sudo password.

## Fail-first checkpoint

The v9 umbrella contract was committed before the protected-root and gate
tools. Its first run failed at the first missing implementation:

```text
FAIL missing executable A660 GMU resume-entry v9 root tool: scripts/host/prepare-a660-gmu-resume-entry-v9-export.sh
```

The fail-first commit is `36c27fb`. The green implementation commit is
`de80737`.

After implementation, POSIX/Bash syntax, ShellCheck, the complete v9 runtime
mutation suite, the target-gate suite, the permanent v8 consumption test, and
the strengthened root umbrella contract all pass.

## Immutable rejected-and-consumed predecessor

The root derives only from:

```text
/var/lib/rog5-network-root-a660-gmu-resume-entry-v8
```

Before every construction or verification pass, the tooling reruns the
complete v8 root verifier and permanent consumption test. The predecessor
remains root-owned mode `0555`; its root-owned mode-`0444` seal remains:

```text
a6c14600ed17a52641f8700393d095e7cd86f2aa0d01c1f1f6bf649e283f2923
```

The v9 seal pins:

| Predecessor evidence | SHA-256 / identity |
|---|---|
| safe v8 live-rejection report | `fe5a6130cce3063ef6a0b1093d492d2a35763781f23af029c2959548cb092a9c` |
| v8 export verifier | `fe45a420b7241bea6dc3f37fc4beba5397221a8e27d747bd64baab0971181972` |
| v8 permanent-consumption test | `efbea8d09ecf81be8df32a0aaaffc55ecdd65209ef7fc1e1d71945a7d38180ec` |
| v8 consumption commit | `ff1250f` |
| registration-v3 marker | `8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f` |
| registration-v3 report | `2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79` |

The unchanged kernel/runtime evidence is also pinned:

| Evidence | SHA-256 |
|---|---|
| module archive | `38045b4c68d85d32dadf7d8db28f6ce1665fa2718ded3a9777dc0429035da6e7` |
| unchanged v8 `msm.ko` | `b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861` |
| GMU resume-entry boundary report | `41c06dcd895fcc873638ddf40dce0b0d5dd5bbf9e148f5d3abd5521b072c320d` |
| reproducible kernel-build report | `6c50a822d30368bba4564daa77633b6e22ae1e167cd3486670b786e430153b7c` |
| accepted kernel patch | `a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051` |
| v9 runtime report | `a9b99930799902cabf6c65bd877a21588b63ccb6b617d1ac526b9e0d159bf60d` |
| v9 runtime builder | `da8b18e6c995bbc2b7402b7be6d38577911c2258c2b131304865ab55ada0cafb` |
| v9 runtime verifier | `9e3f39e60d5edb06ea50ff2673bd818029274960af0e95c84f3e438a3d1c5ef1` |

## Protected copy-on-write root

PolicyKit created:

```text
/var/lib/rog5-network-root-a660-gmu-resume-entry-v9
```

The builder used `cp -a --reflink=always`. It removed exactly the v8 helper,
baseline, probe, and seal, then added only the versioned v9 helper, trace
oracle, baseline, probe, and seal. It did not replace the kernel, any module,
firmware, boot package, credential, host identity, service, or other rootfs
file.

The final root is root-owned mode `0555`. Its declared v9 inputs are:

| Export input | Mode | Size | SHA-256 |
|---|---:|---:|---|
| v9 export seal | `0444` | 2,644 | `137eb101708a8f96c063ed068caf7f8265641c43c228501fc578d5076be02bd5` |
| one-open helper | `0755` | 896 | `d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae` |
| signed/device-scoped trace oracle | `0755` | 4,764 | `48325037a54fe737aa4c623a1be59f644952bd21d9f13f0bba6a6563fea6f223` |
| generated baseline | `0755` | 12,598 | `337535cda800963bc1887203d1f60d9340b8fc5e9956f652a75bf26ada5d4ecc` |
| generated probe | `0755` | 38,454 | `078bb4cb2e6e1edac0182a22023121f2f6fbef2ec02715b7f3f6a5fe9338f387` |
| unchanged v8 `msm.ko` | `0644` | 12,397,072 | `b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861` |

The firmware set remains exactly SQE and GMU, with ZAP absent:

| Firmware | SHA-256 |
|---|---|
| `qcom/a660_sqe.fw` | `d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76` |
| `qcom/a660_gmu.bin` | `8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7` |
| `qcom/sm8350/a660_zap.mbn` | absent; reference `5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d` |

All seven modules are byte-identical to v8. The verifier also pins the
compiler relocations, all required trace symbols, three mode-`0400`
diagnostic parameters, exactly one versioned control set, and no surviving v8
control.

## Whole-tree and credential verification

Outside the five declared v9 controls and four removed v8 controls, the
verifier compares every regular-file hash, object type, mode, owner, group,
size, and symlink target against v8. The three parent directories necessarily
change entry-table size; their type, owner, group, and mode are compared
separately.

The verifier separately compares both authorized-key files, the Ed25519 SSH
host key pair, the accepted registration marker, all seven modules, and both
firmware files. No key material or credential path is copied into this
report.

Verification passed during staged construction and independently against the
published final path:

```text
PASS A660 GMU resume-entry v9 export modules=7 firmware=2 zap=absent helper=exact oracle=s32-device compiler=v8-relocations gmu_entry=EUCLEAN gpu_runtime_pm=device-scoped logical_vmap=4/4 gem_snapshot=equal credentials=preserved base=consumed-v8 root-owned mode 0555
```

Construction failed closed twice before the accepted root:

1. a malformed 63-digit registration-marker hash was rejected;
2. an over-strict metadata comparison rejected the unavoidable declared
   parent-directory size delta.

Both attempts removed their `.partial` roots. The accepted implementation
corrects the hash and narrows the directory exception to size only while
retaining exact type/ownership/mode and complete child comparisons. No partial
root remains.

## Runtime and compound target gate

The umbrella suite reruns the complete v9 runtime suite. It reproduces
byte-identical controls and rejects mutations to signed return width, GPU
device scope, oracle invocation, process-global PM counting, inner-resource
exclusion, settled snapshot equality, expected errno, authorization,
predecessor identity, parameter mode, and oracle hash.

The target gate requires both exact values:

```text
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_GATE=1
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_REBOOT=1
```

It checks storage-free OverlayFS, the exact read-only NFS lower, exact
baseline/probe/watchdog inputs, and Linux `7.1.4-rog5-a660reg1`. It runs the
baseline under the initial watchdog, starts an independent 240-second
transition watchdog, hands off the first watchdog, invokes exactly one v9
probe, and requests normal reboot only after all invariants pass.

Unlike rejected v8, the gate does not assert a process-global generic runtime
PM count. The installed oracle requires three normalized `-EUCLEAN` returns
and exactly one generic runtime-PM call whose device equals the GPU callback
device, while permitting additional classified generic calls.

Exact tool identities are:

| Tool | SHA-256 |
|---|---|
| strengthened root umbrella suite | `05a4cc134e11e91d7c830a835846acfca6041d073b55362d07024b5741795986` |
| protected-root builder | `ce50a0edcea90c6b7d6b59bbac4a824970876de0fc7fe06468ffa1e6b215cfdc` |
| protected-root verifier | `a3f526c6aa5e2f75af49a5b72b89ee24958ce23898e410e43749b482dde3179c` |
| compound target gate | `3922fdb46b587e543940b6703382568a81601fb50189f6b66231d1b62de629d2` |
| target-gate suite | `8fd487bb88bef19e45c28526e94ec7c78e783f395bd4ed82d4455662f9b697f1` |

The umbrella suite ends with:

```text
PASS A660 GMU resume-entry v9 root is consumed-v8-derived, exact-delta, signed-device-oracle guarded, runtime-mutation-tested, storage-free, target-gated, and HOLD
```

## Offline boundary

At the final check:

- `nfs-server.service`, `rpcbind.service`, and `rpcbind.socket` were inactive;
- there were zero NFS exports, mounts, or listeners on ports 111/2049;
- v8 remained absent from the bounded server;
- v9 had no bounded-server case or host live runner;
- no `.partial` v9 root remained; and
- the phone had not been contacted.

No credential, key material, phone identifier, or private evidence path is
committed.

## HOLD boundary

The protected root and target gate are accepted offline. Hardware use is not.
The next authorized work remains offline:

1. fail-first test and implement a strict one-invocation v9 host runner;
2. pin the root seal, target gate, unchanged RAM-only boot package, repository
   state, credentials, and private evidence boundary;
3. prove with a mock transport that there is exactly one prepare, copy,
   remote verification, and gate call, with no retry;
4. prove an actual unarmed invocation refuses before SSH or host-state
   mutation; and
5. record a separate pre-live HOLD checkpoint.

Only a later attended GO review may add one verifier-before-state,
explicit-opt-in v9 NFS case and decide whether one RAM-only cycle is
justified. Nothing here authorizes flashing, GMU power preparation, or reuse
of v8 authorization.
