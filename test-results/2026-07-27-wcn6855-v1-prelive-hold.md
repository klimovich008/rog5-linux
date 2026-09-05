# WCN6855 enumeration v1 — protected-root pre-live HOLD

Date: 2026-07-27

Decision: **PASS offline / HOLD live**

The exact successor-v3 Arch root plus the accepted WCN6855 overlay is now a
separate protected export at:

```text
/var/lib/rog5-network-root-wcn6855-v1
```

The preparation path verifies the read-only successor-v3 Btrfs root, Arch
archive, WCN6855 bundle manifest, modules, and root overlay before creating
one snapshot. It replaces only the exact module tree and four overlay files,
removes the predecessor seal, generates a distinct Ed25519 server identity,
recursively seals the result, sets mode `0555`, and makes the subvolume
read-only.

| Field | Value |
|---|---|
| promotion | `UNBOOTED_HOLD` |
| Btrfs property | `ro=true` |
| recursive entries | 181,276 |
| recursive tree SHA-256 | `4f1750cf54657aa9aa85c0425fd35ee63d8ab46f6d7f8fb8c9c8a74e323a724b` |
| export seal SHA-256 | `e7249141aea31d743d4d52abc14a0f870f5e57d5e379a7bfdf2963305355a310` |
| host public-key SHA-256 | `53a35ec1c71908faa6ede4ce5896208021cbb658f6352ea88fd6f39c0ea46f91` |
| host-key fingerprint | `SHA256:6hnubHmfGrfLl5KBTfyNUe8dlHjuLEJNK3/g/yq0Ow0` |

The verifier proves the non-Wi-Fi tree remains byte- and metadata-identical
to successor v3, the SSH identity is new, authorized client access is
unchanged, modules and aliases match, automatic module loading is
blacklisted, `wlan0` is unmanaged, and no network/provider credential exists.
Disposable snapshots with a changed seal, probe, blacklist, QMP module, and
injected NetworkManager profile were all rejected and deleted.

The NFS wrapper requires one token and verifies before state. It hash-pins
and sources the accepted NFS runtime suffix. An actual unarmed invocation
preserved relevant host state:

```text
PASS unarmed WCN6855 NFS refusal state_sha256=5f2f0370fa8876d9ab10c527e8aece4e9195805c4f42aa8d1c7a31ca2e34a179
```

The host runner requires separate live/reboot guards, a clean synchronized
branch, caller-owned credentials outside Git, strict host-key checking under
`rog5-wcn6855-v1`, local root verification, and exactly two mode-`0500` files
in target tmpfs. It invokes the existing enumeration-only target gate once,
requires both PASS records, writes one private mode-`0600` log, and never
retries.

ShellCheck, focused contracts, five root mutations, mocked runner execution,
and the complete Linux-rootfs aggregate pass.

No NFS window, temporary boot, reboot, kexec, module load, PCIe/radio probe,
scan, association, AP, VPN, credential use, or flash occurred. The phone
remained untouched on Alpine. A fresh current-state preflight and exact user
authorization remain mandatory before at most one attended RAM-only cycle.
