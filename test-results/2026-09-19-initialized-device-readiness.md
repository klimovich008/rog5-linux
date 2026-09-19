# Initialized virtual-device readiness — 2026-09-19

**The initialized-device barrier passes host/ARM64 regressions, but the controlled VM returns device-wait status 1 before PAM; full session qualification remains FAIL.**
Source/host/ARM64 VM evidence only. Phone physical rows remain NOT RUN and
S06/R01 remain FAIL. This result creates no phone candidate or execution authority.

## Correction and regression evidence

Implementation source `1020884d4a781d0463d25a913b861bdfc0bbedbd`, tree `bb9af6d4b11e7418188d96dc0070b3de9da38e91`; starting source
`23afb74971a6aaee9ae6b00d049dbebe3aace766`. The implementation changes only
`tools/qemu-virtio-drm/logind-session.sh` and
`scripts/host/test-qemu-logind-runner.py`.

The previous global `udevadm settle --timeout=8` made session admission depend
on unrelated queued events. The new production function waits once with
`udevadm wait --timeout=8 --initialized=yes` for card0, event0 and tty1;
combined sessions add fuse; editor/apps observation adds event1 and vport0p1.
Both input nodes are required because keyboard/tablet numbering can swap.
Conflicting observation flags and observation without a combined session fail
before querying devices. Begin/end records preserve the exact wait status.
Later character-device, exact port-name, ownership, PAM, VT, seat/access and
cleanup checks are unchanged. This is a VM-specific barrier, not phone policy.

The test executes the actual helper and extracted supervisor call site.
The previous global barrier fails 23 subtests across four cases (0.738s);
all four corrected cases pass (0.646s) and pass under Python -O (0.816s).
They cover every selected device absent/uninitialized, mode-specific sets,
conflicting modes and fatal helper statuses 1/42/124/127. The fake udev helper
models unrelated queue work; it is not actual kernel event processing.
All 98 runner cases passed in 15.249s including process startup, and shell
syntax passed in 0.004s.

The actual retained ARM64 udevadm fixture separately observes missing=1,
uninitialized=1, initialized=0 and mixed-ready/missing=1, in
1.217/1.267/0.114/1.117s. It uses a synthetic udev database and only a read-only
kernel virtual /dev/null sysfs leaf in an isolated namespace. These checks
prove cached initialization admission/refusal, not a live initialization
transition, full eight-second timing, ACL/logind admission or phone behavior.
The initial fake-filesystem sysfs attempt was refused; that failure remains.
All four corrected checks passed before a metadata step guessed the wrong
shared-library basename. Finalization then recorded the exact installed soname
without repeating the checks. Both original failed/incomplete records are bound.

The exact retained udev rules cover DRM/input groups, tty mode/group, FUSE
mode/static node and named virtio-port symlinks. The retained manual includes
properties or other device settings in initialization. Rule presence is source
support for this barrier, not proof processing completed in the guest.

One frozen active-tier run passed 109 suites in 176.369s:
FAIL 0, BLOCKED 0, SKIPPED 0, NOT_SELECTED 255. Three declared optional historical
subchecks stayed SKIPPED: charging archive, trial-state ARM replay and rail-reader
ARM binary. JSON/JUnit hashes are retained. These were personally executed local
checks; no imported GitHub run is represented as this execution.

## Controlled VM observation

The guest emitted the exact six-device begin record and an end record with status 1, then failed at the supervisor call site, line 150. The serial record does not identify which device was unready or the underlying reason; status 1 alone is not proof of a timeout. PAM, Denial rendering, service snapshot, app mapping, app release and text entry were NOT RUN. There were no app owners, screenshots, actions or release-probe records. The host observer reported application transport closed before approved teardown; the QEMU container command ended -9 after 218.888s. The harness took 262.356s and the wrapper 262.460s. The guest reached normal Power down, but /var unmount failed; normal poweroff does not turn teardown into PASS. Zero RCU stall reports were recorded. These are generic ARM64 VM observations, not phone hardware evidence.

Only the readiness script differs among 38 recorded inputs; all 37 other inputs
match the previous service-snapshot VM. Same kernel, payload, Denial/Flutter,
release probe, two guest CPUs, 1 GiB guest memory, 2 GiB/no-swap host limit, 2 CPU quota,
network disabled, read-only inputs, single TCG mode and 300s QEMU deadline.
No hwdb cache integration or timeout extension. The harness builds only small
fixture helpers/init. Full runtime bytes/mapped metadata and input hashes were
verified after the run, and owned container absence was checked.

Exact commands are in the [qualification JSON](2026-09-19-initialized-device-readiness-qualification.json).
One-use VM command, already executed: `python3 /home/deck/.local/state/rog5-device-readiness-20260919-r1/run-vm.py`.
Raw logs stay in `/home/deck/.local/state/rog5-device-readiness-20260919-r1`. No phone contact, signing, installation, admission,
claim consumption or protected-storage mutation occurred.

## Next action and efficiency review

The mode-specific initialized-device barrier passes 98 runner cases, four actual ARM64 fixture checks and 109 active suites. The controlled VM still returns device-wait status 1 before PAM; device identity and cause are unresolved. Add bounded per-device initialization observations and capture the wait diagnostic with explicit logging, keeping one eight-second wait and exact fatal status. Label any post-failure device snapshot as a later observation. Regress output limits and failed queries before one new controlled VM; do not increase the deadline, remove a required device, or weaken initialization/PAM guards. App release, previous portal-start 124 and Mousepad exit 137 remain open; S06/R01 FAIL and phone physical NOT RUN unchanged; no phone authority.

The preceding storage turn was progress: it recovered 5.56 GB net with verified
restoration while preserving runtime/build inputs. This turn qualified the
previously implemented readiness change through its already frozen test result
and one new controlled VM. The old global queue failure was turned into a
specific host counterexample before changing policy. No kernel, Denial or Flutter
rebuild was needed, and unchanged integrated tests were not repeated after the
cleanup. Do not convert an isolated readiness or rendering milestone into full
app-session acceptance.

A mode-specific udev wait removes an unrelated global-queue dependency, but its aggregate failure does not identify the failed device. This VM returned status 1 before PAM with no device-specific diagnostic; do not label it a timeout from the numeric status alone. The next observation must correlate each fixed device with existence/initialization state and capture bounded udev diagnostics while preserving the single eight-second wait and its original fatal result. Cached ARM64 udev-database fixtures prove the admission predicate, not live guest rule completion. The same turn reused the frozen integrated result after verified scratch cleanup, avoiding another unchanged three-minute tier.
