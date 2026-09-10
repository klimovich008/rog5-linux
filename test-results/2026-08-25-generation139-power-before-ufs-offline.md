# Generation 139 power/USB-before-UFS baseline

Result: **CONSUMED; POWER/USB PASSED; FALSE UFS ZERO; FASTBOOT PASSED.** Never
retry or flash.

Generation 138 used the Generation-109-live-proven ae717 Image, DTB, UFS
modules, and built-in PMK8350 reboot mode. It returned exact fastboot but still
reported `ufs-count-0`. Exact archive comparison proved the remaining
composition difference: Generation 109 executes the sealed 15-module PMIC
GLINK, remoteproc, battery-manager, Type-C, and UCSI loader before UFS;
Generation 138 packaged that loader, firmware, and modules but never called it.

Generation 139 adds only that proven call before the unchanged four-module UFS
chain. The loader validates safe battery voltage and temperature, online USB
sink power, UFP/device role, NCM carrier/address/route, and absence of storage
before UFS. No SSH, mount, installer invocation, or storage-write path exists.

Target twins are `88196bfb...61a0a5f`; manifest is
`21d28652...84af10fc`; Generation-139 recovery is
`a33451c6...816cd8af`. Raw stable recovery remains unchanged.

The sole RAM-only cycle passed the exact power/USB loader and reached the UFS
wait, then reported `ufs-count-0` before returning exact fastboot. The failure
was a shell-runtime defect: `set -f` disabled glob expansion, so the fixed
sysfs loops could never observe any device. No storage node or write existed.
