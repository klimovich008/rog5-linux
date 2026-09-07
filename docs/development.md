# Development loop

Start at [current state](current-state.md). Work on one question and choose the
cheapest artifact that changes its answer. Historical profile names are not
the active server. In particular, `power-usb-active.json` and its generated
lock still describe the older NFS observer track; they are kept for its
regression/publication contract, not current installed-selector identity.

## Qualification-first scope

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
prints per-suite duration. It parallelizes only explicitly isolated suites;
shared-state tests remain sequential. CI uses this same runner. PR head and
merge validation remain separate; main pushes now select from before/head.
Unknown or unavailable diffs broaden validation. Scheduled/manual validation
runs nightly and QEMU. Required job names are retained, with explicit skipped
merge handling for non-PR runs.
The single reviewed current narrative report is documentation in both the
development and CI selectors. Other `test-results` paths remain potentially
executable inputs and select broader checks; mixed critical changes still win.
PR merge checks continue to cover their full relevant branch delta.

Batch related fixes into one frozen integration checkpoint; record the exact
source/dirty-input identity tested. Run focused checks during edits, one full
local CI for relevant shared changes, then publish with existing exact-head
and merge requirements. Documentation-only follow-up gets its link/active
checks; it does not retroactively change the source covered by earlier CI.
No repeated full CI for unchanged inputs. While remote checks run, do useful
independent work without modifying their frozen inputs or starting a second
device coordinator. This policy changes iteration cadence, not release gates.

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

C02's sparse-root checksum still hashes every logical byte. Filesystem-reported
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
