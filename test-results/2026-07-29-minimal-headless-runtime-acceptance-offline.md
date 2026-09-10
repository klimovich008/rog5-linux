# Minimal-headless runtime acceptance — offline

Date: 2026-07-29

Result: **PASS offline; no phone, credential, signing, boot, reboot, or
storage action**

## Outcome

The corrected headless candidate now has one bounded runtime evidence
contract before its next authorized phone cycle. A read-only target probe
emits one canonical 48-field record covering all six active compatibility
capabilities. A separate host verifier binds that record to the exact probe,
boot identity, compatibility oracle, corrected candidate, runtime thresholds,
root hashes, and still-armed rollback watchdog.

The capture runner stages only the hash-bound probe below target `/run`, uses
strict pinned-host SSH, executes the probe once, stores mode-`0600` evidence
outside Git, and invokes the verifier. It contains no fastboot, ADB,
credential creation, signing, `accept-new`, storage mount/write, watchdog
disarm, reboot, or ambiguous retry path.

## Coverage

The target fixture passed its golden record and rejected:

1. a writable NFS lower;
2. a physical block device;
3. an absent block-topology source;
4. an additional USB IPv4 address;
5. an expired rollback watchdog;
6. absent thermal telemetry;
7. password-enabled SSH;
8. a changed no-workload command manifest; and
9. an already-disarmed watchdog.

The host verifier passed 19 test groups covering:

- all exact acceptance values and all corrected-candidate root identities;
- live/test mode and current probe SHA-256;
- boot-ID freshness and exact target kernel;
- eight-CPU, total/available-memory, thermal, and watchdog envelopes;
- canonical unsigned/signed decimal encoding;
- ordered, complete, duplicate-free ASCII/LF records;
- symlink, owner, mode, link-count, and size policy; and
- successful and rejected CLI behavior.

The mocked host runner passed one prepare, copy, remote hash check, boot-ID
read, and record collection. The collection count was exactly one, the
captured bytes matched the supplied target record, and the private result was
mode `0600`.

The 33-case core compatibility suite also passed after the new tests were
added as exact CI gates for the six active capability rows.

## Acceptance envelope

The verifier requires:

- exact Linux `7.1.4-g7a5cef0db479`, AArch64, systemd, and multi-user state;
- at least eight online CPUs, 10 GiB total RAM, and 8 GiB available RAM;
- the exact read-only NFS/OverlayFS/tmpfs storage topology and no physical
  storage;
- exact USB NCM carrier/address and effective key-only SSH;
- 30–128 plausible thermal zones;
- the candidate's 600-second watchdog with at least 60 seconds remaining;
- exact candidate tree, seal, entry-count, subtree, and command-manifest
  identities; and
- no failed units, fatal kernel signatures, or workload.

These are inherited device-specific regression bounds. They do not claim
support for another RAM SKU or a new kernel.

## Safety result

- No phone was contacted.
- No SSH key or known-hosts file was opened by the tests.
- No live signing credential or trust root was created.
- No recovery image, bundle, temporary-boot allowlist, or phone state changed.
- No Podman volume or host artifact was removed.
- The new runner cannot reboot or disarm the watchdog.
- The corrected candidate remains `status=offline`, `authority=none`, and
  `live-pending`.

See the [runtime acceptance contract](../docs/minimal-headless-runtime-acceptance.md).
