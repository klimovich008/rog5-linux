# Generation 102 local-root live result

Date: 2026-08-23

Result: **CONSUMED; DEPLOYED IMAGE/READ-ONLY CONTRACT MISMATCH.** Generation
102 must never be retried or flashed.

The exact userdata-only sparse write completed first: four chunks, 38.194
seconds, exact 243,766,472,704-byte geometry, slot A, safe 8.708 V battery, and
no GPT or non-userdata command. The sparse round trip and nested Arch image
hash had passed before transfer.

Generation 102 then passed signed transfer, PREPARE, and COMMIT. The mature
target exposed `ROG5 persistent root` NCM/ACM from 07:22:51 to 07:23:06 before
stock slot-A return. No target storage write occurred because its sealed mode
was read-only.

The exact deployed target requires a 132-byte, mode-0444
`/var/lib/rog5/local-image-write-probe-v1` bound to writer boot ID
`7c3afb64-8e84-4f4b-87f4-88d19c2646de`. Exact offline inspection of the newly
built image proves that path is absent, while its UUID, label, and root seal are
correct. V9 therefore cannot complete even if all earlier hardware stages pass.
This is an R2 exact-composition defect; no kernel or DT change is indicated.

The successor must use the existing tested `local-write/current` mode to open
the bounded outer/inner write window, create only the probe with the current
boot ID, relock every physical block node, and continue into the unchanged
read-only Arch runtime. No new USB, charging, UFS, or recovery implementation
is justified.
