# Persistent slot-B native Arch installation — PASS

- Persistent artifact: fresh generation-2 AVB `2867666cdb07a3956c94359a0b2cb54081a6dff78a129d18eb1102a6fbb0e3a3`, binding twice-proven raw boot `f235719b2041615ef7d8d044538ad6f5da0589e18bbbdcce2385deb4e91a641b`.
- Recovery platform: exact live-proven wrapper kernel `838425a8...` plus canonical recovery local-loader ramdisk `31c4c075...`.
- Prewrite record: private `EXECUTION-RECORD.json` SHA-256 `645292cd9dc2aaa5569bafb170f19bcae26c0c7953d9a62d797030f627e1ea58`; old boot_b backup `0a67358d...` verified in two retained paths.
- Transaction: only `boot_b` was flashed; active slot changed A → B. Transfer completed in 2.564 seconds. Slot A and B both remained bootable, and B retry count was 3 before reboot.
- First persistent boot: recovery USB at 27.237 seconds, persistent-root USB at 36.933 seconds; boot ID `3bbc9bfb-d9b5-480d-b6cf-c3258a050626`; systemd running, required units active, zero failed units, key-only SSH, high-speed NCM, read-only UFS/root, battery full/charging, maximum sampled thermal zone 38.8°C.
- Unattended reboot: no fastboot or slot action; recovery USB at 35.445 seconds, persistent-root USB at 45.131 seconds; distinct boot ID `84b9b0f0-dfaa-471d-ab4f-40b9028fa7bc`; the same runtime/storage/SSH/charging predicates passed with maximum sampled thermal zone 39.5°C.
- Reliability note: the second boot had one temporary NCM/SSH interruption while systemd initialized. USB remained configured and NCM recovered without reset; final acceptance passed.
- Current state: phone remains running native Arch from persistent slot B. Slot A WW33 charging/recovery remains untouched. Root lower filesystem and physical UFS remain read-only; package/service changes are still volatile in tmpfs OverlayFS.
- Next phase: add bounded persistent service state and secrets, then permanent remote networking and rescue validation. GPU, desktop, display, audio, and sensors remain deferred.
