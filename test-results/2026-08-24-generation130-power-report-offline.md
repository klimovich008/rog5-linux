# Generation 130 early power/USB report

Result: **CONSUMED; HOST CALLED THE WRONG WAIT HELPER.** Never retry or flash.

Primary question: which exact power/USB loader boundary follows the now-proven
target NCM path, or does the loader pass and permit UFS/SSH/image staging?

The stager now reuses the existing seven-field stage protocol after exact
NCM/carrier and before the loader. A terminal `power-usb-*` result is sanitized,
published once per second, and held for ten seconds before slot-A fallback.
No new shell, SSH, storage, or kernel surface is added. Target twins are
`3814d298...401af0`; manifest is `f333316a...3222915`; Generation-130 recovery
is `a1cc3db2...ec3923`. Focused tests and active tier pass.

Live result: exact target NCM enumerated from `15:50:20.954107` through
`15:50:31.460514`, 10.506407 seconds. This proves the reporter's terminal dwell
executed. The runner created only an empty `target-host-key.log` and called
`wait_for_stage_host_key()`, which has no port-8079 listener; the existing
`wait_for_target_host_key()` implementation was unused. The exact stage detail
was therefore sent to no listener. Slot-A fallback and cleanup passed; no SSH,
installer, or storage write occurred. Failure class: R7.
