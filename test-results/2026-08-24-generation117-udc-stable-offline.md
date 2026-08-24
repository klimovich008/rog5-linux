# Generation 117 stabilized UDC inventory

Date: 2026-08-24

Result: **OFFLINE PASS; ADMITTED ONCE.** Generation 117 remains unbooted.

Generation 115 observed expected `a600000.usb` plus an extra candidate after
ConfigFS setup. Generation 116 sampled earlier and found no extra, proving a
late registration race. Generation 117 adds only a five-second stabilization
window before applying the same no-bind basename classifier.

It reuses Image `a7e0cd84238d9e0c399a6c93d3c7a5996571dc3536b10c7323cbe1455dbad01e`
and DTB `4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8`.
Clean-twin initramfs is
`3cf4d974f21170ab143bf34f4e10b190d69a0743951f90e870d16713d826ecb9`,
signed manifest `f26c2a4c90d19250f9c3475ac5d0008e9d5024cde66a123befc9f545b50a9e09`,
and wrapper `0fb3e2504c62b7718c5e72237c38c9c409c6f07c6115f02ec157a8963a925d62`.

No binding, gadget, UFS, block-device, storage, SSH, or installer surface.
