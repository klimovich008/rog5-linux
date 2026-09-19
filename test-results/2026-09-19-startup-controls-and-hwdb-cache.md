# Startup controls, hwdb cache and TCG mode — 2026-09-19

**The latest close-only Denial VM remains FAIL at accessibility/portal startup;
its app-release probe was NOT RUN. The original startup-only control passed. The debug and cached multi-TCG runs
remain FAIL for incomplete timed-out timing queries. The cached multi-TCG run
also reproduced the earlier RCU signature. The single-TCG run reached authentication, cleanup and poweroff in 174.734s without an RCU report, but remains FAIL: its query timed out after five of nine required unit rows.**
Mousepad close exit 137 remains open. No Denial session ran in the four startup-only guests. A separate fifth VM
ran Denial as described below. No phone operation occurred. Component observations do not promote failed runs.

## Source and scope

VM source `ec8890c4d50c978749acf248e094e78762efe9d1`, tree `8df1b441b0aaded61f46ca2c60e87f068bb510da` remained unchanged during
all four runs. The subsequent runner change is `c49cd51d738642b3f3a036ac8b73b39657ca9c79`, tree `88142a2d67a9a222074edec20c73caea37d90753`;
its local integrated test result is retained separately. Generic ARM64 kernel is pinned Linux
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`, Image SHA256
`2b1c8d95f54dda28e772df82be54af7508b2ce84183f1b0024a7f14e3d5ce0fc`.
The retained Arch runtime, Denial payload and compiled PAM/seat probes were reused.
The initial control harness rebuilt its existing small probes; the other three
startup-only runs reused all compiled artifacts without a kernel/Rust/Denial/
Flutter rebuild. The separate fifth app trial reused Denial, Flutter and the
kernel, but rebuilt its small Rust probes and guest init through the standard
harness (Rust steps 6.231s and 6.632s).
All guests use two virtual CPUs, 1 GiB RAM, 2 GiB/no-swap host memory, 2 CPU/64 PID
host limits, network disabled, readonly runtime/payload and retained VirGL render
node. Each retains the 300s QEMU and existing guest deadlines and 8 MiB serial-log
bound. Single-TCG changes host execution scheduling, not guest CPU count.
These are VM identities, not installed phone or signed candidate identities.

## Executed results

| Run | Overall | QEMU host-monotonic seconds | Timing query code / rows | RCU reports |
|---|---|---:|---:|---:|
| startup-multi/vm | PASS | 204.749 | 0 / 9/9 | 0 |
| startup-debug | FAIL | 211.365 | 124 / 8/9 | 0 |
| startup-hwdb-compressed | FAIL | 291.691 | 124 / 8/9 | 1 |
| startup-hwdb-single | FAIL | 174.734 | 124 / 5/9 | 0 |

Authenticated readiness, scope cleanup and normal poweroff are independently
recorded per run in the qualification. No incomplete timing inventory is called
PASS. The control hwdb rebuild took 12.409384 systemd-monotonic seconds; debug
rebuild took 13.339646s. The cached multi-TCG record has ConditionResult=no and
zero ExecMain start/exit timestamps: generation was actually skipped despite
that run's overall FAIL. Cache RAM staging took
3.820 BOOTTIME seconds.

Do not subtract BOOTTIME handoff/staging from systemd CLOCK_MONOTONIC timestamps.
Whole QEMU durations share a host monotonic clock, but this ordered comparison
is not statistical speedup/reliability proof. The multi-TCG RCU delay makes its
total unsuitable as a clean cache-speed control.

## Failed diagnostics and repeated RCU evidence

Both debug and cached multi-TCG queries authenticated to the private systemd bus
and received eight GetAll replies, then sent the ninth sysinit.target request
without a recorded reply before code 124. The strict parser correctly rejects
failed packets/incomplete inventories. No parser relaxation or query-deadline
extension was added. All 28 recorded debug inputs were freshly rechecked because
the original wrapper stopped before its final hash loop. Cached and single runs
perform their input/runtime verification even when qualification fails.

All 17 system generators and one environment generator returned success in the
debug log. Its 6.3s message measures unit loading/initial transaction, not
generator duration. No per-query timing attributes all eight seconds to the
ninth call. Packaged tmpfiles reports Result=success despite ExecMainStatus 73;
do not rewrite that as every unit exiting 0. Global logging may perturb timing,
but the cached multi-TCG timing failure also occurred at normal INFO level.

The exact kernel disassembly places an earlier CPU0 sample at `dsb ish` after
TLB invalidation, and CPU1 immediately after `copy_page` returns. The cached run
again sampled CPU1 at PC/LR `0xffff80008001f818` during `(sd-gens)`, with the same
seven-address fault stack. An earlier matching run predates both the new unref
probe and icon-cache integration; neither is necessary to trigger the symptom.
A sampled PC is not proof of a loop or a QEMU defect.

Read-only host samples during the same cached VM cover 2.012019s. Two likely TCG
threads received 1.625755s and 1.599836s CPU, with 0.078002s and 0.084167s runqueue
wait; the record does not prove their guest-vCPU mapping. Cgroup usage increased
3.898688s, throttling 0.093662s, and memory remained about 1.58 GB with zero recorded
OOM events or swap. This disproves continuous host descheduling only in that
short window; it neither explains the prior stall nor excludes other pauses.
The audit's original serial-prefix hash is explicitly not a terminal log hash.

The one controlled follow-up changed only `tcg,thread=multi` to
`tcg,thread=single` and the owned container name, retaining the same initramfs,
cache, runtime, kernel, payload, two virtual CPUs and all limits. Its result is
above. Do not infer the cause or silently replace the multi-TCG failure.

## Cache path actually exercised

The preparer revalidates the authenticated real-symlink runtime and mapped VM
view, executes its actual ARM64 `systemd-hwdb --usr update` under explicit QEMU
userspace in network-isolated bwrap, then queries a synthetic USB modalias. The
expected vendor/model matches packaged text; no hardware is queried. Canonical
runtime bytes remain unchanged. Generation took 4.678s,
query 0.067s, and preparation including full input
verification 41.720s.

Cache SHA256 `f08f47c0b7054020ad7671e78d85b4d0633a4a88887f06e61e63085505484655`, 13996390 bytes.
The guest copies its decoded udev directory into RAM, verifies compressed and
expanded cache identities, installs package mode 0444 and bind-mounts the private
directory at `/usr/lib/udev`. No unit, mask, drop-in or update stamp is changed.
The packaged condition expressions naturally skip generation when the /usr
cache exists and /etc overrides are absent. The linker cache remains separately
bound. Full runtime byte/symlink/mapped metadata verification passed afterward.

Review found missing source-revision and exact-runtime/mount guards before
execution; both were added. The final review is source-only evidence, not an
additional runtime test. The cache remains a private experiment, not a public
runner option or installed mobile package.

Initial assembly failed before any VM: expanded 14 MB exceeded the existing
8 MiB cpio output cap (SIGXFSZ). Original recipe and FAIL are retained. Gzip
transport kept assembly within the same cap and the guest checks both byte
identities. No bound was raised.

## Actual close-only Denial follow-up on the tested runner

This separate run uses `c49cd51d738642b3f3a036ac8b73b39657ca9c79`, tree `88142a2d67a9a222074edec20c73caea37d90753`, and the public
`--tcg-thread single` option. Its command differs from the retained multi-TCG
app trial only by the explicit mode and fresh output. All 37 other recorded input
hashes match; the runner difference is recorded explicitly. Source-only review
caught and closed the original same-paths-versus-same-bytes comparison gap.
Live container inspection confirmed single-threaded TCG, two virtual CPUs and
1024M guest memory. The private hwdb cache was not used in this run.

The QEMU operation lasted 278.116s; full harness
321.745s. Overall FAIL: `application transport closed
before approved teardown`. Serial evidence contains normal guest poweroff,
but the host container step exits -9 on the observer error; these are distinct.
Zero RCU reports is an observation, not a fix or reliability qualification.

PAM opened the mobile session; launcher overrides were prepared. Denial ran and
logged 6 raster frames/6 page flips/6 vsyncs before teardown. These terminal counters
are limited VM rendering evidence, not a qualified app session or phone graphics.
No app mapped, no pointer action/screenshot was taken, no release-probe stage was
recorded, and no approved teardown token was sent. Mousepad teardown remains
NOT RUN in this trial, preserving the older exit 137 failure.

The exact failing boundary precedes the app flow: the four requested
accessibility/portal units in `qualify_activated_services()` did not satisfy the
existing 25s start command. The observed CLOCK_MONOTONIC bracket is
227.455459984 to 254.238179008 (26.782719024s including clock/command overhead),
status 124. The subsequent 3s service snapshot also returned 124, so this evidence
does not identify the lagging unit or its root cause. Denial cleanup reported
launcher 143, and the guest reported `FAIL local PAM fixture: session child
failed: exit status: 124`. A /var unmount failure is retained despite final
poweroff. Do not attribute these failures to hwdb cache omission or change
service deadlines from this evidence.

Run command: `python3 /home/deck/.local/state/rog5-app-unref-single-20260919-r1/run.py`. Input and complete runtime byte/symlink/mapped
metadata verification passed after failure; owned container absence was checked.
The command, result, review, recipe, logs and analysis hashes are retained in the
[separate app qualification](2026-09-19-single-tcg-app-control-qualification.json). This run answers whether single-TCG alone reaches the release
probe: it did not. No identical retry was made.

## Reproduction and next action

Private commands, already executed; existing output directories must not be reused:

- `python3 /home/deck/.local/state/rog5-vm-startup-stall-20260919-r1/startup-multi/run.py` — PASS; full harness254.855s.
- `python3 /home/deck/.local/state/rog5-vm-startup-stall-20260919-r1/run-debug.py` — FAIL, incomplete diagnostic; guest normal poweroff observed.
- `python3 /home/deck/.local/state/rog5-vm-startup-stall-20260919-r1/prepare-hwdb.py` — PASS, 41.720s.
- Initial expanded `run-hwdb.py` revision — FAIL assembly; VM NOT RUN.
- Current `python3 /home/deck/.local/state/rog5-vm-startup-stall-20260919-r1/run-hwdb.py` — FAIL incomplete query; RCU, cache skip and normal poweroff recorded.
- `python3 /home/deck/.local/state/rog5-vm-startup-stall-20260919-r1/run-single.py` — FAIL; exact command and timing in paired evidence.
- `python3 /home/deck/.local/state/rog5-vm-startup-stall-20260919-r1/audit-debug.py` and `summarize-startups.py` — offline replay/descriptive decoding; failed packets stay failed.

Every owned container is absent after its run. All exact commands, recipes,
source/binary/cache identities and observed unit rows are in the paired
qualification JSON. The new runner option adds three regression cases covering
real argument parsing and emitted command construction. The three-test class fails against the
old source with five subtest errors (the invalid-mode rejection case already
passes), then all three pass normally and under Python -O. All 93 runner
tests passed in 14.097s. One frozen active-tier execution returned
exit 0 in 175.549s at `c49cd51d738642b3f3a036ac8b73b39657ca9c79`.
All 109 suites passed; FAIL/BLOCKED/SKIPPED suites 0, NOT_SELECTED 255.
Three declared optional historical artifact subchecks were skipped (charging
archive, retained trial-state ARM binary, and PMIC rail-reader ARM binary).
Its JSON/JUnit summaries remain in `/home/deck/.local/state/rog5-vm-startup-stall-20260919-r1/active-report`. These are personally
executed local checks, not imported CI. Publication checks are separate. No phone contact, signing,
admission, claim consumption, installation or protected-storage mutation.
S06/R01 remain FAIL; real OLED/touch/Adreno and native-phone acceptance remain open.

The single-TCG close-only VM reached Denial rendering and normal guest poweroff without RCU, but service-start timed out 124 within the existing 25s bound before either app mapped; the 3s unit snapshot also timed out. App release probe NOT RUN. Capture which accessibility/portal job remains pending using a bounded diagnostic that preserves partial replies, then change only a demonstrated cause before another full app trial. Do not increase deadlines or retry unchanged. Startup controls remain FAIL where inventories are incomplete; Mousepad exit 137, S06/R01 FAIL and phone physical NOT RUN remain open. No phone authority.

## Publication verification

Eight mobile-status regressions passed in 0.090s. Artifact inventory initially
rejected duplicate ownership of a combined qualification output. The startup
and app qualifications now have distinct files and source identities; all 550
historical artifact rows remain unchanged. Final inventory check passed in 0.080s
(552 sets), generated status in 0.043s, and whitespace in 0.044s. Initial failure and
both check records remain under the private startup investigation. Large/private
byte checking and physical admission are outside that inventory check; the
actual VM wrappers verified their inputs separately. No integrated rerun was
needed for this evidence-only publication after the frozen 109-suite result.
