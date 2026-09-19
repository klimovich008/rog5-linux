# Nested VM session budgets and FUSE readiness — 2026-09-19

**Host correction PASS; VM FAIL before PAM; extended session runtime NOT RUN.**
No phone operation, signing, candidate, claim or protected-storage mutation.
Accepted server/rescue, signed fallback and all earlier failures are preserved.
Physical rows remain NOT RUN; S06/R01 remain FAIL.

Starting HEAD `407846dfacd03a9fffc37c4efb84781f66696421`, tree
`d45a224768fdf7e5c8b19b6ea735e39a7e5b284a`. Frozen tested/executed source is
`4752ea529197af94390c170afa5199ed633b0949`, tree
`a6416acf31d933df0c123e3c7f5224740f0a2013`. Previous turn was progress:
Mousepad was visibly mapped in the full MOPS-disabled control, before its
whole-VM deadline cut short the two-app flow.

## Correction and regression

The old full-session parents allowed300s host,170s fixture and145s PAM. The
retained service start at235.52s plus a permitted40s portal wait,60s app flow
and30s cleanup cannot fit the former host limit. PAM begins before compositor
preparation and also needs room for those later stages.

Only the full combined VM now receives420s host,240s fixture and210s PAM.
These fixed budgets reserve180s boot plus240s fixture,30s surrounding fixture
work plus210s PAM, and60s preparation/40s services/60s flow/30s cleanup plus20s
PAM scheduling margin. These are fixture budgeting allowances, not measured
performance guarantees or new permission to extend a stage indefinitely.
All inner service, app, cleanup, output and resource limits remain. The existing
single30s host cleanup grace still requires approved teardown before cutoff.
Basic logind remains180/65/45s; startup-only remains300/170/145s.

Changed files: `scripts/host/test-qemu-logind.py`,
`scripts/host/test-qemu-logind-runner.py`,
`tools/qemu-virtio-drm/logind-boot.sh`, and
`tools/qemu-virtio-drm/logind-session.sh`.

The new regression evaluates the actual runner deadline expression, executes
the guest timeout-selection block and generates the actual temporary service
unit. It fails before the fix. The first focused run then exposed an existing
call-site fixture missing `startup_only`; supplying the real argument shape
corrected that fixture. Final20 focused budget/cleanup/CPU-mode cases PASS
in0.844s wall time. Active tier executed once on frozen source:111 PASS,
0 FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED, three declared optional historical
subchecks SKIPPED;179.663s,528.7MiB peak,0swap. These are local results, not CI.

## One bounded VM

The command retains the previous explicit `--disable-mops` control, single TCG,
two guest CPUs,1GiB guest/2GiB container RAM, no swap/network, retained runtime,
kernel, Denial/Flutter, caches and observer. No large component rebuild. Only
the three changed consumed scripts differ; remaining declared inputs match.
Complete runtime bytes/metadata and input hashes pass post-run preservation.

The VM fails the eight-second initialized-device wait: boottime145.10–154.05s,
producer status1 with an explicit initialization-timeout diagnostic. The later
database-first snapshot captures all six entries before slower queries expire:

| Device | Later udev database observation |
| --- | --- |
| DRM card | Present,261bytes |
| Pointer event | Present,292bytes |
| tty1 | Present,0bytes; valid empty database |
| FUSE | Absent at `/run/udev/data/c10:229` |
| Keyboard event | Present,340bytes |
| Observer port | Present,61bytes |

This is a post-failure observation, not an atomic capture at the wait cutoff.
It narrows the missing initialization evidence to FUSE; it does not establish
why the database is absent. The node itself is character10:229,root:root,0666.
The later per-device/journal portion times out124 after3895bytes, with no output
truncation. The earlier bounded database diagnostic is now exercised in a real
generic VM; its previous NOT RUN result remains historical.

The packaged coldplug service had already completed before sysinit/fixture
startup. Its ordering therefore disproves a simple missing-before-coldplug
hypothesis. Packaged rules set FUSE0666/static-node; the pinned systemd source
expects even empty character-device databases. Node presence and permissions
are not substituted for the required initialization receipt.

PAM, Denial/apps and the extended session limits are NOT RUN in this attempt.
No RCU stall was observed. Normal guest poweroff passes the existing RCU-aware
check, while a `/var` unmount failure remains recorded. Host cleanup succeeds;
owned container absent. Harness229.445s; wrapper229.513s.

Next isolate FUSE event/database processing, preserving the initialized-device,
permission, PAM and actual FUSE mount checks. Do not repeat the unchanged VM,
increase the device wait or claim the session-budget repair runtime-qualified.
Private exact commands and logs: `rog5-session-budgets-20260919-r1` in local
state. [Qualification record](2026-09-19-session-budgets-qualification.json).
