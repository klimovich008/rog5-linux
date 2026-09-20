# Last-window capture qualification — 2026-09-20

Source repair and offline diagnostic qualification; phone remains NOT RUN.
Starting source `16b7791ee1eac5fc8e6a15b8dd066c6632cd3961`, tree
`3c2d4e721ed2606627ac40d8de527501b3387537`. Executed source
`2c1f47121ba75c4eb74b337bfd52464e621ec043`, tree
`3b42caab497f9f998bee2a83f107b13ee7e2a29f`. Metadata publication follows.

The explicit `--app-close-after-window` mode selects the existing bounded
reader at loaded → APP_RUN_BEGIN → WINDOW_REMOVED_ZERO. NONZERO and duplicate
removals refuse capture. Quit return or shutdown without an observed quit return
invalidates readiness; a partial later record also prevents capture. PID/clock,
owned0600/single-link/append-only identity guards, capture revalidation and the
1200ms total budget remain. Old sync mode is preserved and mutually exclusive.
No DSO marker, close grace, kernel, compositor or engine change was made.

The previous reader fails the new exact-prefix regression with
stage-order-or-unknown-phase (exit101). New host helper tests pass in15.152s;
18 runner cases pass in0.667s and47 launcher cases in34.125s. The frozen active
tier passes112 suites in203.628s:0FAIL/BLOCKED/SKIPPED,255NOT_SELECTED. Three
optional historical subchecks remain skipped; no physical proof is inferred.
Independent source review found no blocking issue.

ARM64 compilation took15.062s including bounded container cleanup. Small native
ARM64 system-VM qualification passes in3.723s:15 reader cases, deadline behavior,
and real owned-child capture/completion refusal/detach. Replaying three retained
actual GTK/Mousepad lifecycle logs through the reader admits precisely the third
complete prefix and refuses all later prefixes. In particular the post-return
hold does not stay eligible. These are replays of the prior QEMU-user execution,
not a new GTK run or ARM64 ptrace of a host emulator. Native capture uses a real
ARM64 kernel and an owned fixture process. The full harness separately compiles
its release helper with LTO; source identity is shared, binary identity distinct.

Changed implementation/test files:

- tools/qemu-virtio-drm/app-close-stage.rs
- tools/qemu-virtio-drm/app-close-probe.rs
- scripts/host/test-qemu-logind.py
- scripts/host/test-app-close-probe.py
- scripts/host/test-qemu-logind-runner.py

Exact commands, times, input/output hashes and evidence references are in the
adjacent qualification JSON. Raw diagnostic payloads remain private. No phone,
signing, candidate, admission, claim, protected-storage or installed-image change.
S06/R01 FAIL and all historical evidence remain unchanged.

## Full VM result and exact instruction attribution

One controlled full VM **FAIL**,375.350s:Foot0/Mousepad137. Both clients
map and report ready, with protocol focus history Mousepad→Foot; attributed
client presentation, text entry and visual semantics remain NOT RUN in this
close-only run. Normal VM poweroff PASS; historical /var unmount FAIL persists.
Runtime bytes/metadata and all input hashes are unchanged. No containers remain.
Outer service6min37.088s, peak1.4GiB, no swap. Source was frozen throughout.

The new helper succeeds: five unclipped/untruncated records,300ms total;
34.492ms interrupt-to-detach, with all stage/identity checks accepted. The DSO
observes WINDOW_REMOVED_ZERO289.033403408 and no quit return or shutdown.
The snapshot ends289.782994656, CLOCK_MONOTONIC. These clocks are not subtracted
from launcher BOOTTIME values. Stack observation reports zero candidates and
Deadline under its unchanged15ms cooperative budget, not a complete backtrace.

PC resolves to file/ELF offset0x31528 of retained libgobject (SHA256
`db2f18d8fd70549cfb99a4c53499b29154c42a4ee4746549ba594a4abf8d809f`, build ID`619c5b221f2987e8632468b9541d1d41a239d94b`). The exact instruction is
`cbz w23,0x31578`, inside FDE0x31290..0x3181c. Binary callsites from five exported
signal-handler APIs plus [matching-version gsignal.c](https://raw.githubusercontent.com/GNOME/glib/2.88.3/gobject/gsignal.c)
strongly identify static handlers_find. This is binary/source attribution without
matching debug symbols. The disassembler's nearest g_param_spec_variant label
lies outside that exported function's declared size and is not attribution.
LR0x31610 is the internal return after g_slice_alloc(24), not the missing caller.

One sample does not establish an infinite loop, a corrupt handler list, a GLib
bug, or which exported API was called. No behavior fix is justified yet.
The prologue/unwind data place the saved caller at FP+8, but no such word was
captured. Next qualify the first-frame path using the small native ARM64 fixture
and realistic maps. Measure read/parse/PEEK costs; Deadline alone does not prove
map parsing caused it. Keep existing bounds and qualify any measured optimization
before another full VM. No compositor/engine rebuild is indicated.

Full-VM release helper SHA256:
`18b74e9eb49db0b7be98e42c0753ac3c22e67883762d9efea3d0fee6989f1f4d`.
Qualification JSON SHA256:`3a86c5f79540ac289bbaab4a9fa8cb927b612e66ed2703943a526f5ac467e542`.
Private evidence roots: `rog5-window-gate-20260920-r1` and `rog5-window-gate-vm-20260920-r1` under local state.
