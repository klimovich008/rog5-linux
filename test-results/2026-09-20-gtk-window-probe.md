# GTK last-window observation — 2026-09-20

The explicit window observer is qualified in a **host-only actual ARM64
Mousepad/Weston component test**. Full Denial VM Mousepad close remains FAIL.
No phone operation, candidate, signing, admission, claim or protected-storage
mutation occurred. This turn did not rebuild Denial/Flutter or run a full VM.

Starting source: `3e64777bd9072a5fffbc551d6416220834c363bd`,
tree `34c6ae405176490b09aa9dbc18501936d9de0263`.
Frozen executable source: `617c4e7800bcc721ac6b7ee650adfc49c934a2d1`,
tree `331dbaab3465dcda309ea9f28e42fb2c6c300dc1`. Source changes are
`tools/qemu-virtio-drm/settings-sync-diagnostic.c` and
`scripts/host/test-settings-sync-diagnostic.py`; documentation/provenance follow.

The compile-only ROG5_WINDOW_PROBE requires ROG5_NO_UNREF_PROBE. Its
G_CONNECT_AFTER window-removed handler calls public gtk_application_get_windows
and records ZERO/NONZERO. GTK3 declares this signal RUN_FIRST, so the observation
follows the default removal handler; it does not bracket that handler or prove
private application hold count is zero. No extra object reference is acquired.
The handler preserves errno and is disconnected before the existing observer
cleanup receipt. The explicit one-window mode retains the12-record/1536-byte
limit. Default and earlier no-unref binaries are byte-for-byte unchanged.

Five new semantic cases fail against the previous source, then all24 cases pass
normally in0.766s and with Python -O in0.816s. They cover ZERO/NONZERO, callback
order, errno, disconnect, missing getter, connection failure and forbidden macro
combination. The unchanged private harness's six cases also pass in0.021s.
All three ARM64 variants compile with -Wall -Wextra -Werror, approximately0.467s
each; the new71208-byte DSO SHA-256 is
`4d9817c6bba700a8d2ea4b73b79ca53a0e58317571939e7b5f7b426529b86614`.
An initial private build-script indentation error preceded any compilation.

| Actual component execution | Result | Duration |
| --- | --- | --- |
| r1, outer TasksMax96 | FAIL before mapped frame; image-loader thread creation EAGAIN, abort134 | 8.836s |
| r2, outer TasksMax256, otherwise same source/binary/harness | PASS mapped frame, last-window observation and clean Mousepad0 | 8.991s |

The r1 cgroup records peak96 and two task-limit hits, no OOM. The r2 peak is98,
no task-limit hit or OOM, memory peak459280384 bytes under512MiB with no swap.
This demonstrates fixture resource failure, not a Denial/GTK shutdown defect.
Both owned compositor containers are removed and absent. Document bytes remain
unchanged; DConf is mapped and owned before/after. The session uses QEMU user,
Weston headless Pixman and a private dbus-daemon; no host GPU/input/network.
The original65-second app timeout, two-second kill-after,90-second service limit,
CPU quota and bounded log drains remain intact.

Observed monotonic stages in r2:
WINDOW_REMOVED_ZERO410543.266641132;
SHUTDOWN_BEFORE410543.816792099;
settings-sync BEGIN410543.820622339 / END410543.820787411;
SHUTDOWN_AFTER410543.831169504;
APP_RUN_END410543.836498207;
APP_OBSERVERS_REMOVED410543.836603039;
DSO_FINI410543.839854760. Last-window to shutdown is approximately550ms in
this single fixture; it is not a general performance measurement.

The frozen active tier passes112 suites in199.352s.
Counts: {'PASS': 112, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255}. Optional historical subcheck counts: {'SKIPPED': 3}.
These are personally executed host checks, not imported GitHub CI or phone proof.

Next prepare one full Denial observation with the qualified window variant.
Do not combine it with the existing strict stage-after-sync reader, whose grammar
rejects these new markers. Preserve close limits; distinguish absence of removal,
empty-list before shutdown, and later shutdown stalls. No new compositor build is
needed. Physical work remains NOT RUN and requires its own authorized process.

Exact commands, timings, failed and successful results, runtime identities and
artifact hashes are in the [qualification record](2026-09-20-gtk-window-probe-qualification.json).
All583 older artifact rows, headless/mobile acceptance contracts, historical
current-state tail and previous FAIL/BLOCKED/NOT RUN results remain unchanged.
