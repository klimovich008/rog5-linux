# Generation-6 deferred-profile association correction — offline

Date: 2026-08-03

Result: **PASS focused offline**. The complete-transfer/empty-control-log
boundary is reconstructed from sealed private timestamps, the lifecycle's
source order, and the host NetworkManager journal. The host aborted on a false
deferred-profile rejection before it waited for `PREPARED`; Generation 6 did
not establish recovery-side silence. This result does not create a live
`PREPARED` record, authorize a boot, or permit reuse of Generation 6.

## Reconstructed order

- the signed 46,163,787-byte transfer completed at Unix time `1785754867`;
- the private fallback-profile-restore log was created at `1785754877`, exactly
  the lifecycle's 10-second cleanup-stabilization window later;
- the collector did not expire until `1785754969`, 102 seconds after transfer
  completion;
- the recovery-control log was opened at `1785754859`, remained zero bytes,
  and was terminated by the pre-commit exception path before the lifecycle
  reached its later control wait.

The source order is fixed: after `wait_bundle()` returns, the lifecycle calls
`wait_host_clean(recovery_ncm=...)`; only after that passes does it start NFS
and wait for recovery control. The live error was
`deferred recovery interface retains an active profile`, so the lifecycle
entered fallback from the first post-transfer cleanup gate.

NetworkManager's journal independently records that the exact interface was
deactivated, became `unmanaged`, and accepted `device-managed=false` at Unix
time `1785754858.844`. There was no subsequent activation before bundle
controller exit. `GENERAL.CON-UUID` retained the exact fallback UUID as the
last profile association even though the device was unmanaged and
address-free. The verifier treated that retained association as an active
profile and rejected clean state.

## Correction

The deferred-profile verifier still requires:

- exactly one anchored recovery NCM interface with unchanged product, name,
  and firewall zone;
- no IPv4 address on that interface;
- NetworkManager ownership reported as `no`;
- one exact fallback profile UUID, ID, interface binding, and
  `connection.autoconnect=no`; and
- the full host residue check and one continuous clean dwell.

Only after those checks pass may `GENERAL.CON-UUID` be empty or contain one
line equal to the exact fallback profile UUID. Any wrong, duplicate, mixed, or
otherwise malformed association remains a rejection. Managed, addressed, or
autoconnect-enabled state still fails even with the exact retained UUID.

## Verification

- Python syntax compilation and diff checks: pass;
- focused lifecycle suite: 56 tests pass;
- transient wrong-association observation: rejected until the outer bounded
  stabilization loop observes one continuous clean dwell;
- constrained credential-free Claude Opus diff review: completed; direct
  `nmcli` inspection disproved its colon-record concern, while supported
  mixed-UUID, precedence, explicit-empty, and exact-error coverage was added;
- complete repository Linux `ci` tier: pass;
- phone, fastboot, recovery, SSH, NFS export, and host-network mutation: none.

A distinct successor must still prove a live correlated `PREPARED`; this
offline result cannot infer one from Generation 6.
