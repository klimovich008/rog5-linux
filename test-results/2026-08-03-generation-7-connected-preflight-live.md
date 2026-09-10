# Generation-7 connected preflight — live

Date: 2026-08-03

Result: **PASS connected preflight**. The exact Generation-7 recovery image,
diagnostic bundle, deployment-key chain, installed host components, fallback
prerequisites, and one `lahaina` fastboot device passed the lifecycle's
credential-bound connected gate. No phone boot, payload transfer, target SSH,
privileged server, target execution, or artifact consumption occurred during
preflight.

## Pinned checkpoint

- repository commit:
  `158a8ac39eb2f29c44983d66e916d4e823babdb5`
- GitHub Actions run:
  [`30815999859`](https://github.com/klimovich008/rog5-linux/actions/runs/30815999859),
  with `qemu-system` passing in 35 seconds and `recovery-core` passing in
  3 minutes 30 seconds
- recovery profile: `headless-diagnostic-generation7-live-v1`
- recovery SHA-256:
  `d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901`
- bundle: `headless-netroot-early-diag-v1`
- runtime manifest SHA-256:
  `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`

The phone began on exact Alpine fallback. Local credential admission passed
without contacting the phone. The reviewed strict-key helper then passed its
fallback health gate, issued one guarded `RESTART2("bootloader")` request,
and proved that the same physical USB port re-enumerated as exact `lahaina`
fastboot. The fastboot serial and private credential/evidence paths remain
outside Git.

The connected preflight emitted:

```text
PASS headless-netroot-early-diag-v1 lifecycle preflight is clean; the
deployment key was admitted locally, and no phone boot, payload transfer, SSH
connection, or privileged server was started
```

The subsequent one-shot lifecycle is recorded separately. This preflight did
not grant authority to retry its result.
