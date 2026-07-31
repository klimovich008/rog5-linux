# Minimal-headless one-shot lifecycle

This is the host runbook for one temporary stable-recovery boot, one signed
minimal-headless target, one private strict-SSH observation, and automatic
return to the untouched Alpine fallback.

Tracked status: **controller and fixture path pass hardware-free tests;
non-fixture artifact pins and host installation remain deployment inputs**.
Tracked execution **HOLD**: this file never grants credential use or a phone
boot. Those require explicit invocation-time authorization after all
preflights pass.
The admission gate derives the public half locally, rejects every tracked
fixture identity, and requires one exact v3 package/candidate/runtime-manifest
chain before privilege or phone discovery. The fixed no-replace export
installer and launcher pass hostile tests. Repository text never grants live
authority; invocation-time guards and explicit operator authorization remain
mandatory.
The retained historical `artifact-preflight` remains regression evidence for
its old profile. `key-preflight` performs only local key admission. `preflight`
continues into fixed-host and connected checks only after admission. `run`
boots the phone and later offers the dedicated SSH client key; it therefore
requires fresh explicit authorization and every exact guard listed below.

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
  `persistent-root-tool.py`, plus the fixed
  `install-headless-ssh-deployment-export.py`, below
  `/usr/libexec/rog5-recovery-host`;
- `run-headless-network-root-server.sh preflight` requires those installed
  bytes to match the reviewed repository sources;
- the reviewed server accepts the historical
  `/var/lib/rog5-headless-network-root-v1/root` without a deployment package,
  or the exact `/var/lib/rog5-headless-ssh-network-root-v3/root` with its
  admitted package hash;
- it requires a non-root `PKEXEC_UID`, a fresh 256-bit handoff token, and a
  bounded 600-900 second window; and
- it exports only read-only NFSv4.2 to `169.254.77.2` over the isolated USB
  link and removes its runtime export, listener, marker, firewall, and
  interface state on exit.

The historical path remains unchanged. The exact key-bound v3 path and package
identity are independently mutation-tested, but no v3 export exists there.

After this change is reviewed, committed, and pushed, the installed copies
will be stale by design. Updating them is a separate privileged host mutation:

```bash
pkexec scripts/host/install-recovery-host-controller.sh
```

Do not run that command without explicit approval. It changes only the host,
not the phone.

## Fixed v3 export installation

`run-headless-ssh-deployment-export-install.py` is the only reviewed
unprivileged entry point for publishing the deployment lower. It fails before
credential inspection unless all three one-operation guards are set, requires
a clean branch synchronized with `origin`, and proves the fixed installed
installer/verifier bytes match the reviewed checkout. It then reruns exact
private-key/package/candidate/runtime-manifest admission. The privileged
command receives only:

```text
pkexec /usr/libexec/rog5-recovery-host/install-headless-ssh-deployment-export.py \
  ARCHIVE PACKAGE ADMITTED_PACKAGE_SHA256
```

The private key, candidate, and runtime manifest never cross that boundary.
The root-owned installer:

- requires canonical caller-owned read-only archive/package inputs below a
  caller-owned mode-`0700` parent;
- rejects the fixture fingerprint and every tracked fixture root identity;
- copies the archive into an anonymous root-owned `O_TMPFILE`, then inspects
  and extracts only that immutable-to-the-caller snapshot;
- rejects escaping, duplicate, sparse, device/FIFO, embedded-credential,
  symlink-ancestor, and unsafe-hardlink members before extraction;
- verifies the complete extracted v3 root against the admitted package;
- syncs every regular file and directory before publication; and
- uses `renameat2(RENAME_NOREPLACE)` so it never replaces an export that
  appeared concurrently.

A failed deterministic partial stage is retained for explicit privileged
inspection; the installer never silently removes or overwrites it. Do not set
the guards or invoke this launcher without fresh authorization to use the
deployment key and mutate the host. No installation command has been run.

## Inputs

The lifecycle now selects one exact deployment profile and bundle:

- `ROG5_STABLE_RECOVERY_PROFILE=headless-ssh-deployment-v3`
- `BUNDLE=headless-ssh-network-root-v3`
- `LIVE_BUILD_ROOT`
- `RECOVERY_COMPONENT_ROOT`
- `TRUST_KEY`
- `BUNDLE_ROOT`: canonical caller-owned mode-`0700` directory containing
  `headless-ssh-network-root-v3/manifest`;
- `RECOVERY_SHA256`
- `TRUST_KEY_SHA256`
- `MANIFEST_SHA256`
- `HOST_VERIFIER_SHA256`

The lifecycle adds:

- `SSH_KEY`: absolute canonical caller-owned mode-`0600` dedicated Ed25519
  phone client key outside the repository;
- `HEADLESS_ROOT_PACKAGE`: canonical caller-owned read-only v3 package record;
- `RECOVERY_CANDIDATE_RECORD`: canonical caller-owned read-only candidate
  record;
- `FALLBACK_KNOWN_HOSTS`: caller-owned mode-`0600` strict pin for
  `rog5-fallback`; and
- `EVIDENCE_DIR`: existing caller-owned mode-`0700` directory outside the
  repository.

`key-preflight` and later actions read the private key only through fixed
`/usr/bin/ssh-keygen -y` from the already-open file descriptor. They do not
emit the private path, public-key body, or private material. Only `run` may
later offer the key to SSH after all full-run guards and gates pass.

The deployment profile is a fail-closed artifact identity. The lifecycle
rejects every historical profile and wrong bundle before opening the private
key.

## Build the non-fixture chain

Run this only with a clean branch at its exact pushed origin commit and a
caller-owned mode-`0700` directory outside the repository. The dedicated
Ed25519 client key and Ed25519 PKCS#8 recovery signing key must remain there.

The explicitly guarded build sequence is:

```bash
ARCH_ROOTFS_GENERATION=headless-ssh-v2 \
  scripts/host/run-private-arm64-binfmt.sh \
  scripts/host/stage-arch-rootfs.sh \
  /private/deployment-ssh-key.pub \
  /private/rog5-arch-headless-ssh-v2-7.1.4.tar.gz

chmod 0444 /private/rog5-arch-headless-ssh-v2-7.1.4.tar.gz

ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD=1 \
ALLOW_PHONE_CREDENTIAL_USE=1 \
  scripts/host/prepare-headless-ssh-deployment-root.sh \
  /private/rog5-arch-headless-ssh-v2-7.1.4.tar.gz \
  /private/network-root

scripts/host/prepare-headless-ssh-deployment-candidate.py \
  --package /private/network-root/manifest \
  --output /private/headless-ssh-network-root-v3.json

ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD=1 \
ALLOW_PHONE_CREDENTIAL_USE=1 \
ROG5_DEPLOYMENT_CANDIDATE_RECORD=/private/headless-ssh-network-root-v3.json \
ROG5_DEPLOYMENT_SIGNING_KEY=/private/recovery-signing-key.pem \
  scripts/host/build-headless-ssh-deployment-candidate.sh \
  "$PWD/build/headless-ssh-deployment"
```

The root packager accepts only an external read-only source archive below a
private parent, rejects every fixture identity, verifies a clean-extracted
root, and atomically publishes a new output directory without replacement.
The candidate generator derives the root identities accepted by recovery from
the fixed corrected-DTB template and the verified package. The recovery
builder verifies a clean pushed checkpoint, snapshots one external
unencrypted Ed25519 signing key and one template-constrained candidate into
private temporary storage, hash-binds the candidate at its consumer,
twin-signs and twin-builds from those snapshots, destroys them, and produces
no live authority or phone action.

The resulting exact wrapper, trust, manifest, and host-verifier hashes must be
reviewed and pinned in the live-gate profile before host installation or
connected preflight.

## Local deployment-key preflight

After a reviewed commit is pushed and the branch is clean and synchronized
with its exact `origin` peer, local admission is:

```bash
scripts/host/run-minimal-headless-live-cycle.py key-preflight
```

The action requires exactly:

```text
ALLOW_HEADLESS_SSH_KEY_ADMISSION=1
ALLOW_PHONE_CREDENTIAL_USE=1
```

It then derives one unencrypted Ed25519 public key, rejects the tracked fixture
fingerprint and every tracked fixture root/package/manifest identity, and
requires exact equality across the v3 package, offline candidate, and runtime
manifest. The accepted tuple also pins the corrected DTB and established
Image/generic-initramfs identities. It exits before PolicyKit, host network
inspection, fastboot discovery, boot, payload transfer, or SSH. Passing it
does not grant live authority.

## Historical phone-free artifact preflight

The retained historical candidate can still cross its exact production
artifact boundary without a connected device:

```bash
scripts/host/test-corrected-successor-live-gate-offline.sh
```

This verifies the signed bundle, stable initramfs, raw boot-v3 image, ASUS
wrapper, AVB descriptors, corrected DTB, trust root, and every pinned recovery
component, then exits before the first fastboot device query. A clean checkout
without the ignored retained candidate reports a skip rather than weakening
the gate. It does not admit the new deployment profile and cannot substitute
for rebuilding the non-fixture v3 chain.

## Read-only preflight

Run this only after the branch is clean, tracks its exact `origin` peer, the
reviewed commit is pushed, and the fixed host components are installed:

```bash
scripts/host/run-minimal-headless-live-cycle.py preflight
```

Preflight proves:

- local deployment-key admission already passed for the exact non-fixture v3
  package/candidate/runtime-manifest chain;
- every private output name is unused;
- the repository is clean and exactly synchronized with its remote-tracking
  branch;
- no NFS handoff marker, export mount, TCP 8080/2049 listener, NFS export,
  NFS worker, or `drop`-zone runtime state remains;
- both privileged launchers are installed and byte-current; the fixed
  root-owned NFS entry point and export installer are byte-current; the NFS
  entry point also verifies the sealed export root and required host commands
  through a read-only PolicyKit preflight;
- the corrected recovery image, twin, target bundle, trust root, native
  verifier, wrapper configuration, and AVB layout pass the existing live-gate
  verification; and
- exactly one `lahaina` fastboot device is present.

The stable-recovery artifact gate still rejects
`headless-ssh-deployment-v3`, so this action remains HOLD before a phone query
until its wrapper/trust/manifest hashes are pinned and the fixed read-only v3
export is installed. The NFS controller already requires the exact admitted
package hash, fixed export root, and canonical handoff marker. Once complete,
preflight must not boot, transfer a payload, start a network service, contact
SSH, or offer the key to a phone. The NFS artifact check may execute the fixed
root-owned verifier through PolicyKit, but creates no export, mount, listener,
marker, firewall rule, or interface state.

## Authorized run

`run` additionally requires every guard to equal exactly `1`:

```text
ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE
ALLOW_HEADLESS_SSH_KEY_ADMISSION
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

`test-verify-headless-ssh-v2-key-admission.py` covers fourteen admission
scenarios, and `test-run-minimal-headless-live-cycle.py` covers seventeen
lifecycle scenarios. Together they prove:

- exact non-fixture v3 key/package/candidate/manifest binding passes;
- tracked fixture keys and each tracked fixture root identity fail;
- wrong, encrypted, RSA, symlinked, linked, replaced, or loosely protected
  key inputs fail;
- package/candidate/manifest/artifact tuple mutations fail;
- admission emits only canonical public identity hashes and no key body or
  path;
- `key-preflight` stops before privilege, network inspection, or phone
  discovery;
- all guards fail before any dependency or credential use;
- the consumed historical recovery profile fails before credential paths;
- preflight admits the local key before live checks and stops before boot and
  SSH;
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

The tests use only temporary mock processes, private fixture files, and
disposable test keys. They do not contact the phone, start PolicyKit, open a
real firewall/NFS window, or use personal/deployment credentials.

The exact source identities, test result, and independent review closure are
recorded in the
[original lifecycle result](../test-results/2026-07-29-minimal-headless-live-cycle-offline.md)
and the
[deployment-key admission result](../test-results/2026-07-31-headless-ssh-v2-key-admission-offline.md).
