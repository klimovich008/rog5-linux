# SteamOS prompt-free recovery host control

Date: 2026-08-01

Result: **accepted. The fixed operator socket is installed and active, the
deployment NFS preflight crossed the real root broker without PolicyKit, and
the host returned cleanly to its idle state. The phone remained in the exact
Alpine fallback and the diagnostic candidate remains unexecuted.**

## Reviewed checkpoint

- Git commit: `aa39503a73b95ed6faa1af975186e1b1b2ccd633`
- GitHub Actions:
  [run `30710113419`](https://github.com/klimovich008/rog5-linux/actions/runs/30710113419)
  passed both `recovery-core` and `qemu-system`.
- Local repository CI passed before publication, including the ten hostile
  socket-protocol tests, thirteen root-controller tests, and thirty-four
  lifecycle tests.

The one-time installer ran with the authenticated operator UID explicitly
bound as `1000`. No credential value was written to a command line, log,
artifact, or Git.

## Installed boundary

The installer restored SteamOS read-only mode to `enabled`, then systemd
reported `rog5-recovery-host.socket` as `enabled`, `active`, and `listening`.
The runtime and root-owned metadata were:

| Object | Metadata |
|---|---|
| `/run/rog5-recovery-host.sock` | UID/GID `1000:1000`, mode `0600`, socket |
| `/etc/rog5-recovery-host/control.conf` | `root:root`, mode `0444`, regular file |
| `/etc/systemd/system/rog5-recovery-host.socket` | `root:root`, mode `0644`, regular file |
| `/etc/systemd/system/rog5-recovery-host@.service` | `root:root`, mode `0644`, regular file |
| installed broker and client | `root:root`, mode `0555`, regular files |

The reviewed and installed executable identities matched byte-for-byte:

| Component | SHA-256 |
|---|---|
| root broker | `dcdfc90f6d9576bc669ac3829590d95f11e274192e13a18f06748b3ab75921d8` |
| operator client | `2082e32410d86f4fe6fdf084af2f4a94a70f1b625c2843e4ef1954c7957a7022` |
| bundle controller | `cb8807e0ebb96df5d1366539692e72918293e740333ee26422b2c7080ce3441c` |
| network-root server | `f316b1c706584c2d0ccfd311d56866dfcff0c1ba3d574658b261a1bc5b2c7e65` |
| service unit | `661331cd04d8e9b7a37e51b8ee5de2435ec832e5e210da25f277f0828e304eb4` |

The root-owned configuration pins the same controller hashes and exactly one
operator UID. The socket admits at most one long-running serve request plus
one independent cancellation connection.

## Real prompt-free preflights

The bundle launcher verified that its fixed controller, server, and socket
client were installed, root-owned, non-writable, and byte-identical:

```text
PASS fixed recovery bundle server is installed and current
```

The deployment NFS launcher then sent
`network-preflight-v3` through the real mode-`0600` socket. Systemd accepted a
root broker instance for UID `1000`; no PolicyKit request appeared. The broker
verified the fixed controller hash and completed with:

```text
PASS verified deployment export ancestry
PASS verified installed headless network root entries=37735 tree_sha256=f4affd6d83f3af48259c7d7f650e91461465b59e045519310ac81bb5d71a0087
PASS fixed headless network-root root and host state verified
```

The admitted deployment package manifest remained
`9eb60d6e4254986dc8e017fc1dd9d76d699e8d35cb3716d8fdef72ca6df1199d`.
The transient service deactivated successfully after 5.02 seconds with a
58.4 MiB peak. The socket returned to zero active connections.

## Phone and cleanup evidence

Before installation, the connected USB device was the exact same-port Alpine
gadget (`1d6b:0104`, NCM plus ACM), and the guarded strict-SSH fallback
preflight passed. The host operation did not reboot, boot, flash, mount, or
write phone storage.

After the broker preflight:

- no transient `rog5-recovery-host@` service remained active;
- no project server process remained;
- no listener remained on TCP ports 111, 2049, or 8080;
- the ordinary host SSH listener and the persistent idle control socket were
  the only relevant listeners; and
- SteamOS read-only mode remained enabled.

This closes the host-authentication timing remediation. The next phone action
is a new admitted diagnostic lifecycle: prove fallback again, use the guarded
`RESTART2("bootloader")` transition, revalidate the exact fastboot device and
artifacts, and perform at most one temporary boot. It is not a retry of an
ambiguous execute because the prior lifecycle never transferred a bundle or
created `COMMIT_EXEC`.
