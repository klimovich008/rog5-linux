# Persistent slot-B loader v1 offline checkpoint

- Architecture: ASUS 5.4 wrapper with a built-in local loader; exact `arch_root_a` is mounted `ro,noload`, one root-owned selector chooses a project-signed bundle, the bundle is copied to tmpfs, verified by the existing hardened Ed25519 verifier, and kexeced after exact Haven-watchdog deactivation.
- Recovery: every loader failure and a 180-second loader watchdog request the bootloader through the fixed restart2 helper; slot A remains untouched.
- Production target: unchanged proven Image/DTB plus standalone initramfs twins `6de3147854e3bab4b64720d1aa881b746e7bcdd3b6d5dca7185ced359d62ff94`; normal shutdown reboots the active slot after clean volatile-root teardown.
- Signed release bundle: `persistent-native-root-release-v1`, manifest `2b259a6e5912549dc2210d12c5f3b4da5422817720addc85e660bf9d3edf75ec`; hardened verifier PASS.
- Loader initramfs twins: `f3c44020fc6b806b4913d6e1af8b6f8089c659f1031d1575662b8cf7efdf4bdb`, 7,603,257 bytes.
- Wrapper clean twins: Image `d65a3f79921145a9dffc286a1213f907c794e27c06b10e55df38060f6b40c857`; raw boot `193bd269c7ddb4bc10964424b0aeb59f44a0a7540b21803950b98124e8241361`; AVB boot `0a118dcd0200af7d4defa5f9bd32d09198b877302cf2c1e8632b4eb1342c2038`.
- Release p24 source: ext4 SHA-256 `70d336f831ad9408643bb01c4d5f462dde0acaeb604e8c2122ca0edbc1715ed0`, clean fsck; allocated-RAW sparse twins `c95a0e3ad7d611e5db05e559fbffa5be6e28048fd264012eb12895d84a06d30c`.
- boot_b backups remain hash-verified at `0a67358df714570af18d4dd209785ab337d5e6a1ec9dd6532babc30bf83a95f1`; no phone partition was written at this checkpoint.
- Next: full CI, exact-head CI, controlled p24 release-bundle staging, then repeated RAM-only loader tests before any boot_b flash.
