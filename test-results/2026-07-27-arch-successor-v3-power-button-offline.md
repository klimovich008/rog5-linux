# Arch successor v3 power-button screen toggle — offline result

Date: 2026-07-27

Result: **PASS OFFLINE. A separately versioned Arch Linux ARM successor-v3
root now enables a confined `pmic_pwrkey` handler that maps only a
`KEY_POWER` press to the existing DPMS/backlight screen toggle. The complete
successor-v2 verifier remains byte-exact and passes first. The 655-package
AArch64 root passed its v3 verifier before archival and after extraction into
a second clean volume. The resulting archive is manifest-pinned,
path-safe, and credential-clean.**

No phone command ran. No input device, backlight, display, NFS export,
firewall, interface, service, boot, kexec, module, partition, or credential
changed on the phone. The v3 archive is unserved, unbooted, and `HOLD`.

## Fail-first sequence

The work preserved three independent red gates before implementation:

1. Commit `424c74e` added the event/service test. It stopped on:

   ```text
   FAIL missing executable power-button handler
   ```

2. Commit `b94ca31` added the successor-v3 layering contract. It stopped on:

   ```text
   FAIL missing or linked successor-v3 input: .../stage-arch-rootfs-v3.sh
   ```

3. Commit `51a4d5f` added the archive contract after the first successful
   archive was built. It stopped on:

   ```text
   FAIL successor v3 archive lacks one exact manifest identity
   ```

The implementation commits are `3f6cc68`, `f0a10ac`, `09c5cbf`, `b8b8001`,
`1a33df3`, and `f8aa37f`.

## Input-event behavior

`power-buttond.py` uses only the Python standard library and the native
AArch64 `struct input_event` layout:

```text
@llHHi = 24 bytes
EV_KEY = 1
KEY_POWER = 116
press value = 1
```

At runtime it requires exactly one character device whose sysfs input name is
`pmic_pwrkey`. It ignores release value `0`, autorepeat value `2`, other
event types, and other keys. One accepted press invokes:

```text
/usr/local/bin/rog5-screen-toggle.sh toggle
```

The existing toggle preserves/restores brightness, writes backlight zero for
off, and attempts the matching Wayland DPMS transition without suspending
server workloads.

The synthetic regression verifies:

- release, repeat, and `KEY_VOLUMEDOWN` do not invoke the toggle;
- one `KEY_POWER` press invokes exactly one `toggle`;
- a truncated input record is rejected explicitly;
- a failed or timed-out screen toggle is not reported as success; and
- the implementation uses neither a shell command string nor a boot,
  storage, Fastboot, or ADB action.

## Service boundary

`rog5-power-button.service` is enabled by successor v3 under
`multi-user.target`. It runs as root because the existing toggle writes the
root-owned backlight sysfs node and may lower identity to the active
compositor user for KScreen. Its capability bounding set contains only
`CAP_SETUID` and `CAP_SETGID`.

The unit also applies:

- a closed device policy allowing read-only Linux input character devices;
- a private network namespace plus `AF_UNIX`-only sockets;
- strict read-only system files and read-only home directories;
- no privilege escalation, ambient capability, kernel module/log, cgroup,
  clock, namespace, realtime, SUID/SGID, or writable-executable-memory access;
- restart backoff and a five-start/five-minute limiter; and
- no access to block-device classes through its device cgroup.

`systemd-analyze verify` passes. The host systemd security audit reports
overall exposure `3.4 OK`; remaining exposure is intentional for input
access, backlight sysfs, active-session discovery, and user switching.

## Versioned rootfs layering

Successor v3 does not rewrite successor v2. Its stage:

1. runs the complete existing successor-v2 stage and verifier;
2. installs only the handler and service;
3. enables the service; and
4. runs the v3 verifier.

The v3 verifier pins the accepted v2 verifier at:

```text
5137868d14400815e99ee642d78ccd125196ce811238120836c59cce92abe44e
```

It reruns that verifier, compares both installed v3 files byte-for-byte with
the repository, checks their modes and enabled state, executes the synthetic
input regression against the installed paths, and runs
`systemd-analyze verify`.

The Linux host staging selector accepts only `v2` or `v3`; `v2` remains the
default. The v3 wrapper selects the new stage and output without duplicating
the complete archive pipeline.

## Clean AArch64 build

The first two build attempts failed safely before a package transaction:

- the first v3 runner used `/workspace` before entering the chroot; and
- the corrected path then exposed that the inherited runner is intentionally
  mode `0644` and must be invoked through Bash.

The retained failed volumes were inspected, confirmed unused by any
container, and removed by their exact generated names. Commits `09c5cbf` and
`b8b8001` fix and contract-test those paths.

The third attempt:

- verified the signed Arch Linux ARM input and package signatures;
- used the existing network-root module and A660 firmware manifests;
- passed the full v2 and v3 verifiers in the staged root;
- archived with ACL, xattr, flag, ownership, and mode preservation;
- extracted into a separate clean volume;
- passed the full v3 verifier again; and
- removed both transient stage/verify volumes.

The package count remains `655`; no dependency was added. Python was already
part of the accepted Plasma/server package set.

## Exact archive

| Property | Value |
|---|---|
| local artifact | `artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor-v3.tar.gz` |
| size | `2,007,033,670` bytes |
| SHA-256 | `a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7` |
| embedded project commit | `b8b80013d0acd912530ce42af7bc0adf7f9fd6ea` |
| kernel release | `7.1.4-g7a5cef0db479` |
| packages | `655` |
| machine ID bytes | `0` |
| builder image | `34ecc17078b364df195ad61253520b1cac487dca05773dc4b2fc2bacb0941941` |
| builder digest | `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c` |
| promotion state | `UNBOOTED_HOLD` |

The independent archive contract:

- requires one exact manifest identity;
- verifies size, SHA-256, gzip integrity, and safe archive paths;
- requires the installed handler, service, enabled symlink, build metadata,
  package database, and unchanged v2 hotspot controls;
- compares the installed handler/service and hotspot files byte-for-byte with
  their reviewed sources; and
- rejects embedded SSH host keys, WireGuard profiles, NetworkManager
  connections, KRDP/KWallet state, or files inside the agent private
  directory.

The approved public SSH key is still the only deployment authorization input.
No private key or runtime credential is in the archive.

## Exact source identities

| Input | SHA-256 |
|---|---|
| power-button handler | `66b3a8bfc32434e450d10ea707e21481b991e6fc728cd7afa618664331b4298a` |
| systemd service | `c617188753e17482328f69abc55c3d2b6da62dd543ecb3a14f551c4f17fb72c7` |
| event/service regression | `ac01eb949e9ae1a663041d22e46bc3a4669072636b7153f98193a373cd927e57` |
| v3 device stage | `b5204db26b265c06d6abcc77744646cc6c4d55c731e643200c76cbda43ac1658` |
| v3 staged-root verifier | `734283f0a465011682f8cca625614f4e67ec4554d3b3163e9bad326d78f3551d` |
| v3 stage runner | `4fc7a4a8ca4d7b677483b6f3f1b66489e905acb078e41c67f7e50c79aac5b4bc` |
| v3 host wrapper | `d735097f0b3b2d42c462b40c3342fb687acfc869a315bec7031b0dd1b4eb1081` |
| v3 layering contract | `27c18029a6855135230e3f241b21a381bd37a9c279cc32eb771effb34a27013d` |
| v3 archive contract | `72191d13b34ebc68cf5b6d51291039efea802d1c1e22b6198d686119f2b1d44a` |
| Linux-rootfs aggregate | `33af51b33f77fa2b3a299dd899fcfa8af73380340030bb96b9f7fe167e5e3fcb` |

## Current validation

```text
PASS KEY_POWER screen toggle
PASS power button handles only KEY_POWER presses, rejects truncated input and failed toggles, and is device-confined
PASS successor v3 layers the confined power-button toggle over byte-exact v2 evidence without a phone command
PASS staged Arch successor v3 rootfs kernel=7.1.4-g7a5cef0db479 power-button=press-only-screen-toggle
PASS successor v3 archive is manifest-pinned, path-safe, credential-clean, v2-preserving, and power-button-enabled
PASS Linux rootfs tools pin signed input, preserve metadata, and avoid phone writes
```

Python compilation, Bash/POSIX syntax, ShellCheck at warning severity,
`systemd-analyze verify`, `gzip -t`, exact source/archive hashes, clean
extraction, credential-path rejection, and `git diff --check` pass. No
disposable container or stage/verify volume remains.

## Remaining live gates

This result does **not** prove that pressing the physical button toggles the
phone display. Hardware acceptance still requires:

- one attended `pmic_pwrkey` press and release through the real switch/IRQ
  path;
- Linux 7.1 DRM, DSI, panel, Pixelworks/backlight, KWin, and KScreen
  acceptance before using the display as an indicator;
- screen on/off/on checks while SSH, VPN, hotspot, and server workloads
  remain alive;
- confirmation that PowerDevil does not duplicate the system handler;
- long-press emergency-power behavior, debounce, repeated presses, input
  disconnect/rebind, suspend/wake, and reboot tests; and
- panel-off, 60/90/120/144 Hz, thermal, charging, and battery measurements.

Successor v2 remains the separately protected server-path candidate.
Successor v3 has no protected export, NFS allowlist, target gate, runner, or
live authorization. No live authority follows from this offline result.
