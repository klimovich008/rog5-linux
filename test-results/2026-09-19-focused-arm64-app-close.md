# Focused exact-ARM64 Mousepad shutdown — 2026-09-19

**Scoped app-close PASS in 12.77 s. The Denial VM's Mousepad exit 137 failure remains unresolved. No phone operation; physical rows NOT RUN.**

## What ran

The unchanged packaged ARM64 Mousepad ran under QEMU user emulation against
Weston 13's headless Pixman backend. Its configured native Wayland surface received
a non-null buffer commit and matching frame callback before the controller
requested close. GNU timeout forwarded TERM with the same two-second kill-after
policy as the VM. Mousepad and its log reader both exited 0; the opened document
was unchanged. The app's actual DConf backend was mapped, both ownership queries
returned status 0/true, and the private bus recorded successful DConf activation
requested by Mousepad. The existing settings-sync probe recorded loaded,
BEGIN and END in the same process: **0.337173 ms inside g_settings_sync**.

Readiness took 10.558 s after app-session launch. The close clock samples bracket
TERM/wait in 0.62 s, including controller overhead; this is not a pure function
timing. Overall experiment 12.771 s, service 12.855 s, ARM64/controller cgroup peak
354,365,440 bytes (337.9 MiB), no swap/OOM. Its task peak 90 stayed below 96.
Weston had a separate 256 MiB/no-swap, one-CPU bound. Container removal and absence
passed; Weston exited 0. No host render/input device or host desktop bus was used.

## Establishing the fixture and retaining failures

No suitable compositor was found in the host PATH or three retained build
images. A separate host-only Ubuntu image added Weston 13.0.0-4build3; installation
took 44.666 s. Image identity:
`dc817b835e4dc74967379b2189d4b88265e709828fd7ea3bfd5c5ba5b8334c51`.
Package versions, downloaded archive hashes, authenticated repository metadata,
tool hashes and saved local command help are retained. Package archive files
were removed from the container after recording their hashes; the exact image
is retained. No phone candidate, root image, signing or admission was created.

The original materialized ARM64 package tree, real symlinks and mapped-view
metadata were fully reverified through the existing linker-cache validator;
preparation 23.350 s. The exact GTK IM and Wayland diagnostic overrides and
settings-sync library were verified separately. All original runtime mounts
remained read-only. Account files, a synthetic machine ID, HOME and caches were
private. Target GTK/MIME/font cache derivation took 10.668 s (service 10.719 s),
peak 111.8 MiB, no swap. The target font consumer observed the prepared cache.
This does not claim execution of the root/setpriv VM cache path.

| Attempt | Result | Evidence |
|---|---|---|
| r1, eight host CPUs visible, 96-task bound | FAIL before mapping; 45.740 s | Mousepad aborted 134 while the SVG loader could not create a worker thread. The controller originally waited for mapping instead of reporting early child failure. |
| r2, same resource bounds, early-exit observation and cgroup metrics | FAIL before mapping; 10.568 s | Actual app exit 134; task peak 96, pids.events max 2, memory peak477,700,096 bytes; no OOM. Task exhaustion is established. |
| r3, two-CPU affinity, same memory/task/close limits | PASS focused close; 12.771 s | App exit 0, matching frame callback, DConf active, sync BEGIN/END; task peak 90, pids.events max 0, no OOM. |

The retained VM advertises two vCPUs. Restricting host affinity avoided the
measured limit in this run; the exact thread contribution of each loader/service
was not separately established. No application package, backend, image-loader
policy or shutdown grace was changed to obtain the pass.

## Meaning and limits

This proves that the retained ARM64 app and diagnostic can complete normal
shutdown with a working DConf backend. It disproves a universal shutdown failure
of those bytes. It does **not** identify the Denial VM exit 137 cause or prove that
the same sync call returns there. The full VM's broker/systemd activation,
Denial, guest kernel, scheduling and session state differ from this fresh-HOME,
standalone dbus-daemon/Weston fixture. No replacement desktop was selected;
Denial remains the goal.

The raw run also contains a document-portal FUSE failure, GTK no-seat criticals,
Glycin-without-sandbox warnings and unavailable PipeWire/system-bus services.
These remain explicit limitations. Full portal/security qualification, focus,
OSK/touch, accelerated phone graphics and Denial presentation are NOT RUN here.
Historical VM exit 137, complete startup timing FAIL, S06/R01 FAIL and consumed claims
are unchanged. Do not repeat a full boot unchanged when its deadline expires
before the app can reach the close observation. The next comparison needs actual
sync BEGIN/END under the failing broker/systemd session context.

## Review, regression and reproducibility

Independent source/raw-evidence review confirmed surface 7, configure/ack 1,
buffer 16 commit, frame callback 19.done, reader/app exit 0, real DConf ownership and
cleanup. It found two harness weaknesses for future reuse: worker-thread log
write exceptions could be missed, and ownership booleans did not also check
query exit status. The writer-error regression failed before correction;
all 6 focused harness checks pass after correction,0.022 s. Exact reply/status
checks independently reconfirm the already-executed r3 evidence. No app replay
was needed. Current reusable harness additionally disables future target core
dumps; two earlier startup cores remain private. These post-run changes are
unit-tested/source changes, not a new execution of r3.

[Qualification JSON](2026-09-19-focused-arm64-app-close-qualification.json)
contains exact launch vectors, source/binary/package identities, the current
fixture source text, executed-script snapshot hashes, each failure result,
raw protocol/probe/map/query/status hashes and the strict publication checks.
Inputs came from source `e18413e40e290f710d04086682a932a072f84809`, tree
`e40dff4a2e5ae3f916a24b18f82c191458982e97`. Fixture scripts and raw evidence are
private under `/home/deck/.local/state/rog5-arm64-app-close-20260919-r1`.
Historical execution snapshots are distinct from subsequently hardened scripts.

The preceding cleanup turn was PROGRESS: 8.25 GB reclaimed with restoration and
retained-input verification. This turn replaces repeated 300 s boot timeouts with
an observed 12.77 s component run while preserving separate full-session acceptance.
No kernel/Denial/Flutter rebuild or integrated 108-check replay was needed for
unchanged production code. This is local evidence, not a new GitHub CI result.

Final local validation: 6 harness tests and 8 mobile-status tests PASS; inventory,
generated-status and whitespace checks PASS. Five command wall times were
0.1144 s, 0.1145 s, 0.1144 s, 0.0642 s and 0.0646 s respectively. Exact commands
and logs are retained in the private `final-checks.json`. No physical results
were promoted through these checks.
