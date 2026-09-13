# Non-root Denial session — 2026-09-13

**PASS in the ARM64 VirGL VM. Phone hardware NOT RUN.** Denial, session bus,
Mousepad and Foot use UID/GID1000 with empty supplementary groups/capabilities
and NoNewPrivs. The final run rendered 210 frames/page flips, completed the four
native focus visits and delivered all 12 expected OSK press/release events.
Manual capture inspection shows `test → tes → test` and the mobile-user terminal.

Starting `84efe306d7d4453d2852dfd358bcb2cd5a634dd0`, tree `a020b642899309ca69f4ba36033ad3f1baa98d8b`.
VM1/view source `46fbcd5ac7755c4d17904bd8605762ff9aa511ff`.
Final VM source `fcf8068558bc908618a5494f26df319eb1efb404`, tree `ab636f0bef668c050a6893898f7294275e565134`.
Integrated source `a00a99d6531ffc272879808b6e0fbf0f5334ba8f`, tree `24adab15e34913ed93086e759fc36968fb2c7126`;
only the public test-selector entry changed after the final VM.
Publication changes evidence/status metadata only.

| Personally executed check | Result | Duration |
| --- | --- | --- |
| Complete archive/payload view preparation | PASS; no full runtime copy | 33.210s |
| First small ARM64 permission VM | FAIL: private probe nested quoting | 3.654s |
| Corrected ARM64 permission VM | PASS actual non-owner access/private denial/symlinks/capability checks | 4.105s |
| Initial non-root Denial/apps VM | PASS; 215 frames/flips; bus cache warning retained | 105.793s |
| Final non-root Denial/apps VM | PASS; 210 frames/flips; cache and locale warnings gone | 109.785s |
| View regression suite | 13 PASS, including two failing-before source-output guards | 0.243s |
| Guest/prerequisite suite, Python -O | 35 PASS | 0.613s |
| All 55,811 retained entries after both VMs | PASS contents/modes/links; generated metadata unchanged | 14.722s |
| Integrated active tier | 94 PASS; 0 FAIL/BLOCKED/SKIPPED; 255 NOT_SELECTED | 142.852s |

The initial integrated launch failed its selection consistency check in 0.164s,
before any test executed. The retained shell selector now includes the same new
test as the manifest. Independent read-only review identified the nested-output
source mutation counterexample; real temporary-tree regressions now reject it.
The implementation agent also ran the existing 10 launcher tests (PASS; 2.239s).
All are local results, not imported GitHub CI.

The runtime view uses QEMU's separate mapped-file ownership/mode metadata and
stored symlink descriptions, with regular bytes hardlinked. Format semantics
were checked against [upstream QEMU 8.2.2](https://github.com/qemu/qemu/blob/v8.2.2/hw/9pfs/9p-local.c)
and then exercised with the retained packaged QEMU image. Both the host bind and
9P export remain read-only. Cached archive hashes and every retained file hash
were checked; the existing signature audit was reused. Host source nlink/ctime
change through hardlinks and reads can update atime; contents/modes/owners are
not rewritten. Generated metadata SHA256 is
`743e11d5e7341e87d28929478f0482b7bb4f2605bf96f07065367f538c212857`.

The unchanged native binary SHA256 is `40b1fc631643d602b57db2b988eb2caf8839e1e044890f7c9aa4ad0555bb8af0`;
engine `a75c88d8f12d9ec7a24bb107ff9dc0349b6bb2d5b0f18cb4d40b9e54227e9418`;
AOT `e6434b805636598a937cfa69736012c213bd3e5b6c99f3607d495f7e4e292ba5`.
No compositor, engine, AOT or kernel rebuild was needed.

Source changes: `scripts/host/prepare-qemu-runtime-view.py`,
`scripts/host/test-qemu-runtime-view.py`, `scripts/host/test-qemu-virtio-drm.py`,
`scripts/host/test-qemu-virtio-drm-prerequisites.py`,
`tools/qemu-virtio-drm/nonroot-session.sh`, `tools/qemu-virtio-drm/guest.sh`,
`scripts/host/test-repository-linux.sh`, `configs/repository-tests.json`,
`docs/development.md`, `docs/development-lessons.md`. Publication adds this report,
its qualification JSON and updates the existing artifact inventory/pointer,
project status and generated current-state header.

[Qualification](2026-09-13-nonroot-session-qualification.json) binds exact commands,
input/output hashes, raw results, cleanup, failed first probes, before/after
regressions and final captures.33 redundant files from a terminal historical VM
payload were removed only after matching durable copies, checking open handles,
mounts and active references; its FAIL/logs and a complete retention map remain.
The 3 GiB host reserve was retained throughout.

This remains a seatd VM fixture with root seatd/udev/supervision, not logind,
authentication, lock-screen or production security qualification. Realtime
scheduling requests remain refused; optional Mousepad shortcuts/spell plugins
still lack optional libraries. Post-terminal app exit codes are retained;
successful owned-process cleanup does not claim every app exits zero.
Manual viewport panning remains in the test. The editor keyboard-dismissal
capture is intermediate, so settled dismissal and automatic caret visibility
remain NOT RUN. VirGL is not Adreno evidence.

Next prepare the non-root target session composition against the existing mobile
policy and preserve the explicit logind/login boundary. The smallest pending
physical question remains A660 XR24/fence/readback on the frozen trial under
separate authorization. No phone operation, candidate, signing, admission/claim
or protected-storage mutation occurred. All mobile physical rows remain NOT RUN;
S06/R01 FAIL and historical evidence remain unchanged.

Publication validation also passed: five optimized metadata regressions, eight
mobile-status regressions, inventory and generated-status checks, and
`git diff --check` (1.142s combined). Active-tier memory peaked at354.9MiB with no swap.
