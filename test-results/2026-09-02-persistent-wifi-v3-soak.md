# Persistent native Wi-Fi V3 soak

Result: **PASS**.

- Candidate: `persistent-native-root-wifi-v3`.
- Kernel: `7.1.4-g1eea8970e87f`.
- Boot: `e4424825-a7b0-4d33-8a4f-fcad3f9e479b`.
- Signed manifest: `3848a4741bcf9b06e97f1fcfe5f27b70caedda885de2d0fe29341efd738deb23`.
- Selector: `47fe38b7de4789f034e96caac3391fd9dc28b6936273c0ebc5bab9b8e65ecaf0`.

The host observer completed 720 sequential samples from
`2026-09-02T01:26:09+02:00` through `2026-09-02T03:38:52+02:00`, a wall-clock
span of 2h12m43s. Private log SHA-256:
`c8ce481b197cac4f0403907dbe13ce10a89f48ea847cc9c5a53782a7b126fbd3`.

Every sample preserved:

- the exact boot, bundle, Wi-Fi address and Tailscale address;
- active Wi-Fi radio/WPA/DHCP, health, persistent-state, SSH and Tailscale units;
- inactive 600-second probe and 900-second boot rollback timers;
- NCM ping and strict SSH over both NCM and native Wi-Fi;
- p24 read-only, 117 block nodes, and only `sda`/`sda23` writable;
- battery `Good`, USB online, safe battery/thermal values and zero fatal
  UFS/ext4/panic/oops signatures.

One Wi-Fi ICMP request missed at sample 474. Strict Wi-Fi SSH succeeded in that
same sample and all 720 samples; this is optional ICMP loss, not service loss.
No NCM SSH retry was needed.

Observed ranges:

- battery voltage: 8.576–8.582 V;
- battery temperature: 29.9–30.0 C;
- USB input current: 175–500 mA while battery status remained Full;
- maximum thermal-zone sample: 38.5 C.

Final target uptime was 9,262.74 seconds with systemd `running`, both rollback
timers inactive, p24 read-only and no storage errors. Full local CI passed in
479.665 seconds; GitHub exact-head/merge/QEMU/publication run `33572144028`
passed. No phone storage was written by the observer.
