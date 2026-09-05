# Agent-isolated Arch rootfs — offline result

Date: 2026-07-26

Result: **PASS OFFLINE for account/service isolation and the complete rootfs
archive round trip; the artifact was not exported or booted on the phone**.

The Arch staging pipeline used the authenticated Arch Linux ARM base, signed
package databases and packages, the exact Linux
`7.1.4-g7a5cef0db479` modules, pinned A660/SM8350 firmware, and one external
public SSH key. No SSH private key, API credential, browser session, email,
CV, model-provider account, or remote-desktop credential was supplied.

The new `rog5-agent` system account is distinct from root and the interactive
`rog5` desktop user. Verification requires:

- a locked password, `/usr/bin/nologin`, no supplementary groups, and no
  `.ssh` directory;
- mode-`0700`, `rog5-agent`-owned `/var/lib/rog5-agent` and
  `/var/lib/rog5-agent/private`, with no other staged content;
- Chromium state under `/var/lib/rog5-agent/chromium`, never the desktop
  user's home;
- CDP bound only to `127.0.0.1:9222`;
- an on-demand service with empty capability sets, private devices and
  temporary files, no privilege escalation, protected home/kernel/system
  state, and only `/var/lib/rog5-agent` writable; and
- successful `systemd-analyze verify` inside the AArch64 rootfs.

The complete staged-root verifier passed before archival. The pipeline then
created the gzip archive, extracted it into a second clean Podman volume with
ACLs and xattrs preserved, and passed the same verifier again. An independent
host-side SHA-256 and `gzip -t` check matched the pipeline result.

## Exact output

| Field | Value |
|---|---|
| Source commit | `f279343192f10a5f86ca9389733ed3abf2c8e8da` |
| Size | `2,006,969,651` bytes |
| SHA-256 | `9f6ca6181f6d43101cd8b836d63ca96bdeea97aea225bb78b22aafe33fc24e53` |
| Builder image | `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c` |

## Source identities

| Input | SHA-256 |
|---|---|
| `rog5-chromium-headless.service` | `a6149e256a10cd9f35ecd52d862f199a696380ea8d6fba4012ec047d91a47d75` |
| `stage-arch-rootfs.sh` | `1da36cf801634176685c727c8b9bd91babc2d53098b7e8d587f26791919086ea` |
| `verify-staged-arch-rootfs.sh` | `7eba3d51015d89303522512ca4ffdf3c6f32854365e2e96c803f02808ecebcd6` |
| `test-agent-isolation.sh` | `c035fc99a2bc3e80694bc1131137c57c42b80b6229878f6da660758f7b838549` |

## Remaining gates

This is a local development artifact, not the currently manifest-pinned NFS
root. It has not been exported, booted, or exercised on ARM hardware. Before
automation is usable, the phone must pass the existing kernel/network-root
hardware gates; the artifact must be promoted deliberately; and runtime
resource, thermal, encrypted-secret, audit, and approval controls must be
implemented. Connecting email, model providers, or other external accounts
requires separate user confirmation.
