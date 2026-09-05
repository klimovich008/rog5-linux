# ASUS charging recovery

Status: completed on 2026-08-19.

This document is a guard against repeating the completed repair. Detailed
build, flash, and charging evidence is retained privately under:

`/home/deck/.local/state/rog5-super-explicit-ab-20260819-r1/`

## Root cause

The reconstructed `super` metadata incorrectly used slot-suffixed physical
block-device semantics on a phone with one physical, unsuffixed `super`
partition. On slot B, liblp requested nonexistent `super_b` during
`FirstStageMount::InitDmLinearBackingDevices`. `/vendor` did not mount, ASUS
charger services did not start, and charger mode returned to fastboot.

## Accepted repair

One corrected factory-style sparse image restored:

- physical block device `super` without the slot-suffixed flag;
- explicit `system_a/system_b`, `system_ext_a/system_ext_b`,
  `product_a/product_b`, `vendor_a/vendor_b`, and `odm_a/odm_b`;
- WW33 payloads in A and factory-empty B logical partitions;
- verified WW33 AVB metadata and payload hashes.

Candidate SHA-256:
`281d5f6bc48972a1d428db5a268a2a6078d05fbceb0008d4996ceae1f4e0f549`.

The 28 sparse chunks completed, read-back sizes matched, slot A activated,
stock recovery remained stable, charging raised the battery from about 3% to
47%, and official WW33 Android completed boot.

## Permanent operating rule

- Keep slot A as the known-good ASUS charging, Android, and recovery route.
- Do not rebuild or reflash `super`.
- Do not attempt WW18 rollback; rollback state and signing lineage advanced.
- Do not write GPT, `persist`, `factory`, `batinfo`, modem/EFS, calibration,
  RPMB/devinfo, or per-unit keys.
- Do not expect normal Android from slot B; its logical partitions are
  intentionally factory-empty.
- Use RAM-only `fastboot boot` for Linux development until a persistent design
  explicitly preserves slot A.

The next project phase is Linux dual-port power and USB, not charging repair.
