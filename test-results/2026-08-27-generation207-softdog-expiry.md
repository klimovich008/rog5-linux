# Generation 207 softdog expiry proof

Result: **PASS; consumed; never retry.**

The exact-ABI `softdog.ko` loaded after NCM, armed with a 20-second margin and
`soft_reboot_cmd=bootloader`, and emitted exact `softdog-armed-20`. Exact
slot-A fastboot returned automatically 23.6 seconds after that stage. Durable
intent resolved `TARGET_ACCEPTED`; battery remained 8711 mV. No power, UFS, or
storage path ran.

This proves a kernel hrtimer rollback layer can survive independently of the
clone shell and return through the built-in reboot-mode path. The Stage-2 clone
successor may now arm softdog for a measured bound, hold the watchdog file
descriptor without pinging during the clone, and magic-close it only after the
destination is verified and relocked.
