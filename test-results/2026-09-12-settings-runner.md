# Settings runner, complete assets and truthful runtime qualification

Two builds of the real Denial settings ARM64 native runner are byte-identical.
The actual GTK application object renders a 900×620 settings page under QEMU
with a software Broadway display. It shows **Settings are unavailable** because
no Denial backend is running. This is not a clean settings session, Wayland
qualification, touch test or phone observation.

Starting checkout: `c0faab37ab1bf3e4bae801e871c4f94d397e2573`, tree
`b96b694cf3500123c95fe2525fa3ec32bf9c33e8`. Implementation commits:

- `27957a4ac006508ef93795dbde4b841a57d7016c`: resolved-path asset assembly.
- `5d32efcb791c46a2a4fae2001939bed6723aed52`: Rust prerequisite selection.

The integrated active tier ran on the latter commit, tree
`6be81ffdaaf2619fa4a04ac56a9bcac2a29d1bf5`: **86 PASS, 0 FAIL, 0 BLOCKED,
0 SKIPPED, 255 NOT_SELECTED**, in 137.748 seconds. This is a personally executed
local tier, not a new remote CI result or full phone-kernel rebuild. Two earlier
attempts each produced 12 PASS, 74 BLOCKED and 255 NOT_SELECTED; both remain
retained. Their prerequisite mismatch was corrected before the final tier.

## Demonstrated fixes

The old asset fixture moved settings to `/app`. Its relative `denial_dart_shell`
root consequently resolved to `/dart_shell`, outside the mounted workspace.
Flutter emitted six valid assets but omitted dependent-package assets. The
actual startup returned zero and rendered a frame while logging unhandled
missing-logo exceptions. The new log regression rejects that result as asset
success; it accepts the corrected frame without asset exceptions.

`scripts/host/assemble-denial-flutter-assets.dart` keeps the project at its
resolved package-config location, checks every package root and refuses an
existing asset output. The actual tool rejects the relocated root before
assembly and generates 29 declared assets at the proper workspace path,
including the package logo and fonts. The new root check also found an absent
`sky_engine` mount; the already-built matching package now supplies it. This
changes `NOTICES.Z` to include SDK licenses. The other 28 corrected asset files
are unchanged. The final fixture and frame use this complete output. Previous
six-asset assembly evidence remains historical and does not establish complete
settings assets.

`scripts/host/repository-test-report.py` now checks the compiler selected through
`RUSTC`, matching the GLES test's existing behavior. The regression executes a
real fixture compiler and covers a spaced absolute override without a PATH
compiler, a missing override despite a PATH compiler, an empty override, and
the default PATH compiler. Three subcases fail before the fix; all four pass
afterward. The full report suite passes 19 tests in 1.894 seconds, retaining its
process-group, deadline and reporting checks. Invalid overrides remain BLOCKED.

## Builds and bounded runtime checks

| Executed check | Result | Seconds |
| --- | --- | ---: |
| Real plugin generation with normal template renderer | PASS | 7.533 |
| Plugin generation at corrected resolved paths | PASS; same generated files | 7.583 |
| Native runner build / fresh second output | PASS; identical bytes | 2.319 / 2.069 |
| Observer main with actual application/registrant sources | PASS | 2.119 |
| First Broadway namespace readiness | FAIL; app not launched | 8.036 |
| Initial application frame | Asset qualification FAIL despite exit 0 | 7.834 |
| Corrected package assets, prior private builder | PASS | 8.937 |
| Repository helper: relocated / correct package root | 2 PASS | 7.383 / 8.987 |
| Existing output refusal | PASS; bytes preserved | See qualification JSON |
| Final assets application frame | PASS for frame/assets; cleanup diagnostic remains | 7.886 |
| Qualified schema-cache overlay and actual frame | PASS for frame/assets/schema; cleanup diagnostic remains | 8.136 |
| Runner ELF, loader, no-display and missing-engine checks | 5 PASS | See qualification JSON |
| Missing-asset log regression, before and after | 2 PASS | See qualification JSON |

The first plugin invocation lacked `TemplateRenderer` in the source tool
context. The corrected invocation uses the same Mustache renderer as the pinned
Flutter executable. Initial compiler-internal path guesses failed; querying
GCC's `-print-prog-name` resolved and hashed the actual tools. These preparation
failures are retained, not classified as upstream application defects.

The runner compiles all three sources from the actual CMake target with its
C++14, `-Wall -Werror`, `-O3 -DNDEBUG` and application-ID settings. This is direct
affected-target compilation, not full Flutter CMake assemble/install. It uses
authenticated Arch headers/libraries because the older engine Debian sysroot
lacks the GLib API used by this application. GCC 13.3 and binutils 2.42 are
recorded from the retained builder image. The dynamic loader resolves 72 runtime
libraries whose bytes match the authenticated Arch payload tree. The unmodified
production main predictably refuses startup without a Wayland display; that
negative case is not reported as a successful session.

The visual observer changes only main: it calls the actual
`settings_application_new`, observes the real Flutter first-frame signal,
captures GTK drawing to PNG, and requests cleanup. No successful backend
responses are fabricated. The release runner binary remains separate. The
final displayed image was inspected and retains the backend-unavailable overlay.
A frame or process exit alone is insufficient to prove settings operations.

| Artifact | SHA-256 |
| --- | --- |
| Runner, both builds, 75,528 bytes | `15d69037d73f8ea0f4df03ae7bfcb829277a2c34f33fc4104f40c84eca23024c` |
| Final 34-file fixture tree, including separate observer | `66e1ec932577122b6e0ad43d5e874f755cbf28a0428fda91378d9555523d1556` |
| Final actual settings PNG | `4dc8f8e4c0d8656c2b5e576d42fc4eeb97e6c2f16f37e2ecba0481e35e019bbc` |

Denial source remains `85b2303e2f09ae7b7b993641f90061a200f03d53`; Flutter remains
`d728e61e7d835e02c453c70ae9523a40f6c03215`. Native source copies and generated
registration were checked against their inputs. Settings AOT and GTK engine
bytes are reused unchanged; no kernel, AOT or engine rebuild was needed.

Private evidence is
`/home/deck/.local/state/rog5-settings-runner-evidence-20260912-r1` (E).
The [qualification JSON](2026-09-12-settings-runner-qualification.json) contains
exact executed commands, timings, inputs, outputs, script hashes, counts and
retained failures. E/completion.json records the ending commit/tree and all
changed-file hashes. Compilers are network-disabled and bounded to 1 GiB/one CPU;
GTK fixtures use 1.5 GiB/one CPU and a 45-second runtime limit, with no host
devices or network access. The active tier uses 3 GiB/two CPUs and per-suite
limits. Heavy phases run sequentially; build/evidence scratch is disk-backed.

## Remaining issues and next step

1. **Clean GTK session FAIL:** `fl_view_dispose` calls `fl_engine_remove_view`
   for the implicit view; the actual engine rejects it as invalid. This exact
   source-level counterexample and runtime diagnostic need an affected-library
   fix/regression before claiming clean cleanup.
2. **Backend and Wayland NOT RUN:** the settings-unavailable overlay is expected
   in this fixture. Full Denial services, settings actions, real Wayland rendering
   and interaction remain unqualified. Broadway's EGL/ATK diagnostics are retained.
3. The missing GNOME schema diagnostic was resolved by mounting the existing
   qualified GSettings cache; schema sources and cache identity were checked.
4. Phone OLED, calibrated touch, Adreno acceleration and physical lifecycle
   remain **NOT RUN**. S06/R01 remain **FAIL**. No software frame closes them.

Next: fix and exercise implicit-view disposal, then qualify the complete offline
Wayland/backend path. The separately reviewed provider/display question remains
the next hardware experiment; this task grants no authority to run it. No phone
contact/operation, signing, new candidate, claim operation or protected-storage
mutation occurred. ASUS slot A, signed fallback/candidate, installed observations,
consumed claims and headless acceptance remain unchanged. All 479 prior parsed
artifact records are preserved; the inventory now has 480 sets.

Changed files across this turn: `scripts/host/assemble-denial-flutter-assets.dart`,
`scripts/host/repository-test-report.py`, `scripts/host/test-repository-test-report.py`,
`docs/development.md`, `docs/development-lessons.md`, `configs/project-status.json`,
generated `docs/current-state.md`, `manifests/current-artifact.json`,
`manifests/artifact-sets.json`, this report and its qualification JSON.

Final metadata validation after the evidence/status edits:

| Command | Result | Seconds |
| --- | --- | ---: |
| `python3 -O scripts/host/test-review-metadata-checkers.py` | 19 PASS | 1.908 |
| `python3 scripts/host/check-mobile-status.py` | PASS | 0.040 |
| `python3 scripts/host/check-artifact-inventory.py` | PASS | 0.063 |
| `git diff --check` | PASS | 0.025 |

Metadata regression counts: 19 PASS, zero FAIL/BLOCKED/SKIPPED; the three
other checks pass. The active tier was not repeated for this metadata-only
checkpoint. E/metadata-final-results.json preserves exact commands and timings.
