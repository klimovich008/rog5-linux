# Generation 79 Type-C role discriminator

Date: 2026-08-22

Result: **consumed; exact failure identified; fallback passed.** Generation 79
must never be retried or flashed.

- Recovery transferred the complete signed bundle and accepted COMMIT once.
- The target emitted exact stage sequence 3 at `ufs-ready` with
  `detail=power-usb-typec-data-role`.
- The reviewed two-second rollback ran before UFS, local-root, or SSH work.
- Exact stock slot-A fallback, host cleanup, and `FALLBACK_RETURNED` passed.
- No phone-storage write occurred.

Root cause: R3 exact target-interface dialect mismatch. Retained V26 evidence
shows mainline sysfs values `host [device]` and `source [sink]`; brackets mark
the currently selected role. The persistent loader required bare `device` and
`sink`, so it rejected a valid side-port device role before reaching the power
role check.

The regression accepts only `device` or `host [device]` for the data role and
only `sink` or `source [sink]` for the power role. Inactive, unbracketed,
trailing, and malformed variants remain rejected.

Private evidence remains outside Git at:
`/home/deck/.local/state/rog5-generation79-live-20260822-r1`.
