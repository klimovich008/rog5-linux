# Generation 232 native-root acceptance

- Result: consumed successfully; `TARGET_ACCEPTED`; exact slot-A fastboot returned in 255.879 seconds.
- Passed: repaired p24 read-only root verification, tmpfs OverlayFS, switch-root, stable USB NCM, first-attempt Ed25519 SSH in 0.166 seconds, UFS health snapshot, PID 1 systemd, system state `running`, both required units active, and zero failed units.
- Fix proven: the runtime connection waited boundedly until the ready marker, PID 1, system state, and both required units were simultaneously ready.
- Artifact policy: RAM-only recovery/kernel execution; no boot, firmware, GPT, userdata, or protected-partition write; Generation 232 must never be retried or flashed.
- Next: repeat the same baseline under a fresh one-use identity before reviewing persistent slot-B installation.
