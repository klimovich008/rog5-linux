# Generation 26 RMTFS-reserved UFS live result

Status: **consumed, no target USB, never retry**.

The sole RAM-only cycle completed exact signed transfer and correlated
`COMMIT_EXEC`. Recovery USB detached at 12:31:04.890465 CEST. No intermediate
target USB identity appeared, and exact Alpine enumerated at
12:31:30.223468, a 25.333-second interval. The durable intent resolved to
`FALLBACK_RETURNED`, host cleanup passed, and the Steam TCP/8081 socket was
restored.

Generation 26 restored the 4 MiB RMTFS reservation and omitted ramoops while
retaining the Generation 25 Image and persistent initramfs. The result rejects
that memory-ownership change as sufficient. It does not prove a UFS failure:
`persistent-root-init` configures USB before its command-line, release, and UFS
gates, so no UFS inventory or userspace storage access occurred. Pstore was
empty and `androidboot.bootreason=unknown`; absence of a retained record is
inconclusive. No phone-storage write occurred.

The fixed `usb:15` failure delay plus the roughly ten-second Alpine boot is
consistent with an early `configure_usb()` failure, but not proof. Generation
27 therefore reuses the exact live-proven Generation 20 Image/DTB with the
same persistent initramfs and a deliberate pre-UFS release mismatch.
