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
| Applied ASUS board DTB | 839,798 | `c37d9212ee56dc4ee9d14f4a66fd0e85f8532217d145c92e0fbe44323139654b` |
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
- clean payload builds completed in 2.205 and 2.189 seconds;
- Image, DTB, command line, initramfs, and `SHA256SUMS` matched byte-for-byte.

Twin output identities:

| Output | SHA-256 |
|---|---|
| Image | `54b8d9d23ace1126bf1059f1ab483c027b50865695c7b305a15311e30a217b33` |
| board.dtb | `c37d9212ee56dc4ee9d14f4a66fd0e85f8532217d145c92e0fbe44323139654b` |
| cmdline | `479d963465806f4be6e000dbb61ee52a51a0eb36514da3973908f37b0c37d0aa` |
| initramfs.cpio.gz | `22bccf4d3a138cc09c1120d787a0a67a5079c6d7c78dd579468498077c58f639` |
| SHA256SUMS | `71bf7f06675468ff2216a07b967045c9ab01333bf093f3db49153000671bb924` |

## Remaining gate

Offline correctness does not prove positive battery current. The next
coherent checkpoint is publication plus exact-head CI, followed by one new
one-use RAM-only recovery/kexec cycle. Stage 1 remains refused until fastboot
reports `battery-soc-ok: yes` and voltage has risen substantially.
