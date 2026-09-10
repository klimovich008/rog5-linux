# Three-key minimal-root runtime gate — offline result

Date: 2026-08-09

Starting repository SHA:
`2a8f0e1e3e5a5ab0db82e2794b0c69c6298b1fd1`.

Result: **PASS for hardware-free runtime-gate and wake-call-path coverage;
no phone execution and no physical-input acceptance.**

## Defects fixed

The historical attended input monitor embeds Python and observes only
`pmic_pwrkey`. The active minimal root intentionally has no Python package,
and H4 requires power, volume-down, and volume-up. That monitor therefore
could not execute the current acceptance plan or prove two candidate wake
sources.

The buttons source oracle also stopped at registration and
`device_init_wakeup()`. It did not pin the accepted Linux 7.1.4 suspend and
resume callbacks that actually arm and disarm the PMK8350 and `gpio-keys`
IRQs. A future source change could therefore retain probe-time markers while
silently breaking wake behavior.

Post-CI review found a third target-only defect: the initial binary reader
opened and closed evdev around each 24-byte record. A quick release between
the two opens would have no client buffer and could be lost. The corrected
reader opens each event node once, retains that descriptor across the exact
press/release pair, and closes it only after both records are accepted. A
FIFO test writes both records in one burst and proves both remain readable
from the retained descriptor. A second ordering regression requires that
descriptor to be open before the `READY` line; otherwise an immediate first
press could race readiness itself.

## Correction

`run-network-root-physical-keys.sh` is a guarded POSIX-shell gate using only
the exact base-package closure already present in the 152-package root. It
requires the accepted kernel, normal systemd state, active server inhibitor,
read-only NFS/OverlayFS, tmpfs `/run`, zero physical or block-backed storage,
disarmed rollback, and the exact USB gadget/link/address/direct route.

It then requires exactly one of each accepted input identity:

| Key | Input / code | Driver | Wake policy |
|---|---|---|---|
| power | `pmic_pwrkey` / 116 | `pm8941-pwrkey` | enabled |
| volume down | `pmic_resin` / 114 | `pm8941-pwrkey` | absent/off |
| volume up | `gpio-keys` / 115 | `gpio-keys` | enabled |

Each future attended run must observe exactly one press and release in order.
The corresponding named IRQ must advance by 2–16 counts, rejecting both a
dead path and an interrupt storm. Target binary records are written only to a
private directory below tmpfs `/run` and removed on exit. There is no Python,
module load, sysfs control, LED, power-state, block-device, boot, or
persistent-storage write path.

Afterward the gate rechecks kernel/systemd, NFS, storage, rollback, UDC,
binding, interface, carrier, address, direct route, fatal signatures, and the
warning digest. The fixture backend is restricted to an unprivileged caller
and a caller-owned mode-0700 non-linked tree.

The source oracle now pins both accepted drivers' real PM callback paths:
power calls `enable_irq_wake()`/`disable_irq_wake()` when wake-capable;
resin shares those callbacks but remains non-wake-capable; and `gpio-keys`
arms only DT children carrying `wakeup-source` and restores their IRQ state on
resume.

## Fail-first and focused timing

The dynamic runtime suite failed before the gate existed:

```text
status=FAIL, 8 ms
FAIL missing executable physical-key gate
```

The source suite then failed before wake-path markers were added:

```text
status=FAIL, 96 ms
wake-path marker is not pinned: ... pm8941_pwrkey_suspend(...)
```

The post-review descriptor regression then failed before the reader fix:

```text
status=FAIL, 12 ms
FAIL target reader does not keep one evdev descriptor across press/release
```

The readiness-order regression also failed before the open was moved ahead of
the readiness line:

```text
status=FAIL, 40 ms
FAIL target reader announces readiness before retaining evdev
```

Post-correction focused results:

```text
three-key dynamic hostile gate plus retained-descriptor burst/order: PASS, 6,124 ms
retained source + 287 MiB accepted module projection: PASS, 11,368 ms
core compatibility oracle: 39 tests PASS, 682 ms
core source/DTB contract: 77 tests PASS, 13,806 ms
repository runner contract: PASS, 6,379 ms
```

The first complete repository CI pass took 439,624 ms. Post-CI review then
found the evdev close/open and readiness races described above, so that pass
is discovery evidence rather than the final checkpoint. After both reader
fixes and their fail-first regressions, the complete
`scripts/host/test-repository-linux.sh ci` tier passed again in 442,469 ms;
the corrected physical-key suite took 6,098 ms within that run. The previous
accepted repository checkpoint was 460,174 ms, making the final result
17,705 ms (3.85%) faster despite the added gate.

The runtime matrix covers missing guard, timeout bounds, exact minimal-server
preconditions, every key identity and wake policy, duplicate devices,
release-before-press, autorepeat, wrong code, missing release, linked fixture
ancestry, no IRQ movement, IRQ storm, and post-return UDC, interface, carrier,
address, route (including late `via`), NFS, warning, and fatal changes.

No kernel, DTB, root archive, wrapper, or boot artifact was rebuilt because
this increment changes no target payload bytes. The retained accepted source,
config, module archive, and buttons DTB remain the exact inputs under test;
performing another clean kernel build would not strengthen this userspace
gate or its source oracle.

## Boundary and next step

No phone, fastboot, ADB, SSH credential, signing key, GitHub service, or
external reviewer was used. No artifact was packaged, signed, issued,
published, or granted boot authority. Static wake-call-path evidence does not
prove firmware wake, physical IRQ routing, switch behavior, indicator color,
suspend, or idle power.

A later separately authorized temporary target must pass the normal minimal
SSH/storage/rollback gate, then run this attended three-key check. Only after
physical power and volume-up evidence exists should either be evaluated as a
wake source under the suspend plan; real suspend remains forbidden until its
separate gates are satisfied.
