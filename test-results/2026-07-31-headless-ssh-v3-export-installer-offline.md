# Headless SSH v3 export installer: offline result

Date: 2026-07-31

Outcome: **PASS for the host-only installation boundary; real installation
and connected execution remain HOLD**.

No phone, fastboot/ADB transport, PolicyKit action, firewall/NFS service,
personal or deployment credential, root credential, signing credential, or
real host export was used. The machine root password was not used or stored.

## Boundary implemented

The v3 deployment lower now has a separate unprivileged admission launcher and
fixed root-owned installer.

The launcher:

1. requires three exact one-operation guards before parsing arguments or
   inspecting a credential;
2. requires a clean branch tracking its exact `origin` peer with local
   `HEAD` equal to the remote-tracking checkpoint;
3. requires root-owned mode-`0555` installed installer/verifier components
   whose bytes equal the reviewed checkout;
4. reruns the complete non-fixture private-key/package/candidate/runtime
   manifest admission gate;
5. independently binds the archive size and hash to the admitted package; and
6. invokes PolicyKit only with the fixed installed program, canonical archive
   and package paths, and admitted package SHA-256.

The private key, candidate, and runtime manifest never enter the privileged
command.

The installer:

1. accepts only canonical caller-owned, single-link, read-only archive and
   package files under a caller-owned mode-`0700` directory;
2. requires the exact `network-root-v1` / `headless-ssh-v2` / package-v3
   tuple and rejects the public fixture fingerprint plus every tracked fixture
   root identity;
3. copies the caller-owned archive into an anonymous root-owned `O_TMPFILE`
   while checking the exact admitted size and SHA-256;
4. inspects and extracts only that unreachable private snapshot, closing the
   caller-owned inode rewrite and pathname-replacement windows;
5. rejects escaping, duplicate, sparse, device/FIFO, embedded-credential,
   symlink-ancestor, and unsafe-hardlink archive members before extraction;
6. extracts into a private deterministic stage, writes the package manifest
   exclusively, and verifies the complete root through the shared v3
   verifier;
7. fsyncs regular files and directories bottom-up; and
8. publishes with `renameat2(RENAME_NOREPLACE)` and syncs the parent, never
   replacing a concurrently created or previous export.

Failed deterministic stages remain for explicit privileged forensic
inspection. They are never silently removed or reused.

## Hardware-free verification

Focused results:

```text
test-install-headless-ssh-deployment-export.py: 11 passed
test-run-headless-ssh-deployment-export-install.py: 8 passed
test-recovery-host-controller.py: 12 passed
test-headless-network-root.py: 13 passed
Python and shell syntax: PASS
git diff --check: PASS
```

The complete host suite passed:

```text
PATH="$PWD/build/ci-host-tools:$PATH" scripts/host/test-repository-linux.sh ci
PASS repository Linux ci tier
```

## Independent review

A bounded, safe-mode, tool-free, nonpersistent Claude Opus review received the
complete privileged installer source. It identified a real archive TOCTOU:
holding a descriptor did not stop the caller from making its own inode
writable and changing bytes between inspection and extraction. It also found
that syncing only the stage directory did not make extracted file data durable
before publication.

The installer now creates one unreachable anonymous snapshot and uses it for
both inspection and extraction. It also syncs regular files and directories
bottom-up before no-replace publication. New in-place rewrite and durability
ordering tests pass. A full-source re-review confirmed both fixes and the
archive, metadata, descriptor, and publication boundaries.

The follow-up noted that a failed deterministic stage blocks automatic retry.
That is the intended fail-closed forensic policy: the installer does not
delete root-owned extracted state or hide a failed attempt. Cleanup is a
separate explicit privileged decision.

A separate complete launcher review returned `NO_BLOCKERS`.

## Remaining HOLD

This result implements no real host or phone mutation. Before connected
preflight:

1. obtain fresh explicit authorization to use one deployment key;
2. rebuild the root, package, candidate, runtime manifest, and signed bundle
   around its public identity;
3. review and install the fixed host components;
4. invoke the admitted no-replace launcher once to publish the exact v3
   export;
5. pin and mutation-test the stable-recovery wrapper, trust root, manifest,
   and bundle hashes;
6. pass every host-only build, signature, export, key-admission, wrapper, AVB,
   and artifact-preflight gate from a clean pushed checkpoint; and
7. request fresh authorization for connected preflight and, separately, one
   attended temporary boot.

No credential, signing, phone, boot, flash, wipe, storage-write, watchdog
disarm, cleanup, or retry authority is granted.
