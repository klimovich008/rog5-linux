# Launcher diagnostics and observed no-pan typing — 2026-09-13

The corrected shell completed visible **test → tes → test** in the ARM64 VM,
with the OSK remaining open and no scripted viewport panning. Mousepad/Foot
launcher switching and all12 expected key press/release events passed. **The
overall VM remains FAIL:** Mousepad returned137 during approved cleanup; Foot
returned0. Successful typing does not supersede the client-cleanup failure.

No phone contact, signing, admission, claim consumption, phone candidate,
installation or protected-storage operation occurred. Physical rows remain
NOT RUN; S06/R01 remain FAIL. The native phone goal is still active.

## Implemented diagnostic change

The old runner terminated the VM after observer failure before the guest printed
its retained compositor log. Two bounded snapshots now travel through the
existing atomic evidence writer, before launcher readiness and five seconds
later. Each snapshot is at most32KiB including framing; the host rejects more
than64KiB in aggregate. FIFO opening and the complete producer pipeline have a
three-second timeout and one-second forced termination allowance. Long lines
and the tail are deliberately truncated; snapshots are not complete logs.

`DENIAL_DIAGNOSTIC` records are retained as data and excluded from client,
readiness, terminal and acknowledgement oracles. Embedded success text cannot
approve a session. Producer errors remain errors. The new regression is mandatory
in the existing relevant tiers; current public commands and original deadlines
remain. No icon or shell behavior was changed for this VM.

Source `35b23112454ab9f9a021c46cff4abe33d967be5e`, tree `01a946904223a8f51e8d77606e3b7d6271a17f70`.
The ARM64 writer build passed in1.005s;
its SHA256 is `873201eb160d83a017ba21a572d2f67029ba010255b956ee45001df6959d1675`.
The shell remains source `43ec481d5409288a8eb28dfd0f31c1781a9535be` and native compositor
remains source `daf4b119d5d45334cea00dec774e26e24d44fa23`. The exact existing archive
`cc07a0966cd878bc9ec5c8138c9ab37f079cd4501511fad18cdf19244913dc48` was reused. Kernel, engine and runtime inputs stayed
unchanged. All31 declared VM input files passed post-failure streaming checks.

## Checks personally executed

| Check | Result |
| --- | --- |
| Writer before diagnostic allowlist | 2 expected failures; existing16 host cases and3 Rust units pass |
| Corrected writer | 18 host cases and3 Rust units PASS |
| Snapshot bounds/errors/deadlines, Python-O | 7 PASS3.102s |
| Real host writer plus actual snapshot pipeline | 7 PASS3.092s |
| Socket/parser/ACK regression suite | 51 PASS2.932s |
| Actual guest supervisor host fixtures | 24 PASS4.745s |
| ARM64 helper build | PASS1.005s |
| Diagnostic VM | FAIL294.635s; typing/app-switch subchecks passed, client cleanup failed |
| Integrated active tier | {'PASS': 103, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255}; 159.579s |

Three declared optional subchecks were SKIPPED; no mandatory suite was skipped
or blocked. The active run peaked at573.8MiB with no swap. No new remote GitHub
CI result is claimed. Exact commands, timings, input/output hashes and private
trace locations are in the qualification JSON.

## Observations and limits

The launcher icons were visible in the first readiness capture. Their prior
absence did not reproduce; there is no demonstrated icon fix, and additional
diagnostic work can alter scheduling. The snapshots delivered47,757bytes of
real compositor output without gaining any qualification authority.

Original-resolution captures show test, then tes after backspace, then test
again while OSK remains open. The native protocol oracle received all12 expected
key events while focused. The app focus sequence was Mousepad → Foot → Mousepad
→ Foot. This VM covers top-line caret visibility and the no-pan typing path;
actual bottom-edge displacement, rotation and phone touch need separate proof.

The observer sent its exact ACK only after its actions and protocol checks
passed. Approved teardown began; Foot exited0, but Mousepad reported
`phase=normal-close status=137 child_status=137`. Real terminal counters show
185 raster frames and185 page flips with no reported render errors. The VM
powered down normally, but authenticated session/scope cleanup failed; these
partial results must not turn into an overall PASS.

The unchanged editor supervisor runs `timeout -k 2 65 mousepad` and sends TERM
to that wrapper for controlled close. In the guest, surface destruction began
around00:04:24.015 and buffer cleanup was still progressing around00:04:25.868,
about1.85s later. There is no retained signal-sender trace and no OOM message.
The65-second natural deadline is not shown to have elapsed.

A cheap host fixture used the actual supervisor and unchanged timeout arguments.
A0.1-second TERM handler exited0; a2.5-second handler returned137. Strace shows
the timeout process forwarding TERM then sending SIGKILL two seconds later.
This establishes the host escalation mechanism; it does not identify the sender
in the VM or explain why GTK teardown was slower there. Limits were not raised.

Next smallest experiment: add sender-specific timeout diagnostics and
same-clock close-start/reap observations to the VM-only supervisor, retaining
its current bounds and exact shell/native inputs. Confirm the escalation before
changing grace or treating137 as a clean result. Keep the earlier icon and
keyboard failures as historical evidence.

[Exact commands, identities and evidence](2026-09-13-launcher-diagnostics-qualification.json).
