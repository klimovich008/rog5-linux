# Display60 V5 SSH evidence boundary

Result: **display evidence unavailable; fallback PASS**.

- REFGEN was changed from module to built-in; incremental build took 156.83 s.
- Image SHA-256: `7b4ff169230ed66c4be1395cc0212cbbb9534f686108bd91da45093071838ef6`.
- `Module.symvers` was unchanged.
- Target `2e30cda7-5016-455f-a23a-8b42dc6d067c` reached switch-root PASS.
- NCM remained alive through the rollback window; there was no reset/panic.
- SSH exposed only a per-boot key with fingerprint
  `SHA256:d2SL4BPTdIl9JdPMKaBr9OaqEAhIo0XWr6nbTn7f32U`.
- The reviewed persistent key never appeared; no TOFU exception was made.
- The host runner ended after 870 seconds, 30 seconds before the sealed
  900-second rollback timer (R4 timeout-lattice defect).
- Automatic rollback then restored V11 boot
  `059fa53b-8e16-4b0f-abf9-f78d391f6a91`, p24 read-only, battery Good at
  8.564 V and 30.0 C.
- V5 is consumed and must never be retried; phone storage was unchanged.

No further display candidate should rely on SSH for first evidence. The next
architecture checkpoint is a signed post-switch NCM reporter carrying bounded
REFGEN/DSI/DRM/fb/backlight/status fields, followed by strict SSH only after the
persistent host key appears.
