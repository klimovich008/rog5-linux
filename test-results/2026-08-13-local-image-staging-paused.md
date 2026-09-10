# Local-image staging paused before image creation

Date: 2026-08-13

Status: **paused at an exact recoverable cleanup boundary. No image, loop
device, filesystem, raw-device write, partition operation, or reboot occurred.**

The sealed 536,746,495-byte headless Arch archive and signed Alpine
`libarchive-tools 3.8.7-r0` APK were copied only to fallback tmpfs. The APK
passed its Alpine signature check and exact SHA-256 check. A trial
`apk extract --root /run/...` invocation unexpectedly interpreted its output
relative to the SSH session working directory and created this complete
userdata subtree:

```text
/root/usr/
/root/usr/bin/
/root/usr/bin/bsdcat
/root/usr/bin/bsdcpio
/root/usr/bin/bsdtar
/root/usr/bin/bsdunzip
```

The two directories contain exactly those four regular files and no other
entry. Each file has one link and matches the corresponding member of the
retained, hash-pinned APK:

| File | SHA-256 |
|---|---|
| `bsdcat` | `fd509aa892f0e5ae5bb6aea12835e6d0754bf5bb64e98f4b13e176d74014f2a1` |
| `bsdcpio` | `3bf8c918fcb1f03b50376b9266fe20b4e55ee8303fd3ad9629557781ffca8260` |
| `bsdtar` | `a119cde57ed38a306bcb235cd275646723e6c84fa1923c77027b23dd1c8c2ca0` |
| `bsdunzip` | `8c208e795581a806ec9ddb291e7d34b3e4b2356c535a6eb5ec7a9d92cbd15229` |

The workflow stopped immediately after the read-only inventory. The corrected
workflow extracts the one exact ARM64 `bsdtar` member on the PC, verifies its
ELF architecture and hash, and will copy that binary directly to `/run`; it
will not invoke `apk extract` on the phone. The exact `/root/usr` subtree is
preserved until its cleanup is confirmed.
