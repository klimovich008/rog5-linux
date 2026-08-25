# Generation 138 UFS and fastboot-return baseline

Result: **CONSUMED; UFS COUNT ZERO; EXACT FASTBOOT RETURNED.** Never retry or
flash.

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

The sole RAM-only cycle passed exact preflight, signed transfer, PREPARE/COMMIT,
target NCM, release, command line, and all four UFS module-load checks. It then
emitted `stage=ufs-ready state=FAIL detail=ufs-count-0` after the bounded
20-second wait. Built-in PMK8350 reboot mode returned the exact serial at
slot-A fastboot, and fallback plus host cleanup passed. No storage node or
write existed.

Comparison with the exact sealed Generation-109 init proved the missing
dependency: it calls `/sbin/rog5-load-persistent-power-usb` before UFS, while
Generation 138 packaged the same loader, 15 modules, and firmware but never
executed it. Generation 139 restores only that proven ordering.
