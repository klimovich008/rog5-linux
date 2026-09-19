# Full Denial VM MOPS control — 2026-09-19

**FAIL: whole-VM deadline; Mousepad mapped and visibly rendered; Foot and
controlled teardown NOT RUN. No RCU stall observed in this one run.**
No phone operation, signing, candidate, claim or protected-storage mutation.
Physical rows remain NOT RUN and S06/R01 remain FAIL.

## Identity and comparison

Executed source `96b44f257d29e3cf99a4f798a68329a9afaf74bf`, tree
`11f5c6837987699e4ffef59299916cb72e1b59d0`. No implementation changes this
turn. The previously executed111-suite active PASS at `bc8918e1` is reused
after confirming unchanged scripts/tools; it was not rerun. Its counts are
111 PASS,0 FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED, plus three declared optional
historical subchecks SKIPPED. Prior goal turn was progress.

Compared with the preceding r2 VM, the command adds only `--disable-mops`
and fresh output paths. The guest confirms `arm64.nomops` on its command line.
All declared input hashes match: kernel, Denial/Flutter, payload, caches,
helpers and observer. Both use single TCG, two guest CPUs,1GiB guest RAM,
2GiB container RAM/no swap, network disabled and read-only runtime backing.
No Denial/Flutter/kernel rebuild; the usual tiny harness probes are assembled.

An initial exact initramfs-member comparison failed on `apps-observe-token`.
Source inspection confirms a new UUID is required for each observer session.
The corrected comparison verifies25 of26 member bodies equal; the sole body
difference is that correctly formed fresh token. Other header changes are only
inode/mtime. Archive bytes are not identical. Tokens were not reused or
published in this report. This does not change the executable/policy comparison.

## Executed result

- Device readiness passes at boottime168.80–169.37s under the8s limit.
- Decoded PAM snapshots confirm local active tty1, user manager and mediated
  devices. Denial activates; its pre-service monotonic sample is235.521630496s.
- The40s service boundary is entered. The actual controller later emits
  `flow-ready`, which follows successful service-state and document-FUSE checks
  in the executed source. Exact completed service timestamps were not captured;
  no precise portal-duration comparison is claimed.
- The observer matches the home launcher and clicks Mousepad. Protocol evidence
  attributes its mapped surface and keyboard focus to the owned Mousepad process.
  The retained VNC screenshot visibly shows the Mousepad title, menu and editor.
  This visual inspection supplements, rather than rewrites, the raw observer's
  `visual_semantics=NOT RUN`. Attributed presentation feedback remains NOT RUN.
- The observer sends the return-home gesture, but the300s whole-VM deadline
  expires before its completion, Foot launch or teardown approval. Text entry
  was outside this close-only probe and remains NOT RUN.
- No RCU stall is observed. No terminal rendering counters, PAM close or normal
  guest poweroff were captured. Host cleanup succeeds and the container is absent.
- Harness duration358.303s; wrapper358.374s includes identity checks. All declared
  input hashes and complete original/mapped runtime bytes/metadata are unchanged.

One stall-free run does not establish a MOPS cause or justify changing the
default CPU feature policy. The preceding normal run's RCU failure is retained.

## Next bounded correction

The existing test has a300s whole-boot deadline,145s combined PAM deadline,
40s service start and60s app flow, with separate cleanup bounds. The host's30s
cleanup reserve is available only after approved teardown; it correctly does
not extend an incomplete app flow. Here startup consumed most of the host
budget and the first app only reached buffer activity near guest299s.

A source-level counterexample to assuming a full app window is available:
a flow starting at270s may legally run until330s under its own60s bound, but
the host kills it at300s even if it continues to make progress. The guest PAM
limit is another independent cap and must be included. This is an observation
budget limitation, not evidence that the gesture is broken or that more time
will make it succeed. Reconcile the nested VM bounds with explicit startup,
flow and cleanup limits before another run; preserve all required app actions,
failure propagation and resource limits. Do not repeat unchanged or extend
deadlines implicitly on arbitrary progress messages.

Private commands, logs, token-safe comparison and screenshots are retained in
`rog5-denial-session-resume-20260919-r3` under the local state directory.
The [qualification record](2026-09-19-denial-nomops-session-qualification.json)
binds the exact command, inputs, screenshot hashes, reused tests and failed result.
