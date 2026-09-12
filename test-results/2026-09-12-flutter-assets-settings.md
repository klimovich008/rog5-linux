# Real Flutter assets and settings ARM64 AOT

Flutter's real asset builder produces the shell and settings assets, including
binary asset manifests, font manifests, notices and compiled material shaders.
Two fresh shell asset outputs are byte-identical. The settings frontend and two
ARM64 AOT builds pass, with identical AOT bytes. A private 32-file shell runtime
fixture now contains the exact engine, shell AOT, ICU and declared assets.
VM/isolate, compositor and physical startup remain **NOT RUN**.

Execution source: repository `ef2648d41b455e195482d5431936264e088657cd`, tree
`b92dfa3a8af39b6df6120cb96a17fbe60c34e2b3`. Denial remains
`85b2303e2f09ae7b7b993641f90061a200f03d53`, Flutter
`d728e61e7d835e02c453c70ae9523a40f6c03215`, and Dart
`d684a576a6aa954ae107a03b2b4e1d61c3bebe93`.

| Executed final stage | Result | Seconds |
| --- | --- | ---: |
| Verify 100 source-pinned tool packages, reusing 52 archives | PASS; 48 fetched | 23.708 |
| Fetch two additional constrained transitive packages | PASS | 0.737 |
| Materialize and verify the first 100 payloads | PASS | 4.720 |
| Materialize and verify the additional two payloads | PASS | 0.070 |
| Source-pinned Material font archive and 23 payload files | PASS | 0.398 |
| Real offline tool dependency resolution | PASS | 0.515 |
| Lock-preserving offline resolution repeat | PASS | 0.415 |
| Normal source SDK engine-metadata bootstrap | PASS | 0.315 |
| Real source CLI version, with verified upstream metadata | PASS | 19.562 |
| First real shell asset assembly | PASS | 8.935 |
| Second fresh-output shell asset assembly | PASS; identical bytes | 8.835 |
| Settings release frontend compilation | PASS; zero errors | 20.715 |
| First settings ARM64 AOT compilation | PASS | 13.545 |
| Second settings ARM64 AOT compilation | PASS; identical bytes | 13.395 |
| Real settings asset assembly | PASS | 8.685 |
| Source/cache, lock, asset and reproducibility audit | PASS | 1.044 |
| Exact private shell runtime fixture composition | PASS | 0.157 |

All 17 final stages above pass. Four earlier attempts remain failed and retained:

- The archive collector initially compared a raw URL with an unencoded version
  string. Pub percent-encodes `+`; the corrected check retains the exact host,
  decoded version path and archive hash. It resumed the 76 verified archives.
- The initial offline tool resolver exposed two transitive dependencies absent
  from the source's list of 100 exact pins. A complete selected-package dependency
  scan identified both: `dart_service_protocol_shared 0.0.3` satisfies `^0.0.3`,
  and `record_use 0.6.0` satisfies `^0.6.0`. The real solver accepted and locked
  them. Their versions are explicit constraint selections, not upstream exact pins.
- Direct source CLI execution initially omitted the normal SDK engine-stamp
  bootstrap. The actual pinned `update_engine_version.sh` then ran successfully
  in the isolated cache.
- Its next offline version attempt lacked `engine_stamp.json`. The exact
  source-pinned upstream metadata was separately fetched, checked against its
  revision, and retained; the subsequent CLI version command passed offline.

The newly generated isolated tool lock has 102 hosted packages and the package
configuration 103 roots including the tool. All archive identities and payloads
verify; all 9,558 archive members and 1,396 copied tool-source files remain
unchanged. New Pub archive hashes were observed through HTTPS metadata and frozen
in this lock; they are not represented as an upstream committed lock or signature.
The new lock SHA-256 is
`1aa193fc5df798338a2ca97d1737450f9c2cc1984ec0095b2efbaa0f4dcad340`.
Only 16,876,274 bytes of new Pub archives were downloaded.

The CLI reports framework revision `d728e61e7d` on a user branch, Dart 3.12.2,
and upstream SDK engine revision `69c8c61792`. That engine metadata comes from
the pinned `bin/internal/engine.version`; it is **not** the locally compiled
fork engine's identity. The latter remains bound to its previously verified
source, arguments and binary hash. Historical Flutter-tool snapshot notes and
checksums refer to older inputs and were not replaced or claimed to match this
source execution. A new deterministic Flutter-tool AOT snapshot was not built.

The asset driver calls the actual pinned `ManifestAssetBundle` and
`ShaderCompiler`, using the engine build's real host `impellerc`. It targets
Linux ARM64 with Flutter's GLSL/Vulkan runtime shader stages. Fonts are copied
whole through the supported non-subsetting path. It decodes the binary manifest
with the actual `StandardMessageCodec`, checks every declared variant exists,
and checks every font-manifest path. Unsupported custom transformers fail.

The shell has 29 declared entries, 23 manifest variants and four font files;
settings has six declared entries, zero ordinary asset variants and one font.
Both contain two compiled material shaders. Byte equality compares the complete
fresh shell output trees. These checks do not decode or render the images/fonts,
exercise GPU shaders, or prove UI behavior.

| Output | SHA-256 |
| --- | --- |
| Shell asset tree, both fresh builds | `5b30028692afc04c736e8d378f7abbeaafa4dd29a4f763cb4bc2708dd2296645` |
| Settings asset tree | `ec5c98dfa9e14265f98a4f4c82ca5cc3aa5a9c4a5259d1041b44178b7c51ad82` |
| Settings ARM64 `libapp.so`, 8,127,376 bytes, both builds | `721bd95061468b5ae3ded62d47e4999bb5bd3786fa98f43705f5a702ef18f10b` |
| Private shell runtime fixture tree | `e2cfdd7c25fbd00c6a705c0084f0d1a9fb806c00ea2ec3d4c808f93386d6f9de` |

The fixture copies the 29 declared shell entries plus the exact engine, AOT and
ICU inputs; compiler SPIR-V intermediate files stay outside it. Every copied
file is hash-checked against its input. It has no installation/admission authority
and is not a boot image or signed candidate. Settings still needs its native
runner/GTK runtime and initialization qualification.

Private evidence is
`/home/deck/.local/state/rog5-flutter-assets-evidence-20260912-r1` (E).
The [qualification JSON](2026-09-12-flutter-assets-settings-qualification.json)
contains exact commands, timings, source/tool/output hashes and retained failures.
Executed Python drivers under E are `fetch-tools.py`, `fetch-tools-r2.py`,
`fetch-extra.py`, `materialize-tools.py`, `materialize-extra.py`, `fetch-fonts.py`,
`prepare-tool.py`, `prepare-tool-r2.py`, `bootstrap-metadata.py`, `run-assets.py`,
`finish-asset-runs.py`, `qualify.py` and `stage-runtime.py`; the finishing driver
executes `run-assets-r2.py` and `run-settings-assets.py`. Settings compilation
executes `settings-build/run-frontend.py` and `settings-build/run-aot.py`.
The separately fetched upstream engine metadata has its URL/hash/timing receipt.
E expands to the absolute directory above.

Tool/asset executions run with no network, at most two CPUs, 1.5 GiB memory/no
extra swap and 180-second host deadlines; compiler phases use 2 GiB and
300-second host deadlines. Container deadlines are slightly shorter. Heavy
phases run sequentially. Package/font acquisition is independently bounded and
streaming, with no installation hooks. Source inputs are mounted read-only;
only isolated tool/cache/output copies are writable. All owned processes are
terminal and the host retains more than 3 GiB free disk.

Next: use the fixture for bounded offline engine/VM initialization, and complete
the settings native runner/runtime. No phone operation, signing, claim creation
or consumption, boot candidate creation, or protected-storage mutation occurred.
Accepted/signed/installed/fallback bytes and historical S06/R01 **FAIL** results
remain unchanged; physical rows **NOT RUN**. The previous turn was progress and
this turn completes actual tool, asset and application builds. No unchanged
kernel build or full CI was repeated for this metadata checkpoint.

Changed files: this report, its qualification JSON, `configs/project-status.json`,
generated `docs/current-state.md`, `docs/development-lessons.md`,
`manifests/artifact-sets.json` and `manifests/current-artifact.json`.
Private `E/completion.json` records ending commit/tree and changed-file hashes.

Final metadata checks executed personally on this checkpoint:

| Command | Result | Seconds |
| --- | --- | ---: |
| `python3 -O scripts/host/test-review-metadata-checkers.py` | 19 PASS | 1.982 |
| `python3 scripts/host/check-mobile-status.py` | PASS | 0.040 |
| `python3 scripts/host/check-artifact-inventory.py` | PASS | 0.062 |
| `git diff --check` | PASS | 0.025 |

The metadata suite has 19 PASS and zero FAIL/BLOCKED/SKIPPED; the three other
checks pass. The 17 final preparation/build/qualification stages above pass,
with four earlier failed attempts retained separately. All 476 earlier parsed
artifact records remain unchanged; the inventory now contains 477 sets.
These are local checks, not a new remote CI result or verification of unrelated
large/private artifacts. Exact commands/timings are in
`E/metadata-final-results.json`.
