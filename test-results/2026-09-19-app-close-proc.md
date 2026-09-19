# Read-only app-close observation — 2026-09-19

Generic ARM64 VM and host fixtures only. No phone operation, candidate, signing,
admission, claim consumption or protected-storage mutation. Physical NOT RUN;
ASUS slot A, signed V11 fallback, server/rescue and historical S06/R01 FAIL preserved.

Starting commit `7e15a93f2c00aba46a3909e631ae014be3ed4e3d`, tree
`9deacc035f3a0155d749ccaa66ccf20c1c7ef4c7`. The preceding goal turn confirmed
unchanged upstream findings, so was no progress toward the active blocker.

Source frozen at `348daa7a88c4a7c414599e2650fc63aa464b974e`, tree
`ac45e0d4bb7ea9265f7f64b3eff5f31d08867cae`.

## Changed layer and question

The explicit `--app-close-probe` VM mode adds a read-only Rust sampler around
owned Mousepad close. It requires close-only and the settings diagnostic,
VM markers, uid1000, current PID/starttime/parent identity and a new private
output file. Six rounds at200ms sample task syscall/signal state, the main
thread PC mapping and at most eight FD link targets. It never reads FD contents,
environment or process memory, or signals the application. Missing proc/permission
information stays unavailable. Output is escaped, capped at8KiB/64records and
prefixed as diagnostics; it cannot qualify successful close.

The sampler checks a1.2s elapsed budget between rounds; proc reads can block
inside the kernel, so a separate timeout2s plus1s kill grace owns its execution
bound. Existing app2s kill grace remains unchanged. The original nonzero app
status wins over probe failures. Sampling begins after the pre-close serial
record to avoid spending its budget waiting for that transport. Its presence
can perturb scheduling; this is not a performance comparison.

ARM64 and x86_64 have different O_NOFOLLOW values; actual ARM64 symlink refusal
passed through qemu-user. All five ARM64 Rust tests passed in0.164527407s; the
owned-child test inspected a host child under emulation, not a guest process.
Release/test cross-builds took7.181108323s/13.449077370s. Host Rust wrapper
passed in1.818136085s, 46 app-supervision tests in31.186543950s and139 runner
tests in34.494313958s. A newly retained interruption regression passed2.395s;
independent disposable interruption arms passed2.387s and0.413s, including
termination/reaping while the app was already closed and the probe remained live.
Fixture preparation failures (stdout symlink metadata and ignored-TERM shell
under errexit) are retained privately; these were test-fixture corrections.

Changed files: `tools/qemu-virtio-drm/app-close-probe.rs`,
`tools/qemu-virtio-drm/logind-apps.sh`, `scripts/host/test-app-close-probe.py`,
`scripts/host/test-logind-apps.py`, `scripts/host/test-qemu-logind.py`,
`scripts/host/test-qemu-logind-runner.py`, `scripts/host/test-repository-linux.sh`
and `configs/repository-tests.json`.

## Frozen validation and experiment

The single VM fails before PAM/app launch in246.445123469s (wrapper246.514684331s).
The8s initialized-device wait begins at139.51 and returns failure148.73 BOOTTIME.
Its own text says only that initialization timed out; it does not name a device.
The pre-wait database snapshot138.96→139.18 contains only an empty tty1 record.
After failure, the complete database portion152.68→152.86 still has no event0
or event1 record. The following property queries hit their3s timeout (status124);
this partial query must not be described as a complete successful snapshot.

The original-event capture succeeds with6497bytes, no truncation. Worker
completion times are tty1=135.008027, fuse=144.223409, card0=144.614881,
vport0p1=144.779979, event0=157.079786 and event1=157.119893 CLOCK_MONOTONIC.
The guest did not suspend; BOOTTIME and MONOTONIC remain distinct recorded clocks.
These records establish late input processing in this run, about17.61s after
readiness began, rather than merely an undelivered event for already-ready input.
They do not establish the reason for the slow workers or explain every prior run.
Input hwdb misses are not proof of broken rules: both original workers finished.

The failure-only FUSE retrigger later succeeds; it neither repairs admission nor
overrides the earlier FAIL. Existing priority ordering already includes input
and its enumerated ancestors, so another priority change lacks a demonstrated
basis. The separate guest.sh chroot udev path is not this systemd-PID1 fixture.

Mousepad, Foot, close sampler and corrected PAM alarm runtime: NOT RUN.
No screenshots or input actions occurred. New VM-built sampler and PAM binaries
match their prior ARM64 build hashes exactly: sampler
15ad7c72cb72e17b5588d7f52fc1fbbda6fb38c7feb26582dcd9fe3a95af324d,
PAM bffcf5eaa028c901de437953ad30f4934578097b9b0814c74305895308bcdddd.
Normal guest poweroff passes the actual RCU-aware check; /var unmount FAIL remains.
Runtime bytes/metadata and all input hashes pass post-run verification; no owned
containers remain. Service peak1.3GiB, zero swap.

Next smallest experiment: prepare an explicitly selected combined-VM20s
initialized-device wait, preserving8s default, all six devices, all rule processing,
identity/permission/PAM checks and the existing outer caps.20s provides2.39s beyond
this run's last input completion; this is a measured experiment, not a proven
reliability margin. Review the nested timing budget and test selection/failure
semantics before another VM. Do not retry unchanged, skip input rules, treat node
presence as initialization or convert the existing failure into success.

The private decoder initially rejected duplicate DEVICE_WAIT packets because the
journal replay repeats the same record. It now accepts only byte/status-identical
copies and records their count; conflicting duplicates still fail. Original raw
serial bytes remain unchanged. No new source/runtime qualification is implied.


Frozen active tier112PASS,0FAIL/BLOCKED/SKIPPED,255NOT_SELECTED in191.088851425s; three declared optional historical subchecks SKIPPED. Peak378.6MiB, zero swap. Full commands, source/artifact identities and per-step durations are retained in the qualification JSON and private records. No new kernel/Denial/Flutter build.
