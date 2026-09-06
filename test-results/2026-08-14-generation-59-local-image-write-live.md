# Generation 59 bounded local-image write live result

Date: 2026-08-14

Result: **consumed failure; exact fallback passed; never retry.**

Generation 59 entered its exact one-use claim and temporarily booted the
reviewed RAM-only recovery wrapper. Recovery transferred and accepted the
exact `persistent-root-local-image-write-v37` bundle. Mainline Linux
`7.1.4-gae717d919f87`, boot ID
`206e8453-8467-40c8-be27-27fd98988902`, then reported:

- UFS ready;
- exact `userdata` resolved;
- initial read-only `userdata` mount entered;
- bounded image write entered; and
- terminal `image-write: FAIL`.

The first UFS record arrived at host monotonic `186300.848402`. The exact
`image-write` enter and fail records arrived at `186309.899184` and
`186310.905281`. These are receive times, not target syscall timestamps.

The lifecycle returned exact Alpine fallback, restored the host profile,
proved strict fallback identity, resolved the execution intent as
`FALLBACK_RETURNED`, and cleaned the recovery host state. Fallback thermal
maximum was 40.1 C. PMIC PON reported the expected PS_HOLD hard-reset path.
Pstore was empty; that absence is not treated as proof that no crash occurred.

Read-only fallback inspection attached the 16 GiB image through a read-only
loop and mounted it `ro,noload,nodev,nosuid,noexec,noatime`. The image remained
clean with mount count one, so its filesystem had not completed a new
read-write mount. `/var/lib/rog5`, the fixed marker, and the temporary marker
were all absent. Generation 59 therefore failed before its bounded payload
write and made no marker mutation.

The v37 terminal stage was too coarse to distinguish write-window setup,
outer userdata RW mounting, loop setup, or the inner image RW mount. This is
the concrete defect addressed by the Generation 60 discriminator. Generation
59 is revoked and must never be retried or flashed.
