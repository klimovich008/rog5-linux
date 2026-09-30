# Fallback rehearsal: safe-r8 (2026-09-30 22:29-22:37)

Starting point: default production-7.2.7-r207 (kernel r110 + DTB r9), committed healthy; fallback production-7.2.7-safe-r8 (kernel r69 Image, DTB usbbtm-r2 + memx, init with v2 restore, audio route -12 dB without the protection DSP).

1. 22:29 On r207: `/run/rog5-production-trial/trial-state reject <r207 trial_id> production-7.2.7-r207` -> state healthy -> failed (the helper printed `rollback`), synced, `systemctl reboot`.
2. 22:31 The loader selected the fallback: cmdline `rog5.bundle=production-7.2.7-safe-r8`, uname 7.2.7-rog5-production. `systemctl is-system-running` = running, no failed units, Wi-Fi 192.168.1.83, SSH OK. `/proc/device-tree/reserved-memory/memory@34a000000/reg` = `00 00 00 03 4a 00 00 00 00 00 00 00 04 00 00 00`, `no-map` present. Sound card up; `SPK Digital PCM Volume` = 361 (-12 dB) as intended without protection.
   - Finding: on the r69 kernel with the MSI monitor on the side port, qcom-battmgr-usb/online = 0 and the battery discharged (-165 mA); the installer's "USB power offline" gate refused to install until the phone was put on a wall charger (then online=1, Charging). Expected safety behaviour; note for recovery: have a plain charger at hand.
3. 22:35 From the fallback: install-default-kernel.py preflight PASS, --stage PASS for production-7.2.7-r208 (= r207 content with a fresh trial descriptor), p24 relocked ro, reboot.
4. 22:37 Primary r208 booted and `PASS production-7.2.7-r208 committed healthy`; charge policy active; bottom-port stick attached at boot (0146).

Result: PASS — the try-once fallback path works end to end, including reinstalling a default from the fallback.
