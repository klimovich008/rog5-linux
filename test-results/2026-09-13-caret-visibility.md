# Caret visibility and keyboard policy — 2026-09-13

Committed caret geometry now crosses Denial's existing bridge, and the shell
uses one bounded displacement calculation for painting and native input.
The source fixes and ARM64 builds pass. **The corrected VM typing sequence is
not qualified:** its retest failed at launcher readiness before editor launch.
No phone operation, signing, admission, claim use, phone candidate creation,
installation or protected-storage mutation occurred. S06/R01 remain FAIL;
mobile physical rows remain NOT RUN. The full phone goal remains active.

## Changes and identities

- Patch0014 carries optional committed caret geometry and activation identity
  with generated Rust/Dart bindings. Coordinates are already relative to the
  owning content origin. Zero width is valid. Focus/lock/enable/disable/destruction
  prevent stale publication; same-editor touch preserves unchanged committed
  geometry. Pending owner data is retained until matching window metadata arrives.
- Patch0015 shares caret visibility arithmetic between painting and native input,
  bounded by the existing pan range. Missing geometry retains manual fallback;
  a manual override survives a same-activation missing rectangle. The 8px margin
  is best effort within that range.
- Patch0016 publishes input when caret, manual mode or window metadata changes,
  including new unfocused windows; post-frame coalescing and disposal stay intact.
- Patch0017 updates caret independently from keyboard policy. Geometry-only
  messages cannot replay close policy against a manual opening. An explicit
  opening also cancels a pending close timer.
- The VM observer has an explicit no-manual-pan mode. Manual keyboard reveal
  remains because synthetic pointer input does not gain touch-only authorization.

Starting source `637efae6bff7838792d5d74e20f558239a1f66e6`, tree
`60cf072d852607c91c145de0d3d6ea84397f57c1`.
Native build source `daf4b119d5d45334cea00dec774e26e24d44fa23`; native binary
`b3bc17099f666ef920412183c59f179160fb28033a38d79f61f18e17e3f0dcf5` is reused for both VM runs.
The first shell/VM source was `381ab261ede833c0a38b68f2d791fc7681908d89`.
Corrected shell, second VM and integrated host tier source:
`43ec481d5409288a8eb28dfd0f31c1781a9535be`, tree `c45922135868e50415cae2d99346f698acb4274e`.
Documentation/evidence publication is a later revision, not a new compiled image.

The 703-file native inventory and 383-file shell inventory are private retained
inputs. Only the publisher and controller differ between shell workspaces;
patch application reproduced those exact files. The second VM archive differs
from the first only in libapp.so, apart from its provenance metadata. The
kernel, native compositor, engine and assets are unchanged. Generated bindings
use the verified FlatBuffers25.9.23 release tool.

## Executed checks

| Check | Result |
| --- | --- |
| Native committed-caret state | 16 PASS; two same-editor-touch counterexamples failed before correction |
| ARM64 actual encoder and old/new generated readers | 7 PASS; build5.179s, run0.119s; both compatibility directions |
| Native compositor build | PASS212.575s, bounded3GiB/no-swap offline build |
| Old viewport counterexample | Expected FAIL: top caret shifted by367.2 logical pixels |
| Publisher invalidation before fix | 5 expected FAIL,2 PASS |
| Keyboard policy before fix | 4 expected FAIL,6 PASS |
| Final merged caret/animation/publisher/policy | 13+10+7+10 PASS; 26.219s total |
| Shell frontend | PASS 23.508s |
| ARM64 shell AOT | PASS 21.508s |
| First no-pan VM | FAIL271.396s: keyboard closed after te |
| Second no-pan VM | FAIL238.613s: launcher icons absent; no editor actions |
| Integrated active tier | {'PASS': 102, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255}; 150.272s |

Declared optional subchecks: `{'SKIPPED': 3}`. Exact commands,
per-case timings, hashes and private evidence locations are in the linked JSON.
These host suites execute production methods with geometry/provider/scheduler
adapters; they do not execute full Flutter/Riverpod or physical input. The first
wire link failed on bitcode-only dependencies; matching thin-LTO settings fixed
that test build. The earlier failed results are preserved. No new GitHub CI
execution is claimed.

## VM evidence and unresolved boundary

The first VM's initial capture shows a visible top-line caret with OSK open and
no scripted pan. Only te reached Mousepad; the remaining captures fail the
required test/tes/test sequence. Source and client-log deduction identified a
caret update replaying unchanged false visibility policy, consistent with the
separate failing controller regression. The native-to-Dart wire was not recorded;
the deduction is not a direct wire observation. The observer withheld ACK.

In the second VM, wallpaper, clock, battery widget and app labels rendered, but
expected icons were absent in all eight readiness captures. The observer made
zero app/input actions and retained FAIL. Identical captures over this bounded
interval do not prove a compositor deadlock. Independent source review found
no direct icon-loading dependency changed by0016/0017. Actual tiles use
AppIconImage directly; an unused deferred icon widget is irrelevant. SVG/bitmap
loading, decode/fallback completion and subsequent presentation remain unresolved.

Both failed runs cleaned their owned host VM containers. Neither demonstrated
approved guest teardown or normal successful session completion. Do not turn
host cleanup into a guest-cleanup PASS. The older qualified manual-pan VM remains
historical evidence; it is not transferred to the new shell.

Next smallest experiment: retain this exact shell/native/kernel/runtime and
collect bounded icon path/load/decode/error plus presentation diagnostics that
survive readiness failure. Distinguish missing load completion from missing
paint/presentation before changing code or readiness timing. Do not bypass the
icon gate, repeat an unchanged VM, or treat this as phone GPU evidence.

[Exact test/build commands, identities and retained evidence](2026-09-13-caret-visibility-qualification.json).
