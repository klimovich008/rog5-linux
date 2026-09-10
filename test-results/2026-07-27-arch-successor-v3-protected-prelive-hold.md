# Arch Plasma/server successor v3 — protected pre-live HOLD

Date: 2026-07-27

Decision: **PASS OFFLINE, HOLD LIVE. Successor v3 now has a separately
protected read-only root, an exact-root verifier-first NFS control, a
power-input-aware target gate, and a strict one-shot SSH runner. The NFS
window was not started and the phone was not booted.**

PolicyKit was used only to create and verify a host-local Btrfs subvolume,
test disposable mutation snapshots, and confirm an unarmed server refusal.
No NFS, RPC, firewall, interface, listener, mount, boot, kexec, reboot,
Fastboot, ADB, flash, partition, phone-storage, or credential change ran.
The connected Alpine fallback was contacted only by strict, read-only SSH
after the host checks passed.

This checkpoint builds on the
[successor-v3 archive result](2026-07-27-arch-successor-v3-power-button-offline.md).
It does not modify or replace the accepted v1/v2 roots or controls.

## Protected export

```text
path=/var/lib/rog5-network-root-arch-successor-v3
owner_mode=0:0:0555
btrfs_ro=true
seal_sha256=26b4fcd8f21c5974d281d4b39386f82965265a31728c3a54877ab6717e98f2a7
archive_size=2007033670
archive_sha256=a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7
project_commit=b8b80013d0acd912530ce42af7bc0adf7f9fd6ea
kernel=7.1.4-g7a5cef0db479
packages=655
tree_entries=181243
tree_sha256=fe0852cb8ad5e4611f6dd63cd65713520776817b242e8881f7aa4d1869c02657
ssh_host_public_key_sha256=8473f387fd69149a4b970b93e617cc61afdd2e7f6a5cceeae64fd19c1bc15976
promotion=UNBOOTED_HOLD
```

The preparer requires one exact manifest identity, the exact local artifact,
12 GiB free on Btrfs, and a previously absent exact destination. It extracts
with ACL/xattr/flag/ownership preservation, installs the reviewed SSH policy,
generates one dedicated Ed25519 host identity, recursively seals metadata,
file contents, ACLs, and xattrs, changes the root to mode `0555`, and sets the
Btrfs subvolume read-only before final verification and rename.

The seal additionally pins the package, Chromium, fail-closed hotspot,
power-button handler/service, offline report, and staged-root verifier
hashes. The private host key remains root-only mode `0600` inside the
protected root and is neither printed nor committed.

## Fail-first and mutation sequence

Commit `d1ebf7e` added the export contract before either implementation. It
stopped on:

```text
FAIL missing executable successor v3 export tool: .../prepare-arch-successor-v3-export.sh
```

Commit `3c1e17f` added the dedicated preparer and verifier. The resulting root
passed full verification, then four independent writable COW snapshots were
mutated, changed to read-only, rejected, and deleted:

- export seal;
- installed power-button handler;
- installed power-button systemd service; and
- account database.

No partial export or mutation subvolume remains.

Commit `39b291b` added the NFS, target, and host-runner contracts before their
implementations. They stopped independently on:

```text
FAIL missing successor v3 NFS control: .../serve-arch-successor-v3.sh
FAIL missing Arch successor v3 target gate
FAIL missing Arch successor v3 live-gate control: .../run-arch-successor-v3-live-gate.sh
```

Commit `504c707` added the inert controls and included all v3 checks in the
aggregate Linux-rootfs regression.

## Exact-root NFS boundary

`serve-arch-successor-v3.sh` accepts only:

```text
/var/lib/rog5-network-root-arch-successor-v3
```

It requires the exact separate token:

```text
ALLOW_ARCH_SUCCESSOR_V3_NFS=1
```

The exact-root check, token check, and complete v3 protected-root verifier
all precede `etab=` and every mutable host-state line. From `etab=` onward,
the server is byte-identical to the accepted shared runtime:

```text
runtime_suffix_sha256=e6e0f8907ed86dbdd8be0ed58009ce34d6b157defbd8836706f1d1e2beef1a6a
```

That inherited runtime remains NFSv4.2/TCP only, read-only, restricted to the
exact USB host/phone addresses, isolated by runtime firewall rules, bounded
to 60–86,400 seconds, and cleanup-on-exit.

An actual PolicyKit invocation without the token returned:

```text
FAIL set ALLOW_ARCH_SUCCESSOR_V3_NFS=1 for the attended Arch successor v3 window
status=1
```

Normalized NFS/RPC units, exports, listeners, temporary mount, mount daemon,
NFS threads, `ip_nonlocal_bind`, firewalld state, protected-root properties,
and seal hashes were byte-identical before and after:

```text
before_sha256=47d3ce82b03b7a22adb16d6cb8583ce4fbf94323ed897800ed7ea4b3a3cdd401
after_sha256=47d3ce82b03b7a22adb16d6cb8583ce4fbf94323ed897800ed7ea4b3a3cdd401
```

## Target and host gates

The target gate requires separate exact gate/reboot tokens, Linux 7.1.4,
systemd `running`, headless default, successful coldplug/module/sysusers/
tmpfiles units, read-only NFS lower plus volatile OverlayFS state, zero
physical storage, exact v3 seal/archive/package identity, zero failed units,
zero fatal kernel signatures, and every present backlight at zero.

It additionally requires:

- active, zero-restart `rog5-power-button.service`;
- exact installed power-button handler and service hashes;
- exactly one `pmic_pwrkey` event character device;
- inactive optional Chromium, ttyd, VPN-hotspot, and graphical-login units;
- unchanged isolated agent and fail-closed hotspot controls; and
- an independent transition watchdog before initial-watchdog handoff and
  exactly one normal fallback reboot request.

The gate does not synthesize an input event or claim a physical-button/display
pass.

The strict host runner does not start NFS or boot the phone. It requires clean
synchronized Git, caller-owned mode-`0600` key and known-hosts files outside
Git, a mode-`0700` private evidence directory, complete PolicyKit root
verification, host-key alias `rog5-arch-successor-v3`, two exact mode-`0500`
tmpfs controls, one invocation, no retry, a private mode-`0600` log, and an
expected reboot disconnect. Its mock proves one verify, prepare, copy,
remote verify, and gate call.

## Validation

```text
PASS Arch successor v3 export package=655 agent=isolated hotspot=fail-closed-v2 power-button=press-only-screen-toggle services=exact secrets=absent root-owned read-only Btrfs mode 0555 promotion=UNBOOTED_HOLD
PASS Arch successor v3 export is manifest-pinned, recursively sealed, read-only Btrfs, power-button-pinned, mutation-tested, predecessor-independent, unbooted, and non-flashing
PASS Arch successor v3 NFS window is exact-root, one-token, verifier-first, bounded, predecessor-independent, and non-flashing
PASS Arch successor v3 target gate is first-boot, screen-off, storage-free, power-input-pinned, fail-closed-hotspot-pinned, watchdog-handed-off, and one-reboot
PASS host Arch successor v3 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries
PASS Linux rootfs tools pin signed input, preserve metadata, and avoid phone writes
```

Bash/POSIX syntax, ShellCheck at warning severity, archive identity, recursive
seal, four negative mutations, runtime-suffix equality, mock call counts,
one-reboot ordering, and `git diff --check` pass.

| Control | SHA-256 |
|---|---|
| v3 export preparer | `a773506fab1b3f9e0f1de3bf1dc33da4cc5cc11f0442eaa82f1562a5570b0251` |
| v3 protected-root verifier | `ee301696a22565bb338781b455e5510dbb7102b1e11e1653baba9538a3282e1e` |
| v3 export contract | `11a64f4a4e6a7a3005d124da2fc1e2ba5c0254023422b488233f5c7ef9f8c22c` |
| dedicated v3 NFS server | `1489b0df9bd8451f09446631a56a607c15c6961deadd8a08cbcf2c1176849491` |
| v3 NFS-window test | `68eaa122289061a8423a205bd99db5968d89513021aebb18ca030747f5f329ef` |
| v3 target first-boot gate | `7b7b291d7972730f7914b6d23dcd41295e03e0931d51c37ba6ef7c8e0da9ba79` |
| v3 target-gate test | `14fc3ba9235657240bab47723fb2672c2787cd50e2b5722a53e2eae5ac2a5cb1` |
| v3 strict-SSH host runner | `38f4dc5b86c28d8e017603a9d6dc78e04bbdacda8b294356ee988e0835461493` |
| v3 host-runner test | `7fcfdc8c2e2134833d64bf254c763bb821bb056724ceaf3c75f3911d1a64074b` |
| aggregate Linux-rootfs test | `93bfc97526542a749b7d81832f8d1514d0d2de7c2e5e488cab8524768766a2ac` |

Accepted predecessor identities remain unchanged:

```text
v1_server_sha256=e3961cc441ae6cb75f1a3dcbbd5e4ccc99b31c67018159ac10f61c11f1548769
v2_server_sha256=5101b94b472cce99b55414516003b08c306e758b27dbdf6efd3bff0ad96f93ac
v2_target_gate_sha256=bfacfeb83bf14468ea1fd349a3bc71ff443fb5c303a47fa2d761fa5291455c1f
v2_host_runner_sha256=7151690f219d0d6e8a5df4a84d615e792e2c65d44e98e77211aa7ded80cc42a1
v2_staged_verifier_sha256=5137868d14400815e99ee642d78ccd125196ce811238120836c59cce92abe44e
```

## Connected fallback health

Strict read-only SSH to `rog5-fallback` returned:

```text
kernel=5.4.134-qgki-perf-00001-g6c308144c23e
os=alpine
version=3.24.0
brightness=0
nfs_mounts=0
http_7681=ok
http_6080=ok
http_9222=ok
```

## Remaining live boundary

This result authorizes no NFS start, phone boot, target invocation, reboot,
retry, or flash. Successor v3 still needs one separately reviewed attended
RAM-only cycle to prove the real power switch/IRQ, service stability, screen
off/on behavior, server continuity, and exact fallback/cleanup.

GPU acceleration remains the critical dependency, so the separately reviewed
v10 GMU/CX runtime-PM diagnostic remains the next selected live candidate.
Its sole acceptable authorization text remains:

```text
GO A660 GMU/CX runtime-PM v10 one-cycle RAM-only diagnostic
```

That phrase authorizes only the v10 diagnostic, not successor v3. No v3 live
authorization phrase has been issued.
