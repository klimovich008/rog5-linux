# Generation 122 explicit-sysfs full staging

Date: 2026-08-24

Result: **CONSUMED; UDC IDENTITY TIMEOUT.** Never retry or flash.

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

Recovery USB departed at `12:13:54.141606`; exact fastboot appeared at
`12:14:26.133500`, 31.991894 seconds later. With no second mdev scan or
deliberate failure delay, this is the 25-second UDC stability timeout plus the
6.903-second restart baseline. No target USB, SSH, installer, or storage write
ran. Fallback and durable intent resolution passed.

Therefore NCM ConfigFS construction prevents the UDC inventory from remaining
exactly one `a600000.usb` entry for 50 consecutive samples. The next target is
a no-bind, no-storage classifier that names the first unexpected UDC or
distinguishes zero/expected churn.
