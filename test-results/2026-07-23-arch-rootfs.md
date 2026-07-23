# Arch Linux ARM rootfs intake

Result: **PASS** for the authenticated userspace input. This is not an ASUS boot image and was not installed on the phone.

## Inputs

- Rootfs: official generic AArch64 `ArchLinuxARM-aarch64-latest.tar.gz` from an Arch Linux ARM mirror.
- Detached signature: matching `.sig` from the same mirror.
- Public keyring: `archlinuxarm/archlinuxarm-keyring` commit `91e6b11698f8df66042d56aaa56fbe9c9263847d`.
- Expected signer: full fingerprint `68B3537F39A313B3E574D06777193F152BDBE6A6`.

## Gates

- Interrupted download quarantine and resume: **PASS**; incomplete bytes were rejected and never promoted from `.part`.
- Detached signature and exact full fingerprint: **PASS**.
- Archive traversal/absolute-path check: **PASS**.
- Required `os-release`, shadow database, Bash, and pacman paths: **PASS**.
- Cached re-verification: **PASS**.
- Deliberately wrong fingerprint: **PASS** by rejection.
- Final size: `818293654` bytes.
- Final SHA-256: `3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a`.

GNU tar reports libarchive capability-xattr keywords while listing the archive. Final extraction must therefore happen on a Linux filesystem with a tool that preserves ACLs, xattrs, capabilities, ownership, and modes. Password accounts must be locked and signature-enforced pacman updates must pass before any network listener is enabled.
