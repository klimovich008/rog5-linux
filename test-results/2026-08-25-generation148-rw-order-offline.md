# Generation 148 parent-before-child read-write correction

Result: **OFFLINE PASS; UNBOOTED; ADMITTED ONCE.** Never flash or retry after
claim entry.

Primary question: does clearing and verifying the parent UFS disk before
userdata permit the already-proven bounded Arch image installation?

Generation 147 passed UFS, key-only SSH, transfer, and the corrected content
glob, then emitted exact `reason=write-window` before mount or image creation.
This is R3: the installer cleared the child partition while its parent disk
remained read-only. The fail-first ordering test rejected the old source in
0.408 seconds. The fix clears and verifies the parent first, then clears and
verifies userdata, preserving the same one-file scope and complete relock.

Target initramfs twins are byte-identical at SHA-256
`efdd2a131fcc38cefc660df3f74552f4191604785bfe55ffa38ab02a71206d12`
and size 23,804,943 bytes. Target-only twin build time was 6.540 seconds. No
kernel or ASUS wrapper compilation ran.

Signed bundle manifest SHA-256:
`59a2ebc8798354545159cf24a836cc23fe9e9a031eea7c7fe181f8674ee8dab3`.
Generation-148 RAM-only AVB SHA-256:
`ed8611651c205a91b2ad457bb3889a366c304d3f67c7421c1cba1f0269dac002`.
