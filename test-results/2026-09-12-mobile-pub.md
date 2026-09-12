# Locked mobile shell and settings package archives

All 84 distinct hosted package/version pins from the existing Denial mobile shell
and settings lockfiles are now retained and verified: **84 PASS, 0 FAIL,
0 BLOCKED, 0 SKIPPED**, 51,229,183 bytes in 45.388 s. Package resolution, SDK
closure and shell AOT compilation remain **NOT RUN**. These archives are build
inputs; they are not a completed pub cache, installed phone software or proof of
a usable shell.

Execution source: repository `dc9c7a23cf03ff483bcabfa872ce8fd1a252d56e`, tree
`3b0ab846f6a4cea28b67eadd5c0ff07c2a0e7942`. Denial source remains
`85b2303e2f09ae7b7b993641f90061a200f03d53`, verified clean before acquisition.
No tracked source, lockfile or active engine input changed.

| Locked input | Hosted rows | SHA256 |
| --- | ---: | --- |
| `dart_shell/pubspec.lock` | 75 | `a1ac5efa8a9458e3f761b39a76a639bc7740fcf5070f9908734b30481ecad604` |
| `settings_app/pubspec.lock` | 76 | `eda67da1b3f4e50eecb5820d835dd5ba8bc002bfd3c64cb2e406988b9e54a3f7` |

The union retains different versions where the two applications pin them; it
does not update or collapse either lockfile. SDK dependencies and local path
dependencies are enumerated separately in the
[qualification JSON](2026-09-12-mobile-pub-qualification.json). Matching Flutter
SDK/generated artifacts and actual pub resolution still need their own evidence.

Private evidence is
`/home/deck/.local/state/rog5-mobile-pub-evidence-20260912-r1` (E).
The executed command was `python3 E/fetch.py`, with E expanded to that absolute
path; the JSON records the collector hash and each exact API/archive URL, pin,
hash, byte count, package identity and duration. API metadata was retained and
had to agree with the existing lockfile digest. Every downloaded archive was
stream-hashed before accepting it, then its contained `pubspec.yaml` name/version
was checked. No package was extracted into a runtime or executed. Authentication
here is agreement with the pinned source lock, not an independently signed
package-freshness or mobile-update guarantee.

Acquisition used one request stream at a time, 1 MiB chunks, bounded metadata,
64 MiB per archive, 512 MiB total downloads, 20-second network timeouts and a
900-second overall deadline. Archive inspection bounded member count and expanded
bytes. Disk checks stopped before the 3 GiB reserve could be consumed. Downloads
went to a new private directory and were fsynced before publication; no old cache
or source tree was replaced. The collector used PyYAML 6.0.2.

The same engine build was verified live through its actual container, rather
than inferred from a RUNNING note. At the retained observation it had completed
571 of 6,674 steps, with 286,261,248 bytes peak cgroup memory and zero OOM events.
Container `d49de96af625ecb05244dca8aba6a9c6f4fef5065080e23bf196ec59a8013e03`
and exec session `98288` remain the recorded owner. Its terminal receipt is
`/home/deck/.local/state/rog5-engine-clang-evidence-20260912-r1/build-r1/compile-result.json`.
Poll that owner or receipt before any continuation; retain the incremental
output cache and never start a duplicate from this historical paragraph.
Compilation has no PASS result at this checkpoint.

The previous turn was progress, and this turn independently prepared actual
locked shell inputs while the build continued. Observed compiler memory is low,
but the sampled early Skia phase does not bound later Dart or LTO linking. Keep
the memory/disk guards. A reviewed two-worker continuation can be considered
after the existing owner is terminal; do not interrupt or restart it merely to
change a status update.

No phone contact, signing, claim operation, candidate generation or protected-
storage mutation occurred. ASUS slot A, the accepted server/rescue baseline,
signed fallback/candidate and consumed claims remain preserved. S06/R01 remain
**FAIL** and all mobile physical rows remain **NOT RUN**. This metadata checkpoint
does not repeat the unchanged board build or full integrated CI.

Final checks executed personally on this checkpoint:

| Command | Result | Seconds |
| --- | --- | ---: |
| `python3 -O scripts/host/test-review-metadata-checkers.py` | 19 PASS, 0 FAIL/BLOCKED/SKIPPED | 2.369 |
| `python3 scripts/host/check-mobile-status.py` | PASS | 0.065 |
| `python3 scripts/host/check-artifact-inventory.py` | PASS: 470 sets, 68 small tracked hashes | 0.115 |
| `git diff --check` | PASS | 0.032 |

The previous 469 parsed artifact entries are unchanged. Inventory validation
does not rehash unrelated large/private artifacts. New package archives have
their separate download-byte verification above. Exact final check commands
and timings are in `E/metadata-final-results.json`.

Changed files: this report, its qualification JSON, `configs/project-status.json`,
generated `docs/current-state.md`, `docs/development-lessons.md`,
`manifests/artifact-sets.json` and `manifests/current-artifact.json`.
Private `E/completion.json` records ending commit/tree, changed-file hashes and
the latest actual build-owner state. That receipt closes this checkpoint only;
the engine build and real-phone goal remain incomplete.
