# Generation 145 post-UFS pre-SSH discriminator

Result: **CONSUMED; EXACT RUNTIME/NOLOGIN FAILURE; NO WRITE.** Never retry or
flash.

Generation 144 proved immediate target activation and UFS, then returned exact
fastboot before host-key readiness. No transfer or storage write occurred, but
the target had cleared its current stage after UFS and therefore discarded the
failure reason.

Generation 145 adds only existing `userdata-resolved`, `storage-locked`, and
`runtime` stage records around exact userdata identity, read-only lock,
`/etc/nologin` removal, host-key generation, and sshd. It remains pre-write
until strict SSH, exact image transfer, and explicit installer invocation.

The sole cycle passed UFS, userdata identity, and storage lock, then emitted
`stage=runtime state=FAIL detail=nologin-identity`. The archive contains no
nologin member, while root's shadow entry is locked as `!`. No SSH, transfer,
installer, mount, or storage write ran; exact fastboot fallback passed.
