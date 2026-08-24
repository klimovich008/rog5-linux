# Generation 121 pre-bind mdev full staging

Date: 2026-08-24

Result: **OFFLINE PASS; ADMITTED ONCE.** Generation 121 remains unbooted.

Generations 119 and 120 proved that post-bind `mdev -s` was followed by loss of
`usb0` before its first address query. The mature working persistent-root path
runs the scan before UDC selection/bind and never after binding. Generation 121
makes only that ordering correction, with unchanged Image, DTB, UDC stability
policy, address command, power/USB loader, UFS modules, one-file installer, and
rollback path.

Clean-twin target initramfs SHA-256:
`db01c89a7d8b499c738bfcca488ebb3a9e5616f6db6abfa361d94ac4361b3c8e`.
Signed runtime manifest SHA-256:
`60d264a02ba91ad0839f27a8d8054092dd435414d247a9bc50495ca470d5ac70`.
Generation-121 recovery SHA-256:
`08c78710259a8eb6da4545249ba86aaae2fed5e59d4eb6d6a1548c1050df80b5`.
