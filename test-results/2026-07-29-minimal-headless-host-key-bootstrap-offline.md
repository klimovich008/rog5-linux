# Minimal-headless volatile host-key bootstrap — offline

Date: 2026-07-29

Status: **PASS for hardware-free USB-continuity and public-key pinning; no
phone or credential action**

## Finding

The sealed 535,094,061-byte minimal network lower intentionally contains no
`ssh_host_*` files. Its `sshd.service` requests `sshdgenkeys.service`, which
creates a volatile server key in the RAM-backed upper layer. Therefore the
runtime acceptance runner's strict known-hosts input cannot be derived
statically from the sealed lower.

Using `accept-new` with the client private key would merge peer discovery and
credential use. The new bootstrap separates them: it learns only a public
Ed25519 key while continuity is bound to signed recovery's physical USB port,
then the existing runner performs credentialed SSH with strict checking.

## Implemented boundary

`scripts/host/pin-minimal-headless-host-key.py`:

- records one canonical mode-`0600` recovery anchor with current host boot
  ID, creation time, exact USB location, VID/PID, and recovery product;
- accepts the anchor for at most 600 seconds, rechecks freshness before
  publication, and requires the same host boot;
- inventories the USB bus independently of class interfaces, then requires
  one target product, one `cdc_ncm` interface, and the same physical USB
  location;
- requires exactly `169.254.77.1/30` on that interface and a direct
  no-gateway route to `169.254.77.2`;
- invokes only fixed root-owned `/usr/bin/ssh-keyscan`, for Ed25519 only;
- parses the SSH wire blob itself and rejects zero or extended key material;
- rechecks target identity and routing after the scan;
- atomically publishes one alias-bound, caller-owned mode-`0600` known-hosts
  file outside Git; and
- requires one explicit observation guard before any live inspection.

It never opens a client key, logs in over SSH, disables host checking, boots
or reboots the phone, signs an artifact, changes a watchdog, or writes phone
storage.

## Test result

The hardware-free suite passed 15 test groups:

```text
Ran 15 tests
OK
```

Coverage includes:

- canonical anchor and known-hosts publication;
- raw sysfs product strings bound to both initramfs sources;
- exact recovery and target products;
- same-port continuity and unique NCM interface;
- exact direct route;
- one valid Ed25519 key;
- stale and malformed anchors;
- duplicate target gadget with no class interface and duplicate NCM interface;
- wrong product/driver/port;
- absent, multiple, RSA, all-zero, and trailing-data keys;
- repository, existing, linked, and loose-parent output refusal;
- cleanup after a failed atomic publication; and
- expiry after discovery, authorization-before-inspection, CLI failure
  translation, and forbidden surface scans.

The complete staged `scripts/host/test-repository-linux.sh ci` suite passed,
including all existing recovery, fetch, verifier, controller, storage-safety,
compatibility, and QEMU-contract tests.

## Remaining boundary

This closes only temporary-development host-key discovery. It does not
provide a persistent server identity and grants no live authority. The next
phone cycle still requires a fresh live signing trust root, exact release-pin
update, full controller composition, independent review, and explicit
attended temporary-boot authorization.
