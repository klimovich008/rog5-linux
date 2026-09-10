# Canonical selector-v2 recovery live checkpoint

Result: **PASS**.

- Restored proven old `boot_b` `2867666c…` and verified fresh V11 boot
  `ef4b7151-3f64-47ef-8085-3650cc64f904` before testing the correction.
- Canonical artifact `f2a73030…` RAM-booted through `ROG5 recovery` into fresh
  V11 boot `3d2db548-01fe-48fc-9a6c-82840241bb22`.
- A second AVB identity `665c69e4…`, with byte-identical raw recovery payload
  `d17f63fd…`, repeated the result in boot
  `87448efd-b03d-49b1-9beb-cf3e23831645`.
- After those two RAM-only passes, only `boot_b` was updated with
  `f2a73030…`. Normal slot-B boot reached V11 as
  `fcdab471-3c8d-45d8-beaf-cd06749bdedb`.
- Every pass preserved selector V1 `650e09d6…`, signed V11 manifest
  `a684bad1…`, p24 read-only, p23 as the only writable service-state partition,
  active state/Tailscale services, strict SSH and NCM.
- Persistent validation reported battery Full/Good at 30.1 C, side USB online,
  and a 38.8 C maximum thermal-zone reading.
- Slot A, GPT, selector, p24 contents and userdata were not changed. The retired
  standalone image `f049dc19…` was not reused.

The next physical question is the already-built signed Wi-Fi primary under the
bounded selector-v2 try-once path. This checkpoint grants no destructive storage
authority and does not promote the Wi-Fi primary.
