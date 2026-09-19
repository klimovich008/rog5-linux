# VM coldplug priority and corrected-child qualification — 2026-09-19

Generic ARM64 VM only; no phone operation, new candidate, signing, admission,
claim consumption or protected-storage mutation. Physical NOT RUN. Preserve
ASUS slot A, signed fallback, accepted server/rescue, buttons/LED and S06/R01 FAIL.

Starting source03d06168c2183846dc16700995f9d62bb8a9da33, tree
5b261d35735f227b021149b1706fa501c476387a. The previous turn was progress:
it observed both apps and corrected the Rust child watchdog offline.

## First VM: useful failure before PAM

Private `rog5-pam-child-session-20260919-r1` ran the unchanged corrected source.
The rebuilt ARM64 PAM helper matched the previous offline output exactly:
e19a41da1a425ffdd434f84d0f222c3fb8b805e127aaba6a4e252265538cb004,564224B.
The prior111-suite integrated result was reused after matching implementation
bytes; no unchanged host tier, kernel or Denial build was repeated.

The VM failed before PAM in250.715967495s (wrapper250.790211047s). Its original
initialized-device wait ran boottime160.02→169.82 and returned1 with an explicit
initialization timeout. A later database-first snapshot captured input/tty
entries but absent DRM c226:0, FUSE c10:229 and virtioport c252:1; property-query
capture then reached its3s deadline. The original failure remained fatal.

The new10s failure-only diagnostic executed successfully. Its BEFORE-retrigger
snapshot already showed an empty FUSE database. The journal contains original
coldplug event1608 creating that database (receipt173.255866) and completing
(receipt173.255946), before diagnostic event1634 at178.713289. The bounded
retrigger and independent initialization reader both returned0. Thus the
retrigger did not create the first database. This run demonstrates late original
FUSE processing, not database loss or a successful retrigger repair. Journal
receipt times are observations, not guaranteed exact transition timestamps.
DRM/virtioport late completion is not independently timestamped here.

The failure-only diagnostic is now exercised in a real generic VM. Corrected
PAM/application lifecycle is still NOT RUN in this arm because readiness failed.
The ignored network-namespace warning is not established as the cause. Original runtime
bytes/metadata and input hashes passed post-run checks; no containers remained.

## Scoped scheduling change

Pinned systemd3255daee1572366b74fe92f002a3d60ecbb27103 (v261.3) processes
prioritized subsystems in list order and promotes their already-enumerated
ancestors, sorting parent-before-child within groups. Existing --type=all covers
those ancestors. Trigger queues events; it is not a completion barrier.

The packaged priority list includes module,block,tpmrm,net,tty,input. The combined
VM now stages a RAM-only drop-in appending drm,misc,virtio-ports. It preserves
the original command, action, type, ignored trigger-exit convention and priority
prefix. Exact initialized-device/permission/PAM/FUSE-mount gates and all deadlines
remain. No global settle or device-unit dependency was added. Basic fixture
policy is unchanged. A changed packaged command or existing override refuses
preparation instead of being silently replaced. The retained vendor unit is
unchanged (SHA42e585c2859b76e4106b64b915dc900f1e5390bf32686a9181acd95eea1c7064).

This is an evidence-led queue-order experiment, not a guarantee of timely
processing. It addresses the observed virtual consumers, not phone udev policy.

Files: tools/qemu-virtio-drm/logind-session.sh (generator), logind-boot.sh (call),
and scripts/host/test-qemu-logind-runner.py (executable fixture regressions).
The regressions execute the actual generator, inspect command semantics,
preserve vendor bytes, refuse changed/multiple commands and existing overrides,
and retain the basic fixture. Existing failed-initialization regressions remain.
No duplicate model of systemd's sorting algorithm was introduced.

Frozen source d579cbca43983d754cf9bee2f52933a6911b41b2, tree
dacf7020a7337061edab499f871bcab47ec2230b. Old source lacked the required generator;
the initial focused regression failed. Final24 focused cases passed12.820s;
actual-package staging passed0.008177951s. Integrated active tier111PASS,
0FAIL/BLOCKED/SKIPPED,255NOT_SELECTED,three declared optional subchecks SKIPPED,
182.522658039s,498MiB peak,zero swap. All commands and logs are retained privately.

## Comparison VM

The comparison at d579cbca also FAILS before PAM in231.071733755s
(wrapper231.142025013s). Wait139.92→149.42 returned1. Original FUSE event1508
processed at journal144.762944 and sent multicast at144.763314, inside that
window. The later snapshot has all six database entries without ID_PROCESSING,
but does not establish their state at the deadline. I: timestamps are not final
processing times. The comparison therefore does not qualify a readiness fix.

The failure-only retrigger succeeds; original FUSE already existed before it.
Normal poweroff passes the actual RCU-aware check; /var unmount FAIL is retained.
All runtime bytes/metadata and locked input hashes remain unchanged. Both owned
VMs are terminal, with no containers remaining. Neither reached PAM or Denial;
the corrected Rust child watchdog remains runtime NOT RUN.

Pinned systemd source creates a fresh device object per check. Initialized mode
checks before monitoring, before the event loop, and on matching events; it has
no periodic check or final check at timeout. The monitor receives all udev events
and handles one datagram per callback. Equal-priority timeout can win before a
queued matching event is dispatched. This is a possible source counterexample,
not an established cause here: five other completion times were not captured.
The network-namespace warning is diagnostic-only and does not disable monitoring.

Next: extend the existing scoped debug rule to six exact consumers, and retain
timestamped pre-wait and failure snapshots alongside original completion events.
Keep the8s initialized gate, original failure and all independent readiness checks.
Do not repeat unchanged VMs or expand deadlines to conceal the unresolved stage.
No third VM, kernel/Denial rebuild, phone operation or protected-storage mutation
occurred. Exact commands, durations and output identities are in the accompanying
qualification JSON and private terminal/result records. Historical evidence stays
unchanged; this scheduling change is VM-only and remains insufficient at runtime.
