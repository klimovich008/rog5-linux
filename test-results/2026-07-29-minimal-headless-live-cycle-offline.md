# Minimal-headless one-shot lifecycle — offline result

Date: 2026-07-29
Result: **PASS — hardware-free implementation and review**

No phone was booted or contacted. No SSH client credential was offered or
read by a child process, no PolicyKit action was executed, and no firewall,
NFS, NetworkManager, kernel, phone-storage, signing, or GitHub state was
changed by this checkpoint.

## Result

The host now has one fail-closed controller for the complete temporary
recovery → signed minimal-headless target → exact fallback lifecycle.

It performs all read-only preflight checks before boot authority, captures a
same-boot recovery USB anchor, starts the fixed one-transfer bundle server,
waits for its process and independently proves cleanup, starts the fixed
root-owned read-only NFS server, allows one non-retryable COMMIT, pins the
volatile target Ed25519 key before offering the client key, verifies one
canonical runtime record, leaves the watchdog armed, waits for exact fallback,
proves host cleanup, and only then resolves the durable intent.

The NFS privilege boundary no longer requires root to execute a mutable
repository script. The host installer publishes root-owned mode-`0555`
copies of the server and its two root-tree verifiers. A PolicyKit preflight
verifies their source hashes, the sealed minimal root, host NFS dependencies,
service state, and firewall baseline without creating runtime state.

## Failure policy

- Bundle cleanup must restore the global firewall/nonlocal-bind snapshot and
  exact recovery-NCM address, firewall-zone, and NetworkManager state before
  NFS can start.
- Protected-zone rules, TCP/UDP listeners, exports, NFS workers, export
  mounts, handoff markers, temporary `/30` addresses, forwarding changes, and
  `ip_nonlocal_bind` changes are independently rejected.
- One new caller-owned mode-`0600` ledger record is discovered by directory
  delta. COMMIT is never replayed, including transport loss with no diagnostic
  and parent interruption while the child remains alive.
- A rejected target can resolve only as `FALLBACK_RETURNED` after exact
  fallback and cleanup. An accepted target resolves as `TARGET_ACCEPTED` only
  after runtime acceptance, exact fallback with a different boot ID, and
  cleanup.
- Missing fallback, ledger correlation, or cleanup proof leaves the durable
  outcome `UNKNOWN`.

## Focused verification

`test-run-minimal-headless-live-cycle.py` passes fourteen scenarios:

1. guards win before dependency or credential-path inspection;
2. preflight stops before phone boot and SSH;
3. successful bundle-cleanup → NFS → target → fallback ordering;
4. runtime rejection returns to fallback without COMMIT retry;
5. control failure before intent is never resolved;
6. transport loss uses the durable ledger without replay;
7. silent post-arm loss is recovered from the ledger without diagnostics;
8. real parent `SIGINT` after ledger arm terminates the child, rescans the
   ledger, and resolves through fallback;
9. missing fallback proof leaves `UNKNOWN`;
10. protected-zone cleanup residue blocks NFS;
11. recovery `/30` or NetworkManager residue blocks NFS;
12. final protected-zone residue prevents resolution;
13. final address residue prevents resolution; and
14. the installed NFS surface remains exact and fixed.

The related headless-root, NFS host, recovery controller, stable control,
host-key, runtime-acceptance, and fallback suites also pass. ShellCheck,
Python compilation, Markdown-link validation, and `git diff --check` pass.

The complete repository Linux `ci` tier passes after integration.

## Independent review

The Standards axis initially found four hard issues: late privileged `PATH`,
an uninventoried `python3`, guard ordering after credential-path inspection,
and over-forwarded authorization guards. All four were fixed and the reviewer
returned `RESOLVED`.

The Spec axis initially found incomplete bundle/final cleanup proof, a
diagnostic-dependent ambiguous-intent oracle, and missing injected failures.
It then found one parent-interruption race. Independent state/zone/NCM checks,
direct ledger-delta discovery, cleanup-residue fixtures, and the real-SIGINT
fixture fixed those findings; the final reviewer returned `RESOLVED`.

The already-authorized Claude safe reviewer was retried with tool-free,
nonpersistent input. Claude returned the existing session-quota limit
(`resets 11:20pm Europe/Warsaw`) before reviewing. This was an advisory
availability failure, not an authentication or security failure, and no
Claude finding is claimed.

## Reviewed identities

```text
4ab24d4cbdfd20c6e7d3a7acaa3aabf06d9dc8f8ed09832528458c2777d3c42d  scripts/host/run-minimal-headless-live-cycle.py
c642789dddda5b2e0ce091019d7958a31680e0aa7b2b23d11e4ddcd5832cd662  scripts/host/test-run-minimal-headless-live-cycle.py
1e113834257b26e57e04b15f34740efe6b1a796ad7d61056f96e4771e714858d  scripts/host/run-headless-network-root-server.sh
3718d6944fb02a1981786fc30c54bcf664f0336dbfd744a7fb94991b8edda5ed  scripts/host/serve-network-root.sh
daf3b866963e2c94fda89ddafe396dfa4c8f389a0caf1128637c8f4bbecd1cdc  scripts/host/headless-network-root.py
184cdc8c37a7d8e1aa55314866bfad2137c9b626657bfe8f1d0c4c9f11c2cdbc  scripts/host/install-recovery-host-controller.sh
544de4b61cc65ffc162d540fc7fb8154e1e4170fd4900fc926fec5b92aaf87f0  scripts/host/run-recovery-bundle-server.sh
097fb88be1a8e3e3155025091725750f722890637b323b445ea00e1710a315e2  docs/minimal-headless-live-cycle.md
```

These are source identities, not live authority. The installed root-owned
host copies are expected to be stale until a separately approved PolicyKit
installation.
