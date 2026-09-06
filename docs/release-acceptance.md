# Headless server release acceptance

The existing goal ends when **one coherent release passes every mandatory row**
in [the executable contract](../configs/release-acceptance.json). Display,
buttons, GPU, audio and other optional features are not completion criteria.
This is a qualification contract, not new boot or storage authority.

## Commands and evidence

Use `scripts/host/rog5-dev accept quick|offline|device-smoke|release` with
`--output /absolute/new/private-directory`; add `--list` to inspect without
executing. Quick checks run first in offline/release; broadening cannot omit
them. Device smoke never silently initiates a boot. Physical checks are blocked
until connected to the existing admitted, single-coordinator execution path.

Each run writes `results.json`, per-test logs and **one `matrix.md`**:
required test → PASS/FAIL/BLOCKED/NOT RUN → evidence → next action.
Nonzero exit means failure or blocked selected checks. A quick PASS is **not**
a qualified release. Missing prerequisites, unimplemented runners, mandatory
skips and transport loss never count as success. There is no historical-results
import or cross-release merge. Explicit rescue-cycle replay below revalidates
raw evidence and authenticates the same live boot; reused evidence is labelled.
Source changes during execution invalidate the run.

`--release` accepts private `rog5-release-inputs-v1` JSON with `candidate_id`,
`source_revision` and `artifacts`: `kernel`, `dtb`, `initramfs`, `rootfs`,
`boot_bundle`. Each artifact has an absolute `path`, `size`, and `sha256`.
All bytes are hashed; metadata is not itself an admission or compatibility
proof. Exact source/dirty-tree digest, contract/runner/test versions, artifact
identities, times, durations and log hashes are retained. Qualification also
requires clean frozen source and every mandatory row passing for these inputs.
Private paths, credentials, dumps and raw logs remain outside Git.

Supporting A01 component check: `rog5-dev check-rescue-root --inputs RECEIPT
--root PRIVATE_RO_LOOP_MOUNT --output PRIVATE_NEW_DIRECTORY`. It runs the exact
archive's preparation functions, Arch systemd/sshd and generated-unit validation
with a disposable tmpfs upper. The caller provides/cleans a dedicated host-only
`ro,noload,nodev,nosuid` ext4 loop mount. This checker permits a four-artifact
receipt before wrapper packaging; full release still requires all five roles.
It does **not** qualify the final wrapper, module loading, hardware or A01 alone.
The sealed shutdown helper must match the reviewed source and file metadata.
After runtime preparation, the checker parses it from the actual Arch root
through `/usr/bin/chroot /run/initramfs /bin/sh -n /shutdown`. If Arch lacks
musl, it also reproduces the failed direct absolute-path BusyBox invocation;
an executable path alone does not relocate the ELF interpreter. Neither check
executes shutdown or reboots any system.
It also checks all sealed power/UFS module names, regular-file metadata,
AArch64 relocatable headers, consistent vermagic and dependency order within
a ten-second metadata budget. This is not BTF/symbol-resolution or hardware
load proof; those remain separate from metadata agreement.

Supporting deployed-userspace check: `rog5-dev check-deployed-server --profile
CLAIM_PROFILE --manifest EXACT_MANIFEST --boot-id BOOT_ID --identity-file KEY
--known-hosts PINNED_HOSTS --output PRIVATE_NEW_DIRECTORY`. Use an already
admitted persistent selector trial and its existing SSH credential. The host
checks the canonical consumed record and manifest, exact NCM topology/driver
and route before credential use, then pinned SSH verifies the requested boot,
bundle and kernel. The target uses isolated Python without bytecode writes to
read six repository-owned runtime/helper/healthd/unit/exitrd paths. Descriptor-
relative no-follow access, file metadata, content hashes, bounded reads and
before/after identity checks reject stale or changing deployed files. Sizes and
hashes come from one source inventory, not manually copied constants.
It requests no phone mutation, reboot or service restart; ordinary read/atime
semantics apply. A failed read or missing file fails this required composition
component. The 15-second SSH deadline does not extend any boot watchdog.
`result.json` binds observed/expected bytes, source, canonical manifest and boot.
This is not whole A01, installed-recovery, charging or standalone qualification.
A02 includes its stale-overlay and strict metadata regressions in both Python
modes; the active tier retains them when broadening to full CI.

Add `--readiness-only` for an already admitted target's bounded SSH/readiness
component instead of the six-file inventory. This uses shell/coreutils, not
target Python, with the same canonical consumed-record, manifest, pinned SSH
and host topology/route gates. It checks the exact expected boot before/after,
kernel/bundle, stable root-owned 0444 single-link regular marker on tmpfs and
active persistent SSH identity service. Current server families require a
matching `attested_boot_id`; only the canonical fallback-only family may use
the observed older marker without that field. Such results explicitly say
`legacy fallback SSH/readiness component`, `marker_boot_bound=false` and
`release_qualified=false`. They do not qualify H02, R01, the watchdog, power,
or installed recovery, and never overwrite an earlier failed smoke result.
Future supervisors should call this observer instead of copying a marker grep;
do not change a running supervisor or reuse its execution claim to repair an
observer. The 15-second read-only call does not extend boot/rollback deadlines.

`rog5-dev check-rescue-startup --cycle PRIVATE_CYCLE --execution-record
EXACT_RECORD --profile CLAIM_PROFILE --manifest EXACT_MANIFEST --output
PRIVATE_NEW_DIRECTORY` replays the original supervised startup without phone
contact. It binds the canonical consumed record, manifest, original receiver
receipt, pre-execution host preparation and original 300-second SSH timeline.
The captured readiness fields are revalidated rather than trusting their PASS
label. Changed producer versions, mismatched boot/source, duplicate JSON,
symlinked/oversized/mutating files, late setup and ambiguous execution fail.
Evidence reuse is explicit and hashes are recorded. This does not restart a
dead receiver or execute a target. Default replay reports `h02_qualified=false`.
Add `--qualify-current --archive EXACT_ARCHIVE --boot-image EXACT_BOOT
--identity-file KEY --known-hosts PINNED_HOSTS` to qualify H02 on the same
still-running boot. The canonical record binds artifact hashes; archive checks
pair the actual watchdog with startup/identity producers and exclude the radio
payload. Pinned SSH checks eight deployed files, cmdline timeout, absent radio,
Good health/USB online, 0–39.9°C and 8.4–9.0 V pack voltage. The original startup
must meet 300 s; later watchdog evidence must show one arm and one current-boot
ACK after the signed timeout (up to 5 s scheduling margin). The checker never
waits out or extends that timeout and cannot qualify a not-yet-observed ACK.
Power safety at Full is not H03 charging regulation. The exact sealed BusyBox
script is exercised with disposable hardware/mount fixtures; live collection
then checks actual paths. Normal/optimized tests run in A02 and active/full CI.

For integrated H01/H02 use `rog5-dev accept device-smoke --release RECEIPT
--rescue-inputs PRIVATE_JSON --output PRIVATE_NEW_DIRECTORY`. The private JSON
contains only `profile`, `cycle`, `execution_record`, `manifest`, `identity_file`
and `known_hosts`; all paths are absolute. It names arguments, never a command.
Do not combine it with live `--capture`. H01 revalidates the original preboot
receipt; H02 additionally requires fresh exact same-boot evidence and complete
qualification output, not just exit zero. Both bind the release candidate and
boot image. Artifact source/previous physical source remains in canonical and
cycle records; the release receipt's `source_revision` identifies the current
qualification checkpoint, not a claim that reused kernels were rebuilt there.
The resulting matrix explicitly labels reuse and leaves all missing mandatory
rows BLOCKED/NOT RUN. This is not an automatic retry or an imported green run.

C01 now runs nine QEMU cases, including P2 success without persistent identity
and stale identity. Its 500 s offline allowance covers nine 50 s subprocess
bounds plus 50 s setup/collection margin; the executable harness test verifies
that lattice. Phone deadlines are unchanged. A latched identity record proves
local initial setup, not authenticated host-side SSH; C02 separately covers
actual service restart behavior.

Supporting C02 check: `rog5-dev check-ssh-rollback --target-archive EXACT_ARCHIVE
--output PRIVATE_NEW_DIRECTORY`. Requires a user systemd manager, sshd,
ssh-keygen/keyscan, bwrap and qemu-aarch64-static. Within 120 s it runs real
loopback-only SSH restarts and the production timer/dependency relationship;
rollback uses sealed BusyBox with fixture identity/acceptance and a reboot
recorder. A healthy ACK must prevent reboot after the original deadline; a
stale ACK must not. Only uniquely named runtime user units and private fixtures
are created, then stopped/removed; no login, phone or host reboot occurs.
The result records source, archive hash, commands, PID changes and timings.
This host-systemd component is not exact target/deployed-unit qualification:
**C02 remains BLOCKED**, and no component PASS is imported into release results.

F01 uses `rog5-dev check-overlay-recovery --kernel EXACT_IMAGE --target-archive
EXACT_ARCHIVE --root-image RETAINED_EXT4 --output PRIVATE_NEW_DIRECTORY`.
It runs three networkless QEMU guests with the supplied release kernel, sealed
BusyBox and archive functions. A real OverlayFS deletion followed by a VM-only
reset leaves a journal-pending disposable 64 MiB ext4 disk. Recovery must replay
the journal, admit only the kernel's cached whiteout, reject unrelated entries,
preserve independent interrupted-update markers and pass read-only fsck.
A separate corrupted copy must fail mounting. The protected virtual disk and
all input hashes remain unchanged. The 240 s row allowance covers three 45 s
guest bounds plus hashing/setup/cleanup. No physical crash is injected; this
does not prove UFS hardware, whole-systemd startup or R01. No prerequisite or
older component result is silently treated as a final-release PASS.

## Required outcomes

| IDs | Outcome | Current coverage / next step |
|---|---|---|
| A01–A02 | Exact final archive/root composition; strict normal/optimized Python | Wire exact composition; test actual composer hashes/metadata in both modes |
| B01 | Every canonical family reaches admission, including fallback-only | Existing registry/consumer regressions; no duplicated candidate IDs |
| C01–C02 | Real BusyBox root handover, hangs/panic, current readiness; no late SSH rollback | Reuse QEMU handover, but consume assembled watchdog; add actual systemd restart transaction |
| D01–D02 | Verified fallback, next-boot primary demotion, interrupted updates | Existing selector and state-helper behavior tests |
| E01–E02 | Safe radio refusal and optional display absence preserve headless mode | E02 executes runtime/attestor with sealed BusyBox and fake hardware; E01 still pending, never lower the 8.4 V gate |
| F01–F03 | Filesystem recovery, repeatable WPA/DHCP, concurrent health requests | Disposable-image and restart tests; slow-client regression |
| G01–G02 | Coverage and revision selection; honest result accounting | Existing selector/Git DAG tests plus acceptance-runner regressions |
| H01–H03 | Capture ready before boot, exact headless rescue/SSH, sustained safe charging | First live milestone; coherent rescue composition and supervised capture first |
| S01–S07 | Local Arch, USB/Wi-Fi, service restarts, durable scratch, 3 boots, off-start, 60 min soak | Subsequent final-release qualification; no historical mixed-build PASS |
| R01 | Real recovery after one controlled failed isolated boot | Separate physical experiment; never corrupt installed payloads or interrupt storage power |

Every row's environment, prerequisites, runner, deadline, outcome, mutation,
cleanup and evidence contract is in the JSON. Empty command lists carry explicit
implementation blockers; they are not placeholders that return success.
Mandatory **E02** qualifies isolation, not display functionality.

## Hardware bounds fixed before execution

Initial conservative boot deadline: **300 s** to authenticated SSH. The retained
[ordinary/off-start observations](../test-results/2026-09-03-unattended-reboot-v10.md)
were 101.273/96.697 s, not a measured p95. Three-boot allowance is 1080 s
(3×300 plus 180 supervision margin); powered-off start 420 s includes an
operator/power-state allowance. These are qualification bounds, not altered
kernel watchdog deadlines. A rescue with a longer verified staging budget must
have its separate timing lattice documented before admission, not after failure.

Charging smoke: **600 s**, samples every **10 s**, 660 s total allowance.
Health must be Good, no unsafe temperature/voltage, and transport must remain
available with Wi-Fi off. The exact current polarity, configured charge limit,
measurement noise and battery-state interpretation must be bound from retained
telemetry and reviewed before H03 runs. Until then H03 is BLOCKED. Below the
limit require sustained net-positive charging; full/regulated batteries can pass
only with validated regulation evidence. A flat voltage or one jump is not proof.
Do not treat fastboot SOC as temperature/current telemetry. Existing stricter
power/temperature gates take precedence; never widen them for this contract.

Transfers: 256 MiB each way on each intended interface, ≤180 s/direction,
matching hashes, using the scope established by the
[NCM qualification](../test-results/2026-08-29-persistent-ncm-two-hour-pass.md).
Scratch is at most 64 MiB in an **explicitly authorized** directory: fsync,
readback and post-reboot hash; remove only that exact test-owned file.
Soak is 3600 s plus 300 s collection margin. No unexplained boot-ID changes,
oops, new UFS errors, emergency RO or unsafe power are tolerated. Missing log
continuity fails rather than proving absence of faults.

R01's initial outer ceiling is 1320 s; the actual receiver lifetime must exceed
the exact deployed target watchdog + recovery + cleanup lattice. The ceiling
does not prove any watchdog survives handover. Independent reset/ramoops
evidence is captured when available; empty pstore remains inconclusive.

For this rescue, the capture lattice is **300 s recovery preparation + 900 s
target rollback + 120 s cleanup = 1320 s**, plus **60 s preflight**, giving a
**1380 s** receiver/firewall lifetime. The manifest owns these values. The live
readiness check refuses execution when less than 1320 s remains. This is a
capture budget, not a longer SSH acceptance deadline or watchdog guarantee.

Run `rog5-dev capture-rescue --profile CLAIM_PROFILE --manifest EXACT_MANIFEST
--output PRIVATE_NEW_DIRECTORY` with scoped host-network privileges while the
exact phone is in fastboot. It does not boot or consume a claim. Its `--check`
mode verifies source, canonical artifacts, process/host identity and an actual
TCP readiness response. Pass the same directory with `rog5-dev accept
device-smoke --capture PRIVATE_DIRECTORY --release RECEIPT --output NEW_OUTPUT`.
H01 refuses another candidate/image or stale receiver. Diagnostic stage frames
are unauthenticated transport evidence; pinned SSH remains a separate test.
The shared profile retains its single normal address. A temporary loopback
diagnostic address and exact USB direct route serve the early reporter; the
receiver binds to the verified NCM interface on enumeration. All owned host
changes are restored; external changes are preserved and cleanup failure is
reported. No NFS service is needed for this local-root rescue.

## Current order and restrictions

Registry checkpoint → final rescue composition → receiver/address/log readiness
→ one admitted headless rescue → charging and pinned SSH → remaining offline
fixes and final server qualification. Reuse the accepted kernel for userspace
changes. No new feature expansion, experimental flashing, destructive storage
or consumed/ambiguous retry. Preserve stock A, accepted signed fallback,
exact device/slot/topology, artifact verification and storage/thermal guards.

Recovery is not delayed until every later test exists. Conversely, old source
tests cannot qualify old signed bytes: the prepared V11-based rescue lacks the
current post-handover watchdog and early health predicate. Keep it preserved,
not silently promoted. A real physical-recovery blocker names the missing
operation; simulations cannot replace it. Optional work is reported separately.
