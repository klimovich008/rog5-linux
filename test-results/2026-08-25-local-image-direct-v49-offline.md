# Local-image direct V49 offline checkpoint

Result: **OFFLINE PASS; ADMITTED ONCE; UNBOOTED.** No V49 phone contact or claim.

The kernel Image, DTB, target script, extent map, power modules, and three UFS
modules are unchanged. Only `ufshcd-core.ko` changes. The writable discovery
profile now executes the standard high-speed gear transition while optional
BKOPS, timestamp, WriteBooster, exception writes, devfreq and runtime PM remain
contained. The only newly allowed UFS query write is exact reference-clock
attribute index 0 selector 0.

Module twins rebuilt from independent A/B cached states in 8 seconds each,
retain vermagic `7.1.4-g359318de534f`, and match at SHA-256
`e3a049d43352fcec6fca6467f6a27b5d827d3d9071a789f782fe26d67f2b777a`.
Target initramfs twins match at
`411a25ed127a370f56fb5daf2d60f2e0c6280ba8a90d26e1f26c7bf450e631ca`.
Signed bundle manifest SHA-256 is
`ac33ccf7cef86f43834f672d652537b7b5790c8949825f8449088a7721c30459`.
Authority-free Generation-158 wrapper SHA-256 is
`00aa48f0258df05983f955095d355de8ef52c451bb2d4d7a352f4b3f5bafe027`.

Full local kernel/trust CI passed in 447 seconds. The derived Generation-158
admission is open once; COMMIT or any ambiguous outcome permanently consumes
it.
