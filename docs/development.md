# Development loop

Start at [current state](current-state.md). Work on one question and choose the
cheapest artifact that changes its answer. Historical profile names are not
the active server. In particular, `power-usb-active.json` and its generated
lock still describe the older NFS observer track; they are kept for its
regression/publication contract, not current installed-selector identity.

## Offline qualification and reporting

The public `test-repository-linux.sh` tier commands are preserved. Test execution
policy is declared in `configs/repository-tests.json`; the retained shell
selection is checked against its tier membership during this incremental
migration. Every selected suite has a deadline, required inputs/prerequisites,
resource classification and an explicit Python optimization/source requirement.
Only reviewed isolated suites run concurrently; the default remains two workers,
bounded by CPU affinity/quota and `ROG5_TEST_WORKERS`. Network, namespace,
high-memory and shared-state work runs serially.

The runner writes per-suite logs plus `summary.json` and JUnit `summary.xml` under
`build/test-reports/` (or a fresh `ROG5_TEST_REPORT_DIR`). Missing mandatory inputs,
unexpected skips, failures and deadlines fail the tier. An early failure leaves
unreached selected suites BLOCKED and unrelated suites NOT_SELECTED. Declared
optional subchecks remain visible separately. Cleanup terminates ordinary test
process groups, including background descendants; this is not containment for
arbitrary daemons that deliberately create another session.

Panel identity, exact-base application, affected-driver compilation, executable
lifecycle behavior and physical validation are separate results. Generic ARM64
QEMU covers userspace/initramfs behavior. It cannot prove SM8350 panel, touch,
GPU, charging or PMIC behavior. The exact production board job is selected for
kernel/DT/build changes; unrelated userspace/documentation work does not require
a full phone-kernel rebuild. Build failures and schema diagnostics must remain
visible even when an unsigned Image was produced.

The mobile package graph checker validates metadata by default. The original
`mobile-package-closure.json` remains a historical graph; select the current
snapshot explicitly through the graph reference in `manifests/current-artifact.json`.
To audit cached archives against the September 12 snapshot without downloading
or installing anything:

```sh
python3 -O scripts/host/check-mobile-package-closure.py \
  --graph packaging/arch/mobile-package-snapshot-20260912.json \
  --archive-dir "$PACKAGE_CACHE" --keyring "$RETAINED_PUBLIC_KEYRING" \
  --trusted "$RETAINED_TRUSTED_KEYS" --revoked "$RETAINED_REVOKED_KEYS" \
  --report build/new-mobile-archive-audit.json
```

Use a disk-backed TMPDIR. The output must be new. Archive audit exit codes are
0 for all requested archives verified, 1 for failed verification and 2 for
missing inputs/tools. JSON enumerates every pinned package. PASS covers archive
size/hash, detached signature hash and GPG verification, explicit signer trust
and revocation, and signed `.PKGINFO` name/version/architecture/dependencies/
provides. It grants no installation authority. Newer cached revisions are not
substitutes for missing pins. The retained graph and historical verification
fields are unchanged; archive receipts bind their exact graph and trust inputs.
Keyring observation, repository selection and engine/AOT closure require
separate evidence. `--trusted` is a direct primary package-signer allowlist,
not a GPG web-of-trust evaluator. It accepts full uppercase fingerprints with
`:4:`, `:5:` or `:6:` record syntax; those values do not cause trust-chain
evaluation. Revoked files use one full fingerprint per line. Comments start
with `#`. No host keyring or network key lookup is used.

[Arch Linux ARM's published policy](https://archlinuxarm.org/about/package-signing)
signs packages and intentionally does not sign repository databases. Preserve
raw database hashes and malformed records, validate the selected dependency
graph against signed package metadata and libalpm, and describe HTTPS snapshot
selection separately from package authentication. Missing upstream database
signatures are not an obtainable prerequisite. This does not establish
cryptographic freshness/anti-rollback or grant signed mobile-update authority.
For an isolated ABI test tree, `scripts/host/materialize-mobile-runtime.py`
requires `--graph`, `--cache`, `--keyring`, `--trusted`, `--revoked` and a new
`--output` directory. It repeats authentication, preflights archive paths and
conflicts, then extracts payloads through a network-isolated bubblewrap sandbox.
It retains a 3 GiB disk reserve and records every output file/link in `tree.json`.
Package installation hooks and metadata are excluded; ownership, privileged
permissions and generated caches are not an installed-system guarantee. PASS
means payload assembly only. Test ARM64 loader/ABI behavior separately, with no
physical device nodes, and retain QEMU/software-rendering scope explicitly.

The native package set includes `archlinuxarm-keyring` explicitly as well as
Arch's general keyring. Current signed ARM keyring package files and the upstream
keyring Git files differ; retain their exact identities and use the documented
package-signing fingerprint deliberately. Do not substitute the Git repository's
master-key owner-trust file for a direct package-signer allowlist.
GPG/bsdtar subprocesses have deadlines, output limits and process-group cleanup.
The mandatory metadata/archive suite runs in the active tier, including under
Python optimization. It requires `gpg`, `gpgv`, `gpgconf`, `bsdtar` and `vercmp`;
Ubuntu 24.04 supplies the last tool through
[`makepkg`](https://manpages.ubuntu.com/manpages/noble/en/man8/vercmp.8.html).

Run the unsigned board build with an existing Git object store containing the
pinned Linux commit and a new output directory:

```sh
scripts/host/build-rog5-production-kernel.py \
  --linux-git "$ROG5_LINUX_SOURCE" --output build/rog5-production --jobs 2
```

The command archives verified immutable source instead of modifying that checkout.
Install the declared compiler, module and schema tools first; absence fails the
selected gate. `--prepare-only` records configuration preparation, never a compile
PASS. An optional `--base-archive` must match the pinned full archive hash.

After a production source preparation/build, run the separate exact-source
regressions with the schema environment on PATH:

```sh
ROG5_LINUX_SOURCE="$PWD/build/rog5-production/source" \
  scripts/host/test-repository-linux.sh board
```

This tier requires the source and schema tools and fails if they are missing.
It exercises the real RPMh binding/PM fixtures and compares touch core extracts.
It does not rebuild Image/modules or establish physical qualification.

The board build stages the local disabled-touch binding without replacing any
upstream binding. It exports base-DT labels, then requires ordered
display/GPU/inert-touch composition and the provider contract before PASS.
The same composition check can use existing exact board outputs:

```sh
python3 scripts/device/test-mobile-dt-composition.py \
  --linux-source build/rog5-production/source \
  --base-dtb build/rog5-production/objects/arch/arm64/boot/dts/qcom/sm8350-asus-rog-phone5.dtb \
  --schema build/rog5-production/objects/Documentation/devicetree/bindings/processed-schema.json \
  --output build/new-mobile-dt-check
```

The output must be new. The source/schema must contain the complete production
bindings and local touch binding. This compiles only DTs, records consumed
includes and tools, and validates all bindings; it never creates a phone image.
The cheap active tier checks semantic guards and actual GENI extracts. The board
tier additionally runs the real touch schema fixtures. Keep missing source or
schema prerequisites visible; an individual driver/module build proves neither
an enabled provider nor physical input.

The mobile acceptance contract is separate from the immutable headless baseline.
`check-mobile-status.py --write` updates only the generated current-state header;
old checkpoints remain unchanged. Neither this status file nor an artifact
inventory grants admission, signing or phone-execution authority.

## Qualification-first scope

The 2026-09-10 user clarification expands the product destination to a mobile
Arch phone, excluding cellular; see [priorities](../ROADMAP.md). The current
buttons/LED milestone and subsequent display/touch/GPU work may proceed under
their bounded gates while unrelated baseline qualification failures remain
open. The acceptance matrix below still defines baseline release qualification,
and its failures must not be relabelled as success.

The mandatory matrix in [release acceptance](release-acceptance.md) is the
definition of done. Select the highest-value failing or blocked outcome, state
one question, and work to evidence. Fix newly found defects now only if they
block qualification or materially threaten the release. Put unrelated work in
the existing [backlog](../ROADMAP.md), not another review or state ledger.
Reopen a completed review only when new evidence changes its conclusion.

Use focused reproduction/correction for demonstrated defects. Repeated,
unexplained or cross-component failures warrant explicit systematic debugging;
failed attempts trigger hypothesis reassessment, not an architecture verdict.
Bounded experiments and labelled mitigations are permitted while an original
cause is unknown. An unrelated incident need not block a separately proven fix.

## Feedback after each run

The r77 fallback had root-owned sticky `/run` mode 1777. The unchanged
0755 staging guard correctly refused before creating its namespace. Separate
recovery used the existing protected 0755 tmpfs `/run/initramfs` as parent,
retaining the guard rather than chmodding global `/run`. Five ARM64 cases and
five coordinator cases passed; actual restoration took 10.340 s. Discover the
actual fallback RAM parent as part of preparation and qualify that exact path.
After any early reboot, collect retained reset evidence before another boot;
PSTORE config with no ramoops DT node does not prove a working crash-log backend.

In r77, the prepared terminal entry started immediately on Ready and both
independent sudo reuse checks passed. Keep the same verified controlling terminal
for subsequent sudo work, with bounded refresh only while a job is active.
Successful RAM transfer and early stage packets do not prove target health:
read the authenticated returned bundle/release before interpreting a generic
identity error. Preserve that distinction in the run summary, and retrieve
retained reset evidence before another boot can replace it. A display DT may
exercise built-in MDSS/DSI before any explicit panel-module command.

A healthy overall boot does not prove all PMIC children bound. In r76, a
0.363-second metadata-only query distinguished the SID-5 unbound PMR735B from
five successfully bound PMICs. Trace the exact failed register and probe return
before changing DT nodes; device labels alone do not prove board population.
Thermal-driver config, module availability, loading and actual alarm binding
are separate facts. Keep this diagnosis independent of a frozen prepared test.


For sudo reuse, retain the actual controlling terminal and verify its shell
PID/start, session, foreground process group and host boot. `/dev/tty` reports
its special device number rather than the underlying pts device; compare the
process's tty number and foreground ownership instead. The r75 live terminal
check and ten launcher cases pass. After local authentication, two separately
owned `sudo -n -v` children must succeed before delegating to the trial. Keep
this wrapper outside the frozen kernel/controller so authentication preparation
does not trigger another build or invalidate qualified controller code.


The r74 provenance fixtures now shift a running monotonic clock past their
accelerated capture closure. A fresh 1380-second software recording must be
replayable immediately; never wait for wall time or relax the production
capture deadline to accommodate a fixture. When rebinding qualified components,
preserve historical source maps explicitly and publish the current dependency
identities separately. Eleven unchanged privilege boundaries were compared
before inheriting actual root/deck handoff evidence, avoiding another password
prompt for an unchanged test. Current credential reuse still needs verification.


The r71 missing-RAM failure is now covered by the actual staging receipt and a
fresh read-only pre-claim observation, with the same binding checked at every
admission gate. In r73, 76 focused cases and four full-flow fixtures passed; the
actual phone recheck took 2.883 seconds. Derivative checkouts must retain explicit
paths to unchanged installed-file evidence: a copied selector path caused the
first fixture failure, fixed without copying or rebuilding the selector. Keep
fixture and actual phone results distinct, and preserve failed attempt outputs.


Standing user instruction, 2026-09-10: reserve a brief review after each run and
at the end of every goal turn. Check whether the run advanced the current
priority, what failed repeatedly, and where measured time or resources were
spent without useful new evidence. A successful build can still be the wrong
next task: kernel and hardware qualification currently precede Denial builds.

When a repeated error or bottleneck has an actionable cause, implement one
scoped improvement and verify it with the smallest relevant check. If the cause
is uncertain, choose a bounded measurement that distinguishes hypotheses before
retrying. Preserve failed receipts and original deadlines; do not turn a fix
into a weaker acceptance gate. Carry larger justified changes into the existing
roadmap, and add a development lesson only when it prevents a reusable failure.
No-change reviews need no new file or repetitive user update. Keep this review
proportional so it improves the next run without delaying hardware work.
Before accepting a mocked boundary test as preparation, run a cheap check of
the actual entrypoint and target tool availability. Record the cause, change
and relevant result together in the existing run record; measured improvements
apply only to the work actually measured.

## Commands and tests

Run these from the repository; `scripts/host/rog5-dev` also works from another
directory. Each command delegates to an existing implementation.

```sh
scripts/host/rog5-dev test active
scripts/host/rog5-dev select --event push BASE HEAD
scripts/host/rog5-dev select --development BASE HEAD
scripts/host/rog5-dev build-initramfs --help
scripts/host/rog5-dev package --help
scripts/host/rog5-dev check-target --help
```

- Documentation: link/context checks and active tier.
- Observer/userspace: focused behavior tests and active tier; copy only the
  admitted script if no reboot is needed.
- Module: exact `.ko`, ABI/vermagic/BTF and dependency closure; no full kernel
  build unless built-in code or ABI changes. Unsafe unload requires a short boot.
- DT/initramfs: compose only the affected DTB/archive, then test that composition.
- Kernel/recovery/shared lifecycle/trust/storage: focused checks first, one full
  `test ci` on the frozen tree. Historical matrices run `test nightly`.

Do not rerun full local tests without changed code or a new failure. The runner
prints per-suite duration. It runs at most two explicitly isolated suites by
default, further limited by CPU affinity and inherited CPU quotas.
`ROG5_TEST_WORKERS=1` serializes those suites; values 1–32 request another cap
without exceeding detected CPU capacity. Unknown quota hierarchies serialize
conservatively. Completed suite logs print as slots are reclaimed, and any ready
failure is handled before refilling the queue. Shared-state tests remain sequential. CI uses this same runner. PR head and
merge validation remain separate; main pushes now select from before/head.
Unknown or unavailable diffs broaden validation. Scheduled/manual validation
runs nightly and QEMU. Required job names are retained, with explicit skipped
merge handling for non-PR runs.
The single reviewed current narrative report is documentation in both the
development and CI selectors. Other `test-results` paths remain potentially
executable inputs and select broader checks; mixed critical changes still win.
PR merge checks continue to cover their full relevant branch delta.

Before full CI in a new worktree, materialize the tracked test fixtures; a sparse
checkout prepared for hardware observation may omit required historical inputs.
Provide the pinned Android boot tools and canonical boot-v3 template using the
bootstrap steps in `.github/workflows/offline-smoke.yml`, or reuse local copies
after verifying their exact pinned hashes. These ignored dependencies are not
created by `git worktree add`. Keep temporary checkout copies on disk, preserve
at least 3 GiB free, and restore the sparse checkout after validation if needed.
The active composition suite also uses the pinned Android unpacker, so active
checks need boot-tool bootstrap or verified local copies. Only the canonical
boot-v3 template remains unnecessary for the active tier.

Batch related fixes into one frozen integration checkpoint; record the exact
source/dirty-input identity tested. Run focused checks during edits, one full
local CI for relevant shared changes, then publish with existing exact-head
and merge requirements. Documentation-only follow-up gets its link/active
checks; it does not retroactively change the source covered by earlier CI.
No repeated full CI for unchanged inputs. While remote checks run, do useful
independent work without modifying their frozen inputs or starting a second
device coordinator. This policy changes iteration cadence, not release gates.

### Human-assisted hardware sessions

Complete the builds, focused tests, review, staging and no-press runtime checks
before asking the user to be available. The
[local-root physical-key reader](../scripts/device/observe-local-root-physical-key.sh)
supports `--preflight`: it checks the actual input FD, driver, device tree and
inhibitor, then exits without a READY prompt or event reads. Run the relevant
key preflights before the handoff; keep the existing NFS-specific gate separate.

Prepare the full launch and cleanup recipe in advance. Wait for a fresh explicit
Ready before starting any operator countdown. After the reply, perform only the
brief current-state guards and runtime arming, then immediately present the
actual reader READY prompt. Ask for one short press/release at a time and collect
events automatically; the user should not have to type terminal commands.

If preparation fails or availability expires, close the session and resolve the
problem independently before asking again. Keep partial valid component evidence
and every raw failure; avoid repeating a completed physical step solely because
a later independent validator failed. Explicitly distinguish a strict test-case
FAIL from separately verified component behavior.

### Development-only fast eligibility

`select --development BASE HEAD` emits a JSON **NOT RUN** decision, the exact
commit/tree, selector hash, impact, focused/optimized tests and remaining
requirements. It is not test evidence or admission. Freeze the named checkout
and retain the decision beside the existing run receipt; record actual tested
source, artifacts, toolchain/configuration/environment and durations. A dirty
checkout is not represented by the committed tree and must be recorded and
reclassified before use. No previous run is relabelled and no new result cache
is introduced by this selector.

The first reviewed leaves are the read-only standalone-root observer and
healthd's isolated userspace implementation (plus their tests). Documentation
and the reviewed current narrative report may accompany them; other retained
test reports can be runtime inputs and are not exempt. Any other changed
dependency selects full CI: notably the
deployed verifier, generated service units, lifecycle, admission, charging,
shutdown, watchdog, DT, initramfs, kernel and storage. A small diff does not
override this. Module work still needs exact module/dependency builds,
ABI/vermagic/BTF/firmware closure and final packaged composition. Registration
changes retain all-consumer/canonical-record and altered/consumed-record
rejection checks in normal and optimized Python; they are not a fast-path leaf.

Under standing authority, an eligible **development observation/experiment**
may proceed after its focused normal/optimized tests, active checks and exact
target/payload compatibility checks, without waiting for unrelated remote CI.
Use a fresh dedicated `/run/rog5-dev-experiments` child (host-side for a host
observer). A healthd experiment uses a separate bounded loopback listener and
exact target Python, never the accepted service, port or persistent unit/config.
Record cleanup and a bounded service-level result; failed/missing prerequisites
remain FAIL/BLOCKED, not development success. Do not promote a changed observer
into a boot/power/storage safety gate through this route. The existing exact
device, signatures, power/thermal, storage and fallback checks still apply.

No fast-path decision grants reboot, target execution, signing, flash or release
authority. Critical integration and final release retain relevant full local
and exact-head/merge CI plus the unchanged mandatory physical matrix. Broader
tiers now union active/probe coverage, execute duplicates once, and preserve
the existing isolated/shared-state scheduling. Reuse kernel/module/wrapper
caches only under their existing exact-input contracts.

A test-fixture-only correction may reuse the last successful full local CI for
unchanged production inputs. Bind the original receipt, enumerate and review
the exact test/documentation delta, run the changed tests and active tier, and
retain exact-head remote checks. The publication adapter must reject any other
changed path or altered receipt. Report original and current tested revisions;
never relabel the older full run as testing the newer fixture.

A01 overlaps its initial full retained-root hash with independent read-only
composition checks. That hash must complete before QEMU; a separate post-VM
full hash and pathname/metadata checks remain mandatory. The 120-second limit
is unchanged. This scheduling optimization does not reuse a stale root digest.
Disposable A01 VM archives use deterministic gzip level 1; exact decompressed
CPIO content remains unchanged. Signed release compression is not affected.
On the constrained development host, do not overlap memory-heavy A01/C02 work
with full local CI: a measured C02 deadline failure passed when run separately.
Overlap remote CI and bounded independent preparation instead. Keep the failed
run and original deadline; a successful isolated rerun does not erase it.

A01 and C02's sparse-root checksum still hashes every logical byte. Filesystem-reported
holes contribute their exact zero bytes without reading them from disk; unsupported
sparse seeking falls back to a full read. Invalid extents, I/O errors and changed
inputs are refused. Results record both checksums' read volume and duration;
neither root check nor the 120-second deadline is omitted.

## Packaging without identity-copy scripts

The runtime packager accepts one JSON `--config` containing its non-credential
Configuration fields. Run `package --help` for field names (JSON uses underscores).
All values are strings. Artifact paths resolve relative to the JSON file.
The recipe cannot contain signing-key/output paths, admission authority or
unknown fields; CLI recipe overrides are rejected. Supply the key and a fresh
private output directory separately. The original CLI remains supported.

The packager computes sizes, hashes and the signed manifest from the actual
input bytes and publishes atomically. Do not copy derived hashes into a second
manual signing script. Keep per-cycle private recipes and receipts outside Git.
`build-initramfs` delegates to the qualified base/radio composer; later layer
builders retain their own explicit input contracts.

For a packaging rehearsal, use an ephemeral test key and the retained accepted
Image/DTB/archive. Compare twin outputs and run the native bundle verifier with
that test public key. Such an output is **not trusted by the phone**. Testing
with a test key must never replace production signature verification.

## Exact target filesystem checks

Host QEMU without filesystem isolation previously exposed host `modules.dep`
and hid a real BusyBox failure. The following command extracts the archive into
a disposable root and runs its own BusyBox, using bubblewrap plus static
`qemu-aarch64-static`. No host `/lib`, network or physical device is exposed.

```sh
scripts/host/rog5-dev check-target --release TARGET_RELEASE INITRAMFS -- \
  sh -n /rog5-native-wifi/runtime
scripts/host/rog5-dev check-target --release TARGET_RELEASE \
  --empty-module-index INITRAMFS -- \
  modinfo -F vermagic /rog5-native-wifi/qcom-pon.ko
```

`--empty-module-index` explicitly simulates the trusted pre-switch runtime's
empty mode-0444 index **inside the disposable extraction**. Omit it to test the
original archive. Check expected output as well as status: BusyBox `modinfo`
can exit zero for a missing module. Archive paths precede runtime relocation;
`/rog5-native-wifi` becomes `/run/rog5-native-wifi` during boot. This runner
does not execute init, load modules, emulate hardware or prove systemd behavior.

## Builds, trials and publication

Reuse the retained kernel/DT/modules for host, documentation and userspace
changes. `kernel-build-contract.sh` already enforces locked exact-state
incremental reuse through `INCREMENTAL_BUILD=1`, optional `KBUILD_CCACHE=1`
and bounded `JOBS`. A changed kernel input must invalidate reuse. The existing
ASUS wrapper cache binds actual source, toolchain, config, initramfs and repack
inputs; host docs and target bundle names are not wrapper-kernel inputs.
Keep clean twins when changed recovery/kernel inputs need release reproduction.

Local development path: freeze source; run the appropriate local tests;
compose/package without remote access; validate exact archive, signature,
payload identity and output inventory; retain source SHA and timings. This
path now uses the shared recipe CLI instead of copied scripts requiring a
fresh remote run merely to package unchanged payloads.

Live admission is separate. Existing reviewed device/topology/slot, power,
fallback, artifact and one-use claim checks still apply. This consolidation
does not add a local-CI waiver to a live gate that requires remote evidence.
Publication/release still requires successful CI for the exact commit plus
merge validation where applicable. A shared trust/runtime change receives full
validation. Admission-only generated data need isolated artifact/claim checks,
not another complete run when the already verified source is unchanged.

Do not invoke historical Alpine/NFS live gates for the installed native server.
The native RAM loader and transaction are
`scripts/device/load-native-ram-bundle.sh` and
`scripts/device/execute-native-ram-bundle-transaction.sh`; host admission must
precede them. Neither this command front door nor packaging consumes a claim.
Never retry an ambiguous or post-COMMIT experimental target.

## Experimental execution and stable operation

| Operation | Rule and required evidence |
|---|---|
| Issue an experimental candidate | Exact signed composition and admission first; one execution claim consumed at COMMIT. Packaging never grants authority. |
| Ambiguous experimental execution | Treat as consumed; collect diagnostics and use the independently verified recovery route. Do not resend COMMIT or relabel it an ordinary reboot. |
| Ordinary accepted-release reboot | Repeated boots are required for qualification, each with fresh boot identity, verified installed artifacts, power gates and complete logs. Do not reexecute an experimental RAM claim. Verify the installed loader/release supports the existing normal path first. |
| Automatic fallback / recovery qualification | Exercise the existing verified selector and rollback path with an isolated failed test candidate. Do not corrupt installed payloads. A simulated pass or host-assisted fastboot rescue does not prove autonomous fallback. |

These distinctions document existing boundaries, not a new retry mechanism.
An accepted release is not permanently barred from reboot by experimental
one-use rules. Conversely, current RAM-rescue success does not qualify an old
installed loader. Any selector/claim/rollback mechanism change needs focused
regressions and the applicable full/trust checks before use. Storage/flash
authorization remains separately scoped; no policy wording grants it.

For an installed-release reboot, start `headless-stage-receiver.py` with
`--source-boot-id` set to the freshly authenticated current boot UUID. Use the
same option with `--check`; experimental RAM executors deliberately reject
this capture mode. Authenticate installed bytes, fallback and power separately
before the reboot request. The receiver is passive and grants no authority.
It ignores the old boot, requires an observed USB disconnect, then accepts
only a different boot's frames. Missing disconnect, returning old identity or
mixed boot evidence cannot qualify a reboot. Complete pinned SSH/local-root
verification and host boot-service-absence evidence are still required for S01.
Do not infer bootloader slot-success state from Linux trial-health records.

## Retention and context

Current state owns accepted identities and links to evidence. Active context
is a pointer; lessons contain failure patterns, not another chronological log.
Use [the archive index](archive/README.md) for superseded instructions. Global
skills/configuration are unchanged; the project debugging skill remains
explicit-only and does not require installing its upstream companion skills.

Before reclaiming a build, check references, mounts/processes, cache twins and
recovery dependencies. Archive the exact tree without dereferencing symlinks,
compare archive members with originals, test restoration, and retain the
archive digest and original path privately. Remove only that verified obsolete
tree; preserve source, cache, unique evidence and recovery inputs.

Authentication preparation lesson (2026-09-11): keep password-entry attempts
separate from the one-use hardware execution entry. Preserve each bounded
authentication result, exclude concurrent owners, and refuse incomplete or
unreaped prior attempts. Reserve the hardware entry only after authentication
succeeds, with the original claim and current-state checks still enforced. A
password timeout before phone actions is not evidence of a kernel failure or a
wrong password. Reuse unchanged artifact and timer evidence when only host
authentication bookkeeping changes; verify the full dependency readers before
asking for fresh availability.

Hardware preparation lesson (2026-09-11, OLED r71): host artifact checks and
generic phone health do not establish that the experiment-specific RAM helpers
exist. Before live admission, claim consumption or asking Ready, stage the exact
source helpers with their boot/owner/custody checks, then run the actual generated
read-only source and route preflight on the phone. Retain its authenticated
receipt and require current boot, owner and file identities. Keep the runtime
verification in the observer; an unstaged phone must refuse. Do not consume a
boot claim merely to discover missing preparatory RAM files. Failed/consumed
experiments and their execution source remain immutable evidence.

Sudo reuse preparation (2026-09-11): independent non-TTY command processes may
not share sudo authentication. Keep one verified controlling terminal alive
across related test launches, and verify noninteractive reuse from separate
child processes after fresh authentication. Retain bounded refresh only during
active work. A terminal handle or an old success is not proof of current sudo
credentials; do not open a password window from automatic goal continuation.

Offline fixture lesson (2026-09-12): admission tests must construct unconsumed
and consumed claim states explicitly. The first integrated repair run exposed
a test that read the host's retained claim state and therefore changed outcome
after a historical trial. Guard the canonical claim paths in unit tests and
mock the admission result; never reset a real claim to make a fixture pass.
The failing run is retained and the isolated nine-case fixture passes.

Integrated repair lesson (2026-09-12): preserve failing receipts while repairing
fixture assumptions, then run the final tier on frozen source. The 536.475-second
continuation exposed stale Action-tag expectations and an orphaned watchdog-test
sleeper. Keep original child identities through mock watchdog termination and
wait for owned supervisors; do not loosen the reporter's descendant rejection.
Keep execution metadata beside the reporter directory, whose JSON files are
per-test receipts, rather than mixing an unrelated JSON record into that namespace.

Provenance lesson (2026-09-12): a raw execution record can correctly identify
a dirty starting checkout whose commit omits later inputs. Use the verified
final-source-binding commit/tree for the resulting source identity, and retain
the dirty execution repository separately. An independent final review caught
that labeling error in the public board summary; the correction changes no
build input or artifact byte.

Component qualification lesson (2026-09-12): use read-only external-module
builds when the compiled kernel inputs are unchanged. Touch twins took about
2.9 seconds each; an archive/source comparison and exact DT rebuild took
15.4 seconds, avoiding another 4,457-second cold kernel compile. Reproduce the
old DTB with its actual kernel flags before interpreting a new DT delta.
Keep full schema checks separate from cheap guard changes: an unchanged
schema/driver/DT input binding can retain the 81.4-second result while a stricter
configuration parser receives focused regressions. Record commands before
launch so failed and interrupted builds retain the same provenance as successes.
