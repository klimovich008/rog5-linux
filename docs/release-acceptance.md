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
import or cross-run merge. Source changes during execution invalidate the run.

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

## Required outcomes

| IDs | Outcome | Current coverage / next step |
|---|---|---|
| A01–A02 | Exact final archive/root composition; strict normal/optimized Python | Wire exact composition; test actual composer hashes/metadata in both modes |
| B01 | Every canonical family reaches admission, including fallback-only | Existing registry/consumer regressions; no duplicated candidate IDs |
| C01–C02 | Real BusyBox root handover, hangs/panic, current readiness; no late SSH rollback | Reuse QEMU handover, but consume assembled watchdog; add actual systemd restart transaction |
| D01–D02 | Verified fallback, next-boot primary demotion, interrupted updates | Existing selector and state-helper behavior tests |
| E01–E02 | Safe radio refusal and optional display absence preserve headless mode | Add regressions; never lower the 8.4 V radio gate or hide partial activation |
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
