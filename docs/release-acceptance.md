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
