# Minimal-headless one-shot lifecycle

This is the host runbook for one temporary stable-recovery boot, one signed
minimal-headless target, one private strict-SSH observation, and automatic
return to the untouched Alpine fallback.

Status: **controller implemented and hardware-free tested; execution HOLD**.
The credential-clean replacement root now passes byte-identical A/B builds
and has a verified key-bound v3 package identity. The retained corrected
recovery profile still names the historical root, so a new complete candidate
profile and live private-to-public key derivation gate remain before this
runbook can pass complete preflight. It is not authorized or runnable on the
phone in the current state. This
document grants no live authority. `artifact-preflight` verifies the retained
candidate without querying a phone or inspecting credentials. `preflight` is
read-only with respect to the phone and credentials, but it does query the
connected fastboot device. `run` boots the phone and uses the dedicated SSH
client key; it therefore requires fresh explicit authorization and every
exact guard listed below.

## Why one controller is needed

The individual recovery, bundle, NFS, host-key, runtime, and fallback gates
already fail closed. Their ordering still matters:

1. The recovery bundle server and NFS exporter both use the isolated `drop`
   firewall zone. They must never overlap.
2. `PREPARE` needs the one-transfer bundle server.
3. `COMMIT_EXEC` needs the exact NFSv4.2 handoff marker and listener.
4. `COMMIT_EXEC` is non-retryable after an ambiguous transport loss.
5. Target SSH must use a key pinned through recovery-to-target USB continuity,
   never TOFU.
6. The durable intent must remain `UNKNOWN` until target or fallback evidence
   resolves it out of band.

`run-minimal-headless-live-cycle.py` enforces the resulting sequence:

```text
complete preflight
  -> temporary stable recovery
  -> private same-boot USB anchor
  -> fixed one-transfer bundle server
  -> PREPARE
  -> bundle server exit and complete cleanup
  -> fixed read-only NFSv4.2 server
  -> exact token-bound NFS marker
  -> one COMMIT_EXEC
  -> same-port target host-key pin
  -> one strict-SSH runtime observation
  -> target watchdog rollback
  -> NFS cleanup
  -> exact strict-SSH Alpine fallback
  -> host cleanup proof
  -> durable intent resolution
```

The target watchdog remains armed. The controller does not disarm it, request
a target reboot, flash, wipe, mount phone storage, use ADB, sign a bundle, or
create a production key.

## Fixed host privilege boundary

The recovery bundle server already runs through a fixed root-owned controller.
The NFS path now follows the same model:

- `install-recovery-host-controller.sh` installs root-owned mode-`0555`
  copies of `serve-network-root.sh`, `headless-network-root.py`, and
  `persistent-root-tool.py` below
  `/usr/libexec/rog5-recovery-host`;
- `run-headless-network-root-server.sh preflight` requires those installed
  bytes to match the reviewed repository sources;
- the installed server accepts only
  `/var/lib/rog5-headless-network-root-v1/root`;
- it requires a non-root `PKEXEC_UID`, a fresh 256-bit handoff token, and a
  bounded 600-900 second window; and
- it exports only read-only NFSv4.2 to `169.254.77.2` over the isolated USB
  link and removes its runtime export, listener, marker, firewall, and
  interface state on exit.

After this change is reviewed, committed, and pushed, the installed copies
will be stale by design. Updating them is a separate privileged host mutation:

```bash
pkexec scripts/host/install-recovery-host-controller.sh
```

Do not run that command without explicit approval. It changes only the host,
not the phone.

## Inputs

The stable-recovery gate retains its existing exact artifact inputs:

- `ROG5_STABLE_RECOVERY_PROFILE=corrected-headless-successor-2026-07-30`
- `LIVE_BUILD_ROOT`
- `RECOVERY_COMPONENT_ROOT`
- `TRUST_KEY`
- `BUNDLE_ROOT=/var/lib/rog5-recovery-bundles`
- `BUNDLE=headless-network-root-v1`
- `RECOVERY_SHA256`
- `TRUST_KEY_SHA256`
- `MANIFEST_SHA256`
- `HOST_VERIFIER_SHA256`

The lifecycle adds:

- `SSH_KEY`: caller-owned mode-`0600` dedicated phone client key;
- `FALLBACK_KNOWN_HOSTS`: caller-owned mode-`0600` strict pin for
  `rog5-fallback`; and
- `EVIDENCE_DIR`: existing caller-owned mode-`0700` directory outside the
  repository.

Preflight inspects only credential path metadata. It does not read a private
key through SSH or offer it to either phone environment.

The profile is a fail-closed artifact identity. The lifecycle accepts only the
corrected successor profile and rejects the consumed historical profile before
inspecting credential paths.

## Phone-free artifact preflight

The retained candidate can cross the exact production artifact boundary
without a connected device:

```bash
scripts/host/test-corrected-successor-live-gate-offline.sh
```

This verifies the signed bundle, stable initramfs, raw boot-v3 image, ASUS
wrapper, AVB descriptors, corrected DTB, trust root, and every pinned recovery
component, then exits before the first fastboot device query. A clean checkout
without the ignored retained candidate reports a skip rather than weakening
the gate.

## Read-only preflight

Run this only after the branch is clean, tracks its exact `origin` peer, the
reviewed commit is pushed, and the fixed host components are installed:

```bash
scripts/host/run-minimal-headless-live-cycle.py preflight
```

Preflight proves:

- every private output name is unused;
- the repository is clean and exactly synchronized with its remote-tracking
  branch;
- no NFS handoff marker, export mount, TCP 8080/2049 listener, NFS export,
  NFS worker, or `drop`-zone runtime state remains;
- both privileged launchers are installed and byte-current; the fixed
  root-owned NFS entry point also verifies the sealed export root and required
  host commands through a read-only PolicyKit preflight;
- the corrected recovery image, twin, target bundle, trust root, native
  verifier, wrapper configuration, and AVB layout pass the existing live-gate
  verification; and
- exactly one `lahaina` fastboot device is present.

It does not boot, transfer a payload, start a network service, contact SSH, or
use phone credentials. The NFS artifact check does execute the fixed
root-owned verifier through PolicyKit, but creates no export, mount, listener,
marker, firewall rule, or interface state.

## Authorized run

`run` additionally requires every guard to equal exactly `1`:

```text
ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE
ALLOW_TEMPORARY_BOOT
ALLOW_HEADLESS_LIVE_GATE
ALLOW_STABLE_RECOVERY_CONTROL
ALLOW_ATTENDED_KEXEC
ALLOW_NETWORK_ROOT_NFS_HANDOFF
ALLOW_HEADLESS_NETWORK_ROOT_SERVER
ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP
ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE
ALLOW_PHONE_CREDENTIAL_USE
```

These guards are an invocation-time authorization boundary, not persistent
permission. A later cycle requires fresh authorization and a fresh evidence
directory.

## Private outputs

All lifecycle outputs are created exclusively as mode-`0600` files below
`EVIDENCE_DIR`. Important records include:

- `recovery-usb.anchor`
- `target-known-hosts`
- `recovery-control.log`
- `minimal-headless-runtime.record`
- `fallback-identity.record`
- `fallback-preflight.log`
- `intent-resolution.log`

The directory and every output must remain outside Git. Existing files are
never overwritten.

## Failure and outcome rules

- Before COMMIT, failure stops all started host processes and creates no
  resolved intent.
- After a normal `CLAIMED` response, or after a transport-lost COMMIT whose
  session/request is recovered from the durable ledger, the controller never
  sends COMMIT again.
- A failed target observation terminates the read-only NFS window, leaves the
  target watchdog armed, waits for exact fallback, proves host cleanup, and
  resolves the intent as `FALLBACK_RETURNED`.
- A passed runtime observation is resolved as `TARGET_ACCEPTED` only after the
  target departs, exact fallback returns with a different boot ID, full
  fallback preflight passes, and host runtime state is absent.
- If exact fallback, ledger correlation, or host cleanup cannot be proved,
  the intent remains `UNKNOWN`. That is an attended investigation state, not
  permission to retry.

## Hardware-free coverage

`test-run-minimal-headless-live-cycle.py` covers fifteen lifecycle scenarios
and proves:

- all guards fail before any dependency or credential use;
- the consumed historical recovery profile fails before credential paths;
- preflight stops before boot and SSH;
- bundle-server cleanup precedes NFS startup;
- residual protected-zone rules, `/30` addresses, or NetworkManager ownership
  changes block NFS startup before COMMIT;
- one and only one `prepare-commit` process is started;
- success resolves only after exact fallback;
- runtime rejection resolves as `FALLBACK_RETURNED`;
- a transport-lost COMMIT uses the durable ledger without replay;
- a silent process loss after ledger arm is recovered from the new durable
  record even when no session/request diagnostic was emitted;
- a real parent `SIGINT` after ledger arm terminates the live control child,
  rescans the ledger, returns to fallback, and resolves without replay;
- a control failure with no intent is never resolved; and
- absent fallback proof or final firewall/address cleanup leaves the intent
  `UNKNOWN`.

The tests use only temporary mock processes and private fixture files. They do
not contact the phone, start PolicyKit, open a real firewall/NFS window, or use
credentials.

The exact source identities, test result, and independent review closure are
recorded in the
[offline result](../test-results/2026-07-29-minimal-headless-live-cycle-offline.md).
