# WCN6855 enumeration v1 — current readiness HOLD

Date: 2026-07-27

Decision: **PASS current readiness / HOLD live**

The post-restart host, persistent Alpine fallback, protected Arch root,
runtime package, and one-cycle controls are technically ready for one
enumeration-only RAM boot. This checkpoint does not authorize that boot.

## Current identities

The clean local branch and its remote-tracking branch both resolve to:

```text
b4a0c11fc1347c7a5ba1ffd59db5242c1cdf656c
```

The immutable runtime inputs remain:

| Input | SHA-256 |
|---|---|
| fifteen-artifact package manifest | `9bc99cf80a85388aff7732a0101771c7fcdd18479ba287c62a8dc9b22bd523cd` |
| temporary-boot AVB image | `1a3358d5c3f90453505c37b4637527701bccbcf0761513636368cf25db0577c4` |
| Linux 7.1.4 target Image | `a4edaee34dca66534cf886fd0daa6068273d4fd722b63960d517ef17699af43e` |
| WCN6855 DTB | `15acdcd6fad910f105047ef53de08b47cafadbbf94827e123931408d92310d89` |
| protected-root seal | `e7249141aea31d743d4d52abc14a0f870f5e57d5e379a7bfdf2963305355a310` |
| protected-root verifier | `5fcb8fb6773c9634e7a333960c1b8a354feb89ada21a1ddc558f1c74db9af078` |
| verifier-first server | `bc0f5a2bc1d82a2638bb318b7cbfa4605cd16c0a675fc2b0faae804f5a137add` |
| strict host runner | `54e91b24e3ebafaf8dddca669619b2e0f0982db3549c96b7006e463a9b656ec1` |

## Protected-root verification

The reboot-persistent export at
`/var/lib/rog5-network-root-wcn6855-v1` remains a root-owned mode-`0555`
read-only Btrfs subvolume. Its mode-`0444` seal is unchanged. A fresh complete
recursive verification returned:

```text
PASS WCN6855 v1 export modules=exact firmware=predecessor-pinned probe=enumeration-only credentials=absent dedicated-host-key root-owned read-only Btrfs mode 0555 promotion=UNBOOTED_HOLD
```

The focused export, bounded-server, and host-runner contracts pass, followed
by the complete Linux-rootfs aggregate:

```text
PASS WCN6855 v1 export is exact-overlay, recursively sealed, read-only Btrfs, dedicated-key, mutation-tested, unbooted, and non-flashing
PASS WCN6855 v1 NFS window is exact-root, one-token, verifier-first, bounded, byte-identical-runtime, and non-flashing
PASS host WCN6855 v1 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries
PASS Linux rootfs tools pin signed input, preserve metadata, and avoid phone writes
```

## Actual unarmed refusal

The current server was invoked through PolicyKit with its opt-in token absent.
It stopped before verification or host-state mutation:

```text
FAIL set ALLOW_WCN6855_V1_NFS=1 for the attended WCN6855 enumeration-only window
```

Normalized before/after state was byte-identical:

```text
before_sha256=122234cbcdaf4e0d9b37c5a2447522c7238c55b4be92bbf6faae2a939686ab9a
after_sha256=122234cbcdaf4e0d9b37c5a2447522c7238c55b4be92bbf6faae2a939686ab9a
```

The snapshot covered NFS, rpcbind and firewalld units; exports; listeners on
ports 111, 2049 and 32767; NFS processes and threads; the temporary mount;
`ip_nonlocal_bind`; runtime firewall state; IPv4 interface identity; the
Btrfs read-only property; and the export seal. Final state retained inactive
NFS/rpcbind, zero NFS threads, `ip_nonlocal_bind=0`, and `ro=true`.

## Current fallback

Strict identity-pinned SSH reached the installed Alpine 3.24 fallback on exact
kernel `5.4.134-qgki-perf-00001-g6c308144c23e`. The existing read-only
preflight found the expected BusyBox PID 1, Qualcomm fallback compatible,
ext4 root, no project diagnostic stage or module, empty pstore, no fatal log
signature, safe thermal telemetry, and the required recovery runtime:

```text
PASS exact persistent fallback ready for guarded bootloader reboot
```

The physical panel remained at backlight zero, the loopback-only four-port
remote tunnel was active, about 10.3 GiB memory remained available, and swap
was unused. These observations are fallback health evidence only.

## Live boundary

No NFS window, fastboot transfer, temporary boot, reboot, kexec, module load,
PCIe enumeration, firmware start, scan, association, AP, VPN, credential
deployment, storage write, or flash occurred. The only phone contact was the
read-only fallback health check.

One live cycle still requires a fresh explicit user instruction that names
the WCN6855 enumeration-only cycle and accepts its no-retry, RAM-only,
never-flash boundary. Until then the root remains unserved and the package
remains `UNBOOTED_HOLD`.
