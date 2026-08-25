# Generation 149 bounded-write kernel composition

Result: **CONSUMED; WRITE KERNEL PASSED; DENSE UFS WRITE STALLED.** Never flash
or retry.

Primary question: does the corrected stager complete when paired with the
retained clean-twin kernel that actually enables bounded UFS data writes?

Generation 148 emitted exact `disk-rw-state`. The deployed ae717 config has
`CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y` but lacks
`CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE`, proving an R2 composition defect. The
retained PC-built twins instead have both symbols enabled, built-in PMK8350
SDAM/reboot-mode support, 15 matching power/USB modules, and four matching UFS
modules. Their byte-identical Image is
`a7e0cd84238d9e0c399a6c93d3c7a5996571dc3536b10c7323cbe1455dbad01e`.

No kernel compilation was needed. Corrected target initramfs twins built in
6.554 seconds and match at SHA-256
`6ed0954e7f01fe5fd437a05872783824b5c975fa9d38d0e561b02fe80871fac8`,
size 23,804,743 bytes. The DTB, installer scope, Arch image, recovery raw
bytes, and slot-A fallback are unchanged.

Signed bundle manifest SHA-256:
`4ed06aa453489f7666c3f7ccb55e519a9fa4074c03edda496326810beed57606`.
Generation-149 RAM-only AVB SHA-256:
`e001c6e580b3a07ee0c863e2a4d72b1a4e68c74edd01cae79e46907870bcadfa`.

The sole cycle passed power/USB, exact UFS, runtime, first-attempt key-only
SSH, and exact transfer. It cleared the disk/partition write window and
mounted userdata RW, proving the kernel composition fix. Dense gzip expansion
then wrote only 825,884,672 bytes in about 20 minutes before gzip and `sync`
entered uninterruptible UFS I/O. The 900-second watchdog was itself blocked in
`sync`. A bounded pinned-SSH snapshot proved the exact process, partial path,
and size. After SIGTERM could not interrupt D-state I/O, the sealed restart2
helper set the bootloader reason and emergency SysRq completed exact fastboot
fallback. The partial file is bounded to the authorized path; GPT and protected
partitions were untouched.

The next design must avoid a dense 16 GiB stream. Use a sealed sparse/extents-
aware writer, repair/replace only the exact partial path, and make emergency
rollback independent of `sync` before another candidate.
