# Generation 204 MMIO pipeline classification

Result: **FAIL-CLOSED; consumed; never retry.**

The module-free `/dev/mem` path ran, but the final tuple failed validation and
the target emitted exact `power-usb/FAIL/watchdog-mmio-detail`. The original
`dd | od | tr` pipeline could return the final applet's success while `dd`
failed, leaving empty fields. Exact fastboot and durable `FALLBACK_RETURNED`
passed; no phone-storage write path existed.

The successor uses one explicit four-byte file per register, checks `dd`, file
size, `od` and exact eight-digit hex independently, and publishes each accepted
EN/STS/BARK/BITE value before composing the final tuple.
