# Generation 149 bounded-write kernel composition

Result: **OFFLINE PASS; UNBOOTED; ADMITTED ONCE.** Never flash or retry after
claim entry.

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
