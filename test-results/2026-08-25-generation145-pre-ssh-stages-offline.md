# Generation 145 post-UFS pre-SSH discriminator

Result: **OFFLINE PASS; ADMITTED ONCE.** Never flash or retry after entry.

Generation 144 proved immediate target activation and UFS, then returned exact
fastboot before host-key readiness. No transfer or storage write occurred, but
the target had cleared its current stage after UFS and therefore discarded the
failure reason.

Generation 145 adds only existing `userdata-resolved`, `storage-locked`, and
`runtime` stage records around exact userdata identity, read-only lock,
`/etc/nologin` removal, host-key generation, and sshd. It remains pre-write
until strict SSH, exact image transfer, and explicit installer invocation.
