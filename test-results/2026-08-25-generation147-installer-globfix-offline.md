# Generation 147 installer glob correction

Result: **OFFLINE PASS; UNBOOTED; ADMITTED ONCE.** Never flash or retry after
claim entry.

Primary question: can the already-proven UFS/NCM/key-only-SSH target stage the
exact Arch image when the installer is allowed to expand its fixed userdata
and relock globs?

Generation 146 classification: R3. Its sole cycle passed the exact 116-node
UFS topology, first-attempt key-only SSH, and the 649,960,943-byte gzip
transfer. The exact installer then mounted userdata, but `set -f` made
`"$mountpoint"/*` a literal path. The content check failed before `mkdir` or
decompression, and the same setting suppressed the relock glob. Exact slot-A
fastboot fallback and host cleanup passed. No image file or directory was
created; normal ext4 mount/unmount metadata effects remain possible.

The fail-first test rejected the old installer in 0.174 seconds. The fix
removes only `set -f` and prints a bounded failure record before reboot. The
exact sealed AArch64 BusyBox content-glob fixture passes. Focused target,
lifecycle, and recovery-gate tests pass in 1.131, 0.216, and 5.989 seconds.

Clean target initramfs twins are byte-identical at SHA-256
`bc9770b48f516db4b91b5955e127208ff8a04bd0c3799a429437e8d0b5b01d4b`
and size 23,804,816 bytes. The target build took 11.561 seconds. Kernel, DTB,
19 modules, stable recovery raw bytes, one-file storage scope, rollback, and
slot-A fallback are unchanged. No kernel or ASUS wrapper compilation ran.

Signed bundle manifest SHA-256:
`1930e049f1f180e90cfcb8e877cb1108e1f1b9a15f3beaf421f4aeac3901a1e6`.
Generation-147 RAM-only AVB SHA-256:
`7f2203a94b4dfc98f15e2a02f29c18cf7b8dbcea24983e66597898e512292563`.

Mandatory pre-build checklist: single objective written; fail-first host test
passed; source frozen across twin build; one candidate record; exact BusyBox
fixture passed; unchanged 900/600-second lattice retained; prior real SSH
timeout classified; sufficient disk check remains part of connected preflight;
proven kernel and wrapper raw bytes were reused.

The active tier passed in 20.108 seconds. The one required full local CI run
passed on the frozen implementation in 403.959 seconds; it was not repeated.
