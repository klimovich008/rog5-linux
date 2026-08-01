# Early-target diagnostic bundle-inventory rejection

Date: 2026-08-01

Result: **rejected before bundle listener, transfer, recovery control, or
`COMMIT_EXEC`; automatic recovery rollback and strict-SSH Alpine fallback
passed. The diagnostic candidate remains unexecuted.**

## Scope and result

The prompt-free host socket, exact diagnostic artifacts, private key
admission, connected fastboot gate, and complete lifecycle preflight passed.
The guarded fallback helper then used only `RESTART2("bootloader")`, verified
the exact `lahaina` fastboot device, and temporarily booted the production
stable-recovery AVB wrapper on the expected USB port.

Stable recovery enumerated as the exact `ROG5_recovery` NCM/ACM gadget. The
receive-only diagnostic collector was ready before the next boundary. The
root broker accepted the bundle request without PolicyKit, but its fixed
unprivileged server rejected during descriptor preparation:

```text
serve-recovery-bundle: unexpected bundle-root inventory
FAIL recovery bundle server did not create its fixed listener
INFO recovery bundle host network state removed
```

The caller-owned mode-`0700` bundle root contained two mode-`0500`
directories: the consumed `headless-ssh-network-root-v3-r2` and the selected
`headless-netroot-early-diag-v1`. The server correctly requires the selected
bundle to be the sole root entry, but the launcher preflight previously
verified only installed program bytes and did not invoke that authoritative
inventory check.

No TCP 8080 listener appeared, no bundle byte crossed the USB link, recovery
control was never started, no intent ledger was armed, NFS was never started,
and the target Linux 7.1 diagnostic payload never executed. This is host
inventory/preflight evidence, not target-kernel evidence. The failed
lifecycle invocation is not retried.

## Rollback evidence

The independent recovery watchdog returned the phone to Alpine on the same
physical USB location. A fresh anchor-bound strict-SSH proof accepted:

- kernel `5.4.134-qgki-perf-00001-g6c308144c23e`;
- boot ID `d3ff5187-6f51-4d85-9832-ff63da2f6752`;
- maximum observed temperature `43.1 C`;
- exact physical location
  `pci0000:00/0000:00:08.1/0000:04:00.3/usb1/1-1/1-1.2`; and
- signed result `PASS`.

No transient host-control instance, bundle/NFS/collector process, or project
listener remained. SteamOS read-only mode remained enabled and the persistent
prompt-free socket returned to its idle listening state.

## Private evidence identities

The mode-`0600` evidence remains outside Git. Its relevant public SHA-256
inventory is:

| Evidence | SHA-256 |
|---|---|
| `stable-recovery-boot.log` | `bf0048cca3f3da57738b20293a7c250821df3ff8b64c232677499cc31bd201d6` |
| `recovery-usb.anchor` | `53bd3105fc052e1725a8e2337ceebbc46d73de966f7a9d0b3a19000d58b28bca` |
| `recovery-usb-anchor.log` | `017ec9cd2b1ebb5e62d411e0035375d1fd67ec453b28f1a72e987b106c70bfb4` |
| `bundle-server.log` | `13aa05e7bedf72506934e44f783646ce5978f8ca939e2b21874f6bdfef2eaa65` |
| `early-target-diagnostics.log` | `860714e24102606aee7dc40637e7bbd620d1d7f3743f018657cb9db56178f088` |
| `fallback-identity.record` | `3ba3058769fc52dee4280e2ca886e4162fdec4dcb998b04b4039a07f62a812d9` |
| accepted fallback preflight log | `c6432c9b31f985030290e137d4f9b3be42e32cb2636c4ef8960aa7f06e9bbe15` |

## Remediation

The consumed r2 bundle was byte-compared and moved from the active root to a
private recoverable archive under `.local/state`; it was not deleted. The
diagnostic bundle is now the sole active root entry.

The host server now has a fixed `--preflight BUNDLE MANIFEST_SHA256` form. It
uses the same root descriptor, shared lock, sole-entry check, artifact
descriptors, metadata/hard-link checks, hashes, and canonical manifest binding
as serve, then closes everything without creating a socket or mutating host
state. The launcher invokes this exact validator before a phone boot. A new
hostile test proves that a second consumed-bundle directory fails with
`unexpected bundle-root inventory`.

Focused bundle/controller/socket/lifecycle tests and complete repository CI
pass. Independent standards review found one exact-CLI documentation gap,
which is corrected; Claude's descriptor-lifetime concern was conservatively
addressed by retaining the root descriptor for the full prepared-bundle
context. Publication, host reinstall, and one real no-listener preflight must
pass before a separate new lifecycle can be admitted.
