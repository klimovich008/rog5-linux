# A660 GMU resume-entry v8 — pre-live control acceptance and HOLD

Date: 2026-07-26

Decision: **HOLD. The exact one-invocation v8 host control plane passes
offline, but this checkpoint does not authorize a phone cycle.**

The phone was not contacted. NFS was not started, no network authentication
occurred, no boot or reboot command ran, and nothing was flashed. The
protected v8 root remains absent from the bounded NFS allowlist.

## Fail-first host control

Commit `6421767` records the missing-runner failure:

```text
FAIL missing host A660 GMU resume-entry v8 live-gate runner
```

Commit `f1e7ae79f0018674de31342217d4847ed41e7b15` adds the guarded
runner and integrates its mock suite with the protected-export and v8 root
contracts.

Exact control identities are:

| Input | SHA-256 |
|---|---|
| one-invocation host runner | `9aaa6da8e115392f4274cead402f017c7772407ecfa6950220942b0b8181e8c5` |
| host-runner mock suite | `36d2fc6c6fad6e2a587f4e5a0f380aa826ccada881db25ff854e53f2693f7872` |
| target compound gate | `62050d15c16cc3a6e4bc11bd7ad3eeee4eb5026de51c4a51d6c61762764182d8` |
| watchdog-disarm helper | `733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc` |
| protected-root verifier | `fe45a420b7241bea6dc3f37fc4beba5397221a8e27d747bd64baab0971181972` |
| v8 export seal | `a6c14600ed17a52641f8700393d095e7cd86f2aa0d01c1f1f6bf649e283f2923` |
| unchanged RAM-only AVB image | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |
| integrated export suite | `388591bf904eb48da565ccd2253a30819cddd198625e47ad8e6d055bd919c53a` |
| integrated root umbrella | `5ff34253b33bd6b81c6095092bbffd4a978d2aa22159ebc682c13f2a7dedf21d` |

## Guard and local preconditions

The runner requires both exact authorization values:

```text
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_LIVE_GATE=1
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_REBOOT=1
```

Both guards are checked before repository inspection, credentials, PolicyKit,
SSH, or any stateful action. Missing or non-exact values fail immediately.

The runner then requires:

- clean Git on `agent/linux-recovery-host`;
- local `HEAD` equal to `origin/agent/linux-recovery-host`;
- caller-owned mode-`0600` regular `SSH_KEY` and `KNOWN_HOSTS` files;
- a caller-owned mode-`0700` existing `EVIDENCE_DIR`;
- all credentials and evidence outside the repository;
- exact hashes for the unchanged RAM-only boot image, watchdog helper,
  target gate, and protected-root verifier; and
- complete PolicyKit verification of the protected v8 root against the
  immutable consumed v7 predecessor before SSH.

The boot-image input is only hash-checked. The runner has no fastboot, ADB,
boot, flash, NFS, server, module-removal, physical-mount, or storage-write
command.

## Strict target identity and one invocation

SSH is fixed to:

- `BatchMode=yes`;
- `IdentitiesOnly=yes`;
- exact `HostKeyAlias=rog5-network-root`;
- `StrictHostKeyChecking=yes`;
- one explicit known-hosts file;
- one connection attempt;
- bounded connect and keepalive failure; and
- no global SSH configuration.

The runner performs exactly:

1. one complete local protected-root verification through PolicyKit;
2. one remote tmpfs-control-directory prepare call;
3. one SCP invocation carrying exactly the watchdog helper and target gate;
4. one remote ownership, mode, count, hash, seal, and registration-marker
   verification call; and
5. one target-gate call.

The target control directory may contain only two root-owned mode-`0500`
files. The remote verifier pins the mode-`0444` v8 seal and checks:

- `diagnostic_generation=v8`;
- immutable accepted-and-consumed v7 predecessor and report;
- exact v8 module archive and MSM module;
- exact SQE/GMU firmware with ZAP absent;
- exact source-boundary, build-report, kernel-patch, and compiler-relocation
  identities;
- exact generated baseline and probe hashes;
- SQE/GMU-only firmware policy and exactly one `EUCLEAN`;
- raw and page-rounded allocation-size layers;
- PID-filtered GMU-entry and logical-vmap trace policy;
- equal pre/post GEM snapshots;
- mode-`0400` GMU-entry parameter; and
- the accepted registration-v3 marker.

The only remote execution command sets the exact target-gate and reboot
guards and invokes the pinned compound gate once.

## Required evidence and reboot disconnect

The private live log would be accepted only if it contains:

- the complete zero-action v8 baseline PASS;
- one exact failed open with `OPEN_ERRNO=117`;
- `gmu_resume_entry_only=Y`, both predecessor diagnostic modes `N`, and two
  firmware requests/releases;
- exactly one lazy-load, runtime-resume, GMU PM-resume, GMU-resume, entry-hit,
  and rollback route;
- one outer and zero inner runtime-PM calls;
- zero clocks, IRQ, HFI, devfreq, LLC, hardware-init, ZAP, and SCM activity;
- accepted three-object rollback, public wrapper `1/2`, logical vmap `4/4`,
  and equal GEM snapshots; and
- the compound transition-watchdog and normal-reboot-request PASS.

SSH must then return nonzero because the target reboots. A normal gate return
is rejected. The log is created under `umask 077` and forced to mode `0600`.

The mock transport suite proves the exact call counts and expected reboot
disconnect:

```text
PASS host A660 GMU resume-entry v8 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries
```

## Local credential readiness

The user explicitly authorized use of the separate phone SSH credential.
This checkpoint used it only for local fingerprint comparison; no SSH
connection or authentication attempt occurred.

Without printing or recording fingerprint values, the local checks prove:

- the private and public client keys agree and are Ed25519;
- the known-hosts file contains one `rog5-network-root` identity;
- that identity matches the protected v8 Ed25519 server host key; and
- both protected v8 `authorized_keys` files contain the same client public
  key.

No credential content, fingerprint value, private path, or phone identifier
is committed.

## Rechecked root and host boundary

At implementation checkpoint
`f1e7ae79f0018674de31342217d4847ed41e7b15`:

- the branch was clean and synchronized with GitHub;
- the complete protected v8 export verifier passed again;
- the root remained root-owned mode `0555` with exact seven modules, two
  firmware files, ZAP absent, generated runtime, compiled relocations,
  logical `4/4`, equal-snapshot requirement, and preserved credentials;
- `nfs-server.service`, `rpcbind.service`, and `rpcbind.socket` were inactive;
- there were zero NFS exports, mounts, or listeners on ports 111/2049;
- the bounded server still had no v8 case;
- no real v8 evidence directory or log was created; and
- an actual unarmed invocation refused with:

```text
FAIL set ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_LIVE_GATE=1 for the one-shot gate
```

NFS/RPC state remained inactive after that refusal.

## Consolidated contract

POSIX/Bash syntax, ShellCheck 0.11.0, runtime mutations, target-gate ordering,
protected-export exact-delta and mutation checks, consumed-v7 lockout,
one-shot runner mock, local credential agreement, actual unarmed refusal, and
`git diff --check` pass.

The integrated umbrella suite ends with:

```text
PASS A660 GMU resume-entry v8 root is consumed-v7-derived, exact-delta, mutation-tested, host-runner-tested, storage-free, non-runnable, and pre-live HOLD
```

## Why the decision remains HOLD

Host-control acceptance is not a live-window or fallback acceptance. This
review intentionally did not:

- contact the phone or inspect its current fallback/bootloader state;
- create private live evidence;
- add v8 to the bounded NFS server;
- start NFS, configure the USB peer, or open SSH;
- issue a temporary boot command; or
- invoke the target gate.

The protected root therefore remains non-runnable, and HOLD is mandatory.

## Requirements to lift HOLD

A separate attended GO review must:

1. fail-first test and implement one explicit-opt-in, exact-v8-root server
   case that runs the complete verifier before host-state mutation;
2. require clean synchronized Git and exact root, seal, verifier, package,
   watchdog, target-gate, and host-runner identities;
3. recheck the unchanged RAM-only package with its complete verifier;
4. confirm strict persistent fallback health, separate client/server SSH
   identities, safe thermals, and clean pstore/module state;
5. create a fresh caller-owned mode-`0700` private evidence directory;
6. prove unarmed runner and server invocations both refuse with zero residue;
7. open one bounded exact-peer, read-only NFSv4.2 window and use only the
   accepted RAM-only temporary-boot path, never flash;
8. invoke the v8 runner at most once; and
9. require immediate normal fallback, exact fallback health, complete host
   cleanup, and permanent v8 consumption regardless of pass or rejection.

No v7 authorization may be inherited, and no retry is permitted.
