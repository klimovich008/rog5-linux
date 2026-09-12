# Pinned engine sysroots and GN graph

The real offline ARM64 Flutter engine graph passes. This is build preparation;
engine compilation and all physical qualification remain **NOT RUN**. The pinned
Clang executable is absent. The next bounded dependency is
`fuchsia/third_party/clang/linux-amd64` at
`git_revision:80743bd43fd5b38fedc503308e7a652e23d3ec93` from the exact Flutter DEPS.

Execution used repository `6097349e29fe8ad2f62eb752a419254adc251d59`, tree
`d0bc83ce6f90a505a66103e3d3a14e6313332553`, on
`agent/review-correctness-20260912`. Repository implementation did not change;
this checkpoint adds qualification data and current pointers. Flutter source is
`d728e61e7d835e02c453c70ae9523a40f6c03215`. Source metadata matched its Git blob.
The [qualification JSON](2026-09-12-engine-sysroots-qualification.json) records
commands, input/output hashes, private collector identities and individual times.
Private raw evidence is under
`/home/deck/.local/state/rog5-arm64-sysroot-evidence-20260912-r1` (E below).

| Executed check | Result | Seconds |
| --- | --- | ---: |
| ARM64 pinned download and confined payload extraction | PASS | 10.182 |
| GN with ARM64 sysroot only | FAIL: missing AMD64 host sysroot | 1.017 |
| AMD64 pinned download and confined payload extraction | PASS | 10.240 |
| Corrected full ARM64 payload verification, 20,820 members | PASS | 5.239 |
| Corrected full AMD64 payload verification, 20,806 members | PASS | 5.084 |
| Contained libc link resolution fixtures | 2 PASS | 0.001 |
| Real network-disabled GN generation and check | PASS | 1.718 |
| Three GN target introspection commands | 3 PASS | 4.002 |

The final table contains ten successful cases and one retained failed graph
attempt; these are scoped checks, not a full repository CI count. The first
payload collector also failed at the final libc digest because the regular-file
hash helper refuses symlinks. Its log is retained; its duration was not recorded.
The corrected collector resolves only within the expected sysroot. Two fixtures
accept an inside link and reject an outside link. An initial ad hoc target
assertion also failed because it assumed one output; actual GN declares companion
TOC/unstripped outputs. The corrected receipt retains those outputs. Neither
collector mistake is hidden as a successful first attempt.

Archives are pinned by exact source metadata, downloaded in streaming 1 MiB
chunks with a 64 MiB ceiling, verified before extraction and retained on disk:

| Architecture | Compressed bytes | SHA256 |
| --- | ---: | --- |
| ARM64 | 19,204,088 | `2f915d821eec27515c0c6d21b69898e23762908d8d7ccc1aa2a8f5f25e8b7e18` |
| AMD64 | 20,781,612 | `36a164623d03f525e3dfb783a5e9b8a00e98e1ddd2b5cff4e449bd016dd27e50` |

The upstream installer was inspected but not executed: it reads the complete
download into memory and replaces an existing root. Exclusive new compiler-cache
roots were populated through the existing confined extractor, without install
hooks. A 3 GiB free-space reserve was preserved. Every archive member's content,
type and link identity was checked against the resulting tree. Readelf confirms
AArch64 target libc and x86-64 host libc. These Debian build sysroots are separate
from the authenticated Arch mobile runtime and grant no installation authority.

GN ran `/gn gen --threads=1 --check /work/out` with read-only source, no network,
512 MiB memory, one CPU and a 120-second deadline. It generated 1,647 targets from
387 files. Its warning that `angle_build_all=false` has no effect remains open;
the argument was not silently removed. The unchanged arguments hash is
`db52820a0702bf63149044f49fcccd600cee55387cd0a441d85ffafadcec3865`.
Target introspection selects `libflutter_engine.so` with
`--target=aarch64-linux-gnu`, and host `gen_snapshot` with `TARGET_ARCH_ARM64` and
`DART_PRECOMPILER`. This does not prove compiled ELF or complete runtime closure.

The collectors were invoked with `python3 E/provision.py`,
`python3 E/amd64/provision.py`, `python3 E/run-gn.py`,
`python3 E/run-gn-r2.py`, `python3 E/verify-payloads.py`,
`python3 E/verify-payloads-r2.py`, `python3 E/test-libc-resolution.py` and
`python3 E/inspect-targets.py`; E is expanded to the absolute path above.
The JSON includes exact nested extraction/container commands and collector hashes.

No phone contact, power operation, signing, candidate creation, claim operation
or protected-storage mutation occurred. Signed/installed/fallback bytes and the
headless contract are unchanged. S06/R01 remain FAIL. Earlier failures and the
previous 467 artifact entries are retained. No full board build or integrated CI
was repeated for this metadata-only checkpoint; current software qualification
does not replace the separately retained kernel and physical evidence.

Final metadata checks executed personally on this checkpoint:

| Command | Result | Seconds |
| --- | --- | ---: |
| `python3 -O scripts/host/test-review-metadata-checkers.py` | 19 PASS, 0 FAIL, 0 BLOCKED, 0 SKIPPED | 2.119 |
| `python3 scripts/host/check-mobile-status.py` | PASS | 0.064 |
| `python3 scripts/host/check-artifact-inventory.py` | PASS: 468 sets, 68 small tracked hashes | 0.064 |
| `git diff --check` | PASS | 0.032 |

The inventory check explicitly does not rehash unrelated large/private artifacts.
The new sysroot payloads have their separate full byte verification above.
Private `metadata-final-results.json` contains commands and exact timings;
`completion.json` records ending commit/tree and changed-file hashes after commit.
Changed files are this report, its qualification JSON, `configs/project-status.json`,
generated `docs/current-state.md`, `docs/development-lessons.md`,
`manifests/artifact-sets.json` and `manifests/current-artifact.json`.
