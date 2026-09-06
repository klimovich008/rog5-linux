# Persistent slot-B release v9 — PASS

- Generation 234 first proved the V49 UFS core with a 64 MiB p23 write,
  sync, hash, remove and sync in 402 ms with zero UFS errors.
- P24 update source remained the accepted v8 ext4 filesystem. The transaction
  retained every v8 bundle and selector rollback, added only the signed
  `persistent-native-root-v9` directory, and atomically selected manifest
  `8bc47f29…63e3`.
- Sparse image SHA-256 `cfda9d59…899e` represented all allocated source blocks
  exactly. All six `arch_root_a` chunks completed in 70.561 seconds while slot
  A remained active; no GPT, boot, firmware or other partition changed.
- First boot ID `43fb3cc9-4b22-4701-b8c1-2e7a18fe173e` and repeat boot ID
  `6e9cd42b-4419-41e8-b279-7a3076666ea1` both selected
  `rog5.bundle=persistent-native-root-v9`.
- Both boots reached the V49 high-speed marker once, zero UFS errors, systemd
  `running`, zero failed units, 117 physical nodes, and only the p23 parent plus
  partition writable.
- The stable persistent SSH fingerprint `SHA256:WSn4Lik…YkhQ` loaded from p23
  on both boots. A clean stop unmounted p23, detached state, relocked all 117
  nodes, and returned exact slot-B fastboot before the repeat boot.
- Repeat-boot power was Full/Good, 8.674 V, 30.0°C, side USB online with
  +181 mA input, and maximum thermal 35.2°C.

V9 is the accepted persistent rollback while V10 adds only automatic Tailscale
runtime preparation.
