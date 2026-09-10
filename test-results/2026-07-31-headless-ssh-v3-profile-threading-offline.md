# Headless SSH v3 profile threading: offline result

Date: 2026-07-31

Outcome: **PASS for host-only identity propagation; connected execution
remains HOLD**.

No phone, fastboot/ADB transport, PolicyKit action, firewall/NFS service,
personal or deployment credential, root credential, or signing credential was
used. The machine root password was not used or stored.

## Boundary implemented

The exact public identities emitted by deployment-key admission now remain
bound across the rest of the one-shot host workflow:

1. the lifecycle passes the admitted v3 package SHA-256 to a fixed
   `headless-ssh-deployment-v3` NFS profile;
2. the launcher maps only that profile to
   `/var/lib/rog5-headless-ssh-network-root-v3/root`;
3. the root-owned server requires a root-owned mode-`0444` package manifest
   whose file hash is the admitted package hash, verifies the root against it,
   and rechecks the hash immediately before handoff;
4. its canonical v2 marker binds profile, fresh handoff token, exact
   `169.254.77.1:2049` listener, NFSv4.2-only policy, fixed export root, and
   admitted package hash;
5. recovery control requires that exact marker and listener before COMMIT;
6. the target probe accepts only `headless-network-root-v1` or
   `headless-ssh-network-root-v3`; and
7. runtime acceptance receives the admitted candidate path and hash, requires
   an absolute canonical caller-owned read-only record outside Git, validates
   the fixed deployment tuple with the shared candidate adapter, rejects the
   tracked fixture tree and seal, detects replacement, and never falls back
   to the historical candidate.

The historical no-argument launcher, v1 marker, recovery-control defaults,
target candidate, and runtime-verifier candidate remain unchanged.

The root-owned server also rejects a package identity for every non-v3 export
root. This closes an independent-review finding that otherwise allowed an
unbound v2-marker branch in a direct privileged invocation.

## Hardware-free verification

Focused results:

```text
test-run-minimal-headless-live-cycle.py: 17 passed
test-stable-recovery-control.py: 13 passed
test-verify-minimal-headless-runtime.py: 27 passed
test-collect-minimal-headless-runtime.sh: PASS, 47 mutations
test-run-minimal-headless-runtime-acceptance.sh: PASS, historical + v3
test-headless-network-root.py: 13 passed
test-network-root-host.sh: PASS
```

The complete host suite passed:

```text
PATH="$PWD/build/ci-host-tools:$PATH" scripts/host/test-repository-linux.sh ci
PASS repository Linux ci tier
```

## Independent review

A bounded, safe-mode, tool-free, nonpersistent Claude Opus review received
only credential-free patch text. It found that the installed NFS server
accepted the optional package argument before proving the selected root was
the v3 root. The server now initializes deployment state explicitly and
rejects any package identity for every non-v3 root. The focused tests and full
CI pass after that correction.

One review claim that the runtime verifier lacked `import stat` was false:
the import predates this patch, the v3 metadata gate executes in 27 passing
tests, and Python bytecode compilation passes.

A full-source follow-up confirmed the exact v3 marker binding, argument
arities, historical marker bytes, and variable initialization. It also
questioned publishing server readiness before target-interface discovery.
That order is required: the target NCM gadget does not exist until recovery
commits kexec, so making interface discovery a pre-COMMIT condition would
deadlock. The marker attests server/export readiness; after COMMIT the server
admits and configures only the exact target gadget, and the independent target
watchdog bounds mount failure.

## Remaining HOLD

This change does not create a deployable chain. Before connected preflight:

1. obtain fresh explicit authorization to use one deployment key;
2. rebuild the root, package, candidate, and signed runtime bundle around its
   public identity;
3. install the package at the fixed v3 export path through a separately
   reviewed no-replace installer profile;
4. pin and mutation-test the exact stable-recovery wrapper, trust root,
   manifest, and bundle hashes;
5. pass all host-only build, signature, root, wrapper, AVB, key-admission,
   export, and artifact-preflight gates from a clean pushed checkpoint; and
6. request fresh authorization for connected preflight and, separately, one
   attended temporary boot.

No credential, signing, phone, boot, flash, wipe, storage-write, watchdog
disarm, or retry authority is granted.
