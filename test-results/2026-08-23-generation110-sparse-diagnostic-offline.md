# Generation 110 sparse-transfer discriminator

Date: 2026-08-23

Result: **OFFLINE PASS; ADMITTED ONCE.** No phone boot or storage write has
occurred for Generation 110.

Generation 109 repeated `userdata-rog5-directory` immediately after the exact
four-chunk fastboot restage, while successfully returning to fastboot through
the new PMK8350 reboot-mode path. The host source and `simg2img` round-trip both
contain `/rog5/images`. Parsing all 11,478 Android sparse chunks proves every
critical ext4 block is RAW, including the high inode metadata around 60.1 GB.

The working hypothesis is a sparse-transfer high-offset or resparse-piece
handling defect. Opus ranked a 32-bit byte-offset wrap first and piece-relative
offset reset second. Independent arithmetic corrected its alias calculation:
blocks 14680096, 14688288, and 14688289 alias modulo 4 GiB to blocks 32, 8224,
and 8225—not 8230/8231.

Generation 110 changes only the target initramfs. On the repeated directory
failure it reads and publishes SHA-256 for blocks 1, 32, 1086, 8224, 8225,
9278, 14680096, 14688288, and 14688289. This distinguishes correct transfer,
dropped high writes, 4-GiB aliasing, and low-region corruption in one read-only
cycle. The host waiter now stops at the terminal target stage, and exact slot-A
fastboot is accepted as a fallback outcome.

Host reference hashes for the same 4 KiB blocks are:

- 1: `d28d5c1faba5a4e80d4af0fbd262714173bc3f41b025b4b5e74d0d30fa7ca304`
- 32: `01b5d9118d159c52a616b4f1ccef4e708c4ab90b09d5d4066abb0d8612cc6590`
- 1086: `809b239b45f8d2d9af2fe4df953a449aa992f78f862cbcbc07e0cf50d6709e92`
- 8224/8225: `ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7`
- 9278: `75977fe054b55827575ba3dd8bc5fc2418be4f082e344151949a8890719d5665`
- 14680096: `682e314bdaac72c350aa6c0d60e0f39d7e0c46f771901fa307ca9e011bd0e3f8`
- 14688288: `12854b3006a02482cb015731fbf316438cf59d8d053bc6d0a58aa36d19a2e883`
- 14688289: `a76a4f89f6100471949004ebc9e5c964cfefd62719037c0f50a71456006a70ab`

Identities:

- target initramfs: `9b34cb5b49b6028fba7cd7becbb76ada14e469894916a19778f3c65b043e8ba0`
- signed manifest: `99ff5e35bf5533df7e99b5bad65aa893f68c69ced22cedd37e74d879041d15cd`
- Generation 110 wrapper: `ce3be4ff692428d56dd92d9daf763803a32e0d129f1b01173229c1ebbe6f3578`

Live result: **CONSUMED; ABL SPARSE STAGING DISPROVEN.** Device block 1,
inode-table block 1086, and root-directory block 9278 differed from the source.
Blocks 14680096, 14688288, and 14688289 were all 4 KiB zero blocks. Alias
blocks 32, 8224, and 8225 retained their source values, ruling out wraparound.
Exact fastboot fallback passed and no target write occurred.
