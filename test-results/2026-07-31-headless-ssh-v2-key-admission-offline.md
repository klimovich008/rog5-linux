# Headless SSH v2 deployment-key admission: offline result

Date: 2026-07-31

Outcome: **PASS for the hardware-free admission boundary; live execution
remains HOLD**.

No phone, fastboot/ADB transport, PolicyKit action, firewall/NFS service,
personal key, deployment key, root credential, or signing credential was used.
All private keys in this result were disposable test fixtures created below
private temporary directories and removed by the test suite.

## Boundary implemented

`verify-headless-ssh-v2-key-admission.py` admits one exact caller key and
artifact chain. It:

- requires an absolute canonical caller-owned private-key path outside Git, a
  private caller-owned parent, mode `0400` or `0600`, one link, and a bounded
  regular-file size;
- opens the key without following links and derives its public half through
  fixed root-owned mode-`0755` `/usr/bin/ssh-keygen`;
- addresses the already-open descriptor through `/proc/self/fd`, supplies no
  interactive input, uses a minimal environment, applies a timeout, and proves
  the named file and descriptor identity stayed unchanged;
- accepts only one unencrypted Ed25519 key and canonicalizes the algorithm and
  Base64 fields without retaining an optional comment;
- requires package format `rog5-headless-network-root-package-v3`,
  `build_profile=headless-ssh-v2`, candidate and bundle
  `headless-ssh-network-root-v3`, target `headless-ssh-network-root`, release
  `7.1.4-g7a5cef0db479`, and the established timeouts;
- pins the accepted 40,049,152-byte Image, corrected 102,870-byte DTB, and
  generic 5,978,369-byte initramfs identities;
- requires exact root-field equality from package to offline candidate to
  signed runtime manifest;
- rejects the tracked public fixture fingerprint plus the tracked fixture
  source archive, sealed archive, tree, seal, and runtime-manifest identities;
  and
- emits only a canonical 15-field public record: artifact hashes, root
  identities, the public fingerprint, and `authority=none`.

The verifier deliberately does not duplicate bundle signature, expanded-root,
wrapper, AVB, or connected-device verification. Those remain later,
independent gates.

## Lifecycle ordering

`run-minimal-headless-live-cycle.py` now accepts only:

```text
BUNDLE=headless-ssh-network-root-v3
ROG5_STABLE_RECOVERY_PROFILE=headless-ssh-deployment-v3
```

For `key-preflight` and `preflight`, exact key-admission and
phone-credential-use guards are required before dependency or path
inspection. The controller then requires:

1. fixed offline dependencies;
2. a clean branch tracking its exact `origin` peer with local HEAD equal to
   the remote-tracking checkpoint;
3. canonical private-key, package, candidate, and bundle-manifest inputs; and
4. successful local admission.

`key-preflight` exits at that point. It cannot inspect host network state,
invoke PolicyKit, discover a phone, boot, transfer a payload, or contact SSH.
`preflight` and `run` may progress to their existing gates only after the same
admission record passes. `run` additionally retains every prior full-cycle
guard, no-retry COMMIT rule, armed watchdog, exact fallback proof, cleanup
proof, and durable intent resolution.

At this checkpoint the real stable-recovery gate and root-owned NFS controller
did not yet implement `headless-ssh-deployment-v3`. The later
[profile-threading result](2026-07-31-headless-ssh-v3-profile-threading-offline.md)
adds exact NFS and runtime identity propagation, while stable-recovery hashes
and the installed v3 export remain intentionally absent. A connected preflight
still cannot reach fastboot until the non-fixture chain and those fixed
artifacts exist.

## Hardware-free tests

Focused results:

```text
test-prepare-recovery-candidate.py: 7 passed
test-verify-headless-ssh-v2-key-admission.py: 14 passed
test-run-minimal-headless-live-cycle.py: 17 passed
```

The admission suite covers the exact passing chain and canonical CLI output,
fixture-key rejection, each fixture root identity, key/package mismatch,
every package/candidate root mismatch, candidate tuple and artifact mutations,
manifest field/hash mutations, unsafe path/parent/file metadata, symlinks,
hard links, file replacement, encrypted and RSA keys, malformed output
records, duplicate fields, fixed-keygen enforcement, and static exclusion of
live transports.

The lifecycle suite proves key guards fail first, historical profiles fail
before private-key inspection, `key-preflight` exits before phone/privilege
operations, admission precedes connected preflight, and all existing
bundle/NFS ordering, non-retry, watchdog, fallback, cleanup, and durable-intent
cases remain intact.

The complete host suite also passed:

```text
PATH="$PWD/build/ci-host-tools:$PATH" scripts/host/test-repository-linux.sh ci
PASS repository Linux ci tier
```

The ignored `build/ci-host-tools` directory supplies only the already-qualified
CI wrappers used by this host; it is not a project artifact or authority.

## Independent review

A bounded, safe-mode, tool-free, nonpersistent Claude Opus review received
only the relevant source and patch on standard input. Its first pass prompted
two useful explicit defenses: compare the derived algorithm directly with
`ssh-ed25519`, and check all six candidate root fields before indexing them.
The shared authorized-key parser and candidate adapter already rejected those
cases, but the admission verifier now states and tests both invariants locally.

The focused follow-up reviewed the shared parsers, revised verifier, and
hostile tests and returned `NO_BLOCKERS`. It specifically confirmed the
open-descriptor/key-path identity checks, candidate two-read reconciliation,
exact manifest schema, package/candidate/manifest cross-binding, fixture
exclusion, fixed failure output, and lifecycle ordering before privilege or
phone action.

## Remaining HOLD

Before connected preflight:

1. obtain separate explicit authorization to use one deployment key;
2. rebuild the source root, v3 package, corrected candidate, signed runtime
   bundle, recovery wrapper, and retained records around that public identity;
3. install the exact `headless-ssh-deployment-v3` read-only export and pin its
   stable-recovery wrapper/trust/manifest hashes;
4. pass local key admission and all host-only signature/root/wrapper/AVB
   gates from a clean pushed checkpoint; and
5. request fresh authorization for connected preflight and, separately, one
   attended temporary boot.

This result grants no credential, signing, phone, boot, flash, wipe, storage,
or retry authority.
