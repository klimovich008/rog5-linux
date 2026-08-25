# Persistent-root local V54 / Generation 163 offline

- Generation 162 passed the local Arch server path in 325.697 seconds, including
  read-only UFS, OverlayFS, systemd, power/NCM, runtime attestation, and key-only
  SSH. Its final reboot entered stock recovery.
- Root cause: exitrd copied `/shutdown` but omitted the static restart2 helper
  referenced by that script. V54 copies and verifies the same helper in exitrd.
- The host now requires exact slot-A fastboot after accepted runtime before it
  may report success; stock recovery remains a valid rescue but not success.
- Kernel, DTB, modules, firmware, image, storage policy, and recovery raw bytes
  are unchanged.
- Target twins completed in 3.409 and 3.394 seconds and matched at SHA-256
  `220c7324f54e588234fd498a3d95047071361a68e3753f965472352e7ccb3642`.
- Signed bundle twins matched at manifest SHA-256
  `af693192164aa50849639bed0e4cae3349dab3f66ea91f5979933b4b88fd0607`.
- Generation 163 wrapper SHA-256 is
  `e05a9d1d8ec27345344a3b70241a9c07f6e8600956af7f52d7453f457a482104`.
  Candidate remains offline with no authority.
- Focused initramfs, candidate, runner, and gate checks passed in 11.91 seconds.
- Exact-head, merge-compat, candidate-publication, and QEMU CI passed for
  `c1ef6b61cda81f4f72fcf187ec624256695abf44`. Generation 163 is admitted once.

## Generation 163 live result

- The complete local Arch path repeated successfully in 338.141 seconds.
- Authenticated SSH passed after six attempts and 118.634 seconds.
- Runtime attestation again proved 116 physical block nodes, two read-only
  block-backed mounts, strict key-only SSH, zero blocked device/SCSI operations,
  zero journal recovery events, and zero UFS errors.
- Side power remained online at 5.035 V / 500 mA; battery was 8.690 V at 30.1 C.
- `systemctl reboot` entered the sealed exitrd; its included restart2 helper
  returned the exact phone to slot-A fastboot. Battery remained healthy at
  8.703 V.
- Generation 163 is consumed. The RAM-only local-root MVP is now reproducible.
