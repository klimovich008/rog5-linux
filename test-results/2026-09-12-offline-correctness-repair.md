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
preserved. This report is in progress; final integrated evidence is pending.

No phone operation, authentication, signing, claim operation, installation or
protected-storage mutation is authorized or executed by this repair. All new
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

Forty patches are classified into disjoint, ordered production (14) and diagnostic
(26) series. Unlisted, duplicate and overlapping entries are rejected. The board
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
