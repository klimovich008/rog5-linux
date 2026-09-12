# Native engine loading and reproducible ARM64 shell AOT

The real Denial engine loader accepts the compiled ARM64 engine, and the real
shell now compiles to ARM64 AOT. Two fresh AOT output directories produce
byte-identical libraries. Six tests through Denial's actual loader pass under
ARM64 QEMU, including loading and releasing the shell's AOT data three times.
This does **not** start a Dart isolate, Flutter shell, compositor or phone session.

Execution source: repository `fcaa289fb5f6ffe10907a9e3b5e36a6a9e19d473`, tree
`54ccb1d9fa5d564d401cd1fedfa0e3637a0bee02`. Denial remains
`85b2303e2f09ae7b7b993641f90061a200f03d53`, Flutter
`d728e61e7d835e02c453c70ae9523a40f6c03215`, and Dart
`d684a576a6aa954ae107a03b2b4e1d61c3bebe93`. The engine and snapshot-tool bytes
qualified in the previous checkpoint are unchanged.

| Executed stage | Result | Seconds |
| --- | --- | ---: |
| Compile actual Denial loader library | PASS | 1.317 |
| Initial standalone test-harness link | FAIL, missing ThinLTO option | 0.515 |
| Corrected harness link | PASS | 3.423 |
| ARM64 engine dynamic-loader dependency resolution | PASS | 0.115 |
| Initial four real-loader tests | 4 PASS | 0.265 |
| Real shell release frontend compilation | PASS, zero errors | 23.171 |
| First ARM64 shell AOT compilation | PASS | 20.111 |
| Second fresh-output ARM64 shell AOT compilation | PASS, identical bytes | 19.961 |
| Used Arch libraries, ICU and compiler-input audit | PASS | 1.935 |
| Expanded AOT-data test-harness link | PASS | 3.775 |
| Final loader/AOT-data suite | 6 PASS, 0 FAIL/ignored/filtered | 0.365 |

The initial linker failure was in the standalone harness. The existing release
dependencies contain ThinLTO bitcode; the source Cargo profile specifies
`lto = "thin"`. Adding that matching compiler option fixes the harness without
changing the engine or replacing Denial's loader. The failed log/result and
original harness remain retained. The final negative test deliberately presents
libc as an AOT application: the engine reports missing isolate snapshot data and
returns invalid arguments, as expected. That diagnostic is a passing rejection.

The six final cases cover missing libraries, a library without the engine ABI,
Denial's custom extensions and required procedure table, release/AOT mode,
callable monotonic engine time, repeated real-shell AOT-data load/cleanup, and
rejection of an unrelated ELF (the ABI and AOT-mode assertions share one case).
The test recompiles Denial's actual `EngineLibrary` from its pinned source and
uses its `create_aot_data` and RAII cleanup; it is not a duplicate loader model.

All 13 libraries resolved by the engine's actual ARM64 loader match the retained
authenticated Arch package payloads, including symlink targets and final file
hashes. The 1,970 frontend depfile inputs match pinned Denial/Flutter sources or
verified locked package payloads. ICU output matches the clean recorded ICU pin
`ee5f27adc28bd3f15b2c293f726d14d2e336cbd5` and the actual Ninja copy input
`common/icudtl.dat`. This verifies the ICU data identity, not ICU initialization.

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| Shell `app.dill` | 45,472,848 | `0a07d9cce460c68374dde3ca233ddcc6463b0c19b95a864800b7928c8692f9d0` |
| ARM64 `libapp.so`, both builds | 10,814,352 | `0d4fae6a98fc5d5e37e8e907db2fcd0484ed9706e89ac3c6bd103e472ad6b871` |
| `icudtl.dat` | 10,822,192 | `1cf67874b5a87a8363a86fb3f81e3cbbed54d389062dab8fb52308d5cf8c8612` |

The frontend uses the verified exact-revision SDK's real
`frontend_server_aot.dart.snapshot`, the qualified Flutter platform, unchanged
application package configuration, and the release options from pinned Flutter
`compile.dart`. AOT uses the built ARM64-target `gen_snapshot`, with
`--deterministic --snapshot_kind=app-aot-elf --elf=/output/libapp.so --strip`.
The comparison proves determinism for two fresh outputs from the same frozen
Dill and tool, not yet a complete reproducible asset/application build.

Raw evidence directories:

- E: `/home/deck/.local/state/rog5-engine-runtime-evidence-20260912-r1`
- A: `/home/deck/.local/state/rog5-shell-aot-evidence-20260912-r1`

Executed drivers are `python3 E/run.py`, `python3 E/run-r2.py`,
`python3 E/audit-inputs.py`, `python3 E/run-aot-probe.py`,
`python3 A/run-frontend.py` and `python3 A/run-aot.py`. E and A expand to the
absolute directories above. The [qualification JSON](2026-09-12-engine-shell-aot-qualification.json)
records exact commands, tools, inputs, outputs, timings and retained failures.
The full input audit is retained privately with its hash in that record.

Compilation has no network, at most two CPUs, 2 GiB memory/no extra swap and
300-second host deadlines (290 seconds inside the container). Smaller Rust
compiles use 1 GiB/one CPU and 90-second host deadlines. ARM64 loading runs in
an isolated read-only package root with no host devices/network, a 768 MiB
memory/no-swap ceiling, one CPU and a 60-second service deadline. All owned
processes have terminal results. Disk reserve remains above 3 GiB.

Next: assemble the real Flutter assets, prepare the settings application/runtime,
and qualify bounded offline initialization. A library load is not shell startup;
settings dependencies resolving does not supply its GTK runtime or a mobile UI.
Hardware scanout, touch, accelerated rendering and real-phone usability remain
unqualified. No phone contact, signing, claim operation, candidate creation or
protected-storage mutation occurred. Signed/installed/fallback artifacts and
historical S06/R01 **FAIL** results remain unchanged; physical rows **NOT RUN**.

The previous turn was progress, and this turn closes real compiler/loader
boundaries. It reuses the verified SDK frontend snapshot and cached Rust
dependencies instead of rebuilding unrelated toolchains. No unchanged kernel
build or full CI was repeated for this metadata checkpoint.

Changed files: this report, its qualification JSON, `configs/project-status.json`,
generated `docs/current-state.md`, `docs/development-lessons.md`,
`manifests/artifact-sets.json` and `manifests/current-artifact.json`.
Private `E/completion.json` records ending commit/tree and changed-file hashes.

Final metadata checks executed personally on the frozen checkpoint:

| Command | Result | Seconds |
| --- | --- | ---: |
| `python3 -O scripts/host/test-review-metadata-checkers.py` | 19 PASS | 1.966 |
| `python3 scripts/host/check-mobile-status.py` | PASS | 0.040 |
| `python3 scripts/host/check-artifact-inventory.py` | PASS | 0.062 |
| `git diff --check` | PASS | 0.025 |

Final executable suites total 25 passing cases (six engine/AOT plus 19 metadata),
zero final FAIL/BLOCKED/SKIPPED. The original harness-link failure remains
recorded above. All 474 previous parsed artifact entries are unchanged; two
new sets bring the inventory to 476. These checks do not newly verify unrelated
large/private artifacts or constitute remote CI. Exact metadata commands and
timings are retained in `E/metadata-final-results.json`.
