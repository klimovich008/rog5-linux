# A660 GMU resume-entry v9 — pre-live control acceptance and HOLD

Date: 2026-07-26

Decision: **HOLD. The exact one-invocation v9 host control plane passes
offline, but this checkpoint does not authorize a phone cycle.**

The phone was not contacted. NFS was not started, no network authentication
occurred, no boot or reboot command ran, and nothing was flashed. The
protected v9 root remains absent from the bounded NFS allowlist.

## Fail-first host control

Commit `b562da0` records the missing-runner failure:

```text
FAIL missing host A660 GMU resume-entry v9 live-gate runner
```

Commit `15d2879b1e0f4c6585be4a51fb54dc240c47f4db` adds the guarded
runner. Exact control identities are:

| Input | SHA-256 |
|---|---|
| one-invocation host runner | `40276c91803d1890b70152064ac47b56ddead96880f52932f11c16feb4ce485b` |
| host-runner mock suite | `81b30b738d9f63919116d9795ff9d16d6dbc520438902e8d290c4a25cf31354f` |
| target compound gate | `3922fdb46b587e543940b6703382568a81601fb50189f6b66231d1b62de629d2` |
| watchdog-disarm helper | `733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc` |
| protected-root verifier | `a3f526c6aa5e2f75af49a5b72b89ee24958ce23898e410e43749b482dde3179c` |
| v9 export seal | `137eb101708a8f96c063ed068caf7f8265641c43c228501fc578d5076be02bd5` |
| unchanged RAM-only AVB image | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |
| v9 protected-root report | `d0fc85905276b202fd54862d1787a98e11c63fbecf2e9e8638850aa302f8c371` |
| v9 runtime report | `a9b99930799902cabf6c65bd877a21588b63ccb6b617d1ac526b9e0d159bf60d` |

## Guard and local preconditions

The runner requires both exact authorization values:

```text
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_LIVE_GATE=1
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_REBOOT=1
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
- complete PolicyKit verification of the protected v9 root against the
  immutable consumed v8 predecessor before SSH.

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
files. The remote verifier pins the mode-`0444` v9 seal and checks:

- exact rejected-and-consumed v8 predecessor report, seal, verifier,
  consumption test, and commit;
- exact unchanged module archive, all-module boundary, and `msm.ko`;
- exact SQE/GMU firmware with ZAP absent;
- exact one-open helper, signed/device-scoped trace oracle, baseline, and
  probe hashes;
- source-boundary, kernel-build, runtime-report, kernel-patch, compiler, and
  runtime-tool identities;
- SQE/GMU-only firmware policy and exactly one `EUCLEAN`;
- separate raw and page-rounded allocation-size layers;
- signed-32, GPU-device-scoped runtime-PM and logical-vmap trace policy;
- equal pre/post GEM snapshots;
- mode-`0400` GMU-entry parameter;
- forbidden v7/v8 authorization reuse; and
- the accepted registration-v3 marker.

The only remote execution command sets the exact target-gate and reboot
guards and invokes the pinned compound gate once.

## Required evidence and reboot disconnect

The private live log would be accepted only if it contains:

- the complete zero-action v9 baseline PASS;
- one exact failed open with `OPEN_ERRNO=117`;
- `gmu_resume_entry_only=Y`, both predecessor diagnostic modes `N`, and two
  firmware requests/releases;
- exactly one lazy-load, runtime-resume, GMU PM-resume, GMU-resume, entry-hit,
  and rollback route;
- three normalized `-EUCLEAN` returns;
- exactly one generic runtime-PM event matching the GPU callback device,
  while allowing additional classified generic events;
- zero inner runtime PM, clocks, IRQ, HFI, devfreq, LLC, hardware-init, ZAP,
  and SCM activity;
- accepted three-object rollback, public wrapper `1/2`, logical vmap `4/4`,
  and equal GEM snapshots; and
- the compound transition-watchdog and normal-reboot-request PASS.

SSH must then return nonzero because the target reboots. A normal gate return
is rejected. The log is created under `umask 077` and forced to mode `0600`.

The mock transport suite proves the exact call counts, evidence contract, and
expected reboot disconnect:

```text
PASS host A660 GMU resume-entry v9 gate stages two exact tmpfs inputs, invokes once, accepts device-classified generic PM, logs privately, and never retries
```

## Local credential readiness

The user explicitly authorized use of the separate phone SSH credential.
This checkpoint used it only for local agreement checks; no SSH connection or
authentication attempt occurred.

Without printing or recording fingerprint values, PolicyKit checks proved:

- the private and public client keys agree and are Ed25519;
- the known-hosts file contains one `rog5-network-root` identity;
- that identity matches the protected v9 Ed25519 server public key;
- both protected v9 `authorized_keys` files contain the same client key; and
- the two inherited authorized-key files are byte-identical.

No credential content, fingerprint value, private path, or phone identifier
is committed.

## Rechecked root and host boundary

At synchronized implementation checkpoint
`15d2879b1e0f4c6585be4a51fb54dc240c47f4db`:

- the branch was clean and synchronized with GitHub;
- the complete protected v9 export verifier passed again;
- the root remained root-owned mode `0555` with the unchanged kernel, seven
  modules, two firmware files, ZAP absent, signed/device oracle, logical
  `4/4`, equal-snapshot requirement, and preserved credentials;
- `nfs-server.service`, `rpcbind.service`, and `rpcbind.socket` were inactive;
- there were zero NFS exports, mounts, or listeners on ports 111/2049;
- the bounded server contained zero v9 paths or authorization tokens;
- no real v9 evidence directory or log was created; and
- an actual unarmed invocation refused with:

```text
FAIL set ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_LIVE_GATE=1 for the one-shot gate
```

NFS/RPC state remained inactive after that refusal.

## Consolidated contract

Bash syntax, ShellCheck, runtime mutations, target-gate ordering,
protected-root whole-tree verification, consumed-v8 lockout, one-shot runner
mock, local credential agreement, actual unarmed refusal, clean synchronized
Git, and `git diff --check` pass.

The host-runner suite ends with:

```text
PASS host A660 GMU resume-entry v9 gate stages two exact tmpfs inputs, invokes once, accepts device-classified generic PM, logs privately, and never retries
```

## Why the decision remains HOLD

Host-control acceptance is not a live-window or fallback acceptance. This
review intentionally did not:

- contact the phone or inspect its current fallback/bootloader state;
- create private live evidence;
- add v9 to the bounded NFS server;
- start NFS, configure the USB peer, or open SSH;
- issue a temporary boot command; or
- invoke the target gate.

The protected root therefore remains non-runnable, and HOLD is mandatory.

## Requirements to lift HOLD

A separate attended GO review must:

1. fail-first test and implement one explicit-opt-in, exact-v9-root server
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
8. invoke the v9 runner at most once; and
9. require immediate normal fallback, exact fallback health, complete host
   cleanup, and permanent v9 consumption regardless of pass or rejection.

No v8 authorization may be inherited, and no retry is permitted.
