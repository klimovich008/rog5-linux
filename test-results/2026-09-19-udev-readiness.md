# Udev database failure snapshot — 2026-09-19

**Host/ARM64 snapshot fixtures PASS; system VM qualification FAIL on timing
inventory. Device/PAM readiness and cleanup PASS in that VM.** Its wait succeeded,
so the new database failure snapshot is NOT RUN in the full-system execution.
Neither intermittent device initialization nor the earlier RCU stall is declared
fixed. Denial and physical-phone execution are NOT RUN this turn. S06/R01 FAIL,
signed fallback and consumed claims remain unchanged.

Starting commit/tree: `648ecd9abc9b4b028f67dfd269b926dcf35f1573` /
`8c0916a3972d6d40c3811d6ad8c9fa36a5334643`.
Frozen source: `b03ed53e35cb55e52181e756b6e134ec6ddf8e4e`, tree
`6c9c33b80ebc872083f7e0cacf8aa577bef3a46b`.

## Source finding and change

The inspected systemd v261.3 reference at
`3255daee1572366b74fe92f002a3d60ecbb27103` permits an empty database record for
a device with a device number but no extra properties. Its reader marks a record
initialized before parsing any fields. Thus an absent initialization timestamp
is not proof of an uninitialized device. References:
[database writer](https://github.com/systemd/systemd/blob/3255daee1572366b74fe92f002a3d60ecbb27103/src/libsystemd/sd-device/device-private.c),
[database reader](https://github.com/systemd/systemd/blob/3255daee1572366b74fe92f002a3d60ecbb27103/src/libsystemd/sd-device/sd-device.c).
This is upstream source evidence, not a rebuilt Arch package or proof of the
state at the prior failed wait. The retained package rules set tty modes and
FUSE permissions, but a correct node mode alone does not prove completed udev
processing. No admission predicate was changed.

`tools/qemu-virtio-drm/logind-session.sh` now captures all required character-device
udev records before slower property/journal queries. One batched stat resolves
device numbers; builtin reads capture at most1024 text bytes per record and mark
truncation. Empty, absent and refused nonregular records remain distinguishable;
raw read status and captured processing flags remain diagnostic data. The outer
three-second snapshot deadline and16KiB encoded capture limit are unchanged.
The eight-second readiness condition, original failure return, successful path,
PAM/seat/port checks and recovery remain unchanged.

`test-qemu-logind-runner.py` exercises the real shell functions with private
filesystem fixtures. A new case failed before the change: a blocked property
query consumed the snapshot deadline without retaining the database states.
It now retains all four states even while that query times out. Coverage includes
empty/absent records, ID_PROCESSING, truncation, and symlink/FIFO refusal without
reading their targets. Existing tests preserve the original wait failure despite
snapshot failures and prove successful readiness does not invoke extra queries.

The focused readiness group passes in8.980s; the then123-case runner passes in
24.372s. A subsequent refusal test passes independently; the final tier includes
all124 runner cases. Six executions also pass using retained ARM64 Bash5.3.15
under qemu-user, with a synthetic database and native host stat reading only
/dev/null metadata. These are shell/ABI tests, not a guest-kernel or live udev
qualification. Targeted source, Bash, loader, libc, tinfo, qemu-user and stat
hashes remain unchanged. The first ARM64 preflight used the9P mapped view as a
host sysroot and failed to find the loader: mapped symlinks are file payloads.
Using the ordinary retained runtime fixed that setup error without editing it.

## One executed system VM

The explicit nomops startup-only configuration from the prior failure ran once,
with the richer failure snapshot and current error reporting. Source/package,
cache, resource and deadline guards were retained.26 prior input hashes and
full original/mapped runtime bytes/metadata are unchanged. No kernel, Denial or
Flutter rebuild occurred; only the existing small VM probes were rebuilt.

Readiness completes BOOTTIME136.91→137.49s, status0, in the existing8s budget.
PAM authentication/account/credentials/open/close/delete/end, active local tty1,
logind-mediated device access, scope removal and normal poweroff pass. No RCU
stall or kernel panic is recorded. Since the failure path did not execute, the
new snapshot cannot explain this success or identify the earlier missing state.

The timing query returns code124 with1866 bytes, covering six of nine units:
hardware database, linker cache, journal catalog, both tmpfiles units and udevd.
It is incomplete and the overall VM result remains FAIL. Harness duration is
231.953s. The exact QEMU duration, initramfs/hash, commands, limits and all selected
input/output identities are in the
[qualification JSON](2026-09-19-udev-readiness-qualification.json).

## Next action and retained limits

The existing normal Denial-session path does not request this startup-only timing
inventory. With both normal and nomops runs having demonstrated PAM/cleanup in
separate observations, the next useful experiment is one bounded default-CPU
Denial/app VM, retaining the timing diagnostic and RCU failures separately. Do
not infer a MOPS workaround, remove readiness checks or repeat unchanged startup
runs merely to force a database snapshot. Hardware scanout/touch/GPU remain
separate physical qualification requirements.

This and the preceding goal turn are progress. Capture cheap distinguishing data
before expensive diagnostic queries, and distinguish node presence, database
presence and active processing. Use ordinary runtime roots for host/qemu-user
execution and mapped-file views only through their intended filesystem consumer.
Private evidence is `rog5-udev-readiness-20260919-r1`; use fresh output names for
any new execution. No phone, signing, claim, admission or protected-storage action
occurred. Historical evidence and the original dirty checkout were preserved.

Final local active tier: **111 PASS,0 FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED**
in179.594s, service peak336.5MiB,0swap. Three declared optional
historical subchecks are skipped separately. Metadata publication checks pass
without rerunning unchanged source tests. These are local results, not GitHub
CI or phone qualification.
