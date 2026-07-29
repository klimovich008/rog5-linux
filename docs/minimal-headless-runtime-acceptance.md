# Minimal-headless runtime acceptance

The minimal-headless runtime gate converts one live SSH observation into a
canonical, private, machine-verifiable record. It covers the six active core
capabilities before any later button, battery, suspend, sensor, audio, GPU, or
desktop work.

This gate is complete offline. It does not grant signing, temporary-boot,
credential-use, reboot, watchdog-disarm, or phone authority.

## Components

- `scripts/device/collect-minimal-headless-runtime.sh` performs one read-only
  target observation.
- `scripts/host/verify-minimal-headless-runtime.py` binds that observation to
  the current compatibility oracle and corrected candidate.
- `scripts/host/run-minimal-headless-runtime-acceptance.sh` stages the exact
  probe below target `/run`, captures one record over strict SSH, and invokes
  the verifier.
- `scripts/host/pin-minimal-headless-host-key.py` creates the private
  known-hosts input for a temporary boot without presenting a client key.
- `scripts/device/test-collect-minimal-headless-runtime.sh` builds a synthetic
  proc/sys/run/root fixture and rejects nine cross-capability mutations.
- `scripts/host/test-verify-minimal-headless-runtime.py` exercises the
  canonical parser, candidate binding, thresholds, private-file policy, and
  CLI.
- `scripts/host/test-run-minimal-headless-runtime-acceptance.sh` proves the
  runner uses one strict SSH collection, private evidence, and no boot,
  signing, reboot, storage, or watchdog-disarm action.

All three tests are part of `scripts/host/test-repository-linux.sh`. The
compatibility profile names them as gates for the capabilities they cover.

## Record contract

The probe emits exactly 48 ordered ASCII `key=value` lines ending in LF. The
record identifies:

- format, profile, live/test execution mode, exact probe SHA-256, active
  capability set, corrected candidate, and current boot ID;
- kernel release, AArch64 machine, systemd PID 1, running system state,
  multi-user default, online CPU count, and memory totals;
- OverlayFS root, exact read-only NFS lower, tmpfs state with `nodev,nosuid`,
  zero physical block devices, zero block-backed mounts, and initramfs
  handoff markers;
- exact `usb0` carrier and `169.254.77.2/30` address;
- active SSH, locked root password, one valid authorized key, effective
  key-only policy, host-key metadata, and active sleep inhibitor;
- zero failed units and zero fatal kernel signatures;
- bounded read-only thermal-zone count and min/max telemetry;
- a live rollback process, timer, start identities, parentage, emergency
  descriptors, canonical lease, timeout, and remaining time;
- exact network-root identity, tree/seal/command hashes, tree entry count,
  root subtree, and `workload=none`; and
- final `result=PASS`.

The target probe fails before emitting a record if any check fails. Its
fixture mode is explicit and records `execution_mode=test`; the host verifier
accepts only `execution_mode=live`.

## Host acceptance thresholds

The host verifier first validates the complete ASUS 5.4/accepted 7.1
compatibility oracle and authority-free corrected candidate. It then requires:

| Boundary | Required result |
|---|---|
| CPU | at least 8 online CPUs |
| Total RAM | at least 10 GiB reported in KiB |
| Available RAM | at least 8 GiB and no more than total RAM |
| Storage | OverlayFS, exact read-only NFS lower, tmpfs state, zero physical devices and block-backed mounts |
| USB/SSH | exact NCM address/carrier and strict key-only SSH |
| Thermals | 30–128 readable zones; values between -20 C and 120 C |
| Rollback | exact candidate timeout of 600 seconds with 60–600 seconds remaining |
| Root identity | exact generation, tree, seal, entry count, subtree, and command-manifest values from the corrected candidate |

The 10/8 GiB memory and 30-zone thermal floors inherit the accepted phone's
roughly 11 GiB usable-RAM and 33-zone Linux 7.1 result. They are runtime
regression bounds for this device, not generic ROG Phone 5 SKU requirements.

The record must be a caller-owned, mode-`0600`, unlinked ordinary file with
one link and a maximum size of 16 KiB. Its boot ID must match a separate
strict-SSH read from the same target. The verifier prints only a bounded
summary and does not expose the boot ID.

## Runner boundary

The runner requires an explicit observation guard plus caller-owned
mode-`0600` SSH key and target known-hosts files and a mode-`0700` evidence
directory, all outside the repository. It also requires a clean local branch
at the exact tracked origin commit.

It assumes the current target host key has already been pinned by
`pin-minimal-headless-host-key.py` within the authorized live-cycle
controller. The sealed lower intentionally contains no reusable server host
key; systemd creates a volatile key in the RAM-backed upper layer. The
bootstrap first records the signed recovery gadget's physical USB location,
then accepts only the exact target NCM gadget on that same port and direct
`169.254.77.1/30` route. It scans only one public Ed25519 host key and offers
no client credential. The acceptance runner itself never uses `accept-new`,
disables host checking, or writes a reusable host identity. It:

1. creates one absent `/run` staging directory;
2. copies the current probe and verifies its root ownership, mode, and hash;
3. reads the exact target kernel and boot ID once;
4. executes the probe once with a fixed empty environment and fixed `PATH`;
5. writes one new private record; and
6. runs the fail-closed host verifier.

The runner deliberately does not boot recovery, sign a bundle, commit kexec,
retry an ambiguous action, disarm the rollback watchdog, reboot the target,
resolve the recovery intent, or inspect fallback. Those actions belong to the
separate attended live-cycle controller and authorization.

The USB-continuity bootstrap is a temporary-development trust bridge, not the
long-term server identity. Persistent operation will require a separately
designed host-key state boundary that survives reboot without placing a
private key in Git, a boot image, or an unsealed writable root.

## Hardware-free verification

Run the focused suite:

```sh
scripts/device/test-collect-minimal-headless-runtime.sh
scripts/host/test-verify-minimal-headless-runtime.py
scripts/host/test-pin-minimal-headless-host-key.py
scripts/host/test-run-minimal-headless-runtime-acceptance.sh
```

Run the complete repository gate:

```sh
scripts/host/test-repository-linux.sh ci
```

See the
[offline evidence](../test-results/2026-07-29-minimal-headless-runtime-acceptance-offline.md)
and [core compatibility oracle](core-compatibility-oracle.md).

## Remaining live work

A live result still requires fresh authorization to create/use one ephemeral
live signing credential and perform one attended temporary-boot cycle. The
full controller must preserve the untouched fallback, keep the target
watchdog armed, avoid an ambiguous execute retry, verify fallback return and
host cleanup, and resolve the durable recovery intent. Until that occurs,
the corrected target remains `live-pending` and `authority=none`.
