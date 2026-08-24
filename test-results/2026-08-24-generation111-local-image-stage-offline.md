# Generation 111 controlled local-image staging

Date: 2026-08-24

Primary question: can the clean-twin bounded UFS writer stage the exact 16 GiB
Arch image at `/rog5/images/arch-local-a.ext4`, relock storage, and return to
fastboot without entering stock recovery?

The preceding Generation 110 failure is R2: ASUS ABL returned successful sparse
transfer status, but read-only target hashes proved the installed userdata bytes
did not match the source. The successor therefore uses the already-reviewed
mainline writer instead of redesigning the kernel or retrying sparse fastboot.

Offline checkpoint:

- kernel source: `359318de534f196c1281de7195fbf5868c6f7333`;
- clean-twin Image: `a7e0cd84238d9e0c399a6c93d3c7a5996571dc3536b10c7323cbe1455dbad01e`;
- clean-twin config: `6329b42fac5876d3f42557802bd530ba2c077aa73c4543f0bbc37ea65902eeb4`;
- target initramfs: `077d7140439f7e861efe9f3a9dc9fcb78a02544d2bc241481ee7184282c79baf`;
- signed manifest: `f296276d49af5db4b498d2f14afc935065adf1ec4ca4e043e2b14c7a3b707bda`;
- Generation 111 wrapper: `f58153ef41186b5f2a5c8b2449d432dc02b6f92a9fb4c9397298d2d026d4e7cb`;
- focused tests: 5 seconds;
- exact sealed BusyBox `stat`, `sha256sum`, `cut`, `cat`, and shell pipeline: passed.

The wrapper remains RAM-only and the target installer is the only storage-write
surface. It accepts one exact compressed source, one exact userdata partition,
one empty ext4 filesystem, and one final pathname before relocking every block
device and requesting bootloader restart.
