# Recovery choreography host update

Date: 2026-08-03

Result: **PASS. The reviewed Generation-4 choreography correction is installed,
the real bundle and deployment-root preflights pass through the fixed host
boundary, and the host returned to a clean idle state. No phone interface was
contacted and no Generation-5 artifact was built or admitted.**

## Published checkpoint

- Implementation commit:
  `38b60192a50b94227e63e7286272a56588698fa7`.
- Provenance commit:
  `03f3cdc571832778154730d05c2f6c41e8b17a0d`.
- GitHub Actions
  [run `30793387343`](https://github.com/klimovich008/rog5-linux/actions/runs/30793387343)
  passed `qemu-system` in 31 seconds and `recovery-core` in 2 minutes 58
  seconds at the provenance commit.
- Complete local CI passed at the implementation commit. The provenance-only
  follow-up also passed the 41-file local Markdown-target check before
  publication.

## Installed identities

The reviewed source and root-owned installed files matched byte-for-byte:

| Component | SHA-256 |
|---|---|
| bundle controller | `c4c3c625a3e3d899e0f57bcb3a6ce51bd8cb1ddbfb9448ab80e77f2106b8e6ab` |
| bundle server | `72c636b73194ed3ccdcbd9cb86c7b25a2a8d2ff83b845e65c6e8cd11027b55ca` |

The unchanged NFS server, verifier, persistent-root tool, export installer,
broker, and client also remained byte-identical to the checkout. The control
socket was `enabled` and `active`; `/run/rog5-recovery-host.sock` remained a
UID/GID `1000:1000`, mode-`0600` socket. The installed controller and server
remained root-owned mode-`0555` regular files. SteamOS read-only mode was
restored to `enabled`.

The host credential entered only through a non-echoing interactive prompt. No
credential value entered a command line, output, artifact, repository file, or
Git history.

## Real host preflights

The prompt-free deployment-root preflight crossed the installed socket and
verified the exact admitted package:

```text
PASS verified deployment export ancestry
PASS verified installed headless network root entries=37735 tree_sha256=f4affd6d83f3af48259c7d7f650e91461465b59e045519310ac81bb5d71a0087
PASS fixed headless network-root root and host state verified
```

The package identity was
`9eb60d6e4254986dc8e017fc1dd9d76d699e8d35cb3716d8fdef72ca6df1199d`.

The updated installed bundle server then preflighted the retained diagnostic
bundle `headless-netroot-early-diag-v1` against manifest
`4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`:

```text
PASS fixed recovery bundle inventory and manifest verified
```

This was an inventory/manifest preflight only. It did not open the transfer
listener or consume an artifact.

## Residue and evidence boundary

After both preflights, no transient `rog5-recovery-host@` unit, NFS listener,
NFS export, or project listener on TCP 8080 remained. The unrelated Steam
client listener on `127.0.0.1:8080` remained and is explicitly allowed by the
lifecycle. The repository was clean and synchronized with its tracked branch.

This checkpoint proves the corrected host installation and its real preflight
paths. It does not prove USB/NCM transfer behavior on the phone and does not
authorize reuse of Generation 4. A distinct Generation-5 build, offline gate,
and one-shot admission remain mandatory before another temporary boot.
