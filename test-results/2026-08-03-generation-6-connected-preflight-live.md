# Generation-6 connected preflight — live

Date: 2026-08-03

Result: **PASS connected preflight**. The exact Generation-6 recovery image,
diagnostic bundle, deployment-key chain, installed host components, fallback
prerequisites, and one `lahaina` fastboot device passed the lifecycle's
credential-bound connected gate. No phone boot, payload transfer, target SSH,
privileged server, target execution, or artifact consumption occurred during
preflight.

## Pinned checkpoint

- repository commit:
  `40ad052fd0f64669e8028f20ebdfec575c9aa19a`
- GitHub Actions run:
  [`30807236352`](https://github.com/klimovich008/rog5-linux/actions/runs/30807236352),
  with `qemu-system` passing in 39 seconds and `recovery-core` passing in
  3 minutes 1 second
- recovery profile: `headless-diagnostic-generation6-live-v1`
- recovery SHA-256:
  `6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398`
- bundle: `headless-netroot-early-diag-v1`
- runtime manifest SHA-256:
  `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`
- trust-root SHA-256:
  `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b`
- host verifier SHA-256:
  `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621`

The phone had returned to the exact Alpine fallback before discovery. The
reviewed strict-key helper first passed its fallback health gate, then issued
one guarded `RESTART2("bootloader")` request and proved the same physical USB
port re-enumerated as exact `lahaina` fastboot. The fastboot serial and private
credential/evidence paths remain outside Git.

The connected preflight then emitted:

```text
PASS headless-netroot-early-diag-v1 lifecycle preflight is clean; the
deployment key was admitted locally, and no phone boot, payload transfer, SSH
connection, or privileged server was started
```

The subsequent one-shot lifecycle is recorded separately. This preflight did
not grant authority to retry its result.
