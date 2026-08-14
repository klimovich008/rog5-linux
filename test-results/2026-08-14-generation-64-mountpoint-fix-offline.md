# Generation 64 local-image mountpoint-fix offline checkpoint

Date: 2026-08-14

Status: **unbooted; no claim created; RAM-only candidate only.**

Generation 63 proved the contained UFS write window, outer userdata RW mount,
and writable loop attachment. Its inner ext4 mount failed because the sealed
initramfs did not create `/mnt/probe-root`. Generation 64 makes the minimal
correction: create that fixed mountpoint with the other repository-owned
mountpoints and fail before userdata unmount unless it is a non-symlink
directory.

Regression coverage proves the directory creation and its ordering before the
write window. The read-only and local-write initramfs profiles both pass; no
kernel, DTB, UFS policy, marker format, storage identity, or write-surface
change is included.

## Reproducible outputs

- release: `7.1.4-g359318de534f`;
- reused clean-twin `Image`: `7c89d9a0a7ace2b0057b6cf2b535e134da596d3f3c3c3774c5b64014e32bf234`;
- unchanged DTB: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`;
- twin initramfs: `8bc752db6e58370b21d531bdd51354233934b9fbfa56e771fb22cf9ff598eed0`;
- signed runtime manifest: `8b2e95268be4e5e0c65eb9367514bb93ab2c20f38a3848a0986de4fe4336d221`;
- Generation 64 recovery AVB image: `9e7fa77363afd7afceceb772d4d4c4b7d7a651e38ea9c44354604c4334da818b`;
- unchanged raw recovery: `5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
- AVB salt: `e53e4b09689e0a2258e6ff0f5c6087a8f669bc5d0c4b53235d7e3e9f153c5902`;
- AVB digest: `7348ccbac3447e0ff9a6452bfa320c9c9b9e52ddf268a05ef798eadcaca73a7d`;
- generation record: `eeff887264c0ba40088b2d647947e97758fd4760594ebc3f0a19c55f4e0c44ca`.

Twin initramfs production builds completed in 2.305 seconds total and matched
byte-for-byte. The focused storage, initramfs, claim, admission, gate, and
current-profile suite passed in 25 seconds; the compatibility-oracle checks
passed in 12 seconds; full `scripts/host/test-repository-linux.sh ci` passed
in 468 seconds. No phone contact, claim creation, or boot occurred during this
offline checkpoint.
