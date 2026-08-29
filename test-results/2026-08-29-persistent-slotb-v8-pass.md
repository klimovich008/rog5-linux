# Persistent slot-B release v8 — PASS

- V8 fixes the v7 executable/record pathname collision by publishing the
  root-owned 0444 identity record at
  `/run/rog5-persistent-ssh-identity.record` and refusing self-aliasing.
- Focused tests and the active tier passed; exact-head, merge, QEMU and
  publication CI run `33253985824` passed for commit
  `047a367da5c0a7d0bba3dac10706263ee4386296`.
- Deterministic identities: initramfs `e60378c1…a2b2`, signed manifest
  `538518c4…4b7c`, p24 source `c9567e80…e6c9`, sparse twins
  `8b6c03a0…5a05`. Kernel, DTB, wrapper, loader, state image and persistent
  Ed25519 identity remained unchanged.
- The one p24 transfer completed in 213.627 seconds with all four chunks.
  Slot A remained active during transfer and no other partition changed.
- First boot reached target USB in 30.062 seconds. Strict SSH using only the
  previously pinned stable fingerprint `WSn4Lik…` passed automatically in
  237.014 seconds; no keyscan or manual helper was used.
- Boot `812ff85d-c070-4502-b9b6-e6315c2fd9d8` reached systemd `running`
  with zero failed units. State and identity services were active, the exact
  112-byte identity record was present, runtime and persistent fingerprints
  matched, and marker `23fd76f7…2f35` remained exact.
- Exactly `sda` and `sda23` were writable; p24 and the other 115 physical
  nodes remained read-only. Charging was +397 mA and maximum thermal was
  38.1°C.
- Explicit state-service stop detached every state mount and loop and relocked
  all 117 physical nodes before the unattended reboot.
- Repeat boot appeared as target USB device 057 in 34.003 seconds and strict
  stable-key SSH in 197.725 seconds. Boot
  `f45e82f0-1662-4837-8219-172061195ea3` reached systemd `running`, both
  services active, zero failed units, exact marker/fingerprint/record, exact
  two-node write scope, p24 read-only, zero state ext4 recovery events,
  +275 mA charging and 37.8°C maximum thermal.
- A subsequent five-minute soak sampled direct ping, strict pinned SSH,
  boot identity, systemd, USB current and battery temperature 60 times. All
  samples passed on one boot with positive current; private log SHA-256 is
  `6a107740…ed8d`.
- Persistent state and stable key-only SSH are now accepted MVP baselines.
