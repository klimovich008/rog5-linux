# Generation 146 key-only account correction

Result: **CONSUMED; KEY-ONLY SSH PASSED; R3 INSTALLER GLOB FAILURE.** Never
flash or retry.

Generation 145 passed UFS, userdata identity, and storage lock, then reported
`runtime/nologin-identity`. The sealed archive has no `/etc/nologin`; the
earlier OpenSSH `Not allowed at this time` came from the builder's `root:!`
shadow entry, which locks public-key authentication too.

Generation 146 accepts exact nologin absence or one empty regular file and
sets root's shadow field to `x`, which is invalid as a password but does not
lock the account. `PasswordAuthentication no`, keyboard-interactive disabled,
and `PermitRootLogin prohibit-password` remain exact. All storage-write bounds
remain unchanged.

The sole live cycle passed power/USB, the exact 116-node UFS topology,
userdata identity, storage locking, runtime startup, first-attempt key-only
SSH, and the exact 649,960,943-byte gzip transfer. The installer then mounted
userdata and immediately returned fastboot. Its retained source proves the
failure: `set -f` disabled the later `"$mountpoint"/*` expansion, so the
literal `*` failed the exact `lost+found` check. The same setting also made the
installer's relock glob ineffective. The failure occurred before `mkdir` or
decompression; no Arch image file or directory was created. A normal ext4
mount/unmount may have updated filesystem metadata. Exact slot-A fastboot and
host cleanup passed.

The successor removes only `set -f`, executes the content glob with the sealed
AArch64 BusyBox in QEMU, and emits a bounded failure record before reboot.
