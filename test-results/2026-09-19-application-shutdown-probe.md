# Application shutdown probe and scoped Denial VM pass — 2026-09-19

**One diagnostic Denial VM session passed clean Mousepad/Foot close under the
unchanged app policy. Earlier Mousepad137 failures remain unresolved.** New probe
source is frozen at `ced1f905203a8d34466dd33181c36f3acddf8264`, tree
`6ce7c3c00d0567ca0234f69f698de7eb541e4c40`. No phone operation or qualification.

## Correction to the preceding interpretation

The earlier0.209312ms settings-sync END proves that observed invocation returned.
It does **not** exclude every later settings-sync call. GLib2.88.3's
`g_application_run()` calls settings sync internally after shutdown emission.
The retained ARM64 binary loads the internal function through GOT0x24ae88 at
0x123080 and calls it at0x123088. Its `R_AARCH64_RELATIVE` relocation points to
0x145b08, the real g_settings_sync address. This binding bypasses the preload
wrapper. The exact disassembly, relocation, library hashes and upstream source
are retained. The original report/qualification bytes remain unchanged; this
correction supersedes their blanket exclusion of unfinished settings sync.
The earlier focused host measurement has the same interposition limitation.

Sources: [GLib2.88.3](https://raw.githubusercontent.com/GNOME/glib/2.88.3/gio/gapplication.c),
[shutdown signal API](https://docs.gtk.org/gio/signal.Application.shutdown.html).
Package-version matching is not a reconstruction of the complete distribution
build recipe; the actual binary binding was checked separately.

## Source change and verification

The existing VM-only interposer now records application-run entry/return and
normal/after shutdown signal observers. GLib's RUN_LAST class closure lies
between these observers. They can also enclose other signal handlers and are
not exact subclass instruction boundaries. The wrapper calls the real function
once, preserves argc/argv, return value and errno, removes its signal handlers,
and leaves application lifetime, main-context iteration and backend selection
unchanged. Existing0600/single-link log checks,12-record/1536-byte bound,
explicit125 instrumentation failure and child-exec environment removal remain.

Changed production files: `tools/qemu-virtio-drm/settings-sync-diagnostic.c` and
`scripts/host/test-settings-sync-diagnostic.py`. The failing-before regression
exercises the actual interposer, verifies real-call arguments/return/errno and
handler ordering, and distinguishes interruption during versus after shutdown.
The independent ARM64 fixture derives a real GApplication subclass and checks
that markers surround its actual shutdown closure; it uses retained target
headers/libraries under isolated QEMU user emulation. It is not a Mousepad/VM
substitute result.

| Executed check | Result / duration |
|---|---|
| New regression against old probe | expectedFAIL,1test,0.370s |
| Corrected controlled-callee suite | 16PASS,0.293s |
| Python-O execution | 16PASS,0.299s |
| ARM64 probe / real-GLib fixture builds | PASS,0.615s /0.565s |
| Real ARM64 GLib fixture old/new probe | expectedexit3 /exit0,0.164s each |
| Frozen active tier | 108PASS,0FAIL/BLOCKED/SKIPPED suites,255NOT_SELECTED;173.793s |
| Declared optional artifact subchecks | 3SKIPPED; no artifact/physical proof |
| Bounded Denial VM | diagnosticPASS,total365.941s,QEMU313.708s |

One initial real-GLib fixture setup failed because `/out` was beneath the
read-only runtime root. A fresh output mounted under private tmpfs `/opt/out`
corrected it; the initial failure is retained. The corrected real fixture used
18.8MiB peak and no swap. Active tier peak544.6MiB,no swap. No kernel, Denial,
Flutter or GTK rebuild; only the small probe, API fixture and usual VM supervision
helpers were compiled. The new DSO SHA256 is
`65535e5520368158cfcaf51b2a2c95fe012ed113aaea288a46c79e94df093b71`.

## Actual VM result and remaining limits

Both owned native clients mapped/focused; exact ACK and approved teardown
passed. Foot0 and Mousepad0; timeout forwarded TERM without KILL. Same-PID966
probe records show:

- SHUTDOWN_BEFORE299.531685216 → SHUTDOWN_AFTER299.573490304:41.805088ms.
- Observed settings sync299.544903248 →299.545113040:0.209792ms.
- SHUTDOWN_AFTER → APP_RUN_END299.615596688:42.106384ms.

These are intervals within one CLOCK_MONOTONIC domain. No subtraction from the
separate BOOTTIME close brackets or Wayland log clocks was used. The returned
application run proves its later internal work also finished in this passing
run, but does not explain the preceding failed runs. Diagnostic hooks can affect
timing. This is not a demonstrated fix for the intermittent137 outcome.

Denial terminal counters report80raster frames/80page flips,no render errors.
They are not per-client presentation, visual, Adreno or phone proof. VM normal
poweroff,QEMU0,owned container removal/absence all pass; all37 input hashes
were independently rechecked afterward. Text entry was deliberately NOT RUN.

The explicit diagnostic allowance remains420s, with existing conditional30s
cleanup reserve unused. Standard300s qualification remainsFAIL and was not rerun
under its normal policy. App65s, TERM/KILL2s, user120s,PAM140s, read-only runtime,
no network,2CPU/2GiB host-container bounds and exact ACK/owner guards remain.
No phone/USB, signing, installation, admission, claim or protected-storage action.
Historical S06/R01 FAIL, rescue/fallback and installed bytes remain unchanged.

## Next useful work

The current payload already includes the source-qualified GTK caret fix; its
low-caret runtime treatment is still NOT RUN. The normal app-switch/OSK flow has
separate earlier evidence, so repeating it or another sync-only close would not
answer that missing question. A one-use `run-bottom-caret.py` is prepared in the
private evidence directory with the same exact inputs and diagnostic allowance;
it selects `--automatic-caret --bottom-caret` and removes close-only mode.
Only Python syntax has been checked for this prepared wrapper; the actual new
flow remains NOT RUN. No shell/engine/kernel rebuild is needed.

Private commands, raw logs, source/API audit and prepared wrapper are under
`/home/deck/.local/state/rog5-app-shutdown-probe-20260919-r1`; the paired JSON
retains exact build/run command vectors, input/output hashes and portable fixture
source. Existing sealed evidence is not rewritten.

## Run improvement

Check actual call binding before inferring universal function coverage from an
LD_PRELOAD trace. The real-library fixture and ELF relocation audit found a gap
that the controlled-callee suite alone could not expose. Keep observer intervals
and internal-call visibility explicit, and move to the unqualified mobile
interaction once a scoped close path can complete without weakening its policy.

Publication checks:8mobile-status tests PASS(0.020s); artifact inventory PASS546sets;
generated-status validation and `git diff --check` PASS. Semantic comparison
preserved all545 earlier artifact sets and every existing current-artifact pointer.
