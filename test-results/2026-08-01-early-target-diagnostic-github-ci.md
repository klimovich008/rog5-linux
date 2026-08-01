# Early-target diagnostic GitHub CI

Date: 2026-08-01

Result: **PASS — the reviewed diagnostic publication checkpoint is pushed and
both required GitHub Actions jobs pass at exact head
`6654c0c843540940e71ddfd9ece10524a4cbb774`.**

The authorized GitHub credential was used only to fast-forward
`agent/linux-recovery-host` from `54d2c807` to `6654c0c`, update draft pull
request [#1](https://github.com/klimovich008/rog5-linux/pull/1), and inspect its
checks. No force push occurred. No production signing key, privileged host
action, phone interface, or phone storage was used.

## GitHub Actions evidence

Workflow run
[`30700630487`](https://github.com/klimovich008/rog5-linux/actions/runs/30700630487)
was triggered by the pull request for exact head `6654c0c` and concluded
`success`:

- [`recovery-core`](https://github.com/klimovich008/rog5-linux/actions/runs/30700630487/job/91370912774)
  passed in 2 minutes 12 seconds. It installed the native dependencies and ran
  `scripts/host/test-repository-linux.sh ci`.
- [`qemu-system`](https://github.com/klimovich008/rog5-linux/actions/runs/30700630487/job/91370912821)
  passed in 6 minutes 51 seconds. Its cache missed, so it fetched exact Linux
  v7.1.4 commit `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`, built the ARM64 `virt` kernel,
  saved the cache, and passed both the generic system smoke and diagnostic
  handoff boots.

This closes the publication/CI gate only. Production signing, artifact
installation, connected preflights, and every phone boot remain separate
guarded actions.
