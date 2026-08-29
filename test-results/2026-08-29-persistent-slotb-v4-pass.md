# Persistent slot-B release v4 — PASS

- Root cause closed: release v2/v3 standalone initramfses copied the unrendered
  `persistent-root-init` template. Literal `@EXPECTED_*@` values caused the
  exact 25-second `kernel-release-identity` failure before watchdog disarm.
- Fix: commit `1d5d3801e6693519d1a98761cfba6a19c5f713b7` renders the five
  proven native-root values and rejects every remaining placeholder. Focused
  tests passed in 16.888 seconds, the active tier in 79.415 seconds, and exact
  head/merge/QEMU/publication CI passed.
- V4 identities: target initramfs `52a7f431...`, rendered `/init`
  `1558fb1a...`, signed manifest `9b787e24...`, p24 source image
  `5f622ebb...`, deterministic sparse image `003c7e22...`.
- Only `arch_root_a` was replaced. Slot A remained the active rescue during
  transfer; `boot_a`, `boot_b`, GPT, firmware, identity and protected
  partitions were untouched.
- First persistent boot: recovery USB at 20.188 seconds, target NCM at 29.888
  seconds, systemd `running` at target uptime 202.97 seconds, and full
  key-only-SSH acceptance at 226.46 seconds. Exact bundle v4, `switch-root
  PASS`, zero failed units, high-speed NCM, read-only p24/UFS, charging and
  safe thermals all passed.
- Watchdog proof: one successful disarm record, zero disarm-failure records,
  no watchdog PID file, and the same boot ID remained healthy through 934.63
  seconds. The orphaned inert `sleep 900` exited at 904.39 seconds without a
  reset.
- Unattended reboot repeat: recovery USB at 23.529 seconds, target NCM at
  33.236 seconds, distinct boot ID `7d038bb3-bf01-4529-987f-92cd70e63e3a`,
  systemd `running` at 197.40 seconds, full acceptance at 222.56 seconds, zero
  failed units, read-only storage, charging online and maximum thermal 35.2°C.
- Current state: slot B runs persistent native Arch through the stable local
  signed-bundle loader. Slot A remains the verified ASUS rescue/charging path.
  The root lower filesystem is persistent and read-only; service state and
  secrets still use volatile tmpfs and are the next phase.
