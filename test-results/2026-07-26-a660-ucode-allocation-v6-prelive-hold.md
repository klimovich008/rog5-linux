# A660 ucode-allocation v6 — pre-live control acceptance and HOLD

Date: 2026-07-26

Decision: **HOLD. The exact one-invocation v6 host control plane passes
offline, but this checkpoint does not authorize a phone cycle.**

The phone was not contacted. NFS was not started, no network authentication
occurred, no boot or reboot command ran, and nothing was flashed. The v6 root
remains absent from the bounded NFS allowlist.

## Fail-first host control

Commit `414d9c6b656b6020790fecc232c2b6e3d2b8b039` records the missing
host-runner implementation:

```text
FAIL missing host A660 ucode-allocation v6 live-gate runner
```

Commit `a235f1938f6350d859fd202e844960948ba7373d` adds the guarded
runner and integrates its mock suite with the v6 root and umbrella contracts.

Exact control identities are:

| Input | SHA-256 |
|---|---|
| one-invocation host runner | `57345cd2839f4c457d3e883dc4f2c55be4dfa98398e3de7060570a5580f4cbd3` |
| host-runner mock suite | `bfcda61e6f35e3ff277fc6f8970fb93abbe2ca29041d706eb000e10ba98083ba` |
| target compound gate | `5657ce39f7e3e8a81445662cda78e080e6b95df745c60d49a89acf716ec7e7a5` |
| watchdog-disarm helper | `733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc` |
| v6 export seal | `e9a9bf460b62d91c44fa15b8258ae5a5660ef387846530e8cf93fce67f7f17ea` |
| temporary AVB boot image | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |

The runner requires both exact authorization values:

```text
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V6_LIVE_GATE=1
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V6_REBOOT=1
```

It also requires explicit regular-file `SSH_KEY` and `KNOWN_HOSTS` inputs and
an existing caller-owned mode-`0700` `EVIDENCE_DIR`. It rejects a dirty or
unsynchronized repository, wrong branch, linked input, permissive
credential-file modes, unsafe evidence directory, pre-existing evidence, or
any changed boot-image, disarm, target-gate, or root input.

Before SSH, PolicyKit reruns the complete protected v6 export verifier. SSH
is fixed to:

- `BatchMode=yes`;
- `IdentitiesOnly=yes`;
- exact `HostKeyAlias=rog5-network-root`;
- `StrictHostKeyChecking=yes`;
- an explicit known-hosts file;
- one connection attempt;
- bounded connect and keepalive failure; and
- no global SSH configuration.

The runner then makes exactly one remote prepare call, one two-file SCP, one
remote verification call, and one gate call. The target tmpfs directory
contains only mode-`0500` copies of the exact disarm helper and v6 compound
gate.

The remote verifier pins:

- the exact v6 export-seal hash and mode;
- `diagnostic_generation=v6`;
- consumed v5 predecessor and `v5_reuse=FORBIDDEN`;
- exact compiler-relocation, SQE/GMU-only, one-`EUCLEAN`, logical-vmap, and
  equal-snapshot policies;
- generated baseline SHA-256
  `5ad24829bd347fcc22239d761029f3c0f8064efa1b16e9f01b6cf745902df854`;
- generated probe SHA-256
  `b90e33524da2558659a733c48d5670d2136208a9186d5abb3ecd79f1e28f2725`;
  and
- the accepted registration-v3 marker and SHA-256.

The sole target invocation is accepted only if its private log contains:

- the complete zero-action v6 baseline PASS;
- exact `EUCLEAN`, three maps/unmaps/closes/frees, three successful
  `kernel_new`, two `kernel_put`, wrapper `get=1, put=2`, logical `4/4`, and
  equal GEM snapshot PASS;
- zero power/HFI/ZAP/SCM/storage evidence; and
- the complete transition-watchdog and normal-reboot-request PASS.

The expected reboot disconnect must make SSH return nonzero. A normal return
is rejected. Evidence is written under `umask 077` to exactly one new
mode-`0600` file.

The mock transport suite proves exactly one call of every stage and no retry:

```text
PASS host A660 ucode-allocation v6 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries
```

The host runner contains no NFS control, ADB, fastboot, boot, flash, module
removal, physical-block mount, or storage-write path. It cannot make the v6
candidate runnable on its own.

## Local credential readiness

The user previously authorized use of the separate phone SSH credential.
This checkpoint used it only for local fingerprint comparison; no SSH
connection or authentication attempt occurred.

Read-only local checks prove:

- the private key is a regular caller-owned mode-`0600` file;
- its fingerprint matches the public-key file;
- the known-hosts file is a regular caller-owned mode-`0600` file;
- it contains exactly one `rog5-network-root` identity; and
- the public-key fingerprint matches both protected v6 `authorized_keys`
  files.

No key contents or fingerprint value were written to the repository.

## Rechecked root and host boundary

At the decision checkpoint:

- branch `agent/linux-recovery-host` was clean and synchronized with GitHub
  at `a235f1938f6350d859fd202e844960948ba7373d`;
- the complete protected v6 export verifier passed again;
- the root remained root-owned mode `0555` with exact seven modules, two
  firmware files, ZAP absent, generated runtime, compiler relocations,
  logical `4/4`, equal-snapshot requirement, and preserved credentials;
- `nfs-server.service`, `rpcbind.service`, and `rpcbind.socket` were inactive;
- there were zero NFS exports, mounts, port 111/2049 listeners, or
  `rpc.mountd`/`rpc.nfsd` processes;
- `net.ipv4.ip_nonlocal_bind` remained zero;
- the v6 root had zero bounded-server cases; and
- an actual unarmed runner invocation refused immediately with:

```text
FAIL set ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V6_LIVE_GATE=1 for the one-shot gate
```

NFS/RPC state remained inactive after that refusal.

## Why the decision remains HOLD

Host control acceptance is not a live-window or fallback acceptance. This
review intentionally did not:

- contact the phone or inspect its current fallback/bootloader state;
- create a new private live evidence directory;
- add a v6 case to the bounded NFS server;
- start NFS, configure the USB peer, or open SSH;
- issue a temporary boot command; or
- invoke the target gate.

Therefore the root remains non-runnable and the correct decision is HOLD.

## Requirements to lift HOLD

A separate attended GO review must:

1. fail-first test a verifier-before-state, explicit-opt-in NFS case for only
   the exact v6 root;
2. recheck a clean synchronized Git checkpoint, root, package, target gate,
   host runner, credentials, and inactive host services;
3. confirm the phone's exact persistent fallback, pinned SSH identity,
   bootloader transition path, safe thermals, and clean pstore/module state;
4. create a fresh caller-owned mode-`0700` private evidence directory;
5. prove an unarmed NFS invocation refuses before host mutation;
6. open one bounded exact-peer NFSv4.2 window and use only the accepted
   RAM-only temporary boot path, never flash;
7. invoke the v6 runner at most once; and
8. require complete logical trace and equal-snapshot evidence, immediate
   normal fallback reboot, exact fallback health, complete host cleanup, and
   permanent v6 consumption regardless of pass or rejection.

V5 authorization cannot be inherited.
