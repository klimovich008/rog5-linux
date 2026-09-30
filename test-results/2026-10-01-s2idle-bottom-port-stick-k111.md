# s2idle with a USB stick on the bottom port (stage B) on main-k111-d10-261001a, 2026-10-01 01:25-01:30

Setup: Kingston DataTraveler 70 (ext4 ROG5-USB, rog5-usb-storage mount) in the bottom port (RT1715 TCPM source, 0144/0146); the user unplugged the side-port hub, screen off, then woke with the power key. On-phone logger (/usr/local/sbin/rog5-sleep-test-once, log /var/tmp/rog5-sleep-test.log) captured state before and after.
- 01:27:12 rog5-sleep-policy: "suspend: on battery, screen off for 62 s"; 01:27:17 PM: suspend entry (s2idle); 01:29:30 suspend exit (2 min 13 s). suspend_stats success 0 -> 1, fail 0.
- After resume: typec port1 partner attached, 5V enabled, DataTraveler 70 enumerated (kernel: "usb 1-1: reset high-speed USB device" on resume, normal), ROG5-USB still mounted; 16 MiB random file written, synced, caches dropped, re-read: sha256 identical (OK). RT1715 alert IRQ count unchanged (2) — no spurious alerts.
- Side hub replug after resume: first enumeration "device descriptor read/64, error -71", rog5-usb-reconnect re-initialised a600000.usb, hub + card reader enumerated 15 s later.
- qcom_stats cxsd count still 0 (no CX collapse; known standby topic, see 2026-09-30-standby-blockers-r9.md).
Result: PASS (stage-B bottom port and the stick survive s2idle; data intact).
