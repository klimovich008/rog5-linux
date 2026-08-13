# Generation 52 fast local-root admission checkpoint

Status: **unbooted RAM-only candidate; read-only storage only; never flash**.

Generation 52 preserves Generation 51's Linux Image, DTB, four UFS modules,
physical read-only locks, exact userdata `ro,noload` mount, tmpfs OverlayFS,
systemd, key-only SSH, outbound-only stage records, and bounded rollback. It
replaces the every-boot recursive rehash with bounded checks of the prior full
seal and exact boot-critical identities: systemd, sshd, the sole authorized
key, and the SSH policy. Owner, group, mode, size, link shape, content hash,
and required policy lines fail closed.

This transitional admission relies on the previously completed full seal and
the immutable `ro,noload` outer mount. It is not complete filesystem integrity;
the full recursive verifier remains available for staging/audit, and the local
image experiment should replace this compromise with scalable image integrity.

Exact identities:

- Image SHA-256: `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`
- DTB SHA-256: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`
- clean-twin initramfs SHA-256: `e6836d2173341a200b2d728d4ade97a09233de1936621073ad32ae32402f9883`
- signed manifest SHA-256: `3cee4b788a2005e90b4c901955a3b1df392cad8b332ea7252580fe1621af1f89`
- manifest signature SHA-256: `14cb1012bdaecc88ee733c5d23473284086cef1bba63f29c297da6ae160691ea`
- Generation 52 AVB SHA-256: `0d0683e3404e890522630808700e6915eb86d83fd3d8ddc8fc5ed716a7e9303f`
- AVB generation-record SHA-256: `0dd094c5119c4317e0057cba97418c43d994f760a7e983f273cf09f3c0f15a31`

The clean-twin initramfs builds took 1.128 and 1.136 seconds and were
byte-identical. Deterministic AVB generation took 1.950 seconds. Focused
storage-resolution, exact-claim, live-runner, current-profile, admission, and
stable-gate tests pass. No candidate has been claimed, issued to recovery, or
booted by this checkpoint.
