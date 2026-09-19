# Service snapshot partial replies — 2026-09-19

**A demonstrated diagnostic output-loss defect is fixed. The controlled VM failed earlier at global udev readiness; the repaired service snapshot and app release were NOT RUN.**
This is source/host/VM preparation for Denial's native phone session, not phone
qualification. S06/R01 remain FAIL and physical mobile rows remain NOT RUN.

## Source correction and tests

Source `814f0cd646f6b74abae738e380bcbe8c3082011f`, tree `770d87d113d95b233bd2844c93533e81f0e096a1`. Starting source was
`3a685c2b6ed0c57347a0d95b791c391156b137c0`. Changes are confined to
`tools/qemu-virtio-drm/logind-denial.sh` and
`scripts/host/test-qemu-logind-runner.py` before this evidence publication.

The three-second service snapshot previously connected systemctl's
stdout directly to a pipe without forcing timely flushes. A libc producer writing a complete small unit reply then
stalling lost that reply when the real timeout killed it. The actual extracted
snapshot function failed the new regression before the fix. The correction uses
`stdbuf -oL -e0` and flushes accepted lines in the capped awk relay. Stderr stays
unbuffered so an unterminated diagnostic survives too. The deadline, kill grace,
65,536-byte output cap, overflow 42 and primary service-start failure are unchanged.
Missing stdbuf reports snapshot 127 while the original start 124 remains fatal.
No service is removed, made optional, or admitted on incomplete output.

Nine focused cases passed normally (0.666s) and
under Python -O (0.533s). All 94 runner tests passed in
14.946s. The host fixture shortens only its real
timeout to 0.2s while asserting the production 3s/1s arguments; the initial
unshortened regression also failed in 3.054s. The actual retained ARM64
bash/timeout/stdbuf/libstdbuf/awk comparison used the full 3s bound: old output
lost the completed stdout reply, new output retained it, and both preserved
unterminated stderr and status 124. The mocked systemctl is a real ARM64 libc
producer; this is not a claim about actual service response timing.

The tiny ARM fixture build took 0.480s;
old/new executions took 3.172s and
3.171s. The exact runtime and mapped
metadata passed before/after validation. Package audit matched the retained
ARM64 systemd 261.3-1 and coreutils 9.11-2 bytes. Symbol inspection does not prove
that every shared-library path leaves buffering unchanged. Neither this fixture
nor the previous empty snapshot proves the old VM received completed replies.

One frozen active-tier command, `scripts/host/test-repository-linux.sh active`,
passed 109 suites in 176.418s: FAIL 0, BLOCKED 0, SKIPPED 0,
NOT_SELECTED 255. Three declared optional historical-artifact subchecks were
skipped: charging archive, retained trial-state ARM replay and rail-reader ARM
binary. JSON and JUnit identities are retained. These were local executions,
not imported GitHub CI results.

## Controlled VM result

The new VM reached `udevadm settle --timeout=8` at the unchanged
`logind-session.sh:124`. The retained journal says the udev queue did not empty;
the supervisor then exited 1. PAM, Denial, the service snapshot and both apps were
NOT RUN. The changed snapshot function was not invoked, so its buffering change
cannot explain this earlier failure. No service unit timing was recovered.

QEMU operation 170.528s; full harness 212.536s. Overall FAIL remains
`application transport closed before approved teardown`, with host container
step -9. Guest `reboot: Power down` is independently present; /var unmount failed
before final poweroff and remains recorded. Zero RCU reports does not establish
reliability or a kernel fix. There were no screenshots, input actions, mapped
clients, release stages or approved teardown acknowledgement.

A bounded read-only follow-up identified the exact consumed-device set. The
retained ARM64 `udevadm wait --help` was executed in an isolated runtime and its
shipped manual inspected: initialized per-device waits are supported and global
settle is a separate optional mode. No device was queried by that help check.
All modes consume card0, event0, tty1; combined adds fuse; observation adds event1
and vport0p1. Actual serial enumerates tablet as input0 and keyboard as input1,
so role-to-number assumptions are invalid. The guest Denial configuration uses
card0 for both DRM and rendering; host renderD128 exposure is not a reason to
require a guest renderD128. Existing port-name/ownership, device-rdev, PAM, logind,
VT and access checks must remain. No readiness behavior was changed in this
revision, and the missing global event is still unidentified.

Only the corrected guest snapshot source differs among 38 recorded inputs;
37 retained input hashes match the preceding single-TCG app trial. Same kernel,
Denial/Flutter/payload/probe/runtime, two guest CPUs, 1 GiB guest memory,
2 GiB/no-swap host memory, 2 CPU quota, network disabled, read-only inputs and 300s
QEMU limit. The standard harness rebuilds only its small fixture probes and
init. No hwdb cache integration or deadline increase. Fresh source/active-test
and exact input comparison guards precede launch; full runtime and input
verification runs even after failure. Owned container absence is verified.

Exact one-use commands, already executed and not to be replayed into these outputs:

- `python3 /home/deck/.local/state/rog5-service-snapshot-20260919-r1/check-arm.py`
- `python3 scripts/host/test-qemu-logind-runner.py ServiceSnapshot ActivatedServices`
- `python3 -O scripts/host/test-qemu-logind-runner.py ServiceSnapshot ActivatedServices`
- `python3 scripts/host/test-qemu-logind-runner.py`
- `scripts/host/test-repository-linux.sh active`
- `python3 /home/deck/.local/state/rog5-service-snapshot-20260919-r1/run-vm.py`
- `python3 /home/deck/.local/state/rog5-service-snapshot-20260919-r1/analyze.py`

See the [qualification JSON](2026-09-19-service-snapshot-partial-replies-qualification.json) for exact
commands, hashes, scopes, raw-result identities and durations. Private full logs
remain under `/home/deck/.local/state/rog5-service-snapshot-20260919-r1`. No phone contact, production signing, installation,
admission, claim consumption or protected-storage mutation occurred. Historical
artifact records and failures are preserved; there is no new phone candidate.

## Next action and efficiency review

Snapshot buffering fix passes native/ARM64 fixtures, 94 runner cases and 109 active suites. The controlled VM instead failed at global udev settle 8s before PAM/Denial, so real service snapshot and app release were NOT RUN. Implement and regress a mode-specific initialized-device barrier within the same 8s bound: card0/event0/tty1; combined adds fuse; editor/apps add event1/vport0p1. Keep both input paths regardless of role order, exact port identity, seat/PAM/access and fallback guards. Retained udevadm wait API and consumer audit support this scope but do not prove it would pass. Prior portal-start 124 and Mousepad exit 137 remain open; S06/R01 FAIL and phone physical NOT RUN unchanged; no phone authority.

The previous goal turn was progress: it qualified the opt-in TCG mode and
isolated the pre-app service boundary. This turn fixed a demonstrated evidence
loss mechanism using native and ARM64 fixtures before one integrated tier and
one controlled VM. The new failure changes the next experiment to exact
virtual-device readiness rather than another service/app retry. The short host timeout fixture avoids adding 3s to every
runner execution while preserving the production bound and process cleanup.
No kernel, Denial or Flutter rebuild was needed. Do not infer service readiness
from recovered partial properties or rerun an unchanged failed VM.

Publication checks: all eight mobile-status regressions passed; artifact
inventory and generated-status checks passed, and whitespace is clean. The
inventory now contains 553 sets; its large/private byte verification and physical
admission sections remain NOT RUN. All 552 previous artifact rows are unchanged.
