# Pinned Clang verified; actual ARM64 engine compilation started

The exact compiler is available and verified. The real engine build has started;
it has **not passed**. A live observation records completed step 75 of 6,674,
container `d49de96af625ecb05244dca8aba6a9c6f4fef5065080e23bf196ec59a8013e03`,
exec session `98288`, and a running, non-OOM-killed process. This is an as-of
observation, not permission to restart a build from this paragraph.

Private evidence is in
`/home/deck/.local/state/rog5-engine-clang-evidence-20260912-r1` (E).
Inspect `build-r1/compile-result.json` for a terminal result, otherwise poll the
recorded live container/session. An observation timeout is not termination.
The existing output directory is `E/build-r1/out`; retain it for incremental
continuation after the current owner is demonstrably terminal.

Repository execution source is `a934418f6edfa98abb29832239aadf9e714b4cb7`, tree
`317fa68436e6cbd1eada1fcbd1e1e703cb9da3ee`. Flutter remains pinned at
`d728e61e7d835e02c453c70ae9523a40f6c03215`; its tracked source is unchanged.
Compiler deployment is private host build tooling, not an Arch mobile package,
phone image, production signature or installed candidate.

| Personally executed check | Result | Seconds |
| --- | --- | ---: |
| Immutable CIPD package deployment | PASS | 54.527 |
| Package digest and all 4,118 deployed members | PASS | 12.404 |
| Exact compiler revision execution | PASS | 0.215 |
| Real GN graph with compiler mounted read-only | PASS | 1.868 |
| Ninja input preflight, 6,674 steps | PASS | 0.766 |
| Actual engine and host AOT compilation | RUNNING at recorded observation | incomplete |

These five completed checks have 5 PASS, 0 FAIL, 0 BLOCKED and 0 SKIPPED.
They do not include an engine-build PASS. The graph's existing ineffective
`angle_build_all=false` warning is retained. The prior missing-compiler blocker
is resolved; historical results remain unchanged.

The source DEPS pin resolves to package
`fuchsia/third_party/clang/linux-amd64`, instance
`LLHJM3zpP8SMJFN354aXWHO3JoSHDFdhCcLMCDAQSwkC`, LLVM revision
`80743bd43fd5b38fedc503308e7a652e23d3ec93`. The 521,383,634-byte package hash is
`2cb1c9337ce93fc48c245377e786975873b72684870c576109c2cc0830104b09`, independently
matched to the SHA256-encoded instance ID. Every deployed archive member was
verified with streaming hashes or exact symlink targets; resolved links remain
inside the compiler root. CIPD-generated metadata is separate from package
payload. Upstream VSA data is retained; its signatures were not independently
verified.

Clang, LLD and LLVM archive/object utilities use the package's multicall binary,
SHA256 `a50ded9e62bb90048748f46106e31bf57f3e5262c5ab93134db9d8f082e89c4b`.
The executable reports `Fuchsia clang version 23.0.0git` and the exact LLVM pin.
The [qualification JSON](2026-09-12-engine-compiler-qualification.json) includes
commands, collector hashes, tool/image identities and the live observation.

Executed collectors were `python3 E/install.py`, `python3 E/verify.py`,
`python3 E/preflight.py` and `python3 E/compile.py`; E expands to the absolute
path above. Acquisition used CIPD's immutable instance and a new private root.
The compile command is
`ninja -C /work/out -j1 libflutter_engine.so clang_x64/gen_snapshot` in the
retained builder image, with source and compiler read-only, network disabled,
one CPU, 4 GiB memory with no additional swap, a 32 MiB log bound and a
1,800-second build-segment deadline. A 4 GiB free-space stop preserves the
required 3 GiB reserve. The collector owns cleanup and records failure on a
deadline/resource stop. It does not silently restart or discard output objects.

The previous turn was progress: authenticated sysroot payloads and a real GN
graph changed the next dependency. This turn closes that compiler dependency
and performs actual compilation. No full sync or unchanged board build was
restarted. A dry-run input check is now explicitly separated from compiler
execution and final linking; it cannot stand in for either.

No phone contact, signing, claim operation, candidate creation or protected-storage
mutation occurred. Mobile physical tests remain **NOT RUN**, S06/R01 remain
**FAIL**, and accepted/signed/installed/fallback artifacts are unchanged. Complete
engine/ICU/AOT closure, native session, touch and GPU physical qualification are
still unresolved. This checkpoint changes only provenance and current-state
metadata; full integrated CI is not repeated for it.

Final metadata validation: `python3 -O scripts/host/test-review-metadata-checkers.py`
passed all 19 cases (2.370 s, zero FAIL/BLOCKED/SKIPPED).
`python3 scripts/host/check-mobile-status.py` passed in 0.065 s;
`python3 scripts/host/check-artifact-inventory.py` passed in 0.115 s with 469 sets
and 68 small tracked hashes; `git diff --check` passed in 0.032 s. The previous
468 parsed inventory entries are unchanged. These checks do not rehash unrelated
large/private artifacts; the compiler has separate complete payload verification.
Exact commands/timings are in `E/metadata-final-results.json`.

Changed files: this report, its qualification JSON, `configs/project-status.json`,
generated `docs/current-state.md`, `docs/development-lessons.md`,
`manifests/artifact-sets.json` and `manifests/current-artifact.json`.
Private `E/completion.json` records the ending commit/tree, file hashes and latest
live build observation after commit. It is checkpoint completion, not goal or
engine-build completion.
