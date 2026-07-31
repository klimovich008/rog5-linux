# Minimal-headless live cycle: strict-SSH fallback accepted

Date: 2026-07-31

Result: **safe target rejection; exact Alpine fallback proved over strict
SSH and the durable intent resolved `FALLBACK_RETURNED`**.

## Accepted boundaries

- Repository checkpoint `80bf94d` was clean, pushed, and synchronized.
- The complete lifecycle preflight admitted the dedicated client key, fixed
  host components, sealed 37,735-entry export, signed bundle, recovery image,
  and exact `lahaina` fastboot device without booting the phone.
- `fastboot boot` accepted the pinned 100,663,296-byte recovery image. No
  partition was flashed, mounted, or written.
- Recovery re-enumerated on the anchored physical USB port and fetched the
  signed `headless-ssh-network-root-v3` bundle exactly once.
- PREPARE succeeded and one durable non-retryable COMMIT intent was armed.
- The target USB-NCM interface reached the exact host `/30` address check.

## Target rejection

The volatile target host-key bootstrap stopped with:

```text
FAIL cannot resolve one exact target route
```

The target route parser required `ip route get` to return one physical line.
On this host, Linux emits one route followed by an indented `cache`
continuation:

```text
169.254.77.2 dev enp4s0f3u1u2 src 169.254.77.1 uid 1000
    cache
```

The preceding exact `/30` check had already passed. The rejection was
therefore a stale host-parser assumption, not evidence that target USB-NCM
failed to enumerate. No target host key was pinned and no target SSH runtime
record was accepted.

The fix accepts only zero continuation lines or one literal indented `cache`
line. It still rejects duplicate primary routes, any other continuation,
`via`, policy-table routes, wrong interfaces, and wrong source addresses.

## Rollback and bottleneck result

The recovery watchdog returned the same physical port to the pinned Alpine
fallback. The persistent `rog5-fallback-usb-ssh` NetworkManager profile
automatically restored `169.254.77.1/16`. The lifecycle then completed one
non-interactive strict-SSH health exchange and verified Alpine's nonce-bound
Ed25519 signature, exact kernel/init/root/board identity, clean diagnostics,
thermal maximum below policy, NCM driver, route, and physical USB continuity.

The private mode-`0600` fallback record reported `result=PASS` at a maximum
sampled temperature of 44.1 degrees C. The durable intent was resolved once
as `FALLBACK_RETURNED`. No ACM shell was opened, no shell-history side effect
was incurred, and no ambiguous COMMIT retry was attempted.

This live result accepts the new SSH fallback control plane. It does not yet
accept the minimal-headless target.
