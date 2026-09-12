# Denial ARM64 engine arguments, 2026-09-12

Added a working exact-source argument generator for the ARM64 Flutter embedder.
It verifies locked Flutter and Skia commits, Dart against pinned Flutter DEPS,
and tracked source cleanliness, then calls the actual pinned GN argument code.
The generated configuration selects Linux ARM64, ARM64 Dart code generation,
release mode, target embedder inclusion and Fontconfig. Internal toolchain jobs
are limited to one; implicit prebuilt Dart SDK selection is disabled. It neither
runs dependency hooks nor downloads, configures a GN graph or compiles anything.
Output must be new and outside the frozen checkout, including through symlinks.

This is **argument-generation PASS**, not an engine build or session PASS. The
upstream helper's x86-64 defaults are appropriate for its documented reference
build, but cannot produce our ARM64 engine unchanged. The exact embedder
`BUILD.gn` includes the library in a cross-target build only when
`embedder_for_target` is true. The exact snapshot target uses the host toolchain
for a generator targeting the selected Dart architecture; a future compiled
`gen_snapshot` must still demonstrate ARM64 output, not merely x86-64 executable
identity. No existing x86-64 engine checksum was repurposed as an ARM64 identity.

The first exact-source invocation caught an integration bug: Flutter's parser
expects argv[0] and otherwise drops the first option. Our initial call consequently
selected debug mode; the release guard rejected it before writing `args.gn`.
The failing regression is retained. Passing the program-name entry fixes it.
Five actual pinned-generator cases now cover correct ARM64 release arguments,
x86-64 default rejection, missing target-embedder rejection, missing argv[0]
rejection and independence from optional prebuilt-cache contents. These execute
the real generator; ordinary CI's nine producer/guard fixtures are separate.

Starting source: `7cdca39a57204fc9bad336f9e0ddbe4c26912a65`, tree
`ed4c7e5552fd2ff798d3b526ad639c83a137f4d1`. Final tested source:
`1d6c8484ddfa777c9d1fb7a642b3fe170838227b`, tree
`7a314db8ba8f16dd696bc8656385f2c0613c7627`. Later changes record qualification,
status and development lessons only. Final commit/tree and all changed files
are retained in private completion evidence.

| Personally executed check | Result | Seconds |
|---|---|---:|
| Producer and refusal fixtures, Python `-O` | 9 PASS | 0.207 |
| Exact-source generation | Argument PASS; graph/build NOT RUN | 0.113 |
| Actual pinned-generator semantic cases | 5 PASS | 0.105 |
| Frozen active tier | 86 PASS; 0 FAIL/BLOCKED/SKIPPED; 255 NOT_SELECTED | 131.663 |
| Final metadata checker regressions | 19 PASS | 1.834 |

Three declared optional subchecks remain SKIPPED within passing active suites:
sealed charging-archive replay, retained ARM trial-helper replay, and retained
ARM PMIC rail-reader replay. The first integrated run was intentionally stopped
before changing its source after the parser failure: 28 PASS and 58 BLOCKED,
exit 143. Its logs and summary remain intact. That is not a successful full tier.
No unchanged kernel build or previous package/runtime tests were repeated.

The generated `args.gn` SHA-256 is
`db52820a0702bf63149044f49fcccd600cee55387cd0a441d85ffafadcec3865`.
The generator source SHA-256 is
`6e1a678804bf5cdc1797340578b082c81f2ebbf7b9c19ce3a8543ae0251ea1cf`.
Flutter remains `d728e61e7d835e02c453c70ae9523a40f6c03215`, Skia
`0ee042f542b3e79f5ac49115387718c6bb3d7d34`, Dart
`d684a576a6aa954ae107a03b2b4e1d61c3bebe93`. Full commands, evidence and artifact
hashes are in the [qualification JSON](2026-09-12-denial-arm64-engine-args-qualification.json).
The inventory adds one configuration fixture while preserving its previous
464 sets; the current pointer distinguishes it from compiled artifacts.

A read-only owner/capacity audit confirms the old engine container is absent,
its sync result is terminal FAIL/137, and its cached builder image still exists.
The pinned GN executable is missing. Approximately 5 GiB is free; the retained
sync recipe requires 80 GiB at startup. That number is the recipe's conservative
guard, not a newly measured universal Flutter requirement. We did not lower it
or restart the interrupted job. Source identity alone does not prove complete
DEPS/CIPD/hooks closure. GN graph generation, compilation, engine/ICU/AOT artifacts
and native mobile session execution all remain **NOT RUN**.

Next: audit project storage for demonstrably duplicate or disposable build
scratch, preserving unique data and recovery evidence. Complete the pinned
dependency cache only within measured capacity and the 3 GiB reserve. Then run
real GN from the checkout's `engine/src` directory, followed by a bounded engine
and host AOT-tool build. These are the next build steps, not executed results.

The authenticated Arch payload, schema cache, Denial native binaries, accepted
server/rescue, kernel/DT/modules, signed candidate/fallback, installed-byte
qualification and consumed claims are unchanged. S06/R01 remain FAIL and every
mobile physical row remains NOT RUN. No phone operation, protected-storage
mutation, signing, admission, claim consumption or candidate generation occurred.
