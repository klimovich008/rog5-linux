# Matching Dart SDK and locked mobile package resolution

The native ARM64 Flutter engine and its host snapshot tool compile successfully.
The exact-revision host Dart SDK verifies, and both Denial shell and settings
resolve their real package dependencies offline with their original locks
unchanged. This closes package resolution; Flutter tool bootstrap, ARM64 shell
AOT and a complete native session remain **NOT RUN**.

Execution source is repository `55962cc3adbd079fe900baa9346e2f41f0b52244`, tree
`fbb6aa06505badc99d3475cc228d0168e2b679ba`. Denial remains
`85b2303e2f09ae7b7b993641f90061a200f03d53`, Flutter
`d728e61e7d835e02c453c70ae9523a40f6c03215`, and Dart
`d684a576a6aa954ae107a03b2b4e1d61c3bebe93`.

The upstream `flutter/dart-sdk/linux-amd64` package resolves that Dart pin to
CIPD instance `mKiCKGu13Mk_I7udqhlk6gAyukzBPONWUy1bcpMF5mEC`.
Its 246,737,284-byte archive has SHA-256
`98a882286bb5dcc93f23bb9daa1964ea0032ba4cc13ce356532d5b729305e661`.
All 1,016 deployed payload members were independently verified, including file
hashes and link/type identities. Its executable reports Dart 3.12.2; its revision
file matches the runtime source pin. This is a verified upstream prebuilt host
SDK, separate from the earlier bootstrap SDK; rebuilding this complete SDK from
source is NOT RUN. Upstream attestations are retained, but their signatures were
not independently verified.

| Executed stage | Result | Seconds |
| --- | --- | ---: |
| Exact SDK package deployment | PASS | 27.511 |
| Independent complete SDK payload verification | PASS | 4.188 |
| Materialize and verify 84 locked package archives | PASS, 12,751 members | 7.120 |
| Real `ninja -C /work/out -j1 sky_engine` | PASS, 270 steps | 5.277 |
| `/sdk/bin/dart --version` | PASS, 3.12.2 | 0.004 |
| Shell `dart pub get --offline --enforce-lockfile` | PASS | 0.165 |
| Settings `dart pub get --offline --enforce-lockfile` | PASS | 0.165 |
| Package roots, locks and post-resolution payload audit | PASS | 2.053 |

These eight final stages pass. Shell resolution contains 81 roots and settings
83, including their application roots. Hosted names, versions, hash sidecars,
contained pubspecs and exact resolved paths agree with the locked archives.
SDK packages resolve to the pinned Flutter sources and the real generated
`sky_engine`; local packages resolve within the isolated workspace. Every hosted
payload tree remains unchanged after Pub, as do all four previously qualified
VM/Flutter platform files after sky_engine generation.

The original shell lock SHA-256 remains
`a1ac5efa8a9458e3f761b39a76a639bc7740fcf5070f9908734b30481ecad604`;
the settings lock remains
`eda67da1b3f4e50eecb5820d835dd5ba8bc002bfd3c64cb2e406988b9e54a3f7`.
The thin Flutter SDK view serves Pub's source-package lookup. Its version
metadata is explicitly derived from the pinned Denial `tools/denial-pc` recipe
(3.44.7 and the exact Flutter revision), with no Git tag mutation. It is not
evidence that the Flutter command-line tool or a complete SDK has been built.

Raw evidence is retained under
`/home/deck/.local/state/rog5-matching-dart-sdk-evidence-20260912-r1` (E).
The [qualification JSON](2026-09-12-matching-dart-resolution-qualification.json)
records exact container commands, source/tool/output hashes, timings, package
roots and evidence paths. Acquisition and audits execute `python3 E/install.py`,
`python3 E/verify.py`, `python3 E/materialize-pub.py` and
`python3 E/verify-resolution.py`; the container executes
`python3 /work/inside.py` from `E/resolve-r1/inside.py`. The complete sky_engine
command is in `E/sky-result.json`. E expands to the absolute directory above.
Extraction runs without installation hooks. Pub executes in copied application
directories, with no network, one CPU, 1 GiB memory/no extra swap, 120-second
child deadlines and a 300-second container deadline. Original source is unchanged.

The second native-engine build segment reached 3,513 of its 3,924 steps before
its explicit 1,800-second deadline (1,800.264 seconds total, exit 137). That FAIL
and the first segment's timeout FAIL remain retained; neither is recorded as a
successful compile or attributed to an observed OOM. After confirming the second
owner absent, a third segment resumed the same objects and arguments with only
411 remaining steps. It keeps two workers, a 4 GiB memory ceiling/no extra swap,
no network, a 1,800-second segment deadline and the disk reserve. The driver now
persists its actual live container identity before automatic CID-file cleanup.
The third segment completed all 411 remaining steps in **746.332 seconds**, exit
0; its actual container is absent and its terminal receipt is retained. The
earlier live observation remains historical evidence. No build owner remains.

`python3 E/verify-engine.py` passed in **0.260 seconds**. It uses readelf to check
the ARM64 engine, SONAME, required embedder exports and declared dependencies,
then executes the AMD64-host snapshot tool's `--version` in a bounded container.
The tool reports Dart 3.12.2 on `linux_simarm64`, confirming its ARM64 target.
Runtime dependency closure and engine execution are **NOT RUN**; declared
`DT_NEEDED` entries alone do not establish that closure.

| Compiled output | Bytes | SHA-256 |
| --- | ---: | --- |
| `libflutter_engine.so` | 15,975,760 | `1948c859989fc8721112ffb6eda4e6869745e0fafcec42d6c2f77d9bd402cadb` |
| `clang_x64/gen_snapshot` | 5,927,352 | `c0d9294287db1e33fea482e6f4f9907b763901f8a6c9bdf025b5791a991ebb01` |

The next offline question is whether this exact engine loads against the
authenticated ARM64 package tree with the matching ICU input, followed by shell
AOT preparation. No rebuilt phone candidate is needed to answer it.

No phone contact, signing, claim operation, candidate creation or protected-storage
mutation occurred. Accepted, signed, installed and fallback bytes remain unchanged.
S06/R01 remain **FAIL** and mobile physical rows **NOT RUN**. These are host build
dependencies and compiler intermediates, not installed qualification. No unchanged
kernel build or integrated CI was repeated for this metadata checkpoint.

Changed files: this report, its qualification JSON, `configs/project-status.json`,
generated `docs/current-state.md`, `docs/development-lessons.md`,
`manifests/artifact-sets.json` and `manifests/current-artifact.json`.
Private `E/completion.json` records ending commit/tree, changed-file hashes and
the latest actual engine state. The real-phone goal remains open.

Final metadata checks on the completed engine checkpoint:

| Command | Result | Seconds |
| --- | --- | ---: |
| `python3 -O scripts/host/test-review-metadata-checkers.py` | 19 PASS | 1.990 |
| `python3 scripts/host/check-mobile-status.py` | PASS | 0.040 |
| `python3 scripts/host/check-artifact-inventory.py` | PASS | 0.061 |
| `git diff --check` | PASS | 0.024 |

The final metadata suite has 19 PASS, 0 FAIL/BLOCKED/SKIPPED; all three
additional checks pass. There are 474 artifact sets and all previous 472 parsed
entries are unchanged. One intermediate inventory check caught the stale set
count after adding the compiled-engine set; the correction and failure are
retained in E. Earlier checks before engine completion remain separately retained.
The eight SDK/package stages plus engine compilation and binary verification
all pass; the two earlier engine-segment deadline failures remain historical.
Exact final check commands/timings are in `E/metadata-final-results.json`.
