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
