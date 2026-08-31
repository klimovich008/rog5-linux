# Wi-Fi RPMh observer — passive V11 checkpoint

Wi-Fi remains unavailable. All five radio trials through s12-ret-v5 remain
consumed. This checkpoint added observation only: no candidate, reboot, radio
activation, module load, power-control write, slot change or storage transaction.

## Question and correction

Which S12 request executes, returns or stalls before the reset? Earlier traces
did not observe the actual voltage/enable transaction. This is an R8 evidence
gap, not proof of a defective rail, GPIO or firmware version.

The existing private trace helper now records entry/return for `rpmh_write`,
`rpmh_write_async` and `rpmh_rsc_send_data`, plus native `rpmh_send_msg` and
`rpmh_tx_done` events. The exact arm64 ABI supplies state/count and the first
command's address/data/wait; the native event records every command. The
command wait field is u32, not a request-completion result. Cleanup remains
private-instance-only and the reader still outlives the 600-second rollback.

The private polling threshold is zero. Exact source shows the blocking text
reader already calls `wait_on_pipe(iter, 0)`, so the previous default50 is
**not an explanation for the lost historical trace records**.

## Passive hardware proof

Exact anchored USB and pinned SSH identified the existing V11 boot
`1b24ebf0-e4a1-466c-8197-13904886f5cf`. All26 probes registered and ordinary
UFS runtime activity produced both synchronous and asynchronous RPMh traces.
The sync trace printed `complete: 0` yet had response bit `msgid: 0x10108`,
an acknowledgment, then return0. The async request printed the same complete0
with `msgid: 0x10008` and returned before its acknowledgment. The sanitized
fixture prevents interpreting that printed field alone as sync/async success.

Three markers arrived in152/167/161ms including SSH command roundtrip. This
proves passive delivery, **not** a crash-time latency bound. The original
global kprobe definitions and RPMh enable state were restored; temporary
instance, ownership marker and RAM-only script were removed. Same V11 boot,
Good8.633V/30.1°C, no radio activation or persistent configuration change.

Read-only command DB identifies `smpb11=0x40000`, `smpb12=0x40100`, and
`smpb10=0x40a00`. Driver offsets are voltage+0, enable+4 and mode+8. These are
RPMh resource addresses, not physical SPMI register-bank addresses. A legacy
PM899x S12-bank assumption returned ENODEV on PM8350; no electrical conclusion
or control write follows from that failed identity read.

## Independent postmortem limits

The exact installed slot-B artifact
`2867666cdb07a3956c94359a0b2cb54081a6dff78a129d18eb1102a6fbb0e3a3`
snapshots pstore into recovery RAM before USB. Its persistent-loader mode has
neither recovery-control nor SSH and exports only ACM progress. The second
kexec discards that snapshot/old_log; native V11 cannot retrieve it afterward.
This is not a claim that ramoops overwrites the old console before recovery
reads it. Merely enabling target ramoops is insufficient for end-to-end capture.
The old physical range also overlaps native rmtfs memory and is not yet proven
safe for the proposed target composition. No retention memory was modified.

An independently reviewed capture route must retrieve evidence before that
second kexec. Keep the installed loader and slot-A rescue unchanged. Missing
pstore or trace frames remains inconclusive. No boot-mode preseed experiment
has occurred.

## Verification and next step

- Four fail-first assertions reproduced the missing probe/event/poll controls.
  Seven focused tests now pass in0.012s, including the real sync/async fixture.
- Exact target shell/utilities accepted setup/read/cleanup and all26 definitions.
- Active tier passed, approximately81.95s from log creation to final output,
  versus81.154s at the preceding module checkpoint. No full local CI repeat.
- Kernel/wrapper build time and additional build disk usage: zero.
- A bounded independent built-in-agent review found no remaining defect after
  correcting the threshold claim. This was not Claude Opus; its OAuth review
  attempt had failed before reviewing. No independent approval is invented.

The next radio cycle must isolate the actual S12 RPMh transaction, keep all117
UFS nodes RO and collect reset evidence. Reuse the proven Image/DT/modules,
not a guessed voltage/HPM/order correction, and use a fresh signed composition
and one-use claim. Conditional hw1.1 modules remain offline and separate.

## Fresh observation-only RAM successor

The reviewed observer source passed every job in GitHub run33341626079.
A fresh RPMh-v6 bundle now has identical signed twins, packaged in0.690s
without rebuilding the kernel, DTB, modules or initramfs. Only bundle identity
and the tool archive's trace helper differ from v5. The old sealed tool tree
was preserved; preparation initially refused its copied read-only helper, then
resumed the verified new copy after making that one destination writable.

The exact record is generated from the private build receipt into the existing
repository-owned claim registry. Its non-consuming comparison failed before
registration and now passes, along with all16 generic one-use tests. The exact
production AArch64 verifier accepts the signature/composition in isolated QEMU.
No one-use claim exists yet. Execute only after publication and connected gates
pass; do not change voltage, HPM, supply order, permanent selector or boot slots.

## RPMh-v6 consumed: fallback before the radio probe

Source `dd76b962e976cd98be743987a4059afc423d6291` passed every job in
GitHub33342087834 and full local CI in451.804s. The first local invocation
had stopped at144.548s because the private runner inherited umask077, masking
a deliberately unsafe0755 test directory to0700. The security guard was not
faulty. The focused22 tests passed under022; only the private CI child's umask
was corrected. The rejected log/receipt was retained, not overwritten.

The sole claim was consumed at1788133455.352283. Loading/staging checks passed,
then `systemctl kexec --no-block` returned0 at1788133458.051729. No stage or SSH
from the target appeared. The first subsequent USB device was the vendor
recovery, followed by V11. The controller rejected that new non-target boot;
**no radio probe ran** and the claim must never be retried.

The source USB removal→vendor recovery appearance interval was29.140s. It
does not identify the cause. The private output concatenates stdout/stderr;
the `/proc/kcore` warnings also occur in successful v5, so neither their text
nor apparent ordering establishes a new failure. A zero dispatch result is
not the native reboot syscall result or proof that the target executed.

V11 recovered as`0e1f7746-de4a-4f38-8dce-39769e379ee3`, systemd running, no
failed units, pinned SSH and active state/Tailscale, onlysda/sda23 writable,
Full/Good8.632V/30°C. A fixed read-only PON snapshot, taken with117 nodes RO,
adds one PS_HOLD warm reset: pointer98→118, count5→6. This does not distinguish
normal fallback from panic/restart. The reader was unloaded and services
restored. Temporary management address/8079 firewall access were removed.

The real sequence is`rpmh-v6-fallback-before-probe.json`. Independent review
finds unobserved gates: exitrd invocation, clean-teardown result, executor
admission, syscall return, and source/early-target failure. Existing tests
inject`clean` rather than exercising its calculation. Improve that narrow
coverage and handoff logging; do not change WCN voltage or call this an S12
result. Pstore remains inconclusive through the current B-loader path.

Separately, the existing userspace Tailscale validation client is now online.
Its peer SSH attempt requires an interactive Tailscale sign-in check and did
not authenticate. No peer-SSH pass is claimed and no check was bypassed.

## Handoff evidence correction, not a root-cause fix

The shutdown script now reports each failed teardown operation, each execution
gate refusal, executor entry and any returned status. Cleanup ordering and
normal fallback are unchanged. The syscall-only executor preserves errno1–125
as exit status;111 also represents other/invalid returns and is not an exact
errno assertion. A returned0 still triggers fallback, never retry.

Twenty fail-first cases demonstrated the missing records/status preservation.
The expanded tests now replay all12 tracked teardown failures (zero execution)
and all-clean teardown (one execution), explicit returns including0, metadata
refusals, static twins and injected AArch64 syscall results under QEMU. The
existing active-tier string assertion was updated without changing its guard.

An optional fixed-device serial logger is bound by the existing tools manifest.
It accepts only one bounded ASCII record, opens a tty with O_NONBLOCK and
O_NOFOLLOW, never creates a file, and refuses regular/block devices. Missing
or backpressured observation is advisory and cannot change execution eligibility.
PTY tests cover delivery, buffer saturation, invalid text, missing devices,
regular files and symlinks. Only trials carrying the logger add an API-only
devtmpfs mount so output survives detachment of the old API mounts.

The unchanged V11 kernel already contains ACM support. A temporary NCM+ACM
configuration was added through the exact UDC, with rollback on setup failure.
NCM/SSH survived re-enumeration, and the anchored serial endpoint delivered a
complete CRLF marker in164.8ms. The exact sealed BusyBox1.37 lacks nonblocking
dd output; no GNU behavior was assumed. The new static ARM64 logger, tested
inside the actual exitrd with a private mount namespace and its BusyBox-mounted
devtmpfs, delivered the exact record in214.8ms. That namespace and test binary
were removed; no phone reboot or storage write occurred in these passive tests.

Source audit then found that `u_serial::gs_close()` ignores O_NONBLOCK and
can wait15s for its FIFO. The initial PTY test did not exercise that driver
behavior. A fail-first close-wait fixture timed out; the corrected logger uses
a periodic250ms signal, explicitly unblocked and without SA_RESTART, to
interrupt that drain wait. The timer remains armed through close. This bounds
the interruptible wait, not an uninterruptible kernel fault. No kernel patch
was required. The earlier unbounded-close test binary was retained, not reused.

The final raw+bounded ARM64 twins match. On the actual source kernel,24 calls
without an application reader completed in2.1785s; a following exact LF record
arrived through the sealed exitrd/ACM path in164.5ms. Seven focused tests pass,
including ignored/blocked SIGALRM, modeled close backpressure and raw/no-echo
TTY setup. This is normal-driver evidence, not an uninterruptible-fault bound.

An earlier private host probe stalled in `tty.setraw`'s default TCSAFLUSH after
its24 target calls had already completed in4.2308s. The host stack/wait channel
and interrupted Python traceback identify that separate setup error. Existing
repository collectors already use TCSANOW; the corrected probe does too,
with CLOCAL/CREAD. It did not consume a phone candidate or indicate a kernel
failure. Keep that non-draining setup for the next source-serial collector.

Both tiny helpers reproduce in their pinned builders. No kernel Image was
rebuilt. This proves runtime logging components, **not** successful shutdown-
time collection, kernel handoff, or crash-surviving evidence. No successor has
been created or consumed after v6; slot A and the installed loader are unchanged.
