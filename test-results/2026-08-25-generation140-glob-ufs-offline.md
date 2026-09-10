# Generation 140 glob-enabled UFS topology baseline

Result: **CONSUMED; EXACT UFS TOPOLOGY PASSED; FASTBOOT PASSED.** Never retry
or flash.

Generation 139 proved the complete power/USB loader passes, including charging,
temperature, PMIC GLINK, remoteproc, UCSI sink/device role, and NCM. UFS still
reported zero because the minimal init used `set -f`, disabling pathname
expansion. Every fixed `/sys/class/block/*` and earlier platform-device scan
therefore iterated a literal asterisk rather than the live sysfs inventory.

Generation 140 removes only glob suppression and replaces the incomplete
physical-disk counter with Generation 109's exact disk-plus-partition topology
algorithm. The unchanged ae717 Image, DTB, 15 power modules, four UFS modules,
firmware, NCM reporter, and built-in fastboot return remain fixed. No SSH,
mount, installer invocation, or storage-write path exists.

Target twins are `6f8b4620...366306b`; manifest is
`5b19fd9c...673a832f`; Generation-140 recovery is
`9b29868c...2899b78c`. Raw stable recovery remains unchanged.

The sole RAM-only cycle passed the full power/USB loader and emitted exact
terminal `stage=ufs-ready state=FAIL detail=count-116`. The terminal FAIL token
is the intentional host-listener stop; `count-116` is the baseline success.
Built-in reboot mode returned exact slot-A fastboot and cleanup passed. No
mount or storage write existed.
