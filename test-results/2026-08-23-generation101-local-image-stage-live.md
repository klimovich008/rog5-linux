# Generation 101 local-image staging live result

Date: 2026-08-23

Result: **CONSUMED; TARGET TRANSPORT ABSENT; IMAGE NOT STAGED.** Generation 101
must never be retried or flashed.

Primary question: can the target expose key-only SSH with exact userdata
identity and then run one explicit, bounded 16 GiB local-image installer?

The exact device, slot A, 8.705 V battery, signed wrapper, served bundle,
manifest, trust root, and installed host verifier passed preflight. Exact-head,
merge-compatibility, publication, and QEMU CI passed at
`d0caa792a0bd0a40fb000c947e3ca507eb23f1a3`.

The first server invocation exposed an R6 host-state prerequisite: the exact
deferred NetworkManager profile existed but was not active on the newly
enumerated recovery NCM interface. This failed before PREPARE/COMMIT. Activating
that exact no-gateway `/30` profile made the server pass and did not consume or
execute the target.

The subsequent sole target execution transferred all 62,101,295 signed bytes,
returned canonical `PREPARED` and `CLAIMED`, and closed recovery USB at
06:31:56. No target NCM or ACM gadget appeared during the next 120 seconds.
The exact phone exposed stock slot-A USB at 06:32:26 and later returned a
responsive ASUS fastboot endpoint at the anchored path. Battery remained safe
at 8.706 V with `battery-soc-ok=yes`.

Earliest failed stage: after COMMIT and recovery USB departure, before any
observable target USB transport. The exact target line is unknowable from the
retained host evidence. The reused Image and DTB are independently live-proven;
the replacement minimal initramfs is the only new target layer. A 20-second UDC
wait followed by stock boot is plausible but not proven.

Failure classes: R6 for the pre-COMMIT host profile state; R3 for the target
initramfs capability/observability gap. No host parser or kernel defect is
claimed.

No staging SSH command ran. Therefore the explicit write window never opened
and the verified image was not written. Generation 101 is permanently consumed.

Regression/prevention: the successor must not introduce another minimal USB
stack. Use a storage staging route whose transport is already proven, or retain
the mature target USB initialization and failure reporter. The immediate route
is stock slot-A ADB writing one file beneath userdata, followed by the proven
mainline local-root reader.
