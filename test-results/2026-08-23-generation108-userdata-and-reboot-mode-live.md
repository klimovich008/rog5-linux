# Generation 108 userdata and reboot-mode result

Date: 2026-08-23

Result: **CONSUMED; TWO EARLY BOUNDARIES PROVEN.** Never retry or flash this
candidate.

Primary question: can the corrected `any-prior` target reach local Arch and
key-only SSH while failure rollback returns to fastboot?

Generation 108 passed signed transfer, PREPARE/COMMIT, kernel identity,
power/USB, deferred UFS, storage lock, userdata resolution, and read-only ext4
mount. Its last exact target record was sequence 9:

`stage=userdata-mount state=FAIL detail=userdata-rog5-directory`

The retained source userdata image contains root-owned `/rog5/images` and the
17,179,869,184-byte `arch-local-a.ext4`, but the live filesystem did not. This
is R2: the previously transferred artifact was not reverified after later
slot-A recovery cycles. No target storage write occurred.

The sealed target contains the exact restart2 helper, and Linux rebooted after
the failure. It did not remain in fastboot: the same physical path returned as
ASUS `18d1:d001`, product `ASUS_I005D`, one unauthorized ADB interface, which
is not the accepted WW33 Android descriptor. Exact config and archive audit
showed `CONFIG_NVMEM_REBOOT_MODE=m` and `CONFIG_NVMEM_SPMI_SDAM=m`, with
neither module in the target initramfs. The standard PMK8350 reboot-mode DT node
therefore had no driver to write mode 2 before reboot. This is R3/R8. The
candidate intent was durably resolved `FALLBACK_RETURNED`; the stock fallback
identity proof correctly remained failed rather than misclassifying recovery.

Successor prerequisites: physically enter exact fastboot; inspect or restage
userdata through the already verified userdata-only image; provide and prove
the exact PMK8350 SDAM plus NVMEM reboot-mode runtime before relying on
restart2; stop the host-key waiter promptly after terminal target departure.
