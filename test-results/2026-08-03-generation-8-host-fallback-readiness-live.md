# Generation-8 pre-issuance host and fallback readiness — live

Date: 2026-08-03

Result: **PASS pre-issuance checkpoint**. The exact pushed host correction,
installed privileged boundary, sealed network root, retained diagnostic
bundle, deployment SSH credential, and persistent Alpine fallback are healthy.
No Generation-8 artifact was issued, signed, admitted, or booted.

## Published correction checkpoint

- implementation commit:
  `61c6ddddf9a5758e7741fe467f58914e5f1f5a42`;
- draft PR: [#1](https://github.com/klimovich008/rog5-linux/pull/1);
- GitHub Actions
  [run `30821583020`](https://github.com/klimovich008/rog5-linux/actions/runs/30821583020):
  `qemu-system` passed in 47 seconds and `recovery-core` passed in 3 minutes
  24 seconds; and
- complete local `scripts/host/test-repository-linux.sh ci`: pass.

The correction accepts NetworkManager 1.52.1's exact one-empty-field NULL
`CON-UUID` rendering only after every existing physical identity, address,
ownership, profile-binding, and autoconnect check. The focused lifecycle suite
passes 61 tests. The constrained Claude Opus review's supported hostile-shape
findings were applied and its final self-contained retry returned `PASS`.

## Installed host boundary

No reinstall was necessary because the corrected file is the unprivileged
lifecycle orchestrator, not one of the root-installed components. The fixed
launchers nevertheless re-hashed their installed controller, server, client,
network-root verifier, persistent-root tool, and export boundary against the
pushed checkout before performing these checks:

```text
PASS fixed recovery bundle inventory and manifest verified
PASS verified deployment export ancestry
PASS verified installed headless network root entries=37735
PASS fixed headless network-root root and host state verified
PASS fallback strict-SSH host prerequisites, client key, and pinned host key
     are exact; no phone contact occurred
```

The retained diagnostic manifest is
`4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`.
It was verified only as retained input; it remains consumed and grants no boot
authority. The admitted read-only deployment package remains
`9eb60d6e4254986dc8e017fc1dd9d76d699e8d35cb3716d8fdef72ca6df1199d`.
The host-control socket remained active at exact `1000:1000`, mode `0600`.

## Live fallback proof

Under the central standing authorization, one fixed, nonce-bound ACM health
probe verified the connected persistent Alpine fallback through its pinned
Ed25519 identity:

```text
PASS pinned exact Alpine fallback verified through fixed USB ACM
```

The mode-`0600` private identity record is retained outside Git with SHA-256
`57c86038ae108da9c917130ee23297f1cf5dca2d88db49d9d0a15be30f2d1f44`.
Its path and contents are private evidence. The probe carried only the already
bounded BusyBox-history and possible ext4-atime effects. It did not reboot the
phone, use fastboot, start a bundle or NFS listener, mount phone storage, or
write a partition.

## Disposition

The temporary-boot policy still contains zero active `allow` rows. Diagnostic
generations 0–7 remain consumed and unreusable. This result permits review of
a distinct Generation-8 issuance; it does not itself create a profile, grant
boot authority, or justify reusing any prior image or manifest.
