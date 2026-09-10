# A660 GMU resume-entry v9 runtime — offline acceptance, live HOLD

Date: 2026-07-26

Decision: **the v9 signed-return and GPU-device-scoped userspace trace
oracles pass offline. V9 reuses the exact v8 kernel, Image, module set, and
`msm.ko`; no kernel rebuild is needed. Duplicate target controls are
byte-identical and the complete verifier rejects signed-width, device-scope,
oracle-bypass, process-global PM, inner-PM, snapshot, errno, inherited
authorization, predecessor, mode, and oracle-hash mutations. This accepts
only the offline runtime controls. V9 remains HOLD: no protected root,
target gate, host runner, NFS case, boot, phone contact, retry, or flash is
authorized.**

## Evidence-derived correction

The
[sole v8 live cycle](2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md)
proved two userspace assumptions false while the intended kernel boundary
remained fail-closed:

1. `adreno_runtime_resume()`, `a6xx_gmu_pm_resume()`, and
   `a6xx_gmu_resume()` return `int`. Arm64 supplied deliberate `-EUCLEAN` as
   zero-extended `4294967179`, while the v8 kretprobes declared `$retval` as
   signed 64-bit and compared it with textual `-117`.
2. The helper's syscall produced 21 process-scoped
   `__pm_runtime_resume()` events across GEM mapping, the GPU callback, and
   rollback. V8 assumed that this generic function would run once globally,
   even though it captured no device argument.

V9 changes no kernel bit. Its runtime trace now:

- records the three negative `int` returns as unsigned 32-bit transport;
- normalizes either signed `-117` or zero-extended `4294967179` to signed
  32-bit `-117`;
- records the `struct device *` argument at both
  `__pm_runtime_resume()` and `adreno_runtime_resume()`;
- requires every generic runtime-PM event to have a classified nonempty
  device field;
- requires exactly one generic event whose device equals the Adreno callback
  device and requires that event to precede the callback; and
- permits unrelated process-scoped runtime-PM events without weakening the
  direct zero probes on inner GPU/GMU resources.

## Fail-first chain

Commit `22fa6babd60e48d5c5c6b71e2f06aec9af5f2b95` records the
missing standalone checker:

```text
FAIL missing executable A660 GMU resume-entry v9 trace oracle
```

Commit `2fa3def528f6b15124c4494ce938155268fcd4c6` adds the
signed/device-scoped checker. Commit
`355ca7711aa1153e2181f113bff6c0febcf7585c` then records the
missing complete v9 runtime builder:

```text
FAIL missing executable A660 GMU resume-entry v9 runtime tool: .../build-a660-gmu-resume-entry-v9-runtime.sh
```

Commit `9867a9e53621ddfebb1ab4a2cf761c26a6e0a01e` adds the
source-locked builder, semantic patches, source verifier, duplicate
generation, and runtime mutations.

## Immutable predecessor

The builder requires permanent v8 consumption before generation:

```text
PASS A660 GMU resume-entry v8 is consumed and absent from the bounded NFS server
```

It pins:

| Input | SHA-256 |
|---|---|
| v8 safe live-rejection report | `fe5a6130cce3063ef6a0b1093d492d2a35763781f23af029c2959548cb092a9c` |
| v8 runtime builder | `95cc98935677617ddf504701858b4a068a25b71a9a9853735a26c7e590cb5a9d` |
| generated v8 baseline | `3a4bcdcd9a96b896f22fda3be3f73c68a3b16e5d154558da9ad299c969faaf23` |
| generated v8 probe | `832a96db228a9f0771c0ff364ed943100f243fbbce51ec4c0e2532e211a9e255` |
| unchanged v8 `msm.ko` | `b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861` |
| v8 consumption test | `efbea8d09ecf81be8df32a0aaaffc55ecdd65209ef7fc1e1d71945a7d38180ec` |

The exact v8 baseline and probe contain 9 and 208 lowercase version tokens.
The builder requires those counts, performs one deterministic `v8` to `v9`
name transform, requires no lowercase v8 token to survive that transform,
and then applies two pinned zero-fuzz semantic patches.

The v9 seal contract explicitly records:

```text
diagnostic_generation=v9
predecessor=v8_live_rejected_consumed
predecessor_consumption_commit=ff1250f
compiler_policy=PINNED_V8_MSM_RELOCATIONS
trace_policy=PID_FILTERED_SIGNED32_GPU_DEVICE_AND_LOGICAL_VMAP
state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL
gmu_entry_parameter_mode=0400
v8_reuse=FORBIDDEN
```

There is no inherited v8 environment authorization or v8 trace group.

## Reproducible controls

Two independent generations produced byte-identical controls:

| Output | SHA-256 |
|---|---|
| v9 baseline | `337535cda800963bc1887203d1f60d9340b8fc5e9956f652a75bf26ada5d4ecc` |
| v9 probe | `078bb4cb2e6e1edac0182a22023121f2f6fbef2ec02715b7f3f6a5fe9338f387` |

Generator and verifier identities are:

| Control | SHA-256 |
|---|---|
| v9 runtime builder | `da8b18e6c995bbc2b7402b7be6d38577911c2258c2b131304865ab55ada0cafb` |
| v9 runtime source verifier | `9e3f39e60d5edb06ea50ff2673bd818029274960af0e95c84f3e438a3d1c5ef1` |
| v9 runtime integrated test | `3f49fbdf2883a4497bc079720ed4608b662bbc89807a816d56b46b5d05d3edd0` |
| v9 baseline patch | `f5c996be5cccc8de45e87591ff1411ad1e6820c233bdcaadf078ecc76a0b0608` |
| v9 probe patch | `83b1df2cd462a6ea16e5471888a8bad11b343861d441758995a5a059929be04c` |
| standalone trace oracle | `48325037a54fe737aa4c623a1be59f644952bd21d9f13f0bba6a6563fea6f223` |
| standalone oracle test | `911d0cab1a0d312c4a217953e87189c3bfbcbd8b9fe32707019a8d112ddaf82c` |

The runtime verifier also reruns the unchanged v8 compiler-relocation
verifier against the exact `msm.ko`. This preserves the v7-proven
three-object allocation/rollback and logical-vmap semantics rather than
claiming a new kernel result.

## Standalone oracle tests

The test suite accepts:

- all three returns transported as zero-extended `4294967179`;
- all three returns already rendered as signed `-117`;
- three generic runtime-PM events with exactly one GPU-device match; and
- the evidence-derived 21 generic events with exactly one GPU-device match.

It rejects:

- a non-`EUCLEAN` return;
- a non-integer return;
- a value outside unsigned 32-bit transport;
- zero or two GPU-device matching runtime-PM calls;
- a matching outer call after the Adreno callback;
- a generic runtime-PM event with no device;
- duplicate Adreno callback entries; and
- a null Adreno device.

The exact result is:

```text
PASS A660 GMU resume-entry v9 trace oracle accepts signed/zero-extended EUCLEAN and rejects malformed returns or unscoped GPU runtime PM
```

## Complete runtime constraints

V9 retains every v8 check outside the two corrected oracles:

- one exact helper open and `OPEN_ERRNO=117`;
- one `adreno_load_gpu()` and accepted load rollback;
- one GMU-entry one-shot hit;
- exact two firmware requests/releases;
- three successful map/new operations and exact unmap/close/unpin/free sets;
- three kernel-new and two kernel-put operations;
- public wrapper counts `1 / 2` and logical vmap balance `4 / 4`;
- no direct inner `msm_gpu_pm_resume()` or `a6xx_pm_resume()`;
- zero clock, IRQ, HFI, devfreq, LLC, initial-frequency, hardware-init, ZAP,
  and SCM events;
- no retained DRM file descriptor, physical storage, or block-backed mount;
- full settle, equal pre/post GEM snapshots, safe thermals, healthy services,
  clean logs, and nested watchdog handling.

The runtime mutation suite independently rejects:

1. restoring signed-64 return transport;
2. omitting the Adreno callback device;
3. omitting the generic runtime-PM device;
4. bypassing the standalone oracle;
5. restoring a process-global runtime-PM count of one;
6. weakening the inner-PM forbidden set;
7. removing final GEM snapshot equality;
8. accepting a successful open;
9. inheriting v8 authorization;
10. changing predecessor state;
11. making the diagnostic parameter writable; and
12. changing the pinned oracle hash.

The complete result is:

```text
PASS A660 GMU resume-entry v9 runtime is reproducibly generated and rejects signed-width, device-scope, oracle, global-PM, inner-PM, snapshot, errno, authorization, predecessor, mode, and oracle-hash mutations
```

## Safety state and next gate

This work ran only against local files. It did not use PolicyKit, start NFS
or RPC, contact the phone, invoke fastboot/ADB/SSH, reboot anything, create a
protected root, or alter any kernel or device artifact.

Before any v9 live decision:

1. derive a fresh root-owned mode-`0555` v9 copy-on-write root from immutable
   consumed v8;
2. replace only the versioned baseline, probe, helper path, seal, and new
   standalone trace oracle; retain the exact v8 module, seven-module set,
   two firmware files, credentials, and every undeclared byte/metadata item;
3. independently verify whole-tree exact delta, seal/report identities,
   credentials, executable modes, no v8 authorization, and no storage;
4. build and mutation-test a fresh compound target gate and strict no-retry
   host runner;
5. keep v9 absent from the bounded NFS server during HOLD;
6. revalidate the unchanged temporary-boot package and exact fallback; and
7. publish separate pre-live HOLD and GO reviews before any one-cycle
   authorization.

No v9 live cycle or GMU power-preparation tier is authorized. HFI, ZAP/SCM,
successful render open, submission, rendering, display, suspend, and
accelerated desktop remain later independent boundaries.
