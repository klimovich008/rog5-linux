# Bounded fallback-profile restoration: offline acceptance

Date: 2026-08-01

Status: accepted offline; host installation and phone execution remain pending.

## Problem closed

The previous live diagnostic lifecycle proved a host race: recovery-bundle
cleanup immediately reactivated the persistent
`rog5-fallback-usb-ssh` NetworkManager profile while the
`ROG5_recovery` gadget was still connected. That could attach the Alpine
fallback `/30` to the wrong USB product during the recovery-to-target
transition.

The accepted correction makes deferral an explicit lifecycle-only operation.
The ordinary standalone bundle action retains immediate restoration. The
one-shot lifecycle now:

1. sets the exact fallback profile to `connection.autoconnect=no` before
   deactivation;
2. serves one recovery bundle;
3. removes the temporary address, firewall rules, and zone ownership while
   leaving the recovery interface unmanaged and the profile inactive;
4. waits through the fixed root broker for exactly one Alpine
   `1d6b:0104` / `ROG Phone 5 Linux Server` / `cdc_ncm` interface at the
   recovery anchor's physical USB location, requiring the real sysfs driver
   target as well as matching udev properties;
5. restores the exact profile and `/30` only after stable raw-product and NCM
   identity agree; and
6. performs strict fallback SSH only after that restoration passes.

The controller uses the same nonblocking lock for serving and restoring.
Restoration is idempotent. Every partial activation failure performs a
fail-closed rollback: the exact profile is down with autoconnect disabled and
the surviving interface is unmanaged. USB identity is revalidated before,
during, and after activation. Duplicate products/interfaces, a different
physical port, an unsafe profile state, or detach during activation fail.

The wait uses `/proc/uptime` as a monotonic decisecond clock. Every `udevadm`,
NetworkManager, and IP operation uses only the remaining restoration budget;
rollback cleanup retains its own safety timeout. Restoration shares the
lifecycle's single fallback deadline with the subsequent strict-SSH proof. No
detached timer or helper survives the parent.
The lifecycle passes only the remaining deadline tail to SSH, including a
valid tail below the standalone 600-second host-preflight minimum. The root
restore location is derived independently by the root broker from a canonical
ordered mode-`0600`, single-link, caller-owned anchor bound to the current host
boot and 3,600-second wall-clock contact-start window. The caller cannot submit
a bare USB location, and host suspend cannot extend that gate.
Before target handoff, the lifecycle also proves the exact profile has no
active UUID and retains `connection.autoconnect=no`.

## Hardware-free evidence

Focused suites pass:

- `python3 scripts/host/test-fallback-acm-control.py`: 47 tests;
- `python3 scripts/host/test-recovery-host-controller.py`: 22 tests;
- `python3 scripts/host/test-recovery-host-socket.py`: 11 tests; and
- `python3 scripts/host/test-run-minimal-headless-live-cycle.py`: 37 tests.

The fault matrix includes deferred-state persistence, exact anchored restore,
idempotent replay, wrong-port and duplicate rejection, shared-lock collision,
hung-udev timeout, false udev driver claims backed by a wrong sysfs driver,
detach during activation, failure at managed-state change, profile activation,
and autoconnect restoration, plus strict anchor metadata/freshness/host-boot
binding at the privileged broker, shared-deadline tails and post-enumeration
timeouts, inactive-UUID/autoconnect-off postconditions, lifecycle ordering,
and one-attempt behavior when restoration fails before SSH.

`scripts/host/test-repository-linux.sh ci` passes the complete repository
Linux CI tier after the correction.

The credential-free, tool-free Claude review identified one actionable issue:
an unbounded `udevadm` call could escape the nominal polling budget. The final
implementation bounds that subprocess and the enclosing loop independently,
with an injected hung-udev regression. Its other two observations were
reviewed as intentional invariants: rollback targets the fail-closed deferred
state rather than a transient newly-enumerated managed state, and the shared
nonblocking lock deliberately rejects concurrent serve/restore operations.
The subsequent standards/spec review found three duplicated or unclear code
paths and three trust-boundary gaps. The implementation now reuses profile
validation, combines broker dispatch, names bounded NetworkManager calls,
strictly validates the privileged anchor, accepts a bounded shared-deadline SSH
tail, and verifies the real kernel driver; each gap has a focused regression.
The final objective-fidelity review then found that only user space validated
the anchor, post-enumeration operations could outlive the nominal deadline,
and the deferred lifecycle postcondition did not inspect active UUID or
autoconnect. The root broker now validates and consumes the anchor itself, all
positive restore operations consume the remaining monotonic budget, and the
lifecycle proves both missing profile properties before target handoff.
The closure review's final suspend finding is also fixed: user space and the
root broker independently reject contact start more than 3,600 wall-clock
seconds after capture, while the later 7,200-second age bound applies only to
the already-started fallback proof.

## Boundary

This acceptance contacted no phone interface, installed no host component,
changed no live NetworkManager or firewall state, used no credential or
signing key, and created no boot authority. The corrected production wrapper
`f710bbcd…97b0ef` remains unexecuted and is still the sole admitted temporary
image.

The next sequence is publication with green GitHub CI, exact host-controller
installation and hash verification, then connected preflight. A temporary
phone boot remains later and must still pass every one-shot gate. Flashing,
wiping, slot changes, and phone-storage writes remain prohibited.
