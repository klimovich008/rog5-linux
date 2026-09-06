# Corrected diagnostic recovery: host listener rejection

Date: 2026-08-02

## Scope

One guarded, non-flashing `fastboot boot` used the production-signed corrected
diagnostic recovery wrapper at SHA-256 `f710bbcd…97b0ef`. Local repository CI,
both GitHub jobs, exact installed-host checks, and the connected no-boot
lifecycle preflight passed first. Private evidence remains outside Git.

## Result

- Fastboot accepted the 100,663,296-byte wrapper and recovery enumerated on
  the anchored USB port with NCM and ACM.
- Recovery reported that no payload had been committed and rollback remained
  armed.
- The privileged host bundle controller exited before its ready marker with
  `FAIL TCP port 8080 already has a listener`.
- The only pre-existing TCP 8080 listener was Steam's loopback-only
  `127.0.0.1:8080` remote-debug endpoint. It cannot conflict with the fixed
  recovery bundle bind at `169.254.77.1:8080`.
- No bundle response, `PREPARE`, durable intent, NFS service, `COMMIT_EXEC`,
  target boot, target SSH, or phone-storage access occurred.
- Recovery disconnected at 11:41:26 Europe/Paris. The exact Alpine USB product
  returned on the same physical port at 11:41:44, and strict pinned SSH proved
  the persistent fallback.

## Classification

This was a host pre-transfer rejection, not a kernel or target result. The
wrapper is consumed by its one-shot policy and has been removed from temporary
boot admission; it must never be retried or flashed. The signed target bundle
remains unexecuted because no transfer or commit occurred.

The lifecycle-level cleanliness check had already been corrected to ignore an
unrelated loopback listener. The root-owned controller duplicated the older
global-port check both before server startup and during listener verification.
Its successor must scope IPv4, IPv6 wildcard, and IPv4-mapped conflicts to the
fixed bundle endpoint while continuing to reject real bind conflicts.

## Next gate

1. Land and install the scoped privileged-controller check with hostile tests.
2. Reissue the unchanged recovery payload as a distinct deterministic,
   twin-built, production-signed AVB successor; do not restore authority to the
   consumed wrapper.
3. Repeat all offline, installed-hash, connected no-boot, and one-shot gates
   before one new RAM-only lifecycle.
