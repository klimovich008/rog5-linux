# Persistent slot-B release v6 — PASS

- V6 corrected the four exact BusyBox/POSIX predicates exposed by v5 and
  added a read-only live preflight. Focused tests passed in 4.813 seconds, the
  active tier in 71.999 seconds, and exact-head/merge/QEMU/publication CI run
  `33247499258` passed at commit
  `3470c06ac56f4b9ece499dc1eb84cd5803a1a25c`.
- Deterministic identities: initramfs `2c2eace8…6f35`, signed manifest
  `385b2804…e3f`, source p24 `8d5058c5…6544`, sparse twins
  `234306ca…c107`. Kernel, DTB, wrapper, slot-B loader and trust key remained
  byte-identical to v4/v5.
- The one p24 transfer completed in 212.755 seconds with all four chunks.
  Slot A remained active during transfer; no other partition changed.
- First v6 boot reached target USB in 29.812 seconds and SSH key publication
  in 137.099 seconds. P2 and the persistent-state service passed with zero
  failed units. Exactly `sda` and `sda23` were writable; p24 and the other 115
  physical nodes remained read-only.
- `/persist` mounted exact loop0 from
  `rog5/state/server-state-v1.ext4`; its 160-byte manifest retained SHA-256
  `2c93224d…9ea6`. Charging was net positive and thermals remained safe.
- Marker `rog5-state-live-marker-v1` was written by boot
  `46041357-db86-4b89-9987-993cccb47874` at SHA-256
  `23fd76f7…2f35`.
- Explicit service stop removed the runtime record, p23 and `/persist` mounts,
  detached all loops and returned all 117 physical nodes read-only before the
  reboot request.
- A later forced recovery reboot replayed both ext4 journals successfully and
  retained the marker. The final unattended clean cycle used target USB device
  045, reached target USB in 33.403 seconds and SSH in 141.498 seconds, then
  reached systemd `running` with zero failed units.
- Final boot `9ea3be90-d339-40ac-9419-4a97c959c4d8` retained the original
  marker byte-for-byte, exact two-node write scope, p24 read-only, zero p23 or
  loop0 journal-recovery events, +403 mA USB current and 36.8°C maximum
  thermal.
- Host-only R6 follow-up: the standalone server needs automatic `/30` profile
  activation on each new NCM instance. The live profile now autoconnects and
  passed first-route/first-ping; the attended recovery lifecycle's deferred
  profile requirement must remain a separate explicit mode.
