# Generation 206 APSS watchdog MMIO classification

Result: **FAIL-CLOSED; consumed; never retry.**

The static helper opened `/dev/mem` and mmaped the watchdog page read-only,
then the first volatile read at `0x17c10008` raised SIGBUS. The target emitted
exact `power-usb/FAIL/watchdog-mmio-bus`; exact slot-A fastboot and durable
`FALLBACK_RETURNED` passed. No power, UFS, or storage path ran.

This disproves direct APSS register observation as a usable development path
on the current ASUS/Haven topology. The stable recovery separately verifies
and disables `qcom,hh-watchdog` before kexec; that virtual watchdog is not the
inaccessible `0x17c10000` APSS register page.

No further direct-MMIO successor is justified. The next offline architecture
check is the standard kernel `softdog` hrtimer with `soft_reboot_cmd=bootloader`
for a clone-bounded fallback that can outlive a userspace UFS D-state.
