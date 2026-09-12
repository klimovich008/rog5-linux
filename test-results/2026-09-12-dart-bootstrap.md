# Pinned Dart bootstrap and SDK package metadata

The pinned bootstrap Dart SDK and DevTools package verify. The actual pinned SDK
metadata generator now resolves 193 local package roots offline. Complete host
SDK compilation, mobile shell pub resolution and shell AOT remain **NOT RUN**.
The existing engine build continues with its original source/cache inputs.

Execution source: repository `497fba3bb255f3767bc663e2ecc810b608164860`, tree
`2ba8c3aff3ed2fe9d14b97545dad39dc6d33421c`. Flutter is pinned at
`d728e61e7d835e02c453c70ae9523a40f6c03215`, Dart source at
`d684a576a6aa954ae107a03b2b4e1d61c3bebe93`. Its bootstrap SDK is deliberately a
separate DEPS pin: `9ac06cdd18015c83a25921e26912c96e3fbe22c2`, version
`3.12.0-210.1.beta`. It is not presented as the completed lock-matched SDK build.

| Personally executed stage | Result | Seconds |
| --- | --- | ---: |
| Bootstrap SDK deployment | PASS | 27.513 |
| SDK instance digest and 1,013 payload members | PASS | 4.204 |
| DevTools deployment | PASS | 4.502 |
| DevTools instance digest and 515 payload members | PASS | 0.652 |
| Bootstrap executable version, final metadata run | PASS | 0.004 |
| Actual offline SDK metadata generation | PASS | 0.777 |
| All 193 generated roots and package identities | PASS | 0.294 |

These seven final scoped stages pass. Earlier failures remain separate:
the rootless OCI runtime rejected a copy-on-write mount (exit 126, 0.251 s);
the first actual generator run found missing `devtools_shared` (exit 255,
0.776 s). Two preparer attempts incorrectly assumed a new/empty DevTools mount
directory, which actually contains a tracked README; neither launched a container.
An initial collector incorrectly required a `lib/` directory for every workspace
entry. Those preparer/collector timings were not recorded. No failure was relabelled.

Private evidence is
`/home/deck/.local/state/rog5-dart-bootstrap-evidence-20260912-r1` (E).
The [qualification JSON](2026-09-12-dart-bootstrap-qualification.json) contains
exact commands, source/tool hashes, pins, timings, retained failures and the live
engine observation. Collectors invoked were `python3 E/install.py`,
`python3 E/verify.py`, `python3 E/devtools/install.py`,
`python3 E/devtools/verify.py`, `python3 E/run-package-config.py`,
`python3 E/run-package-config-r2.py`, `python3 E/run-package-config-r3.py`, and
`python3 E/verify-package-config.py`, with E expanded to the absolute path above.

| Package | Immutable instance | Archive SHA256 |
| --- | --- | --- |
| `dart/dart-sdk/linux-amd64` | `kQHO7IWSgyqTlMF5sQShwKsh_v2nhtDq94BMQSmIfYUC` | `9101ceec8592832a9394c179b104a1c0ab21fefda786d0eaf7804c4129887d85` |
| `dart/third_party/flutter/devtools` | `jnk4ozU2qzyHPF9kkEliL7v7blRhxhor4rTTcud5yd4C` | `8e7938a33536ab3c873c5f649049622fbbfb6e5461c61a2be2b4d372e779c9de` |

Archives contain 247,107,423 and 30,986,312 bytes respectively. Each digest was
independently matched to its SHA256-encoded CIPD instance, and each deployed
payload member was verified with streaming hashes or exact contained link targets.
Upstream attestations are retained; their signatures were not independently
verified. DevTools is pinned by both Flutter and Dart DEPS at
`fa063f322c03cc7a690d819db124c196a69cff56`. A scan of declared root overrides and
workspace entries identified it as the only missing declared local package path.

After the unsupported overlay mount, a bounded private source copy preserved
76,698 files / 476,128,656 regular-file bytes in 31.854 s, excluding Git metadata.
The actual generator ran there with the pinned SDK and DevTools mounted read-only,
no network, a fresh pub cache, one CPU, 1 GiB memory and a 120-second container
deadline. No original source or active engine input was changed. The generator's
own child deadline was 90 seconds; output and disk-reserve guards remained active.
The original Dart checkout still passes its tracked-source cleanliness check.

The resulting package metadata has 193 unique local roots. Their identities and
192 original/copy pubspec hashes match; DevTools comes from the independently
verified package. Eleven workspace entries have no `lib/` directory; their names
and presence flags are retained. Root resolution is therefore qualified without
claiming complete package compilation. Nested Git pins were not independently
revalidated in this checkpoint. No generated metadata has been installed into
the running engine's source cache.

At the retained live observation the original engine container
`d49de96af625ecb05244dca8aba6a9c6f4fef5065080e23bf196ec59a8013e03`, exec session
`98288`, had completed 1,980 of 6,674 steps. Its terminal receipt remains
`/home/deck/.local/state/rog5-engine-clang-evidence-20260912-r1/build-r1/compile-result.json`.
Poll that actual owner/receipt before continuation; never restart from this
historical observation. Its 30-minute segment deadline and output cache remain.

The previous turn was progress. This turn adds actual SDK dependencies and
successfully executes a previously blocked generation step. The useful correction
is to inspect declared dependency paths together, and distinguish legal workspace
metadata from library compilation. Do not require a mount target to be empty:
a read-only namespace mount can shadow a retained README without deleting it.

No phone contact, signing, claim operation, candidate creation or protected-storage
mutation occurred. ASUS slot A, accepted server/rescue and signed fallback/candidate
bytes remain unchanged. S06/R01 remain **FAIL**, mobile physical rows **NOT RUN**.
No unchanged full board build or integrated CI was repeated for this metadata-only
checkpoint.

The first engine segment subsequently reached its 1,800-second deadline:
**FAIL**, exit 137 from the explicit timeout, duration 1,800.256 s. Its container
was confirmed absent before continuation. The output cache was retained; Ninja
then reported 3,924 remaining steps instead of repeating the original 6,674.
The new segment uses two workers/two CPUs with the same 4 GiB memory ceiling,
network prohibition, 30-minute segment deadline and disk-reserve guard.

The current observed owner is
`7c1168c3e0b12c08cd3257120a36d654bb36d8c9047ecf0716dd7055370b7cc0`, exec session
`45465`. Its terminal path is
`/home/deck/.local/state/rog5-engine-clang-evidence-20260912-r1/build-r1/compile-r2-result.json`.
The continuation collector is the sibling `compile-r2.py`; its hash and current
observation are in the qualification JSON. The first pre-launch guard failed
because Podman removed the old CID file during `--rm` cleanup. That failure is
retained. The corrected guard queries the actual container ID from the retained
live observation and refuses a present or uncheckable owner. It does not infer
termination merely from a missing CID file. Flutter/Dart/Skia pins and tracked
cleanliness were rechecked before launch. No engine-build PASS is claimed.

Final metadata regressions: `python3 -O scripts/host/test-review-metadata-checkers.py`
passed 19 cases in 2.370 s, with zero FAIL/BLOCKED/SKIPPED. Status, inventory and
diff checks also passed; their commands and timings are retained in
`E/metadata-final-results.json`. Final status/inventory/diff checks after the
continuation update are in `E/integration-final-results.json`. The inventory has
471 sets; all previous 470 parsed entries are unchanged. Its 68 small tracked
hash checks do not rehash unrelated large/private artifacts.

Changed files: this report, its qualification JSON, `configs/project-status.json`,
generated `docs/current-state.md`, `docs/development-lessons.md`,
`manifests/artifact-sets.json` and `manifests/current-artifact.json`.
Private `E/completion.json` records ending commit/tree, changed-file hashes and
the latest observed engine owner. This checkpoint is progress toward the goal;
it does not complete the engine build or physical acceptance.
