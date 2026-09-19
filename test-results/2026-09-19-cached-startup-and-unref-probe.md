# Denial VM startup and application-release probe — 2026-09-19

**Cached startup is measurably faster in the retained comparison; Mousepad close
still fails. The new release probe passes host and real ARM64 GLib tests, but its
Mousepad VM trial timed out before app mapping/shutdown was observed.** These are
separate results. Phone physical tests remain NOT RUN; S06/R01 remain FAIL.

## Source and artifact boundaries

The cached-startup VM used source `516f8cce3df72c7cfd0773c235f16a102af36271`,
tree `397115bd5becda771e9987d66122f7681ef15bc9`, with the prior probe DSO
`65535e5520368158cfcaf51b2a2c95fe012ed113aaea288a46c79e94df093b71`.
The new probe source/test change is `41b4e607fff85c6a3b25b21858e145d5a17a5e26`,
tree `43c1732e2409064d558ecc529e2dd2bc999b394c`. This was clean and frozen for
the integrated tests and latest VM. Publication changes come afterward.

New ARM64 DSO SHA256: `7a3cac369e1bd0d35b3af53b4b6c91ecbd6d199efd669fddeb7a871eb2edef38`.
Real GLib fixture SHA256: `afbd45cadf282d3d18c72922cf787b15441926158d62a73be077e1db9175f266`.
The latest VM rechecked all 38 input identities. 36 are identical to the cached
startup run; the only changes are the diagnostic C source and its DSO. Kernel,
runtime, Denial/Flutter, graphics, application flags and deadlines are unchanged.
No kernel, Denial, Flutter or app rebuild occurred. The small probe and GLib
fixture builds took 0.718s and 0.615s with -Wall -Wextra -Werror in the pinned
ARM64 toolchain. The harness separately rebuilds its existing small session probes.

## Cached-startup measurement, overall FAIL

| Interval | Historical uncached control | Cached run |
|---|---:|---:|
| Service start | 23.031s | 19.077s |
| GTK portal exec to active | 18.631s | 15.222s |
| Mousepad registry to first buffered commit | 22.304s | 12.026s |
| Foot registry to first buffered commit | 0.674s | 0.729s |

Cache generation added 11 guest integer seconds before PID1. Each client interval
uses its own Wayland log clock; service timings use guest CLOCK_MONOTONIC. A
buffered commit is submission, not presentation proof. This historical comparison
also includes the previously qualified abort-cleanup change and uses the normal
300s outer deadline instead of the old diagnostic 420s envelope; total wall-time
differences cannot all be attributed to icon caching.

Both apps mapped/focused; Foot exited 0, Mousepad 137. QEMU ran 286.841s, the full
harness 328.874s. Normal guest poweroff occurred without kernel panic. This remains
FAIL despite startup improvement. Mousepad's settings sync and shutdown observers
returned, then APP_RUN_END appeared. The old probe still had its own observer
disconnects after that marker, so assigning the stall directly to main's unref
was premature. Historical successful typing is not rerun or relabelled here.

## Diagnostic implementation and regressions

`tools/qemu-virtio-drm/settings-sync-diagnostic.c` now brackets both observer
disconnects, the first matching application unref after run, and this DSO's
destructor. The unref wrapper forwards each call exactly once, preserves errno,
and atomically clears the pending pointer before the real call. No additional
object reference, class-vtable replacement, main-context iteration, timeout
change or forced-success path is introduced. The 12-record/1536-byte cap remains.

`scripts/host/test-settings-sync-diagnostic.py` exercises the compiled interposer
against controlled real callees, including blocked disconnect/unref paths,
unrelated and repeated unrefs, pointer/call-count/errno preservation and absence
of false finished markers. The old implementation failed 4 of 17 tests; all 17 then
passed normally and with Python -O. The real ARM64 GApplication subclass fixture
observes the marker from inside object finalization: old DSO exit 3 as expected,
new DSO exit 0 with all 12 markers, in 0.215s and 0.164s. This uses the retained actual
GLib runtime, not GTK/Mousepad or the phone.

The frozen active tier passed 109 suites,0 FAIL/0 BLOCKED/0 SKIPPED, 255 NOT_SELECTED,
with 3 explicitly optional skipped subchecks in 185.519s.
Its JSON/JUnit content and commands are in the paired qualification. This result
is personally executed local evidence, not an imported GitHub CI result.

Matching the pointer does not prove main-thread execution or final-reference
destruction. A missing END can include probe logging. DSO_FINI only shows this
destructor was reached. An extra settings-sync call can exhaust the deliberate
record cap and produce probe exit 125; do not call that a Mousepad failure.

## New VM: startup timeout, application diagnostic NOT OBSERVED

The new run kept 300s QEMU and existing guest limits. It hit FAIL_TIMEOUT at
300.030s; full harness 352.060s. Two RCU
stall reports occurred during packaged systemd startup, including `(sd-gens)`
and bash. A retained-map decode places sampled frames in page-copy/page-fault
and exec/MM/TLB paths; this is not a root-cause diagnosis. Host cgroup evidence
at 204s recorded zero OOM events, zero swap and about 1.6GB memory under 2GB limit;
CPU throttling totaled about 1.08s. This snapshot does not prove conditions
throughout the run or explain guest timer/scheduler stalls.

Denial eventually rendered its launcher. The inspected 540x1224 screenshot shows
Mousepad and Foot tiles; protocol tile matching passed. Neither app acquired an
observed owner/mapped state before timeout, and no new release-stage markers were
recovered. Thus the intended Mousepad shutdown experiment remains NOT RUN, rather
than PASS or evidence that the new probe caused startup failure. No normal
poweroff was observed; no kernel panic was observed. All three owned build/VM
containers are confirmed absent. No automatic identical retry or deadline
increase was performed.

## Disproved cache assumption and next boundary

The retained gdk-pixbuf2 2.44.6-2 archive has no external loader module entries.
Its runtime library matches the archive and directly links libglycin-2.so.0;
glycin-svg is installed. An absent legacy loaders.cache alone therefore does not
establish a missing package hook. No speculative cache-generation change was
made. Actual SVG decoding and Glycin sandbox execution remain unqualified.

The next useful VM experiment must first isolate pre-app startup variability
using the same retained kernel/runtime and explicit stage timing. Keep that
question separate from application release. Once startup is bounded again, reuse
the qualified DSO to locate the late close boundary. If it points inside matching
unref, collect one bounded stack/syscall observation before adding more interposers.
The retained upstream Mousepad 0.7.0 main only unrefs then returns; its application
class has no own finalize/dispose override. Exact distribution recipe/patch
correspondence and inherited GTK/GLib teardown source remain unverified.

This turn is PROGRESS: completed prior results are reconciled, actual ARM64
diagnostic semantics and frozen integration are recorded, a new VM failure is
localized before the intended observation, and an unjustified cache repair is
excluded. The preceding storage turn reclaimed 2.246GB while preserving active
inputs. Avoid repeating eliminated shutdown stages or treating a diagnostic's
own post-marker work as app code. Physical trial readiness is not requested.
No phone contact, reboot, signing, admission, claim, installation or protected
storage operation occurred. The native-phone Denial goal remains open.
