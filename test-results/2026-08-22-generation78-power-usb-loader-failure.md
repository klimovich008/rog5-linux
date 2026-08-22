# Generation 78 power/USB loader failure

Date: 2026-08-22

Primary question: does removing only rejected BTF from `pdr_interface.ko`
advance the combined side-power plus local-root target beyond Generation 77's
immediate rollback?

Result: **yes, then HOLD for a distinct diagnostic successor.** Generation 78
is consumed and must never be retried or flashed.

- Exact-head CI run `32540300133` passed for commit `3d22fdd`.
- Connected non-consuming preflight passed.
- The durable one-use claim entered before COMMIT.
- Recovery served the complete 62,105,331-byte signed bundle once.
- The target emitted exact stage sequence 3:
  `stage=ufs-ready`, `state=FAIL`, `detail=power-usb`.
- Generation 77 emitted no target stage, so the no-BTF correction definitively
  advanced execution beyond the prior module-loader boundary.
- The target did not reach UFS, local root, or SSH.
- The reviewed initramfs path waited two seconds after the loader failure and
  forced rollback.
- Exact stock slot-A fallback, host cleanup, and `FALLBACK_RETURNED` intent
  resolution passed.
- No phone-storage write occurred.

Failure class: **R3**. The exact target loader capability/behavior failed, but
the legacy generic detail cannot identify whether the first failing boundary
was a module insertion, telemetry publication, safety check, Type-C role, NCM
state, or storage-containment check. This is not evidence of a target kernel
crash. The retained pre-COMMIT pstore record has no matching target lineage;
absence of lineage-safe pstore remains inconclusive.

Regression correction: every loader failure now emits one bounded stable code
such as `power-usb-module-pdr-interface-load`, while empty, multiline,
uppercase, malformed, trailing-hyphen, and oversized outputs collapse to
`power-usb-invalid-failure-record`. The same stage channel and two-second
rollback remain unchanged.

Private evidence remains outside Git at:
`/home/deck/.local/state/rog5-generation78-live-20260822-r1`.
