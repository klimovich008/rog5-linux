# Offline correctness and qualification repair

The project-directory checkout remains on `agent/linux-recovery-host` at
`91334dcb9ef26f21a66fe55a4ae843d8cc218d7c` (2026-08-09), with pre-existing
user changes. It is an older, separate object store and does not contain the
reviewed September commit. Following the local AGENTS handoff, development uses
the latest progress source in a separate worktree.

Integration starts at `8953632620b8a1a8d5a27d40035b0c825d9d873e` on
`agent/review-correctness-20260912`. The reviewed four runtime/panel files still
matched `4bd1a817618c0dbfdf4b96d391fbf53d50c37dc7`; fixes are applied in a separate
worktree. The integration base is 147 commits beyond the audited SHA, with changes
in 64 files (mainly retained progress, composition and input development); none
of those four reviewed defect sources changed. The dirty original checkout and all frozen artifact worktrees remain
preserved. Source fixes are implemented; final integrated evidence is pending below.

No phone operation, authentication, production signing, real claim consumption,
installation or protected-storage mutation was executed by this repair. Offline
fixtures use disposable synthetic records. The first integrated run unexpectedly
read retained host claim metadata through an old fixture; transport was mocked
and no dispatch or claim mutation occurred. That fixture now forbids retained
claim-path access. All new
physical results remain **NOT RUN**. Source changes do not modify retained signed
candidate bytes. Historical S06 and R01 remain **FAIL**.

The existing GitHub run 34426767002 completed successfully at the reviewed
4bd1a817 commit with all four jobs passing. This is imported, independently
read-only-verified CI status, not CI run against the current fixes. Historical
pending-CI prose remains historical. Retained r131/r132 runtime observations show
the corrected shutdown helper hash `fc1ce027c20679a1d18200858e216c106c0fa690224de26e3705c105fda67860`;
the claim that the currently observed runtime still used the old shutdown is
stale. That observation neither qualifies physical shutdown nor verifies every
installed archive byte.

## Screen transitions

Both requested DPMS failures reproduced against the unchanged historical source:
helper status 42 became script status 0 with a success state. The corrected script
propagates that failure and leaves state unknown. It locks the complete transition,
reconciles against current brightness/reported DPMS, and bounds helper execution.
Thirteen semantic regressions pass, including concurrent toggles and interruption;
the retained idempotence test also passes. The final focused run took 3.912 seconds.

An absent optional helper remains an explicitly labelled backlight-only operation.
`DISPLAY_POWER_MODE=required` refuses absence; `backlight-only` deliberately skips
DPMS. A helper acknowledgement without readback is UNVERIFIED. Kernel-reported
DPMS is labelled as reported state, never optical proof of panel power.

The optional legacy screen composition still consumes this helper. The current
retained IOMMU payload was streamed read-only: all 736 members were enumerated and
none are screen-toggle/status-screen/power-buttond. Archive identity is
`dc805f639acd6295138324ecb7e5c687d6d51e2e982509f0ba4e9835c4d9977b`.
Thus this source repair is not already active in that prepared payload.

## Independent policy scope

The storage predicate regression executes extracted kernel code over 98,304
combinations. DATA_WRITE bypasses filtering; parent-disk writes and privileged
SG_IO are not kernel-contained to a partition. No storage-kernel behavior changed.
See [trust boundary](../docs/storage-trust-boundary.md).

The [mobile proposal](../docs/mobile-power-policy.md) is uninstalled and cannot
acknowledge health or authorize a trial. Its nine bounded host fixtures pass;
capacity/energy and current telemetry qualification remain unresolved.

## Boot-health protocol

The failing-before integration used the real C helper and persistent record:
a timer-stop error left persistent healthy state, and the next decision selected
the primary. The repair removes timer cancellation from finalization. Both
rollback timers stay armed; the automatic probe's timer now invokes the same
receipt-aware rollback path. Manual one-shot probe deadlines are unchanged.

A complete, current-boot mode-0444 RAM receipt is published before durable
acceptance. Helper operations serialize on the stable state directory. Rollback
can fence a pending attempt as failed; that fence prevents a later healthy
commit. Invalid RAM evidence rejects even persistent healthy state. Ordinary
accepted persistent boots still rearm as pending and require a fresh ack.

| Observed protocol point | Rollback / next selection |
| --- | --- |
| No complete RAM receipt, or pending durable state | Fence failed; next selection is fallback |
| Both receipts committed | Suppress rollback; next normal boot still requires fresh acknowledgement |
| Reported publication/commit failure | Reject attempt; next selection is fallback |
| SIGKILL before durable acceptance | Armed timer can fence and select fallback |
| SIGKILL after both receipts commit | Acceptance remains valid even without a printed PASS |

Fault tests inject actual helper write/fsync/rename failures, RAM creation and
publication failures, stale boot/trial identities, duplicate bundle tokens,
interruptions and timer races. Timer stop/inactivity operations no longer occur;
hostile fixtures prove they are not relied on. A later fixture audit exposed
that metadata mocking hid wrong modes/hardlinks; it now substitutes ownership
only and exercises actual mode/link checks.

The new immutable helper v3 is 67,520 bytes, SHA
`e73d7fe773bbdbc26ca3b10e0e5ebce5672a83cd48ec8baaef762bb5efb2ca0d`.
Two bounded ARM64 builds matched. Old v1/v2 artifacts remain unchanged; this is
a build dependency, not a newly signed phone candidate. The old installed loader
refuses unknown failed state and selects its signed fallback. No installed
behavior is qualified here. Host filesystem error injection does not prove
power-loss durability or durable rejection when storage refuses every write.

## Client disconnects and artifact metadata

Healthd previously traced back for real TCP resets before headers, after headers
and during body transmission. All three failed before the scoped connection-error
handling change. The nine-test suite passes after it; every disconnect case also
checks that a subsequent health client succeeds. Other unexpected server errors
retain their normal diagnostic path.

The artifact inventory covers registered/tracked sets and the explicit current
private candidate, with unknown build provenance marked BLOCKED. It does not
claim a complete scan of unregistered private evidence. Historical LPG bytes
remain unchanged; an executable regression confirms the active composer rejects
the old module. Large recorded hashes are identified as recorded, not newly
rehash-verified. See [retention policy](../docs/artifact-retention.md).

## Reporting and mobile scope

The reporter's independent review reproduced and fixed masked exit42, a missing
interpreter without a receipt, and a second signal interrupting cleanup. Metadata
validators also retain semantic checks under Python `-O`. A temporary adversarial
status fixture promoted S06/R01 without evidence; the status validator now refuses
that promotion, and physical PASS needs a matching exact-candidate receipt.

The private-profile reader rejects duplicate fields, symlinks and unsafe modes.
The new mobile policy consumes it and binds supplied topology/runtime identity.
Historical sealed controllers and claim records keep their original bytes;
this is not a wholesale migration of those legacy interfaces.

The mobile package lock records 312 ARM64 packages and 1,411 dependency edges,
with exact versions and repository/archive identities. It is **BLOCKED** for
shipping: retained repository integrity/signature issues, unverified package
archives and missing ARM64 Flutter engine/AOT/assets remain explicit. No ordinary
Plasma desktop or remote development service is counted as mobile-shell proof.
The non-root session and five physical trial plans are prepared, not installed
or armed. All mobile physical rows remain NOT RUN.

## Panel correctness and exact-base scope

The extracted actual driver and the pinned DRM core reproduce failed preparation
followed by enable/backlight transactions, and powered-off hardware retained as
prepared after off-command errors. The repaired driver serializes lifecycle and
brightness callbacks, tracks successful initialization and each owned regulator
reference, and rejects transactions after failed preparation. Successful physical
power removal clears the core lifecycle even when an earlier DSI command failed;
a regulator-disable failure retains the references needed for a later retry.

The brightness finding is confirmed independently of its proposed wording. The
vendor's inverted-DBV transform followed by its low-byte-first helper actually
emits high byte first. The corrected source uses the exact kernel's large DCS
brightness helper. Executable vectors cover 0, 1, 255, 256 and 1023, and restore
original DSI flags after success and errors. Fifteen behavioral cases cover the
actual extracted callbacks, exact core lifecycle behavior, faults and concurrency.
The old implementation fails the new cases; artifact hash matching alone is not
counted as behavioral proof.

An ARM64 affected-driver compile on the exact base passed separately. That check
uses defconfig plus the panel, and is not the real merged board build. Full board
qualification is recorded separately below. Physical scanout, brightness and
regulator behavior remain NOT RUN.

The duplicate reset assertion, 28 ms delay TODO, DSC slice TODOs and generated
copyright FIXME remain unresolved. They were not changed without vendor evidence.
The inherited zero-size memory tuple is retained; exact kernel code skips that
empty region, but its original board-memory rationale is not established.

## Build and CI changes

Forty-one patches are classified into disjoint, ordered production (15) and
diagnostic (26) series. Unlisted, duplicate and overlapping entries are rejected. The board
builder verifies the pinned commit and archive, freezes every source/config input,
merges seven fragments, checks resolved mandatory/forbidden symbols, and builds
Image, modules and five required DTB/DTBO targets with W=1. Generated metadata,
module closure, firmware inventory, schema results and output hashes remain
separate from admission or physical qualification. This output is unsigned and
is not a new phone candidate.

The board job is path-scoped and has a 90-minute deadline: the first cold two-job
build exceeded 38 minutes before linking and schema checks. Its inherited ARM64
defconfig includes unrelated GPU modules; narrowing that configuration needs a
separate measured review. An exact-input cache or incremental check should reuse
unchanged objects. No running compile was restarted merely for progress prose.

The display builder now publishes one atomic DTB/provenance directory and refuses
to overwrite it without an explicit replace option. A separate reviewed overlay
uses named binding constants; the sealed historical overlay stays unchanged.
Warnings are visible, binding/schema checks are required for publication, and
missing schema tools cannot produce PASS. Actual schema validation used
dtschema 2026.6; fixture checks are labelled separately.

All third-party Actions are pinned to verified full upstream commits. The CI jobs
record package/tool environments, retain JSON/JUnit results and preserve board
metadata/logs on failure. The historical V27 candidate-publication check retains
its non-authoritative scope. Generic ARM64 QEMU still proves userspace/initramfs
behavior only. GitHub branch protection and CODEOWNERS expectations are prepared;
no repository settings or remote branches were changed by this repair. A pinned
build-container digest is not established; recorded tool environments are not a
claim of a hermetic toolchain.

## Final board result and provenance

**Compilation PASS; production qualification FAIL.** The exact 7.1.4 base is
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. All 15 production patches apply with
`git apply --check` and the merged board configuration resolves unchanged.
The final fresh application/configuration check took 58.799 seconds. The real
Image, 1,031 modules and five DTB/DTBO targets compiled; the AMS678 module is in
the recorded module inventory. Real modpost, corrected `depmod -ae`, vermagic
and dependency closure checks passed. The cold compile took 4,457.016 seconds;
its raw wrapper FAIL remains preserved. Later wrapper regressions corrected an
early kernel-release lookup and module-name normalization without repeating the
cold compile. A 25.220-second incremental check preserved compiled bytes.

The final schema run took 81.658 seconds and emitted one real diagnostic despite
make exit 0: `rsc@18200000 (qcom,rpmh-rsc): 'power-domains' is a required property`.
The gate detects it and fails. Patch 0041 resolves the two ASUS root compatibility
diagnostics from the earlier run without changing any DTB bytes. The remaining
property deletion accompanies a disabled PSCI domain provider in historical
source. Restoring that reference alone would obstruct RPMh probing. Its binding
versus CPU_PM fallback conflict remains unresolved; no generic schema relaxation
or unqualified power-management change was made.

The reviewed W=1 warning policy binds exact diagnostic sites, source/header hashes,
configuration values and occurrence ceilings. Unknown diagnostics still fail.
757 module-declared firmware names are inventoried; presence is NOT RUN. Full
board overlays are compiled individually. A separate composed display-binding
check passed, but this is not a composed, signed, admitted boot artifact.

The final build input binding is source `13c03247088f6ab117909c5af71e19cee75056fd`,
tree `dc395ae3e16cd1cf8ebb43b211f3b500d61a1c19`, covering 59 inputs. It distinguishes
the initial dirty execution from later byte-for-byte committed source binding.
The original compile used the same driver C; a later patch correction changed
only two descriptive geometry numbers, and 0041 changes only binding metadata.
All output and module identities were checked unchanged after schema validation.
See [machine-readable board result](2026-09-12-production-board-build.json) and
[artifact pointer](../manifests/current-artifact.json) for exact hashes and private
raw-provenance references. Registered/tracked artifact inventory now has 442 sets.

| Output | SHA-256 |
| --- | --- |
| Image | `0789c10855e74c2f54caee7437864235f5872118e9f697782cc8547b286d406a` |
| Merged config | `277bc74e104bcdec8e6eda8a345e2a4e7bb15be5118bb829741742e97d8a174c` |
| Ordered production series | `1544f250a9e0305071e4eab6f5082f0ed3f369dbdc257d532b7e195dcb98ff08` |
| Module metadata | `ce75c8c580c82a96cf5b2731c363c91d07f22992f52a893d099c85c97d636a1b` |
| Final board provenance | `b4e9b22be52dda512416ba4313cb8ee78e458c99685bea67ee4ab76e2fc7a999` |

## Remaining limits and next experiment

1. Production qualification remains FAIL at the RPMh RSC schema conflict. Resolve
   the binding and CPU_PM/PSCI topology deliberately before admission; the accepted
   rescue and headless power policy remain unchanged.
2. Physical panel/brightness, touch binding, A660 rendering, charging, suspend and
   cleanup remain NOT RUN for these source fixes. Touch remains disabled; compiling
   EDT FT5X06 does not establish FTS3658U support. S06 and R01 remain historical FAIL.
3. Mobile packaging is BLOCKED by repository/signature/archive integrity and
   missing ARM64 Denial runtime assets. Encryption, bootloader/lock-screen threat
   model, signed-update rollout and daily-device security need qualification.
4. Unregistered private artifact sets and missing old build/toolchain provenance
   remain BLOCKED. Installed archive identity is not established by a runtime
   observation. The new inventory grants no authority to select an old artifact.
5. Active mobile policy uses an ignored private profile. Legacy sealed controller
   interfaces retain embedded identity bindings; wholesale migration is not claimed.
   GitHub protection is documented, not remotely enabled; container digest and
   complete licensing/redistribution provenance remain unresolved.
6. Duplicate reset assertion, 28 ms delay, DSC slice TODOs, generated copyright
   attribution and zero-length memory tuple rationale remain explicit source issues.

The next smallest **future** physical question is whether the corrected panel
shows a stable 60 Hz pattern with correctly ordered brightness levels and clean
blanking. It requires a separately authorized exact-artifact composition and
fully prepared recording/abort/recovery session. The existing signed 136f candidate
lacks these fixes. No claim, candidate, signing operation, readiness countdown or
phone action was created by this plan. Safe display/touch source work need not
wait for unrelated server milestones.
