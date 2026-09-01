# Display60 V2 post-switch result

Result: **FAIL before target SSH; fallback PASS**.

- Source exitrd entered kexec.
- Target boot: `21a74a66-814a-4d59-8793-9a185eb68e4b`.
- Target release: `7.1.4-rog5-display60-v1`.
- UFS, storage lock, userdata, final storage, and `switch-root PASS` succeeded.
- No target FAIL record was emitted.
- Target did not reach key-only SSH before automatic reboot.
- Fresh V11 fallback `1306139f-a31f-4518-8f63-8609a15bbd1e` was running with
  p24 read-only and safe battery state.
- Pstore was empty and remains inconclusive; PMIC PON snapshot was unavailable.
- V2 claim is consumed and must never be retried.
- No phone storage, GPT, slot, or persistent-selector change occurred.

The exact Wi-Fi radio unit has `OnFailure=rog5-wifi-failure.service`; that helper
records a reason only in volatile `/run`/optional ACM and immediately reboots.
Status/backlight unit failure has no reboot path. Wi-Fi failure is therefore the
strongest userspace hypothesis, while a display panic/reset remains possible.

The next discriminating artifact keeps the proven NCM, key-only SSH, rollback,
storage and power path but deliberately omits Wi-Fi radio/WPA/DHCP units. It is
a diagnostic mode, not a claim that Wi-Fi and display work together.
