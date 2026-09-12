# Reproducible VM and Flutter platform-Dill builds

The actual pinned frontend compiler produced the VM and Flutter platform-Dill
files successfully. Two fresh-output builds produced four byte-identical files.
The pinned Dart kernel parser reads all four and confirms their VM/Flutter library
identities. Complete SDK compilation, shell pub resolution and ARM64 shell AOT
remain **NOT RUN**; these are SDK intermediates, not a native engine or phone image.

Execution source: repository `198cb553c79eba9b0bdbaff97f198c0e190e0f6f`, tree
`060f8de8cdcbd1f8c9e6e2e24a5a5f44cc57d1cd`. The existing engine build was neither
interrupted nor given new source/cache inputs. Separate containers bind the
verified Dart source copy, bootstrap SDK and DevTools into the expected source
paths, all read-only. They share pinned tools but use independent writable output
directories. No package installation hooks or phone operations run.

| Final executed stage | Result | Seconds |
| --- | --- | ---: |
| First real GN graph | PASS | 2.252 |
| First VM and Flutter platform actions | PASS, 2 actions | 94.820 |
| Second fresh-output GN graph | PASS | 2.252 |
| Second VM and Flutter platform actions | PASS, 2 actions | 94.071 |
| Pinned kernel-parser process | PASS, 4 binaries | 4.626 |
| Actual dependency-file/source identity audit | PASS, 992 files / 4 Git roots | 0.527 |
| Fresh-output byte comparison | PASS, 4 pairs | 0.058 |

All seven final stages pass. One earlier provenance-collector attempt failed:
it handled absolute input paths but omitted the relative generated input
`vm_outline.dill`. That failure and the initial collector are retained. The
corrected collector resolves such inputs within the Ninja output working directory
and rejects escape. Compilation and binary parsing had already passed; the
collector error is not silently presented as a successful first attempt.

| Output | Bytes | Libraries | `dart:ui` |
| --- | ---: | ---: | --- |
| `vm_platform.dill` | 8,267,376 | 21 | absent |
| `vm_outline.dill` | 1,609,864 | 21 | absent |
| `flutter_patched_sdk/platform_strong.dill` | 9,960,416 | 20 | present |
| `flutter_patched_sdk/vm_outline_strong.dill` | 1,905,984 | 20 | present |

The [qualification JSON](2026-09-12-sdk-platform-qualification.json) records all
output hashes, exact container commands, tool/source identities, timings and
the retained failure. Private raw evidence is
`/home/deck/.local/state/rog5-sdk-platform-evidence-20260912-r1` (E).
Executed build commands were `python3 E/run.py` and `python3 E/twin-r1/run.py`;
both invoke `/gn gen --threads=1 --check /work/out`, then
`ninja -C /work/out -j1 flutter_patched_sdk/platform_strong.dill`.
E expands to the absolute path above. Both Ninja logs confirm the real VM and
Flutter actions ran. The second output began with only the qualified arguments;
no generated binary was copied into it. This proves byte equality for two fresh
outputs under the same pinned tools and virtual paths, not cross-host equivalence.

The pinned parser executes `inspect.dart` through the verified bootstrap Dart
with the generated source package configuration. Its process duration is above;
the four binary reads/checks themselves took 0.490 s. It uses the real
`package:kernel` binary loader, bounds each input to 128 MiB, and checks `dart:core`
plus the expected presence/absence of `dart:ui`. It does not infer semantics from
file hashes or source markers alone. Matching second-build bytes inherit that
same inspection; the parser was not unnecessarily rerun.

The dependency audit executes `python3 E/source-inputs.py`. It compares copied
Dart source bytes to their originals, hashes every actual depfile input, and
checks four clean Git roots against the retained gclient entries:

| Source | Commit |
| --- | --- |
| Flutter | `d728e61e7d835e02c453c70ae9523a40f6c03215` |
| Dart | `d684a576a6aa954ae107a03b2b4e1d61c3bebe93` |
| Dart third-party core packages | `347df4b546f315fc1ff69c6e65f2a023b0263b1d` |
| Dart third-party tools packages | `7f986eaa15f493dd2da081ba0daa49be22fcc2fb` |

The retained gclient-entry hash and all 992 input hashes are in
`E/source-inputs.json`. This is an audit of the inputs these actions used,
not a fresh resolution of every DEPS entry or complete SDK source closure.

Each independent platform container has one CPU, a 1,536 MiB memory ceiling with
no extra swap, no network, a 300-second action deadline, a 16 MiB log bound and a
4 GiB free-space stop preserving the required 3 GiB reserve. The existing
engine continuation retains its separate 4 GiB cap. At the retained observation
it was live at 2,216 of 3,924 continuation steps, with no recorded OOM events.
The same owner is
`7c1168c3e0b12c08cd3257120a36d654bb36d8c9047ecf0716dd7055370b7cc0`, exec session
`45465`. Inspect that owner or
`/home/deck/.local/state/rog5-engine-clang-evidence-20260912-r1/build-r1/compile-r2-result.json`
before continuing. Historical observations do not authorize a duplicate build.

The previous turn was progress; this turn executes and qualifies the next real
compiler stage. The fresh-output repeat answered the previously unproven
reproducibility question. No unchanged full kernel build or integrated CI was
repeated. No phone contact, signing, claim operation, candidate creation or
protected-storage mutation occurred. Accepted/signed/installed/fallback bytes
remain unchanged. S06/R01 remain **FAIL**, physical rows **NOT RUN**.

Final metadata checks executed personally on this checkpoint:

| Command | Result | Seconds |
| --- | --- | ---: |
| `python3 -O scripts/host/test-review-metadata-checkers.py` | 19 PASS, 0 FAIL/BLOCKED/SKIPPED | 2.520 |
| `python3 scripts/host/check-mobile-status.py` | PASS | 0.064 |
| `python3 scripts/host/check-artifact-inventory.py` | PASS: 472 sets, 68 small tracked hashes | 0.115 |
| `git diff --check` | PASS | 0.032 |

All previous 471 parsed artifact entries are unchanged. Inventory validation does
not rehash unrelated large/private artifacts; the new binaries and used source
inputs have their separate byte verification above. Exact metadata-check commands
and timings are in `E/metadata-final-results.json`.

Changed files: this report, its qualification JSON, `configs/project-status.json`,
generated `docs/current-state.md`, `docs/development-lessons.md`,
`manifests/artifact-sets.json` and `manifests/current-artifact.json`.
Private `E/completion.json` records ending commit/tree, changed-file hashes and
the latest actual engine owner state. It closes this checkpoint, not the native
engine build or real-phone goal.
