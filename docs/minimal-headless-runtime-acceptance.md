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
  the current compatibility oracle and either the frozen historical candidate
  or one exact admitted deployment-v3 candidate.
- `scripts/host/run-minimal-headless-runtime-acceptance.sh` stages the exact
  probe below target `/run`, captures one record over strict SSH, and invokes
  the verifier.
- `scripts/host/pin-minimal-headless-host-key.py` creates the private
  known-hosts input for a temporary boot without presenting a client key.
- `scripts/device/test-collect-minimal-headless-runtime.sh` builds a synthetic
  proc/sys/configfs/run/root fixture and rejects 46 cross-capability
  mutations plus an unsupported candidate identity.
- `scripts/host/test-verify-minimal-headless-runtime.py` exercises the
  canonical parser, candidate binding, thresholds, private-file policy, and
  CLI.
- `scripts/host/test-run-minimal-headless-runtime-acceptance.sh` proves the
  runner uses one strict SSH collection, private evidence, and no boot,
  signing, reboot, storage, or watchdog-disarm action.

All three tests are part of `scripts/host/test-repository-linux.sh`. The
compatibility profile names them as gates for the capabilities they cover.

## Record contract

The probe emits exactly 88 ordered ASCII `key=value` lines ending in LF. The
record identifies:

- format, profile, live/test execution mode, exact probe SHA-256, active
  capability set, corrected candidate, and current boot ID;
- kernel release, AArch64 machine, systemd PID 1, running system state,
  multi-user default, exact online/present CPU sets, three EPSS CPUfreq
  policies with exact CPU membership, driver and governor, and memory totals;
- three distinct live mount IDs equal to the initramfs attestation, OverlayFS
  with exact `/mnt/root-ro`, `/mnt/state/upper`, and `/mnt/state/work`
  backing paths, an exact read-only NFSv4.2/TCP lower, tmpfs state with
  `nodev,nosuid`, zero block devices, physical devices, SCSI hosts, RPMB
  devices, UFS platform devices, block-backed mounts, and exact initramfs
  handoff markers;
- exact `rog5-network-root` ConfigFS descriptor, strings, sole `ncm.usb0`
  function/configuration link, primary `a600000` UDC binding, and high-speed
  negotiation;
- exact `usb0` carrier, operational state, MTU, `169.254.77.2/30` address,
  connected `/30` route, only the three kernel-default IPv4 policy rules, and
  absence of an IPv4 default route in every routing table;
- active SSH on port 22, one current server session from the exact USB host
  peer, locked root password, one 256-bit Ed25519 authorized key, effective
  key-only policy evaluated with the real remote/local address and local-port
  tuple, a matching 256-bit Ed25519 host-key pair, and active sleep inhibitor;
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
compatibility oracle. Its no-option compatibility path loads only the frozen
historical candidate. The deployment path instead requires the exact
`headless-ssh-deployment-v3` profile plus an absolute canonical caller-owned
mode-`0400` or `0444`, singly linked candidate record outside the repository
and its admitted nonzero SHA-256. It validates the candidate with the shared
adapter, requires the fixed deployment tuple, rejects the tracked fixture tree
and seal, rereads the file to detect replacement, and never falls back to the
historical candidate. It then requires:

| Boundary | Required result |
|---|---|
| CPU | exactly CPUs `0-7` online and present; exactly `policy0`, `policy4`, and `policy7` for CPU sets `0-3`, `4-6`, and `7`; `qcom-cpufreq-hw` plus `schedutil` on all three |
| Total RAM | at least 10 GiB reported in KiB |
| Available RAM | at least 8 GiB and no more than total RAM |
| Storage | three distinct mount IDs equal to the initramfs attestation; exact OverlayFS lower/upper/work paths over read-only NFSv4.2/TCP plus tmpfs state; zero block, physical, SCSI, RPMB, UFS-platform, and block-backed-mount exposure |
| USB gadget | exact `1d6b:0104` product/configuration, sole `ncm.usb0`, primary `a600000` UDC, and high-speed operation |
| USB network | exact carrier/up/1500-MTU `usb0`, target `/30` address and connected route, only default kernel policy rules, with no IPv4 default in any table |
| SSH | active port 22 reached by exactly one current `169.254.77.1` USB-peer session; one 256-bit Ed25519 authorized key, matching Ed25519 host-key pair, and strict key-only policy evaluated for that exact remote/local connection tuple |
| Thermals | 30–128 readable zones; values between -20 C and 120 C |
| Rollback | exact candidate timeout of 600 seconds with 60–600 seconds remaining |
| Root identity | exact generation, tree, seal, entry count, subtree, and command-manifest values from the corrected candidate |

The exact CPU policy topology follows the accepted DT and Qualcomm driver
behavior. The 10/8 GiB memory and 30-zone thermal floors inherit the accepted
phone's roughly 11 GiB usable-RAM and 33-zone Linux 7.1 result. They are
runtime regression bounds for this device, not generic ROG Phone 5 SKU
requirements.

The strengthened storage checks are documented in the
[offline storage-isolation result](../test-results/2026-07-29-storage-isolation-offline.md).
They preserve the current zero-storage profile and do not authorize the
separate persistent-root design.

The strengthened USB/NCM/SSH checks are documented in the
[offline USB/NCM/SSH result](../test-results/2026-07-30-usb-ncm-ssh-offline.md).
They bind the target-side gadget and current SSH transport to the independent
host-side USB continuity/bootstrap checks; neither side alone is used as proof
of the complete link.

The record must be a caller-owned, mode-`0600`, unlinked ordinary file with
one link and a maximum size of 16 KiB. Its boot ID must match a separate
strict-SSH read from the same target. The verifier prints only a bounded
summary and does not expose the boot ID.

## Runner boundary

The runner requires an explicit observation guard plus caller-owned
mode-`0600` SSH key and target known-hosts files and a mode-`0700` evidence
directory, all outside the repository. It also requires a clean local branch
at the exact tracked origin commit.

With no positional arguments it preserves the historical candidate workflow.
The deployment workflow accepts only the exact triplet
`headless-ssh-deployment-v3 CANDIDATE_RECORD CANDIDATE_SHA256`, checks that
record before SSH credential paths, passes only the fixed candidate identifier
to the target probe, and gives the same canonical path and hash to the host
verifier. Arbitrary target-side paths, profile names, or candidate names are
not accepted.

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
4. executes the probe once with a fixed empty environment, fixed `PATH`, and
   one allowlisted candidate identity;
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
[CPU/RAM topology evidence](../test-results/2026-07-29-cpu-ram-topology-offline.md),
the earlier
[runtime evidence](../test-results/2026-07-29-minimal-headless-runtime-acceptance-offline.md),
and [core compatibility oracle](core-compatibility-oracle.md).

## Remaining live work

A live result still requires a non-fixture key-bound root/candidate/bundle,
the fixed stable-recovery deployment profile, and an installed v3 export
before fresh authorization to create/use one ephemeral live signing
credential and perform one attended temporary-boot cycle. The full controller
must preserve the untouched fallback, keep the target watchdog armed, avoid
an ambiguous execute retry, verify fallback return and host cleanup, and
resolve the durable recovery intent. Until that occurs, the corrected target
remains `live-pending` and `authority=none`.
