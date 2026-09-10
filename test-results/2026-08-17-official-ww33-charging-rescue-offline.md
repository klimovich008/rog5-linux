# Official WW33 charging-rescue checkpoint — 2026-08-17

## Outcome

The prior direct charger probe's missing battery service is now explained by
a concrete composition defect: replacement PID 1 launched the charger UI
without mounting modem firmware or starting the ADSP charger service. A new
RAM-only payload restores the smallest exact stock sequence while retaining
bounded rollback and diagnostics. No phone boot, signature, candidate issue,
or phone-storage write occurred at this checkpoint.

## Exact inputs

| Input | Size | SHA-256 |
|---|---:|---|
| Official WW33 Image | 46,305,792 | `54b8d9d23ace1126bf1059f1ab483c027b50865695c7b305a15311e30a217b33` |
| Official WW33 vendor image | 1,201,238,016 | `c6dd3e4ab60f54a88cccf68f445d694449674ed4c91f777ed57fbdc0cce6befd` |
| Memory-fixed ASUS board DTB | 839,846 | `4a62a4b83ff8948667732e55d8f2e57e575e05e9d3a3aa64b3da1dc58fd78065` |
| Alpine diagnostic ramdisk | 5,830,004 | `64db1bf572e2fb8ac77a8a79ea283e81a57ff8a9a319f0cba68da18f6a8c9841` |

The five embedded modules have exact
`5.4.210-qgki-perf-gc89cd02a7dfe` vermagic. The official kernel has UFS,
DWC3/NCM/ACM, VFAT, service locator/notifier, PMIC-GLINK, and the battery
charger built in; the retired build-21 kernel and mismatched GKI module set are
not used.

## Read-only firmware contract

The target requires exactly one `modem_b` partition at start sector `1704888`
with `450560` 512-byte sectors, a block node, VFAT type, and UUID
`00BC-614E`. That partition is already backed up at SHA-256
`455b8823e4086bcb72c8dd3046d3fdcc1a9e25685667b7729ab3ea955c6b38b9`.
It is mounted only at `/vendor/firmware_mnt` with
`ro,nodev,nosuid,noexec`; the exact source/type/read-only state is rechecked
before `/firmware` is linked and before ADSP activation. No other phone
filesystem is discovered or mounted.

## Verification

The original contract passed in 0.067 seconds before the fail-first change.
The new contract then failed in 0.007 seconds because the resolver was absent.
After implementation:

- resolver hostile fixtures passed in 0.069 seconds;
- the corrected rescue contract passed in 0.079 seconds;
- the focused resolver, rescue, runner, and current-status set passed in
  6.494 seconds;
- corrected clean payload builds completed in 2.520 and 2.496 seconds;
- Image, DTB, command line, initramfs, and `SHA256SUMS` matched byte-for-byte.

Twin output identities:

| Output | SHA-256 |
|---|---|
| Image | `54b8d9d23ace1126bf1059f1ab483c027b50865695c7b305a15311e30a217b33` |
| board.dtb | `4a62a4b83ff8948667732e55d8f2e57e575e05e9d3a3aa64b3da1dc58fd78065` |
| cmdline | `479d963465806f4be6e000dbb61ee52a51a0eb36514da3973908f37b0c37d0aa` |
| initramfs.cpio.gz | `22bccf4d3a138cc09c1120d787a0a67a5079c6d7c78dd579468498077c58f639` |
| SHA256SUMS | `037a1fac2dde71b0a8a887612fcbd6bad5df59e998ab35f802137b9095b96630` |

## Remaining gate

Offline correctness does not prove positive battery current. The next
coherent checkpoint is publication plus exact-head CI, followed by one new
one-use RAM-only recovery/kexec cycle. Stage 1 remains refused until fastboot
reports `battery-soc-ok: yes` and voltage has risen substantially.

The first live-path publication audit then failed before any phone action: it
proved that the builder had selected the bootloader-placeholder DTB with a
zero `/memory` range and that the stable-recovery exact command line omitted
the required `rog5.charging_rescue=1` token. The successor now uses the
already-reviewed explicit memory geometry and binds the current rescue token
and initramfs identity in the native verifier.

The corrected signed runtime bundle is
`official-ww33-charging-rescue-v2-live-v1`; its canonical manifest is
`0d3cca84453b17409fefbbda650f5a46836bb0d3b9e105b0581b37f9d7e2011f`.
The native host-test verifier accepted the exact signature, artifact set,
memory geometry, and command-line hash
`7166b5fc6269864bffaea79e6862aa39b3eef31c0e17ab595b31e11c8260c71e`.
The generic exact-record consumer now owns the matching one-use claim; its
14-test concurrency and filesystem-safety suite passed in 0.429 seconds, the
8-test packager suite passed in 6.755 seconds, and the 27-test admission suite
passed in 6.609 seconds. The claim has been registered but not entered.

The stable-recovery wrapper also passed its mandatory clean-twin build in
2,105.582 seconds. Both builds produced kernel Image
`b108df4651ba5fbf282114617a1f4cf483d497fa2f7d50726af95a4e06022302`,
raw boot image
`509b94d377b304de37a92a92c598644c7c0dca8f58ec1401f984138361629c93`,
and 100,663,296-byte AVB boot image
`004a5a6d4752e939fdf03d89778ab5362fbfaed299f8f40aed98bd9fdd468d54`.
The embedded AVB footer and exact 58,118,144-byte boot payload verified.

The final repository `ci` tier passed in 427.527 seconds. Its first run exposed
the stale exact consumer identity in the retention executor chain; focused
tests failed first, the existing hash/size bindings were updated transitively,
and the complete rerun passed. No claim was entered and no phone boot occurred
during this checkpoint.
