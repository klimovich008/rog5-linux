# Generation 122 explicit-sysfs full staging

Date: 2026-08-24

Result: **OFFLINE PASS; ADMITTED ONCE.** Generation 122 remains unbooted.

The target removes the redundant second `mdev -s` entirely. Devtmpfs and the
initial boot scan remain; USB setup uses only explicit ConfigFS, UDC, and
`usb0` conditions. Image, DTB, address command, power/USB loader, UFS modules,
one-file installer, and rollback remain unchanged.

Clean-twin target initramfs SHA-256:
`ab12eb7f59a64ae50816bfc7550e9640eed59baadf7af3cf4bd9a34ede6622ad`.
Signed runtime manifest SHA-256:
`eb742d37c8f937a95159f96f23f5d543c6657e1cf6e235659c38e206eff79b4c`.
Generation-122 recovery SHA-256:
`5c693c5cbc91338c9f9d53a3c7425b51651e967729e766befe8cdfa49f472071`.
