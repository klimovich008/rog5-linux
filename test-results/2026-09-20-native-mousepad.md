# Native ARM64 Mousepad component — 2026-09-20

Source `d2d346429ed2a09e8e6f51fd95dfbea3b9747ee5`, tree `ae343b3abef4f3b8882dfa135df41dc90f9a095d`. No product code changed.
Previous turn was progress: deadline guard qualification completed. This turn
prepares and executes a separate native ARM64 component control. Physical rows
remain NOT RUN. No phone, signing, candidate, claim or protected-storage action.

## Result

| Controlled arm | VM duration | Close result |
|---|---:|---|
| Idle | 81.291s | PASS, exit 0; 0.95s signal-to-exit, 0.695s window-to-quit; document unchanged |
| Synchronized CPU load | 86.096s | FAIL, exit 137; TERM then KILL after 2.15s; window removed but no quit return |

Both load workers made CPU progress (163 and 179 ticks) during the close interval.
The loaded run's post-close checksum was interrupted and is not verified. Seven
preparatory fixture failures remain recorded. Contention is sufficient for this
symptom in this component; the original Denial cause and instruction location
remain unproven.

Prior full Denial VM remains FAIL: Foot0/Mousepad137. Generic VM or a Weston
component is not Denial acceptance or ROG5 GPU evidence.

## Exact scope and method

Retained Linux 7.1.4, GTK/Mousepad libraries, prepared caches, Wayland/IM overrides
and quit-return diagnostic are used unchanged. Separate [Weston 15.0.1-3 ARM64](https://archlinuxarm.org/packages/aarch64/weston)
archive is 1,404,596 bytes, SHA256
`2da79ea9f1059b5e068debbf6c5b4f650c59c9b6725d98479c5c99753d878f36`.
The existing package verifier checked archive/signature hashes, retained trusted
non-revoked signer and .PKGINFO. Keyring freshness is NOT RUN. This authorizes
no installation. Optional Weston RDP/VNC backends were not exercised.

Weston headless/Pixman runs inside the ARM64 system VM. Native UID 1000 Mousepad
uses a private D-Bus session. Host reuses EditorProtocol to require attributed
committed surface and frame callback before atomically publishing close token.
TERM is sent to the owned timeout wrapper, retaining its 2s TERM/KILL behavior.
The loaded control starts two owned bounded CPU burners immediately before
close and records their liveness and CPU ticks. No graphics/input/close code is
replaced. In the loaded run, status 137 and explicit TERM/KILL were recorded before
the post-close checksum was interrupted by session termination; that checksum
is NOT COMPLETE. Close timing uses CLOCK_BOOTTIME samples only; lifecycle phase
timing uses CLOCK_MONOTONIC separately. Portal readiness requires a real typed Settings.ReadAll reply.

The guest enforces 45s application startup and 70s overall session, and the host
95s overall VM limit. Boot and portal preparation are not subtracted from a
second incorrectly started 70s observer clock. The prior failed observer remains
recorded. No close/capture deadline was widened.

## Retained failed preparation and controls

- Initial package verification used a missing keyring path, then tried an armored
  keyring directly. Reused the repository verifier with a dearmored retained
  keyring; no unverified archive was executed. An adapter type error was fixed
  before verification succeeded.
- First VM: UID 1000 could not read privately permissioned /etc after root copying;
  D-Bus failed before Mousepad. Its memory-allocation message is not an OOM finding.
- Second: writable 9P capture with security_model=none produced subordinate-owner
  mode 0600 files; host could not read or finalize its report. Hashes recovered in
  the owning rootless user namespace without changing source file bytes/modes.
- Third: mapped-file capture worked, but no window arrived within startup bound.
  This is not a close failure.
- Fourth: portal activation completed, but untyped empty argument was sent as a
  string instead of array; corrected to explicit `@as []`.
- Fifth: real mapped frames were logged at 79.579s, after the mistakenly boot-relative
  observer deadline. Retained-log semantic replay confirms the actual parser
  accepts that attributed frame. Runtime remains FAIL, not retrospectively PASS.
- Sixth: mapped frame reached; /proc/PID/task/PID/children lookup failed because
  CONFIG_PROC_CHILDREN is disabled. Cleanup then signalled timeout and recorded
  complete GTK quit/shutdown phases. This is not a qualified controlled close.
  Replaced the lookup with diagnostic PID plus live parent and exact executable
  hash checks; no kernel change or unchecked PID scan.
- First loaded attempt stopped before the intended close: a burner expired during
  sequential readiness. Final loaded fixture blocks both burners on SIGUSR1, then
  starts their unchanged four-second work together; parent records live CPU ticks.
  The idle control never executes this code, so its result is retained.

Run durations/statuses, complete commands, hashes and selected phase evidence are
in the qualification JSON; raw logs/cache-input inventories remain private under
`rog5-native-mousepad-20260920-r1`. Source/runtime inputs stayed unchanged during completed runs.
Controlled close arms: 1 PASS, 1 FAIL; seven earlier preparatory VM failures remain
FAIL. Native run durations and statuses are enumerated in the JSON. The second
run's duration was not finalized because of recorder permissions.
No new full Denial VM, Denial build or active tier was executed: repository product
source is unchanged. The prior 112 active passes belong to source ffaf75ee; they
are not presented as checks executed this turn. Metadata checks are separate.

## Next

Next take one guarded instruction/caller observation in the reproducible loaded native component during WINDOW_REMOVED_ZERO before the unchanged 2s close limit. Compare with the retained Denial handlers_find PC; distinguish time spent executing from scheduling delay. Keep capture 15ms/64KiB/4frames, outer 1200ms guards and original close policy. No GLib patch, deadline widening, unchanged full Denial VM or Denial rebuild is justified yet. Phone graphics work remains independent.

Qualification SHA256 `09b473f4998eaf039bd2b3578b90d9f5b3149e9a999d717a543cc93941bd2a69`.

Metadata validation passed in 0.441s: inventory/current-status checks and the
mobile-status tests. All 589 historical artifact rows, acceptance contracts,
historical current-state text and previous artifact pointers were preserved.
No owned containers remain.
