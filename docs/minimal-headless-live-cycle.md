# Minimal-headless one-shot lifecycle

This is the host runbook for one temporary stable-recovery boot, one signed
minimal-headless target, one private strict-SSH observation, and automatic
return to the configuration-unchanged Alpine fallback.

Tracked status: **diagnostic generations 0–4 are consumed and no image is
admitted**. Generation 4 passed connected preflight and one RAM-only recovery
boot reached verified ACM/NCM with rollback armed. Its collector and bundle
service became ready, but the service never emitted its independent completion
marker before the 45-second NFS-readiness deadline. NFS did not start, COMMIT
was never sent, and no target ran. The phone returned automatically to Alpine.
Initial host cleanup proof failed while the controller remained alive under
its 205-second watchdog and the shared `/30` was outside the managed profile;
after watchdog exit, one fixed anchored restoration and strict fallback
preflight passed with no project server/export residue. The required
hardware-free regression now covers the exact PREPARED/control-exits-first
stall, automatic fixed restoration, strict fallback proof, host cleanup even
when fallback proof fails, and interrupt cleanup. PREPARED is flushed before
the NFS gate, and the real host server and native fetcher pass together at the
Generation-4 artifact sizes. Complete local CI and GitHub Actions run
`30793088424` pass at implementation commit `38b6019`; no new image is
admitted. Do not increase a timeout or revive a consumed image as a substitute
for this ordering evidence. See the
[offline correction](../test-results/2026-08-03-generation-4-choreography-fix-offline.md).
The corrected controller/server are installed, and their real bundle and
37,735-entry deployment-root preflights pass without phone access or project
residue; see the
[host-install result](../test-results/2026-08-03-choreography-host-install-live.md).
Distinct Generation-5 AVB `abe4501f…beb1a` is now twin-reproducible over the
unchanged recovery payload and passes the complete offline artifact gate. Its
profile is offline-only, and it remains absent from boot policy; see the
[Generation-5 issuance](../test-results/2026-08-03-generation-5-choreography-offline.md).
The [standing operator authorization](operator-standing-authorization.md)
covers the in-scope credentials, host changes, connected preflights, and
admitted temporary boot without another consent prompt. Every invocation-time
guard, preflight, one-shot limit, rollback rule, and no-flash boundary remains
mandatory.
The admission gate derives the public half locally, rejects every tracked
fixture identity, and requires one exact v3 package/candidate/runtime-manifest
chain before privilege or phone discovery. The fixed no-replace export
installer and launcher pass hostile tests. Repository guards do not grant
authority by themselves: the central standing-authorization record supplies
operator authority, while every invocation-time guard remains mandatory.
The retained historical `artifact-preflight` remains regression evidence for
its old profile. `key-preflight` performs only local key admission. `preflight`
continues into fixed-host and connected checks only after admission. `run`
boots the phone and later offers the dedicated SSH client key; standing
authorization permits it only after every exact guard listed below passes.
The `diagnostic-key-preflight`, `diagnostic-preflight`, and `diagnostic-run`
actions select only `headless-netroot-early-diag-v1`; they cannot reuse r2 or
promote diagnostic evidence as normal runtime acceptance.
After that candidate resolves as accepted, rejected, or unknown, remove its
temporary recovery row from `manifests/temporary-boot-images.tsv` in the same
evidence/publication update. Never retain the row as authority to retry an
execute action.

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
7. The Alpine fallback profile must remain inactive while recovery or the
   target owns the anchored USB port, then be restored before strict fallback
   SSH only after exact Alpine NCM identity is stable.

`run-minimal-headless-live-cycle.py` enforces the resulting sequence:

```text
complete preflight
  -> temporary stable recovery
  -> private same-boot USB anchor
  -> fixed one-transfer bundle server
  -> PREPARE
  -> bundle server exit, complete cleanup, and fallback profile deferral
  -> fixed read-only NFSv4.2 server
  -> exact token-bound NFS marker
  -> one COMMIT_EXEC
  -> same-port target host-key pin
  -> one strict-SSH runtime observation
  -> target watchdog rollback
  -> NFS cleanup
  -> exact same-port Alpine NCM and bounded fallback-profile restoration
  -> exact host-key-signed strict-SSH Alpine fallback
  -> host cleanup proof
  -> durable intent resolution
```

The diagnostic path replaces only the target host-key/runtime portion:

```text
private same-boot USB anchor
  -> start receive-only collector and require flushed READY
  -> fixed bundle transfer, NFS handoff, and one COMMIT_EXEC
  -> bounded accepted or rejected diagnostic evidence
  -> exact same-port Alpine NCM and bounded fallback-profile restoration
  -> exact strict-SSH Alpine fallback
  -> host cleanup proof
  -> durable intent resolution as FALLBACK_RETURNED
```

Collector readiness is established before the bundle server and recovery
control start. A missing readiness marker therefore fails before the
non-retryable commit boundary. Diagnostic mode never pins a target SSH host
key and never invokes the normal runtime-acceptance runner.

The target watchdog remains armed. The controller does not disarm it, request
a target reboot, flash, wipe, mount phone storage, use ADB, sign a bundle, or
create a production key. Normal fallback proof now uses the dedicated client
key over USB-NCM with strict host-key checking. The host sends a fixed
read-only Python probe through non-interactive SSH; the phone signs the
nonce-bound health record with its pinned Ed25519 host key. The controller
revalidates the exact product, physical USB location, direct route, and NCM
interface after the signed reply. Interactive ACM remains an emergency tool,
but it is no longer in the normal lifecycle. The lifecycle reserves a
separate bounded post-discovery control margin and never contacts fallback
twice if later host cleanup fails.

SSH does not enter the BusyBox line editor, but reading `authorized_keys`,
the SSH host key, Python, and libraries from Alpine's writable `relatime`
root may update inode access times. The live action therefore retains an
explicit `ALLOW_FALLBACK_SSH_ATIME_EFFECTS=1` guard.

## Fixed host privilege boundary

The recovery bundle server and NFS path use fixed root-owned controllers. A
live rejection proved that invoking those controllers through graphical
PolicyKit after temporary recovery boot is too late: authentication can exceed
the recovery server-ready budget even though every target-side guard works.
The corrected runtime boundary therefore removes PolicyKit from the timed
phone path:

- `install-recovery-host-controller.sh` installs root-owned mode-`0555`
  copies of a socket broker and client, `serve-network-root.sh`,
  `headless-network-root.py`, and `persistent-root-tool.py`, plus the fixed
  `install-headless-ssh-deployment-export.py`, below
  `/usr/libexec/rog5-recovery-host`;
- the installer binds `/run/rog5-recovery-host.sock` to the exact authenticated
  operator as mode `0600`; systemd accepts at most one long-running operation
  plus one independent cancellation connection;
- the root broker obtains the connecting process credentials from the Unix
  socket, requires the configured operator UID, verifies a root-owned
  mode-`0444` configuration and exact SHA-256 identities for both privileged
  controllers, accepts one canonical bounded request, and forwards only the
  fixed child output and status;
- the protocol exposes only ordinary or lifecycle-deferred bundle serve,
  exact anchored fallback-profile restoration, fixed
  historical/deployment NFS preflight and serve, and token-bound NFS
  cancellation. It exposes no shell, arbitrary command, arbitrary root path,
  caller environment, installer, or repository executable;
- `run-headless-network-root-server.sh preflight` requires those installed
  bytes to match the reviewed repository sources, then uses the socket; the
  recovery-bundle launcher does the same;
- `serve` publishes one root-owned mode-`0400` PID/start-time/caller/token
  identity before lengthy verification, and `cancel` accepts only the same
  PolicyKit caller and fresh handoff token before signaling that exact root
  process; cancellation waits for terminal process state and state removal,
  including the normal zombie interval before the unprivileged parent calls
  `wait()`;
- the reviewed server accepts the historical
  `/var/lib/rog5-headless-network-root-v1/root` without a deployment package,
  or the exact
  `/home/rog5-linux/exports/headless-ssh-network-root-v3/root` with its
  admitted package hash;
- the broker supplies the socket-authenticated non-root UID as `PKEXEC_UID` to
  the unchanged controllers; NFS still requires a fresh 256-bit handoff token
  and a bounded 600-900 second window;
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

Updating reviewed host components and enabling the operator-owned socket is
one separate privileged host mutation:

```bash
pkexec scripts/host/install-recovery-host-controller.sh
```

The installation at commit `aa39503` is accepted: SteamOS read-only mode was
restored, the socket is enabled and active with exact UID/GID `1000:1000` and
mode `0600`, installed executable hashes match the checkout, and the real
deployment NFS preflight crossed the root broker without PolicyKit. See the
[live host-control result](../test-results/2026-08-01-steamos-prompt-free-host-control-live.md).

After the reviewed change is committed, pushed, synchronized with `origin`,
and its installer preflight passes, the command may run under the central
standing authorization. It changes only the host, not the phone. On SteamOS,
the installer verifies the root-owned, non-writable `/`, `/usr`, and
`/usr/bin` ancestry plus the fixed `/usr/bin/steamos-readonly` leaf, then
executes only the opened and identity-checked controller descriptor. It opens
the read-only `/usr` deployment window only after the pre-mutation source and
existing-destination safety checks pass, and restores read-only mode through
its exit trap on success, failure, or a handled signal. Further termination
signals are deferred by the parent while that trap completes cleanup and
restoration; they are not inherited as ignored signals by the controller
child. Success is printed only after the original state is proved restored and
the fixed systemd socket is active with exact ownership and mode;
if restoration cannot be proved, installation fails instead. A host whose
state was already `disabled` is left disabled. Do not wrap the installer in a
separate manual `steamos-readonly disable` operation.

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
and fixed NFS host preflight. Standing authorization permits the agent to set
the guards and invoke this launcher after its credential-free checks pass.
The no-replace publication contract also refuses the existing export.

## Inputs

> **r2 CONSUMED BY ONE REJECTED TARGET CYCLE:** recovery fetched, prepared,
> and committed r2 exactly once. Linux 7.1 exposed the expected USB-NCM gadget
> and physically disconnected 23 seconds later, before target SSH acceptance.
> The watchdog returned the exact Alpine fallback and strict SSH proved it.
> Do not reuse r2; build a distinct diagnostic successor. See the
> [live result](../test-results/2026-08-01-minimal-headless-r2-target-usb-loss.md).

The lifecycle now selects one exact deployment profile and bundle:

- `ROG5_STABLE_RECOVERY_PROFILE=headless-ssh-deployment-v3` and
  `BUNDLE=headless-ssh-network-root-v3-r2` for normal acceptance; or
  `ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation3-live-v1` and
  `BUNDLE=headless-netroot-early-diag-v1` for diagnostic execution;
- `LIVE_BUILD_ROOT`
- `RECOVERY_COMPONENT_ROOT`
- `TRUST_KEY`
- `BUNDLE_ROOT`: canonical caller-owned mode-`0700` directory containing the
  exact selected bundle and its manifest. Connected preflight/run requires
  the installed no-replace root `/var/lib/rog5-recovery-bundles`; only the
  separate artifact-only gate accepts an ignored build-directory root;
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
  a caller-owned mode-`0700` directory, used both for strict fallback SSH and
  to verify the signed health record. It must contain exactly one literal
  `rog5-fallback ssh-ed25519 BASE64_KEY` line, not a general or hashed OpenSSH
  `known_hosts` inventory; and
- `EVIDENCE_DIR`: existing caller-owned mode-`0700` directory outside the
  repository.

`key-preflight` and later actions read the private key only through fixed
`/usr/bin/ssh-keygen -y` from the already-open file descriptor. They do not
emit the private path, public-key body, or private material. Only `run` may
later offer the key to SSH after all full-run guards and gates pass.

The deployment profile is a fail-closed artifact identity. The lifecycle
rejects every historical profile, wrong bundle, and consumed live manifest
before opening the private key. Candidate and bundle are checked separately:
the target reports the stable candidate ID while recovery commits only the r2
bundle. Exact build evidence and remaining gates are recorded in the
[signed r2 result](../test-results/2026-07-31-headless-ssh-successor-r2-signed-build.md).

## Persistent fallback USB network profile

Alpine uses the fixed address `169.254.77.2`, but it does not provide DHCP.
Without a host profile, NetworkManager waits indefinitely and SSH appears
unreliable even though USB-NCM is healthy. Create one host-only profile bound
to the stable interface name for the anchored physical USB port:

```bash
nmcli connection add type ethernet ifname enp4s0f3u1u2 \
  con-name rog5-fallback-usb-ssh \
  ipv4.method manual ipv4.addresses 169.254.77.1/30 \
  ipv4.gateway '' ipv4.dns '' ipv4.never-default yes \
  ipv4.may-fail no ipv6.method disabled \
  connection.autoconnect yes connection.autoconnect-priority 100 \
  connection.mdns no connection.llmnr no
nmcli connection up rog5-fallback-usb-ssh ifname enp4s0f3u1u2
```

Discover the local interface from the exact fallback product rather than
copying the example name blindly. The profile has no gateway, DNS, forwarding,
or Internet route. Recovery and target servers use the same isolated `/30`.
Recovery pins the exact active profile UUID, deactivates it while serving the
attended bundle endpoint, and restores that same profile after cleanup; target
NFS uses the same address without introducing a competing prefix. When
Alpine re-enumerates,
the profile reconnects automatically and makes strict SSH available without
an attended ACM exchange. Lifecycle host preflight rejects a missing or
altered profile, including DHCP, a gateway, DNS, IPv6, disabled autoconnect,
the wrong `/30`, or an unexpected interface.

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
  --bundle headless-ssh-network-root-v3 \
  --output /private/headless-ssh-network-root-v3.json

scripts/host/prepare-headless-ssh-deployment-candidate.py \
  --package /private/network-root/manifest \
  --bundle headless-ssh-network-root-v3-r2 \
  --output /private/headless-ssh-network-root-v3-r2.json

scripts/host/preflight-headless-ssh-successor-candidate.py \
  --package /private/network-root/manifest \
  --base-candidate-record /private/headless-ssh-network-root-v3.json \
  --candidate-record /private/headless-ssh-network-root-v3-r2.json

scripts/host/build-headless-ssh-deployment-candidate.sh \
  --authorize-recovery-deployment-build \
  --authorize-phone-credential-use \
  --candidate-record /private/headless-ssh-network-root-v3-r2.json \
  --signing-key /private/recovery-signing-key.pem \
  "$PWD/build/headless-ssh-deployment"
```

The diagnostic successor reuses the admitted non-fixture Arch package but
has a separate, exact candidate and guarded build wrapper. Preparing the
external record is credential-free, verifies every root identity against the
package, requires candidate SHA-256
`7081a0c77158ed695e62751e152baff101b18a9b364640c0cbffd6ef8ba1c6e8`,
and creates a new mode-`0444` file without replacement:

```bash
scripts/host/prepare-early-target-diagnostic-deployment-candidate.py \
  --package /private/network-root/manifest \
  --output /private/headless-netroot-early-diag-v1.json
```

Only after the reviewed checkpoint is pushed and GitHub CI is green may one
standing-authorized production-signing invocation use that record:

```bash
scripts/host/build-early-target-diagnostic-deployment-candidate.sh \
  --authorize-recovery-deployment-build \
  --authorize-phone-credential-use \
  --candidate-record /private/headless-netroot-early-diag-v1.json \
  --signing-key /private/recovery-signing-key.pem \
  "$PWD/build/early-target-diagnostic-deployment"
```

Each credentialed launcher starts through `env -i` and isolated Python before
parsing its explicit one-shot authorization flags and external paths, then
verifies a clean synchronized checkpoint, compares the internal Bash builder
to its exact `HEAD` blob, copies it to a sealed memfd, and executes that
descriptor with a fixed environment. Pathname replacement after verification
cannot change the bytes Bash receives. This prevents
caller `BASH_ENV`, exported functions, `PYTHONPATH`, and OpenSSL provider
settings from running while the source key path or snapshot is live. The
neutral recovery stager resolves only the fixed normal or diagnostic
candidate ID; the former SSH-named path is compatibility-only. For the
diagnostic profile it verifies the exact candidate and reserves all three
no-replace outputs before opening the signing key, then snapshots both inputs
privately. After staging, the builder removes the authorization guards. An
executable disposable-key input preflight injects hostile Bash startup hooks,
exported functions, Python and OpenSSL configuration, and a shim for every
builder helper. It proves none can intercept the wrapper-to-stager path, then
checks caller-input preservation, later child-environment scrub, and snapshot
destruction without signing. The diagnostic build must
reproduce manifest
`4eacb90f…e76`; the two signatures, bundles, recovery initramfses, wrapper
kernels, raw images, and AVB images must match before the private key snapshot
is destroyed. Neither preparation nor building grants a phone boot or
installation authority.

The launcher threat boundary trusts the already-running local owner session,
the root-managed dynamic loader, and the absolute `/usr/bin` runtime binaries.
It deliberately does not claim to contain `LD_PRELOAD`/`LD_AUDIT` injected by
an attacker controlling the parent process before `/usr/bin/env` starts; such
an attacker already has the same-user authority needed to read the external
0600 key. Production signing must therefore start from a trusted local shell
with no loader injection. The empty environment and isolated runtimes contain
all subsequent Bash, Python, PATH, and OpenSSL configuration channels.

The recovery gate's credential-free `policy-preflight` action accepts only
fully pinned diagnostic profiles and prints one exact canonical profile/
bundle/manifest/bundle-profile/target/recovery/trust/host-verifier record
before inspecting artifact paths. It grants `authority=none`; the later
`artifact-preflight` must still verify every byte.

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

The resulting exact wrapper, trust, manifest, and host-verifier hashes are
pinned in the live-gate profile. The consumed r2 profile retains its July 31
tuple. The diagnostic profile retains the fetch-policy-corrected August 1
production payload: raw wrapper `2f460aa0…628a01`, trust root
`f10ca076…c57b`, manifest `4eacb90f…f7e76`, and host verifier
`0a570805…b621`. Generation-zero AVB wrapper `f710bbcd…97b0ef` is consumed.
The listener-corrected successor used generation-1 AVB identity
`332889a8…b51830`; its raw payload and full descriptor structure were unchanged
except for the deterministic salt/digest pair. It booted once, fetched and
prepared the exact bundle, then exposed a host control omission that claimed
the diagnostic commit before NFS startup. It is consumed and explicitly
refused with both previous diagnostic wrappers. The corrected control policy
requires the diagnostic bundle to match the exact v3 profile/package NFS
handoff before commit and rejects unknown guarded bundles before phone access.
See the [corrected production build result](../test-results/2026-08-01-corrected-diagnostic-recovery-production-build.md),
the [generation successor](../test-results/2026-08-02-listener-successor-avb-generation-offline.md),
the [live NFS-bypass result](../test-results/2026-08-02-diagnostic-nfs-handoff-bypass-live.md),
and the [generation-2 result](../test-results/2026-08-02-nfs-gated-generation-2-avb-offline.md).
Generation-2 AVB `70fd77f7…fc72b1` changed only deterministic salt/digest
over the same raw recovery, passed artifact and connected preflight, and
booted once. Recovery returned `PREPARED` without a completed host transfer;
the NFS gate stopped before COMMIT, exact fallback passed, and the wrapper is
consumed. See the
[generation-2 live result](../test-results/2026-08-02-generation-2-fresh-fetch-gap-live.md).
Generation 3 includes fatal `/run` tmpfs validation, fresh-fetch-only PREPARE,
and the corrected lifecycle fixture. Those changes pass 41 lifecycle tests,
complete local CI, Claude review, GitHub Actions run `30750260056`, a
production-bound twin build, and exact phone-free artifact preflight. The
resulting AVB is `eb514a57…d77b6`. The immutable
`headless-diagnostic-generation3-offline-v1` profile continues to reject
connected actions. A distinct `headless-diagnostic-generation3-live-v1`
profile pinned the same complete chain and was selected by the lifecycle. Its
connected preflight passed and its sole cycle reached verified `PREPARED`, but
the 70-second host transfer service did not emit its completion receipt. NFS
never started, control failed before COMMIT, no target ran, and exact
strict-SSH fallback passed. Generation 3 is consumed and its allow row is
removed. The old generation-2 and generation-3 diagnostic profiles are now
offline-only historical evidence.
Source now nests the 180-second device worker, 190-second recovery supervisor,
195-second host transfer, 205-second privileged watchdog, 220-second lifecycle
receipt wait, 260-second PREPARE exchange, and 320-second complete control
window. Hardware-free tests enforce those margins and reject PREPARED plus
forged host receipt text when the host service exits nonzero. Commit `4c2da4b`
passed local and GitHub CI; its exact controller/server sources are installed
with matching hashes. Distinct generation-4 AVB `220e8556…270d` was then
issued twice over unchanged raw recovery `f1a7c5ad…6a4ce`, admitted once, and
booted once in RAM. Connected preflight passed. Recovery ACM/NCM and rollback
passed, but the bundle service lacked its completion marker when control's
45-second NFS-ready deadline expired. NFS did not start, COMMIT was never sent,
and no target ran. Automatic fallback returned the phone to Alpine; fixed
anchored restoration and strict fallback preflight passed after the host
watchdog. The versioned consumption transition removes the policy row,
relabels the artifact consumed/offline-only, requires its absence in both
policy gates, and updates both downstream hash pins. The image must never be
retried or flashed.
See the
[generation-4 offline result](../test-results/2026-08-03-generation-4-timeout-lattice-offline.md).
The phone-free profile transition is in the
[generation-4 live-profile result](../test-results/2026-08-03-generation-4-live-profile-offline.md).
The separate authority change is in the
[generation-4 admission result](../test-results/2026-08-03-generation-4-live-admission-offline.md).
The sole lifecycle is in the
[generation-4 live result](../test-results/2026-08-03-generation-4-nfs-readiness-live.md).
Generation-3 `boot` additionally required the lifecycle guard;
the controller sets that explicit policy variable on its boot child after
completing admission and connected preflight in the same invocation, and the
boot child then repeats all artifact and connected fastboot checks. Like the
other `ALLOW_*` variables, it records the intended invocation path rather than
authenticating the caller. Post-result consumption remains the required
versioned policy/inventory/test/hash transition described above; the live gate
does not edit Git. See
the
[generation-3 production result](../test-results/2026-08-02-generation-3-fresh-fetch-production-build.md)
and [live result](../test-results/2026-08-03-generation-3-transfer-timeout-live.md).
The installed r2 bundle remains historical connected-preflight evidence only.

## Historical r2 credential-free preflight

Before the now-consumed r2 production signing, the workflow ran the preflight
shown in the build sequence. Retain it only as regression evidence; do not
reuse r2.

This command requires a clean branch synchronized with its exact `origin`
peer. It securely snapshots the caller-owned mode-`0444` historical and r2
candidates, reproduces both from the non-fixture package, verifies that the
two actual records differ only in `bundle`, snapshots and hashes the exact
Image/DTB/initramfs, and regenerates the pinned unsigned r2 manifest identity
through the same configuration factory and production packager used by the
signed build. It has no signing-key argument; apart from local read-only Git
checkpoint commands, it exits before credential, privilege, external-network,
fastboot, or phone access. A pass grants no artifact admission or phone action
by itself; operator authority comes only from the central standing record.

## Local deployment-key preflight

After a reviewed commit is pushed and the branch is clean and synchronized
with its exact `origin` peer, local admission is:

```bash
scripts/host/run-minimal-headless-live-cycle.py key-preflight
```

For the distinct diagnostic candidate, use the exact parallel action:

```bash
scripts/host/run-minimal-headless-live-cycle.py diagnostic-key-preflight
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
The diagnostic action additionally pins the diagnostic reporter/initramfs,
candidate, bundle profile, and target identities while retaining the same
key-bound v3 Arch package checks.

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

For the diagnostic successor, use:

```bash
scripts/host/run-minimal-headless-live-cycle.py diagnostic-preflight
```

Preflight proves:

- local deployment-key admission already passed for the exact non-fixture v3
  package/candidate/runtime-manifest chain;
- every private output name is unused;
- the repository is clean and exactly synchronized with its remote-tracking
  branch;
- no NFS handoff marker or export mount remains; TCP 8080 has no IPv4 wildcard
  or fixed `169.254.77.1` listener and no IPv6 wildcard or IPv4-mapped
  equivalent; IPv4 TCP/UDP 2049 and 32767, NFS export, NFS worker, and
  `drop`-zone runtime state are absent; an unrelated loopback-only TCP 8080
  listener is allowed;
- both privileged launchers are installed and byte-current; the bundle
  launcher runs the exact descriptor-based inventory/manifest validator
  without a listener; the fixed root-owned NFS entry point and export
  installer are byte-current; and the NFS entry point verifies the sealed
  export root and required host commands through the prompt-free socket;
- the corrected recovery image, twin, target bundle, trust root, native
  verifier, wrapper configuration, and AVB layout pass the existing live-gate
  verification;
- the fallback controller validates its fixed SSH/IP tools, exact client key,
  exact one-line host-key pin, 600-900 second wait, and recovery-anchor age
  budget without contacting the phone; and
- exactly one `lahaina` fastboot device is present.

The stable-recovery artifact gate now admits the exact
`headless-ssh-deployment-v3` wrapper, trust root, manifest, verifier, and
target identity. The fixed host components, read-only v3 export, NFS
preflight, artifact gate, and connected fastboot gate now pass. Fallback
classification uses the already-admitted deployment client key and retained
host-key pin over the exact recovery-to-fallback USB continuity path. Its
fixed non-interactive probe never enters the BusyBox line editor, so
shell-history writes and the ACM storage guard are no longer part of the
lifecycle.
The NFS controller requires the exact admitted package hash, fixed export
root, and canonical handoff marker. Preflight must not boot, transfer a
payload, start a network service, contact target SSH, or offer the key to a
phone. The NFS artifact check may execute the fixed root-owned verifier through
the operator socket, but creates no export, mount, listener, marker, firewall
rule, or interface state. The unprivileged lifecycle opens the fixed server's
canonical root-owned mode-`0600`/`0644` `/var/lib/nfs/etab` with
`O_NOFOLLOW`, validates and reads the same bounded inode, and requires an
empty export inventory. It does not interpret `exportfs -v` output because
that command can return success while emitting an `.etab.lock` permission
diagnostic when run without root. The later fixed root-owned server preflight
performs the authoritative privileged `exportfs` check before any boot.

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
ALLOW_FALLBACK_SSH_CONTROL
ALLOW_FALLBACK_SSH_ATIME_EFFECTS
```

These guards remain an invocation-time technical boundary. The standing
operator authorization permits the agent to set them without another prompt,
but every cycle still requires a distinct unconsumed candidate and fresh
private evidence directory.
Use `run` only for the normal SSH acceptance profile and `diagnostic-run` only
for the exact diagnostic successor. The latter still requires every guard
above because it performs the same temporary boot, credential-bound fallback
proof, and one non-retryable commit; it does not offer the SSH key to the
diagnostic target.

## Private outputs

All lifecycle outputs are created exclusively as mode-`0600` files below
`EVIDENCE_DIR`. Important records include:

- `recovery-usb.anchor`
- `target-known-hosts`
- `recovery-control.log`
- `minimal-headless-runtime.record`
- `early-target-diagnostics.log` and `early-target-diagnostics.json`
- `fallback-identity.record`
- `fallback-preflight.log`
- `intent-resolution.log`

The directory and every output must remain outside Git. Existing files are
never overwritten.
The anchor's exact seven-field schema is directly bound by test to the real
`pin-minimal-headless-host-key.py capture-recovery` producer, including its
literal `ROG5 recovery` USB product. Fallback contact must start within 3,600
seconds of capture; even the maximum 900-second ACM wait remains below the
fallback controller's 7,200-second anchor-age limit. Immediately before root
restoration, both the lifecycle and privileged broker recheck the 3,600-second
wall-clock contact-start age, so host suspend cannot bypass that gate. The
fallback controller then rechecks wall-clock anchor age and physical location
after discovery and before sending the launcher.
The fallback identity record retains only bounded non-sensitive proof
metadata: boot ID, USB location, nonce, maximum sampled temperature, and
SHA-256 identities of the signed record, signature, and inspected host-key
pin. The pin itself, signature bytes, and SSH host private key are never
published.

## Failure and outcome rules

- Before COMMIT, failure stops all started host processes and creates no
  resolved intent. A live privileged NFS child is stopped through its fixed
  authenticated `cancel` action, not an unprivileged signal.
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

The recovery fetch boundary similarly preserves root, staging, connect,
worker setup/fork/timeout/signal, transport, header, manifest, artifact, EOF, parent
verification, normalization, final verification, publication, outer timeout,
and exec failure classes in `last_error`. The 46 MiB fetch uses a 180-second
monotonic inner deadline and a 190-second responder fetch-child deadline. The
260-second same-session host PREPARE deadline also covers the responder's
subsequent 30-second signature verification and 15-second kexec-load bounds;
the 320-second lifecycle wait additionally covers initial ACM stabilization.
A transport replay shares the original host deadline and cannot double the
budget. The larger fetch budget is an exploratory bound for the next measured
run, not evidence that the bundle needs three minutes. These are hard bounds,
not permission to retry a decided PREPARE request.

## Hardware-free coverage

`test-verify-headless-ssh-v2-key-admission.py` covers sixteen admission
scenarios, `test-fallback-acm-control.py` covers fifty fallback
protocol tests, `test-recovery-host-controller.py` covers twenty-two privileged
controller tests, `test-recovery-host-socket.py` covers eleven socket tests, and
`test-run-minimal-headless-live-cycle.py` covers thirty-seven lifecycle test
methods. Together they prove:

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
- bundle-server cleanup and fallback-profile deferral precede NFS startup;
- the exact fallback profile cannot autoconnect to recovery, restores only
  after unique same-port Alpine raw-product/NCM identity, is idempotent and
  serialized, verifies the actual sysfs `cdc_ncm` driver independently of
  udev properties, and rolls partial activation, detach, or timeout back to
  the fail-closed deferred state before SSH;
- the root broker independently accepts only an ordered mode-`0600`,
  single-link, caller-owned, same-host-boot recovery anchor within its
  freshness bound; it derives the physical location itself rather than
  trusting a caller-provided location;
- the deferred postcondition proves the exact profile UUID is inactive and
  autoconnect is disabled, while every positive restoration inspection and
  mutation plus strict SSH consumes one shared fallback deadline;
- residual protected-zone rules, `/30` addresses, or NetworkManager ownership
  changes block NFS startup before COMMIT;
- one and only one `prepare-commit` process is started;
- diagnostic collector readiness precedes recovery control, a startup failure
  prevents COMMIT, rejected evidence is retained, diagnostic mode never enters
  target SSH acceptance, and its intent resolves only after exact fallback;
- success resolves only after exact fallback;
- fallback classification uses strict key-only SSH, one exact nonce-framed
  signed record, exact USB-NCM identity/location and route, bounded output,
  and post-reply USB revalidation;
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
- the standing-authorized guarded reboot requires verified ACK, commit,
  disconnect, same-port fastboot, and exact product without flash, mount, or
  any phone
  write beyond the bounded BusyBox-history and possible atime effects covered
  by the standing authorization;
- a terminal guarded-reboot timeout reports whether fallback disconnect,
  anchored-port re-enumeration, non-fastboot USB, or fastboot-userspace
  discovery was observed; this best-effort classifier cannot admit a device,
  and hotplug races resolve to an unknown observation rather than aborting the
  authoritative exact-fastboot wait;
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
  `UNKNOWN`;
- final cleanup tolerates only a transient disagreement between the exact USB
  identity and `/30` address views, requires one second of continuously clean
  state, and shares one absolute deadline across subprocesses; and
- non-identity cleanup residue fails immediately, while neither cleanup
  stabilization nor its failure can create a second COMMIT or fallback
  contact.

The tests use only temporary mock processes, private fixture files, and
disposable test keys. They do not contact the phone, start PolicyKit, open a
real firewall/NFS window, or use personal/deployment credentials.

The exact source identities, test result, and independent review closure are
recorded in the
[original lifecycle result](../test-results/2026-07-29-minimal-headless-live-cycle-offline.md)
and the
[deployment-key admission result](../test-results/2026-07-31-headless-ssh-v2-key-admission-offline.md).
