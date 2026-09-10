# A660 ucode-allocation v5 — pre-live control acceptance and HOLD

Date: 2026-07-26

Decision: **HOLD. The exact one-invocation host control plane passes offline,
but no phone cycle is authorized by this checkpoint.**

The phone was not contacted. NFS was not started, the v5 root was not added
to the serve allowlist, no SSH connection was opened, no boot command ran,
and nothing was flashed.

## Fail-first host control

Commit `93ab294` records the missing host-runner test before implementation:

```text
FAIL missing host A660 ucode-allocation live-gate runner
```

Commit `0239e8353ab99eb53c3c37e4fec481bcedb16928` adds the runner. Its
SHA-256 is
`c6df42496b2fa6920187773bc7a97a8dc8bc5a7afb518f98ff1265a585580225`.
The mock test SHA-256 is
`d8e08191c50b6f5c925c82d03f837c9757e7e8aa0a9323fd63a8bb9871688cf7`.

The runner requires both exact authorization values:

```text
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_LIVE_GATE=1
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_REBOOT=1
```

It also requires explicit regular-file `SSH_KEY` and `KNOWN_HOSTS` inputs and
an existing caller-owned mode-`0700` `EVIDENCE_DIR`. It rejects a dirty or
unsynchronized repository, wrong branch, linked credential input, permissive
key/known-host modes, pre-existing evidence, and any missing or changed root,
boot-image, disarm, or target-gate input.

Before SSH, PolicyKit reruns the complete protected v5 export verifier. SSH
uses:

- `BatchMode=yes`;
- `IdentitiesOnly=yes`;
- exact `HostKeyAlias=rog5-network-root`;
- `StrictHostKeyChecking=yes`;
- an explicit known-hosts file;
- `ConnectionAttempts=1`; and
- bounded connect/keepalive failure.

The runner makes exactly one remote prepare call, one two-file SCP, one
remote verification call, and one gate call. The mode-`0700` target tmpfs
directory contains only:

- mode-`0500` exact watchdog disarm SHA-256
  `733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc`;
  and
- mode-`0500` exact target gate SHA-256
  `5dfe2703934123d433c5cfb7b3e46b0d51e20333957b64940a429cb2b16dc779`.

The remote verifier pins the v5 seal, baseline/probe hashes, accepted
registration marker, exact two-firmware/ZAP-absent policy, PID-filtered trace
policy, equal-state-snapshot policy, and v4 non-reuse marker before the sole
gate invocation.

Evidence is written under `umask 077` to one new mode-`0600` file. The runner
accepts only the full baseline, trace-balanced probe, and compound reboot PASS
records plus the expected SSH disconnect. It has no retry, loop around the
gate, NFS control, ADB, fastboot, block mount, storage-write, or flash path.

The mock transport suite proves one call of each stage and returns:

```text
PASS host A660 ucode-allocation gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries
```

## Local credential readiness

No network credential was used.

Read-only local checks prove:

- `/home/maks/.ssh/rog5_linux` is caller-owned mode `0600`;
- its private-key fingerprint matches
  `/home/maks/.ssh/rog5_linux.pub`;
- `/home/maks/.ssh/rog5_phone_known_hosts` is caller-owned mode `0600`;
- it contains exactly one `rog5-network-root` host identity; and
- the public-key fingerprint matches both protected immutable v5
  `authorized_keys` files.

PolicyKit read only the public key and protected export metadata; it did not
read the private key.

## Rechecked host boundary

At the review checkpoint:

- Git branch `agent/linux-recovery-host` was clean and synchronized at
  `0239e8353ab99eb53c3c37e4fec481bcedb16928`;
- the root-owned v5 export remained fully verified;
- `nfs-server.service` and `rpcbind.service` were inactive;
- there were no NFS mounts, port 111/2049 listeners, `rpc.mountd`, or
  `rpc.nfsd` processes;
- `/var/lib/rog5-network-root-a660-ucode-allocation-v5` remained absent from
  `serve-network-root.sh`; and
- the runner itself could not boot or contact the phone without a separately
  prepared NFS/temporary-boot session.

## Why the decision is HOLD

Offline control acceptance is not a substitute for an attended live
preflight. This review intentionally did not:

- inspect the phone's current fastboot/Android state;
- re-prove the persistent fallback from the phone;
- add v5 to the NFS allowlist;
- create a new private evidence directory for a live cycle;
- start the restricted NFS window;
- issue the exact temporary boot; or
- use SSH to invoke the target gate.

Therefore the correct decision is HOLD, not GO.

## Requirements to lift HOLD

At a later attended checkpoint:

1. Start from this clean synchronized repository and rerun all root, runner,
   package, NFS-inactive, and credential preflights.
2. Confirm the phone's exact persistent fallback and current bootloader state.
3. Review a minimal temporary allowlist change for only the exact v5 root,
   guarded by its full verifier; do not permit any consumed root.
4. Create a fresh private mode-`0700` evidence directory.
5. Start the restricted NFSv4.2 window and verify the exact USB gadget,
   firewall, host address, listener, and export.
6. Use only the accepted RAM-only temporary boot image; never flash.
7. Invoke the host runner exactly once.
8. Require the complete balanced trace/state PASS, immediate normal reboot,
   exact persistent fallback, NFS/firewall cleanup, zero pstore/project
   module residue, and private evidence capture.
9. Permanently consume and remove v5 from serving regardless of pass or
   rejection.

Only that separately reviewed attended checkpoint may change HOLD to GO.
