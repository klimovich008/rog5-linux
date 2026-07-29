# Minimal-headless volatile host-key bootstrap

The credential-free minimal root has no reusable SSH server host key. On a
temporary boot, its `sshd.service` requests `sshdgenkeys.service`, which
creates one in the RAM-backed OverlayFS upper layer. This bootstrap turns
that volatile public key into a strict known-hosts pin without presenting a
client credential to an unpinned SSH server.

Status: **hardware-free contract complete; no live authority**

## Trust boundary

`scripts/host/pin-minimal-headless-host-key.py` has two guarded phases:

1. `capture-recovery` inventories the USB bus and observes exactly one
   `1d6b:0104` raw
   `ROG5 recovery` USB product (`ROG5_recovery` after udev normalization) and
   writes its physical sysfs location into a private anchor.
2. `pin-target` requires the same current host boot, an anchor no older than
   600 seconds both before discovery and immediately before publication,
   exactly one bus-inventoried raw `ROG5 network root` product
   (`ROG5_network_root` after udev normalization) on the same physical port,
   the `cdc_ncm` driver, and an exact direct route from `169.254.77.1/30` to
   `169.254.77.2`.

Only then does it run the fixed root-owned `/usr/bin/ssh-keyscan` for
Ed25519. It accepts one canonical nonzero Ed25519 wire key, rechecks the USB
identity and route after the scan, and atomically publishes:

```text
rog5-minimal-headless-v1 ssh-ed25519 <public-key>
```

The anchor and known-hosts parent must be caller-owned mode `0700`; each
output is a new caller-owned mode-`0600`, one-link regular file outside the
repository. Existing outputs, linked path components, and stale anchors fail
closed.

The helper never receives or opens a client private key. It has no SSH login,
SCP, `accept-new`, disabled host checking, fastboot, ADB, signing, reboot,
watchdog, or phone-storage operation. The subsequent runtime runner uses the
new file with `StrictHostKeyChecking=yes` and
`HostKeyAlias=rog5-minimal-headless-v1`.

## Why physical continuity is acceptable here

This is a narrow development bridge for one attended, point-to-point USB
boot. The recovery wrapper and target are separately hash/signature checked;
the public host-key scan is accepted only while the target replaces that
recovery gadget on the same physical port and the host route cannot leave the
dedicated `/30`.

This is not the persistent-server design. Long-term operation needs a
separately approved private host-key state boundary that survives reboot and
is backed up or rotated intentionally. It must remain outside Git and outside
immutable public boot artifacts.

## Authorized live sequence

These commands are documentation, not authority. The attended controller
must create the anchor after the exact recovery image is running and before
the non-retryable commit:

```sh
ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP=1 \
  scripts/host/pin-minimal-headless-host-key.py \
  capture-recovery /private/evidence/recovery-usb.anchor
```

After the target NCM gadget appears and the restricted NFS controller owns
the exact `/30`, it may pin the target public key:

```sh
ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP=1 \
  scripts/host/pin-minimal-headless-host-key.py \
  pin-target \
  /private/evidence/recovery-usb.anchor \
  /private/evidence/target-known-hosts
```

The full live-cycle controller must still preserve the at-most-once recovery
commit, start the exact read-only NFS window, run the strict runtime
acceptance once, keep the target rollback watchdog armed, classify target or
fallback outcome out of band, and remove all host runtime state.

## Hardware-free verification

Run:

```sh
scripts/host/test-pin-minimal-headless-host-key.py
scripts/host/test-repository-linux.sh ci
```

The fixture suite covers the canonical positive path plus source-bound raw
gadget names, stale and cross-boot anchors, expiry during discovery, wrong
ports, duplicate products without class interfaces, duplicate interfaces,
wrong drivers, indirect routes, malformed keys, unsafe outputs, and missing
guards. See the
[offline evidence](../test-results/2026-07-29-minimal-headless-host-key-bootstrap-offline.md).
