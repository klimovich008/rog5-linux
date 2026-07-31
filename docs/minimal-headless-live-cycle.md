# Minimal-headless one-shot lifecycle

This is the host runbook for one temporary stable-recovery boot, one signed
minimal-headless target, one private strict-SSH observation, and automatic
return to the configuration-unchanged Alpine fallback.

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
  -> exact host-key-signed ACM Alpine fallback
  -> host cleanup proof
  -> durable intent resolution
```

The target watchdog remains armed. The controller does not disarm it, request
a target reboot, flash, wipe, mount phone storage, use ADB, sign a bundle, or
create a production key. The installed fallback exposes only an interactive
BusyBox shell. Its history feature can persist the launcher before its child
starts, so
fallback ACM use has separately guarded storage effects. Reads of Python,
libraries, `ssh-keygen`, and the host key from a writable `relatime` ext4 root
may also update inode access times. The launcher is bounded below Alpine's
2,048-byte line-editor limit and starts isolated/no-site Python. The host waits
for a nonce-bound loader-ready marker before sending bounded, hash-checked
source chunks. The phone rejects missing or partial chunks under a fixed
receive deadline. The lifecycle reserves a separate bounded post-discovery
control margin and never contacts fallback twice if later host cleanup fails.

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
  or the exact
  `/home/rog5-linux/exports/headless-ssh-network-root-v3/root` with its
  admitted package hash;
- it requires a non-root `PKEXEC_UID`, a fresh 256-bit handoff token, and a
  bounded 600-900 second window;
- it revalidates the fixed deployment-store ancestry immediately before the
  bind mount, then verifies the already bound read-only tree before NFS can
  start; and
- it exports only read-only NFSv4.2 to `169.254.77.2` over the isolated USB
  link and removes its runtime export, listener, marker, firewall, and
  interface state on exit.

The historical path remains unchanged. The exact key-bound v3 path and package
identity are independently mutation-tested. The host installer creates
`/home/rog5-linux` and its `exports` child as root-owned mode-`0700`
directories. This keeps the 1.53 GiB lower on SteamOS's large `/home`
filesystem while the 46 MiB signed recovery bundle remains in the caller-owned
`/var/lib/rog5-recovery-bundles`.

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
- accepts only the fixed
  `/home/rog5-linux/exports/headless-ssh-network-root-v3` destination and
  rejects non-root-owned, writable, or symlinked destination ancestry;
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
inspection; the installer never silently removes or overwrites it. The first
real attempt failed before stage creation when the former `/var` destination
could not hold the anonymous archive snapshot; no export was published. The
reviewed `/home` remediation was subsequently installed and the admitted
37,735-entry export passed atomic publication, full sealed-root verification,
and fixed NFS host preflight. Do not set the guards or invoke this launcher
without fresh authorization to use the deployment key and mutate the host.
The no-replace publication contract also refuses the existing export.

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
- `FALLBACK_KNOWN_HOSTS`: caller-owned mode-`0600` Ed25519 host-key pin below
  a caller-owned mode-`0700` directory, used to verify fallback ACM health
  signatures. Despite the inherited variable name, it must contain exactly
  one literal `rog5-fallback ssh-ed25519 BASE64_KEY` line, not a general or
  hashed OpenSSH `known_hosts` inventory; and
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
  verification;
- the fallback controller validates its fixed host tools, inactive
  ModemManager state, exact one-line allowed-signers pin, bounded loader
  construction, 600-900 second wait, and recovery-anchor age budget without
  opening ACM or authorizing phone-storage effects; and
- exactly one `lahaina` fastboot device is present.

The stable-recovery artifact gate now admits the exact
`headless-ssh-deployment-v3` wrapper, trust root, manifest, verifier, and
target identity. The fixed host components, read-only v3 export, NFS
preflight, artifact gate, and connected fastboot gate now pass. The action
remains HOLD until one live signed-ACM fallback preflight passes. Fallback
classification no longer requires the deployment client key: the fixed ACM
controller verifies a nonce-bound Alpine health record with the retained
host-key pin and exact recovery-to-fallback physical USB continuity. Its
hardware-free tests pass. It performs no `authorized_keys`, fallback
configuration, mount, flash, or explicit partition write. Because Alpine
enables BusyBox per-command history, accepting the launcher can append to or
compact the shell-selected history file; ordinary reads can also update inode
access times under `relatime`. Those action-scoped effects require
`ALLOW_FALLBACK_ACM_STORAGE_WRITE=1` and remain unauthorized by this document.
The NFS controller requires the exact admitted package hash, fixed export
root, and canonical handoff marker. Preflight must not boot, transfer a
payload, start a network service, contact target SSH, or offer the key to a
phone. The NFS artifact check may execute the fixed root-owned verifier
through PolicyKit, but creates no export, mount, listener, marker, firewall
rule, or interface state.

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
ALLOW_FALLBACK_ACM_CONTROL
ALLOW_FALLBACK_ACM_STORAGE_WRITE
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
The anchor's exact seven-field schema is directly bound by test to the real
`pin-minimal-headless-host-key.py capture-recovery` producer, including its
literal `ROG5 recovery` USB product. Fallback contact must start within 3,600
seconds of capture; even the maximum 900-second ACM wait remains below the
controller's 7,200-second anchor-age limit. The controller rechecks wall-clock
anchor age and physical location after ACM discovery and before sending the
launcher, so host suspend cannot bypass freshness.
The fallback identity record retains only bounded non-sensitive proof
metadata: boot ID, USB location, nonce, maximum sampled temperature, and
SHA-256 identities of the signed record, signature, and inspected host-key
pin. The pin itself, signature bytes, and SSH host private key are never
published.

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

Deterministic fallback host prerequisites are checked during lifecycle
preflight before the temporary boot. Once the ACM controller is spawned, the
attempt remains conservatively non-retryable because process failure can be
ambiguous. Nonce-bound remote error frames preserve distinct health,
host-key-signing, ACK, same-boot, and post-ACK timeout failures instead of
collapsing them into one host timeout, including an error received on the last
bounded serial read.

## Hardware-free coverage

`test-verify-headless-ssh-v2-key-admission.py` covers fourteen admission
scenarios, `test-fallback-acm-control.py` covers thirty-eight fallback
protocol tests, and `test-run-minimal-headless-live-cycle.py` covers
seventeen lifecycle test methods. Together they prove:

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
- fallback classification uses one exact nonce-framed record, a real
  Ed25519 signature verifier, exact USB identity/location, bounded output,
  exclusive serial ownership, and no fallback client credential;
- host writes drain and retain bounded shell echoes, fail with canonical
  stage/byte progress, and require one non-echoable nonce shell-ready marker
  after an atomic stale-line reset;
- the action-scoped fallback storage guard fails before pin or device access,
  and the child launcher makes no false claim that changing its own
  `HISTFILE` can disable the parent shell's already-selected history path;
- thermal and pstore inspection fails if an expected entry is missing,
  unreadable, or additional; reboot refuses unless the initial fastboot
  inventory is canonically empty;
- preflight/reboot retains the historical 60 C readiness ceiling while return
  classification has a separate 80 C hard-safety ceiling, so a normal warm
  rollback is not mistaken for an absent fallback;
- the separately guarded reboot requires verified ACK, commit, disconnect,
  same-port fastboot, and exact product without flash, mount, or any phone
  write beyond separately authorized BusyBox-history and possible atime
  effects;
- its 30-second post-ACK COMMIT deadline exceeds the remote's 25-second
  post-ACK deadline; the phone checks that deadline after repeated health
  collection and both before and after COMMIT publication, preventing a late
  reboot after host failure;
- an absent reboot ACK expires on the phone without rebooting or retaining
  the ACM session;
- runtime rejection resolves as `FALLBACK_RETURNED`;
- a transport-lost COMMIT uses the durable ledger without replay;
- a silent process loss after ledger arm is recovered from the new durable
  record even when no session/request diagnostic was emitted;
- a zero-exit process with malformed output recovers the same durable intent;
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
