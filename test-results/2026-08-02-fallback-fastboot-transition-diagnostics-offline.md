# Fallback-to-fastboot transition diagnostics

Date: 2026-08-02

Result: **PASS offline — a failed guarded fallback reboot can now distinguish
the observed USB transition phase without weakening the authoritative
same-port, exact-product fastboot gate. The phone was not booted, flashed,
wiped, mounted, or otherwise contacted while implementing and testing this
change.**

The connected generation-2 preflight first proved the exact deployment SSH
key chain and a fresh signed Alpine fallback health record. Its evidence
record has SHA-256
`ede13f8b635d0f6eacbb5244658d2daf850e2eda0e866794b4a53c951d161ff9`.
The separately guarded `RESTART2("bootloader")` request then detached the
fallback USB gadget, but neither exact fastboot nor any other phone USB mode
was visible during the bounded wait and an additional read-only observation
window. Generation 2 remained unbooted and its connected preflight did not
run.

The former terminal error only reported that fastboot did not appear. The
host controller now samples the VID:PID at the already pinned physical USB
location and classifies a fatal timeout as one of:

- no fallback disconnect observed;
- disconnect with no anchored-port re-enumeration observed;
- a non-fastboot USB mode observed at the anchored port; or
- exact fastboot USB observed while the fixed fastboot client could not
  complete discovery.

This observation is diagnostic only and can never admit a device. Success
still requires one canonical fastboot inventory, exact state, exact ASUS
`0b05:4daf` identity at the pinned physical location, a unique serial there,
and exact product `lahaina`, with physical-location revalidation before and
after the product query.

An initial independent Claude review found that two sysfs reads could race a
hot-unplug and abort an otherwise healthy transition. The probe was corrected
to treat missing, replaced, torn, or malformed best-effort observations as
unknown. The strict success gate remains unchanged.

Verification:

```text
Ran 50 tests
OK
PASS repository Linux ci tier
```

The next hardware step remains the exact generation-2 connected diagnostic
preflight after the phone is manually returned to fastboot. It must not be
replaced by a temporary boot, and generation 2 remains unconsumed.
