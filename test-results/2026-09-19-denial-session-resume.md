# Denial VM session resumption — 2026-09-19

Scope: generic ARM64 VirGL VM on the Deck, not ROG5 GPU/touch evidence.
No phone, USB, signing, claim, candidate or protected-storage operation.
Previous turn: progress from exact upstream/community source comparison.

## Source and executed inputs

Starting project HEAD `70ca0c4eed28fb95c9d45dce750f7f6b76f47210`, tree
`46c3a4726e6c27abd02581d9cc95c1467c388d37`. The retained r1 VM used this HEAD.
Community audit notes were committed separately as `ac2d5c46`.
Frozen implementation `bc8918e19920722ef35766afebfde245c173d7e6`, tree
`d8609f6db52e315079c9e6e6932e2caac79ad243`, is the tested and executed r2 source.
Only `tools/qemu-virtio-drm/logind-denial.sh` changes among the prior VM inputs.
The test change is in `scripts/host/test-qemu-logind-runner.py`.

The retained kernel Image is SHA256
`2b1c8d95f54dda28e772df82be54af7508b2ce84183f1b0024a7f14e3d5ce0fc`.
Both runs use default max CPU features, single TCG, two guest CPUs,1GiB guest
RAM, the retained Denial/Flutter runtime, prepared caches, render audit off,
network disabled, read-only backing and the existing host render node.
The 300s outer VM deadline and conditional cleanup allowance are unchanged.
No Denial/Flutter/kernel rebuild. Tiny harness probes are built normally.

## Observed failure and bounded mitigation

r1: all six virtual devices pass readiness at155.60–158.75s. PAM/logind and
mediated devices pass. The service-start command returns124 under its25s
limit. Its monotonic pre-start sample is221.827817728; the decoded journal
records GTK portal ready255.137549 and main portal ready257.538722:
35.710904272s after that sample. These samples do not identify the precise
external timeout arm instant. Readiness after failure cannot retroactively
pass the gate. The service snapshot also times out with124.

Denial's retained terminal counters show4 raster frames,4 page flips and4
vsyncs. App observation never becomes ready; no app mapping/close success,
text entry or visual semantics are established. PAM closes and the guest
powers off normally without an RCU warning. Shutdown also reports failure to
unmount `/var`; normal poweroff does not erase that failure. Harness time
332.224s; original result remains FAIL.

Set this VM-only service allowance to40s based on observed readiness around36s.
Service-state/FUSE requirements, error propagation, clocks and outer deadlines
remain. This is a bounded timing mitigation, not a startup-performance fix.
A virtual-elapsed-time fixture executes the actual service function: readiness
at36s fails before the change and passes afterward; never-ready still returns124
and prevents clients. Nine focused service tests pass in0.492s wall time.

Final active tier:111 PASS,0 FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED,
three separately declared optional historical subchecks SKIPPED;181.433s,
370.1MiB peak,0swap. The runner suite includes125 cases. This tier was actually
executed once on the frozen source, not inherited from prior CI.

r2: FAIL at the unchanged300s host deadline; harness359.323s. An RCU self-stall
occurs before normal systemd startup. Against the matching retained ELF it
resolves to `copy_user_highpage+56`, followed by `handle_mm_fault` and the ARM64
page-fault path. This repeats an earlier sample location and does not establish
a cause or that the copy instruction itself consumed the reported interval.
Device readiness later passes208.96–210.08s. Encoded PAM snapshots confirm the
active local session, mediated devices and activated Denial; the40s service
start begins at274.177686128, but no terminal service result is captured before
the outer deadline. Therefore the new timing allowance is runtime UNQUALIFIED.
No completed app flow, terminal render counters or guest poweroff are claimed.
Host cleanup completes and the owned container is absent.

A late snapshot of the actual container cgroup reports no local CPU throttling,
no memory-limit/OOM events and peak1833091072bytes. It does not measure every
ancestor or rule out other host scheduling causes. Both runs' complete runtime
bytes/metadata and declared input hashes pass post-run preservation checks.

## Next action and retained limits

Do not repeat the same VM or increase the outer deadline. The smallest distinct
comparison is the existing `--disable-mops` option on the full Denial workload,
with the same cache/payload/limits. Earlier anonymous/file-backed microprobes
and startup-only comparisons do not establish this full-workload behavior and
do not justify a MOPS workaround. Preserve all earlier failures.

This turn made progress through stage-specific evidence and a host-tested
bounded mitigation; real-phone acceptance remains incomplete. S06/R01 stay FAIL,
mobile physical rows NOT RUN, accepted server/rescue and signed fallback intact.
Private exact commands, logs and identities are under
`rog5-denial-session-resume-20260919-r1` and `-r2` in the local state directory.
The [qualification record](2026-09-19-denial-session-resume-qualification.json)
binds source, inputs, failed-before/passing-after checks and both VM outcomes.
