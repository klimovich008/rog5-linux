# Generation 54 fast-attestation local-image checkpoint

Date: 2026-08-14

Status: **historical offline checkpoint. Generation 54 was subsequently
consumed and revoked; see the
[live result](2026-08-14-generation-54-fast-attestation-live.md). Never retry
or flash this wrapper.**

Generation 53 proved that UFS discovery, both `ro,noload` ext4 mounts, tmpfs
OverlayFS, systemd, and strict key-only SSH all work from the staged 16 GiB
Arch image. Its mount handoff passed at target uptime 25.494 seconds, but the
post-handoff attestor did not finish until 282.122 seconds. The dominant
offline hypothesis is repeated dynamic process startup in the 116-node
read-only block sweep, not UFS or mounting: the old loop invoked Arch
`basename`, `cat`, and `blockdev` for every device.

The v33 successor preserves every sysfs read and every `BLKROGET` check while
using shell parameter expansion, shell `read`, and the retained static
initramfs BusyBox. It also emits bounded progress markers at attestor start,
mount verification, physical read-only verification, UFS-health verification,
and SSH-policy verification. The regression test fails if the physical sweep
returns to dynamic `basename`, `cat`, or Arch `blockdev` execution.

Exact target identities:

- Linux release: `7.1.4-gae717d919f87`;
- Image SHA-256: `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`;
- DTB SHA-256: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`;
- clean-twin initramfs: 7,510,374 bytes,
  `0f34702d8984511b63e1975ed71b1e88e20a26f8fdb85128e272b2072d997d82`;
- signed manifest: 855 bytes,
  `40b5573a4d03f4571ead025083a7989e6ac9288a89b8fe64e4b8439b64aaa42e`;
- signature SHA-256:
  `382ef4cf55abbcee406952052724a7dee9f33f54615abd67f10efec371ca36ff`;
- Generation 54 AVB SHA-256:
  `0832ddd484ad00ed3bcda184f1b75ce688c89ead4c52a1f97e93f9a058b0b75a`;
- unchanged raw recovery SHA-256:
  `5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
- AVB salt:
  `684d593dda8f9e9202eafb0348c00d140d6ce48100b5b49f1f8d73b352223e64`;
- AVB digest:
  `e29c10a9c2f1485370c34313f4e68f9ffb10e9730298ced9a48a5dc93d95216a`.

The clean initramfs twins completed in 1.134 and 1.142 seconds and were
byte-identical. A fresh production-key rebuild completed in 0.160 and 0.171
seconds; both outputs reproduced the retained signed bundle byte-for-byte.
Deterministic Generation 54 AVB derivation completed in 1.788 seconds. The
native recovery verifier accepted both signed twins and produced the same
exact execution plan.

Focused checks passed for the 14-case storage-resolution suite, 12-case live
runner suite, 14-case exact-record consumer suite, 27-case retention admission
suite, stable recovery gate, current persistent-root artifact preflight,
shared current recovery profiles, and recovery policy/inventory separation.
At this historical checkpoint, Generation 53 was revoked and consumed and
Generation 54 was the only admitted persistent-root candidate. Its later
one-use claim is now consumed and the candidate is revoked.

The physical cycle should compare the five new progress uptimes, strict SSH
acceptance, and exact fallback with Generation 53. Until then, the expected
speedup remains a hypothesis rather than a live result.
