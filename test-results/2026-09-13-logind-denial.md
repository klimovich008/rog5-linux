# Denial through authenticated logind — 2026-09-13

**The combined generic ARM64 VirGL run remains FAIL**, despite actual Denial
rendering and two native Wayland clients configuring. It observed24 raster
frames/page flips and18 delivered vsyncs through the production mobile entry,
actual PAM login authentication, local UID1000 session and logind device access.
This is VM software integration evidence, not phone GPU or usable-desktop proof.

Start: `a763a2b9e2fe62ff36a833495cd38efdfacfd0b4`, tree `3e9f724bc02756da0c41773eabf7d4cc28830160`.
Frozen implementation: `b79045d74e5973ab85d73bd4b5fabfc0e67e5e0d`, tree `f2725cf1d1cfb740ef1e93a8caeec8015ef5aaa5`.
Publication changes evidence/status only. Exact commands, source snapshots,
per-step durations and artifact hashes are in the [qualification JSON](2026-09-13-logind-denial-qualification.json).

| Executed check | Result | Duration |
| --- | --- | --- |
| Combined VM r1 | FAIL: empty output config refused; shutdown panic |109.748s |
| Actual stat-kind regression, old entry | Expected FAIL | See retained log |
| Corrected mobile-entry suite |19 PASS |0.387s |
| Corrected unsigned session-files composition | PREPARED_NOT_INSTALLED |5.207s |
| Combined VM r2 | FAIL: Foot SIGXFSZ; shutdown panic |163.161s |
| Real runner/process/archive/log-drainer regressions |9 PASS |0.751s |
| Combined VM r3 |24 frames, two clients configured; overall FAIL |201.442s |
| Frozen integrated active tier |97 PASS,0 FAIL/BLOCKED/SKIPPED;255 NOT_SELECTED |136.878s |

Three declared optional subchecks were SKIPPED and are enumerated in the retained
JSON/JUnit report; no selected mandatory suite skipped. Existing GitHub CI and
prior board/build/phone results are separate; none was rerun here.

The production entry rejected GNU stat's `regular empty file` classification,
although upstream permits an empty output configuration. The real-stat regression
fails before the fix and passes afterward. Owner1000, mode0600 and symlink/device
checks remain. Updated session-files archive SHA256:
`1ff417307c96bac90977b64a143e1a81b535d94a03109ca967c40e9b1f269d0c` (26672036 bytes).
It was composed from source `4947e75da6a045e8d7e761364e6f96f21607eeb6` and remains unsigned,
not installed, with authority=none. Denial/Flutter binaries are unchanged.
The old archive and its historical qualification remain retained.

The harness now checks normal VM poweroff explicitly: QEMU exit0 or earlier
success markers cannot override a kernel panic. Archive inventory and parent
directory validation run before launch. A log-only bound uses draining readers
instead of imposing RLIMIT_FSIZE on graphics clients; a real FIFO/writer test
proves the writer finishes after the retained log reaches1MiB. The r2 SIGXFSZ
is observed; the exact offending allocation/file descriptor was not recovered.

In r3, both clients had exited before the intentional stop, whose failed kill
prevented collection of their wait statuses. Their65-second deadline is a
plausible explanation, not an established cause.24 frames over about69 seconds
is not responsiveness proof. Actual at-spi and desktop-portal services aborted;
the document portal exited NOTCONFIGURED. These failures are not hidden by
successful client configuration. No combined input, lock or full-security PASS.

All three runs ended with init SIGBUS during shutdown. Restoring canonical
/usr/bin on success and failure did not eliminate it, disproving that correction
as a sufficient explanation. No specific kernel, 9P or QEMU defect is established.
All runs and failure logs remain intact; there is no complete session PASS.
Owned VM containers were cleaned up. The generic kernel's missing namespaces,
BPF/audit and tmpfs ACL support remains an explicit sandbox limitation.

The supplied framebuffer review is already incorporated: strict explicit
intersection, Invalid-only pool dispatch, and stored/exported descriptor checks.
The patch SHA remains `3d05d2d441d32f852c71887bf750aede1a7a5fc959f5a2ac50234a844783b8f1`.
Retained16 corrected PASS/10 old expected FAIL were not repeated. No modifier
relabeling, external-texture guard removal, fence bypass or driver-version change
was introduced. The current failure occurs beyond that earlier render boundary.

Changed implementation files:

- `configs/repository-tests.json`
- `docs/development-lessons.md`
- `docs/development.md`
- `packaging/arch/mobile/denial-mobile-session`
- `scripts/host/test-denial-mobile-session.py`
- `scripts/host/test-qemu-logind-runner.py`
- `scripts/host/test-qemu-logind.py`
- `tools/qemu-virtio-drm/logind-boot.sh`
- `tools/qemu-virtio-drm/logind-denial-prepare.sh`
- `tools/qemu-virtio-drm/logind-denial.sh`
- `tools/qemu-virtio-drm/logind-pam-session.rs`
- `tools/qemu-virtio-drm/logind-session.sh`
- `tools/qemu-virtio-drm/logind-user.sh`

Publication appends one fixture set (518 total), updates the existing unsigned
session-payload pointer and adds combined VM evidence. The previous517 sets,
accepted signed fallback, headless/mobile contracts, consumed claims and historical
current-state body are unchanged. No independent status ledger is introduced.

Next smallest authorized experiment: a shutdown-only control using retained
passing logind-only VM bytes, changing one parameter at a time. Capture client
wait statuses before another combined run. Further combined VM retries stopped
this turn because repeated shutdown failures did not identify their cause.
A physical Adreno/display/input trial still requires new authorization.

No phone operation, new phone candidate, signing, admission/claim or protected
storage mutation occurred. Mobile physical rows remain NOT RUN; S06/R01 remain
FAIL. The native-phone goal remains active and incomplete.
