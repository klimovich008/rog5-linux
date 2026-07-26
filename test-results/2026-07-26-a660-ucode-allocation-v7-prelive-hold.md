# A660 ucode-allocation v7 — pre-live control acceptance and HOLD

Date: 2026-07-26

Decision: **HOLD. The exact one-invocation v7 host control plane passes
offline, but this checkpoint does not authorize a phone cycle.**

The phone was not contacted. NFS was not started, no network authentication
occurred, no boot or reboot command ran, and nothing was flashed. The v7 root
remains absent from the bounded NFS allowlist.

## Fail-first host control

Commit `0a763d88e20ae98f21c8c5a7ccec4e99022b97e4` records the missing
host-runner implementation:

```text
FAIL missing host A660 ucode-allocation v7 live-gate runner
```

Commit `1125e47aea8391305823871ce767c933ab379d94` adds the guarded
runner and integrates its mock suite with the protected export and v7
umbrella contracts.

Exact control identities are:

| Input | SHA-256 |
|---|---|
| one-invocation host runner | `b6800410bb0692e876129bb2d40d8cde23e60005a3d2c90959f730be7aee510a` |
| host-runner mock suite | `d1c7c18cd1ffdf5a3e0b76fd5bb9be0fa2b72299be8d6af4751e81e6212cdfc4` |
| target compound gate | `f7f223b62521306007c9ac224f008c0a9e6f85fdbdcac1529bf7c8e3a9ea3d1e` |
| watchdog-disarm helper | `733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc` |
| v7 export seal | `c679ff6cbed6aefb28b7537cd30c561948e4d4672cd9320a8e70fd3d79b4f046` |
| temporary AVB boot image | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |

The runner requires both exact authorization values:

```text
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_LIVE_GATE=1
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_REBOOT=1
```

It also requires explicit regular-file `SSH_KEY` and `KNOWN_HOSTS` inputs and
an existing caller-owned mode-`0700` `EVIDENCE_DIR`. It rejects a dirty or
unsynchronized repository, wrong branch, linked input, permissive credential
modes, unsafe evidence directory, pre-existing evidence, or changed
boot-image, disarm, target-gate, or root input.

Before SSH, PolicyKit reruns the complete protected v7 export verifier
against the immutable consumed v6 predecessor.

SSH is fixed to:

- `BatchMode=yes`;
- `IdentitiesOnly=yes`;
- exact `HostKeyAlias=rog5-network-root`;
- `StrictHostKeyChecking=yes`;
- an explicit known-hosts file;
- one connection attempt;
- bounded connect and keepalive failure; and
- no global SSH configuration.

The runner then makes exactly one remote prepare call, one two-file SCP, one
remote verification call, and one gate call. The target tmpfs directory may
contain only mode-`0500` copies of the exact disarm helper and v7 compound
gate.

The remote verifier pins:

- exact v7 export-seal hash and mode;
- `diagnostic_generation=v7`;
- immutable consumed-v6 predecessor, rejection report, and consumption
  commit;
- source-boundary report and accepted compiler-relocation policy;
- raw entry sizes `4/4096/43288`;
- separate page-rounded object sizes `4096/4096/45056`;
- SQE/GMU-only, one-`EUCLEAN`, logical-vmap, and equal-snapshot policies;
- generated baseline SHA-256
  `d8c2d697d20c213f3528d6a4cf99ca7d0243bf83222a34ff6f665ab22fc27386`;
- generated probe SHA-256
  `01a681bdf9fc17b3c676797cafadc43338eee49f2a5e3b7c6789edc1c7056cf0`;
  and
- the accepted registration-v3 marker and SHA-256.

The sole target invocation is accepted only if its private log contains:

- the complete zero-action v7 baseline PASS;
- exact `EUCLEAN`, raw-size oracle, three maps/unmaps/closes/frees, three
  successful kernel-new calls, two kernel puts, wrapper `get=1, put=2`,
  logical `4/4`, and equal GEM snapshot PASS;
- zero power/HFI/ZAP/SCM/storage evidence; and
- complete transition-watchdog and normal-reboot-request PASS.

The expected reboot disconnect must make SSH return nonzero. A normal return
is rejected. Evidence is written under `umask 077` to exactly one new
mode-`0600` file.

The mock transport suite proves exactly one call of every stage and no retry:

```text
PASS host A660 ucode-allocation v7 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries
```

The host runner contains no NFS/server control, ADB, fastboot, boot, flash,
module removal, physical-block mount, or storage-write path. It cannot make
the v7 candidate runnable on its own.

## Local credential readiness

The user explicitly authorized use of the separate phone SSH credential.
This checkpoint used it only for local fingerprint comparison; no SSH
connection or authentication attempt occurred.

Read-only local checks prove:

- the private key is a regular caller-owned mode-`0600` file;
- its fingerprint matches the public-key file;
- the known-hosts file is a regular caller-owned mode-`0600` file;
- it contains exactly one `rog5-network-root` Ed25519 identity; and
- the public-key fingerprint matches both protected v7 `authorized_keys`
  files.

No key content or fingerprint value is written to the repository.

## Rechecked root and host boundary

At the decision checkpoint:

- branch `agent/linux-recovery-host` was clean and synchronized with GitHub
  at `1125e47aea8391305823871ce767c933ab379d94`;
- the complete protected v7 export verifier passed again;
- the root remained root-owned mode `0555` with exact seven modules, two
  firmware files, ZAP absent, generated runtime, raw/object size layers,
  compiler relocations, logical `4/4`, equal-snapshot requirement, and
  preserved credentials;
- `nfs-server.service`, `rpcbind.service`, and `rpcbind.socket` were inactive;
- there were zero NFS exports, mounts, port 111/2049 listeners, or
  `rpc.mountd`/`rpc.nfsd` processes;
- `net.ipv4.ip_nonlocal_bind` remained zero;
- the v7 root had zero bounded-server cases;
- no v7 live evidence directory was created; and
- an actual unarmed runner invocation refused immediately with:

```text
FAIL set ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_LIVE_GATE=1 for the one-shot gate
```

NFS/RPC state remained inactive after that refusal.

## Consolidated contract

POSIX/Bash syntax, ShellCheck 0.11.0, runtime/probe/gate mutations, protected
export checks, consumed-v6 lockout, one-shot runner mock, and
`git diff --check` pass. The umbrella suite ends with:

```text
PASS A660 ucode-allocation v7 is raw-size-pinned, compiler-pinned, logical-vmap-balanced, snapshot-guarded, host-runner-tested, storage-isolated, non-runnable, and pre-live HOLD
```

## Why the decision remains HOLD

Host control acceptance is not a live-window or fallback acceptance. This
review intentionally did not:

- contact the phone or inspect its current fallback/bootloader state;
- create a new private live evidence directory;
- add a v7 case to the bounded NFS server;
- start NFS, configure a USB peer, or open SSH;
- issue a temporary boot command; or
- invoke the target gate.

Therefore the root remains non-runnable and the correct decision is HOLD.

## Requirements to lift HOLD

A separate attended GO review must:

1. fail-first test a verifier-before-state, explicit-opt-in NFS case for only
   the exact v7 root;
2. recheck a clean synchronized Git checkpoint, root, package, target gate,
   host runner, credentials, and inactive host services;
3. confirm the phone's exact persistent fallback, pinned SSH identity,
   bootloader transition path, safe thermals, and clean pstore/module state;
4. create a fresh caller-owned mode-`0700` private evidence directory;
5. prove an unarmed NFS invocation refuses before host mutation;
6. open one bounded exact-peer NFSv4.2 window and use only the accepted
   RAM-only temporary boot path, never flash;
7. invoke the v7 runner at most once; and
8. require complete raw-size, logical `4/4`, pointer-union, rollback, and
   equal-snapshot evidence, immediate normal fallback reboot, exact fallback
   health, complete host cleanup, and permanent v7 consumption regardless of
   pass or rejection.

No v5 or v6 authorization can be inherited.
