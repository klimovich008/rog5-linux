# Early-target diagnostic host-auth timeout

Date: 2026-08-01

Result: **rejected before bundle transfer or `COMMIT_EXEC`; automatic recovery
rollback and exact Alpine fallback passed. The diagnostic candidate remains
unexecuted.**

## Scope

This was the first production-signed
`headless-netroot-early-diag-v1` lifecycle attempt. It used one verified
temporary `fastboot boot` of the fixed stable-recovery wrapper. It did not
flash, erase, change slots, mount phone storage, or write phone storage.

The lifecycle verified AVB and the sealed recovery inputs, anchored the
`ROG5 recovery` ACM/NCM gadget to the expected physical USB port, and started
the receive-only early-target collector. The next host step invoked the fixed
recovery-bundle controller through PolicyKit. Its graphical authentication
did not complete within the lifecycle's bounded server-ready interval.

The controller therefore returned:

```text
FAIL recovery bundle server did not publish its bounded ready marker
```

`bundle-server.log` remained empty. No bundle transfer completed, stable
recovery control was never started, no durable commit intent was created, and
the target diagnostic reporter never ran. This is a host sequencing failure,
not target-kernel evidence, and it does not consume the diagnostic candidate.
The failed lifecycle invocation itself is not retried.

## Rollback evidence

Stable recovery retained its independent `rog5.recovery_timeout=180` rollback
timer. The phone disconnected and returned automatically on the same physical
USB location as the installed Alpine gadget. A separate strict-SSH,
nonce-bound signed fallback preflight passed with:

- kernel `5.4.134-qgki-perf-00001-g6c308144c23e`;
- boot ID `012fcc84-88db-4726-b538-1c2e6ce6263b`;
- maximum observed temperature `42.5 C`;
- exact physical location
  `pci0000:00/0000:00:08.1/0000:04:00.3/usb1/1-1/1-1.2`; and
- result `PASS`.

No project controller, bundle server, collector, or network-root process
remained. The host had no listeners on the project ports and retained only the
normal NetworkManager-owned fallback `/30` link.

## Private evidence identities

The mode-`0600` evidence remains outside Git under the private lifecycle
directory. Its public SHA-256 inventory is:

| Evidence | SHA-256 |
|---|---|
| `stable-recovery-boot.log` | `46f7fc5752e05ba7c61998778273a43d0eec4949fe02622ab57bbe6e9b3e31e2` |
| `recovery-usb.anchor` | `910a9ecb4ecf47a425f8e4cf463ad18ae9ba32e303164dc04bd8bef77e50a93d` |
| `recovery-usb-anchor.log` | `017ec9cd2b1ebb5e62d411e0035375d1fd67ec453b28f1a72e987b106c70bfb4` |
| `early-target-diagnostics.log` | `860714e24102606aee7dc40637e7bbd620d1d7f3743f018657cb9db56178f088` |
| `bundle-server.log` (empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `fallback-preflight.log` | `c6432c9b31f985030290e137d4f9b3be42e32cb2636c4ef8960aa7f06e9bbe15` |
| `fallback-identity.record` | `7c58b0849a4a8b3d97849c9505816210c5d19459113675fdd7a84c99a33e1f15` |

## Required remediation

Interactive PolicyKit authentication must not occur after a bounded phone boot
begins. The replacement design installs one root systemd stream-socket
boundary during the explicit host installation step. The socket is mode
`0600`, owned by the exact operator account, accepts only the fixed bundle and
network-root request grammar, verifies the connecting UID and root-owned
controller hashes, and returns the fixed process status. No shell, arbitrary
path, environment forwarding, repository executable, or PolicyKit prompt is
available through the runtime protocol.

A new lifecycle may be admitted only after that socket implementation passes
its hostile offline tests, review, complete repository CI, real SteamOS
installation, credential-free server preflight, and exact fallback-to-fastboot
transition. Because no bundle or execute request crossed the failed boundary,
that later lifecycle is a new admitted attempt with the still-unexecuted
candidate, not a retry of an ambiguous `COMMIT_EXEC`.
