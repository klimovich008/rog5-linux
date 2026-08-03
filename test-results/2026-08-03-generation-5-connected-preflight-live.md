# Generation-5 connected preflight — live

Date: 2026-08-03

Result: **PASS connected preflight**. The exact Generation-5 recovery image,
diagnostic bundle, deployment key chain, installed host components, rollback
prerequisites, and one `lahaina` fastboot device passed the lifecycle's
credential-bound connected gate. No phone boot, payload transfer, SSH
connection, privileged server, target execution, or artifact consumption
occurred.

## Pinned checkpoint

- repository commit:
  `4c55b1c9da146b90b915a886ee6a1e517eff9a3b`
- GitHub Actions run:
  [`30798754817`](https://github.com/klimovich008/rog5-linux/actions/runs/30798754817),
  with `qemu-system` passing in 1 minute 12 seconds and `recovery-core`
  passing in 3 minutes 28 seconds
- recovery profile: `headless-diagnostic-generation5-live-v1`
- recovery SHA-256:
  `abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a`
- bundle: `headless-netroot-early-diag-v1`
- runtime manifest SHA-256:
  `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`
- trust-root SHA-256:
  `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b`
- host verifier SHA-256:
  `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621`

The fastboot serial and private credential/evidence paths remain outside Git.
The successful fresh evidence directory is mode `0700` and empty, as expected
for preflight: all checks completed without starting the lifecycle outputs.

## Fail-closed correction during invocation

The first invocation supplied the structured recovery component root one
directory too deep. The gate failed before phone discovery when it resolved
`components/components/rog5-recovery-control`. That empty private evidence
directory was not reused. The corrected invocation changed only the component
root to its structured parent, used a new private directory, and passed.

The pass marker was:

```text
PASS headless-netroot-early-diag-v1 lifecycle preflight is clean; the
deployment key was admitted locally, and no phone boot, payload transfer, SSH
connection, or privileged server was started
```

Generation 5 remains unbooted and unconsumed. The next action may be at most
one `diagnostic-run` from a clean, pushed, GitHub-green checkpoint. After any
result—including ambiguous transport loss—the allow row must be removed and
the image marked consumed; it must never be retried or flashed.
