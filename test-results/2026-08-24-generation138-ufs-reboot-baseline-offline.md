# Generation 138 UFS and fastboot-return baseline

Result: **OFFLINE PASS; ADMITTED ONCE.** Never flash or retry after entry.

Generation 137 proved that the old g359 target now returns `ufs-count-0` and
also reconfirmed the known recovery-loop defect: without the PMK8350 SDAM and
NVMEM reboot-mode drivers, `restart2("bootloader")` returns to slot-A recovery.

Generation 109 is the stronger live control. Under the same current wrapper,
its ae717 Image `1a1958fe...f9ce22`, DTB `4f6518b3...6c76b8`, and four exact
modules passed UFS and userdata before its built-in reboot-mode path returned
exact fastboot. Generation 138 reuses those bytes with only the minimal NCM,
UFS count, and bounded fallback initramfs.

Target twins are `45989fd1...78673c`; manifest is
`836ef28f...0bdf4f`; Generation-138 recovery is
`c9716321...d1839ba8`. The raw stable recovery remains unchanged. No SSH,
filesystem mount, installer invocation, or storage-write path is reachable.
