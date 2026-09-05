# Persistent v9 UFS high-speed live result

Status: hardware PASS; lifecycle R7 host-parser failure; Generation 234 consumed.

- Exact device: `M5AIKN00F0353YH`, `lahaina`, side USB `1-1.2`.
- Recovery AVB SHA-256: `6826c4632a835deec8e5249a601f96c47ba973657ff61dca1067b5eecf3a1334`.
- Signed bundle manifest SHA-256: `8bc47f291c97c5d52754bd800011864dd385e6993f04d7da1be31b0fc96563e3`.
- Target boot ID: `7bcbd62d-59b2-47fc-b3ef-787771af8e38`.
- Native p24, OverlayFS, systemd running, zero failed units, high-speed NCM,
  UFS health, and first key-only SSH passed.
- The V49 `ufshcd-core.ko` emitted its high-speed marker. One p23-scoped
  64 MiB write, sync, zero-file SHA-256 verification, removal, and final sync
  completed in 402 ms with zero UFS error events. The probe file was removed
  and the softdog was disarmed.
- The host then counted `ufs_error_events=0` across both appended formatted
  records and rejected the valid base runtime record. Failure class: R7.
- The stable SSH key transition matched retained prior evidence before the
  reviewed reboot helper was used. Exact slot-A fastboot, battery gate, host
  cleanup, and rescue proof passed.
- Durable intent outcome: `FALLBACK_RETURNED`. Generation 234 must never be
  retried or flashed.

Regression: parsers now isolate one exact `format=` record before checking
unique markers; the combined live runtime-plus-probe shape is a focused test.

Next: deploy the already signed v9 bundle to the bounded p24 loader store,
verify every installed byte and selector, then prove repeated slot-B boot before
resuming Tailscale.
