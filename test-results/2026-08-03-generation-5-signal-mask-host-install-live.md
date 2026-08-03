# Generation-5 signal-mask host installation — live host only

Date: 2026-08-03

Result: **PASS. The corrected recovery-host broker is installed at its exact
published hash, both real host-only preflights pass, and the host returned to a
clean idle state. No phone interface was contacted.**

## Published checkpoint

- Broker implementation commit:
  `7777038bc1a5e9e4144ac88b407e9e8aa94adefe`.
- Deterministic cross-shell test follow-up:
  `c9e328526f99a8dca623be31a27df34bc5030089`.
- GitHub Actions
  [run `30803393832`](https://github.com/klimovich008/rog5-linux/actions/runs/30803393832)
  passed `qemu-system` in 32 seconds and `recovery-core` in 3 minutes 3
  seconds at the exact follow-up commit.
- Complete local repository CI passed before publication. The follow-up changed
  only a test and its evidence wording; all 13 broker tests passed afterward.

The first GitHub attempt exposed that Ubuntu's `/bin/sh` clears the unrelated
`SIGUSR2` mask used by the initial regression fixture. The production broker,
all three managed-signal assertions, and the process-group termination test
were unaffected. The corrected fixture explicitly starts from a caller with
`SIGHUP`, `SIGINT`, and `SIGTERM` unblocked and asserts only that production
contract. The replacement run is the accepted GitHub evidence.

## Installed identities

The root-owned installed files match the checkout exactly:

| Component | SHA-256 |
|---|---|
| bundle controller | `c4c3c625a3e3d899e0f57bcb3a6ce51bd8cb1ddbfb9448ab80e77f2106b8e6ab` |
| bundle server | `72c636b73194ed3ccdcbd9cb86c7b25a2a8d2ff83b845e65c6e8cd11027b55ca` |
| network-root server | `f316b1c706584c2d0ccfd311d56866dfcff0c1ba3d574658b261a1bc5b2c7e65` |
| network-root verifier | `af0c28dc37209248c5c68c91005d0b6e74012e6aba0fbe0e9268601377bed76b` |
| persistent-root tool | `0b2a3a9a8ad330dd427427ac8deb79ca18cb2f8575d46cdc9b354594dce27057` |
| export installer | `d92d0cc2d2d8ddbd86123855b4d3ec7322c245cbb31a794f80ca68400c78ae04` |
| corrected host broker | `fbafce24e9c11eea0c79d99f18cb2fb8c849d8b0180883cd8a0a562c8c8cc42c` |
| host-control client | `7ef72fefc2e6348d81f3e3f7d57b998c068d5ec44895b86e01c27fac31464d56` |

The host-control socket is enabled and active. Its runtime socket is owned by
UID/GID `1000:1000`, mode `0600`. SteamOS read-only mode was restored to
`enabled` after the atomic installation.

The existing credential was entered only through a non-echoing interactive
prompt. Its value did not enter a command line, output, repository file,
artifact, or Git history.

## Real host preflights

The prompt-free deployment-root preflight crossed the newly installed broker
and verified the exact admitted package:

```text
PASS verified deployment export ancestry
PASS verified installed headless network root entries=37735 tree_sha256=f4affd6d83f3af48259c7d7f650e91461465b59e045519310ac81bb5d71a0087
PASS fixed headless network-root root and host state verified
```

The package identity was
`9eb60d6e4254986dc8e017fc1dd9d76d699e8d35cb3716d8fdef72ca6df1199d`.

The retained diagnostic bundle `headless-netroot-early-diag-v1` then passed
inventory and manifest preflight against
`4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`:

```text
PASS fixed recovery bundle inventory and manifest verified
```

Neither preflight opened a transfer or NFS listener or consumed an artifact.

## Final residue and disposition

After both preflights:

- no per-request host-control service remained running;
- no project process or TCP listener remained on the bundle, rpcbind, or NFS
  ports;
- no NFS/NFSv4 mount or readable kernel export remained;
- the control socket remained active with exact metadata; and
- the repository was clean and equal to its upstream branch.

This closes the Generation-5 host signal-inheritance correction and removes
the 205-second watchdog bottleneck from the installed path. It does not prove
a recovery transfer on hardware, authorize Generation-5 reuse, create a
successor, or authorize flashing. Generation 5 remains permanently consumed.
