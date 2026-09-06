# Generation 115 ConfigFS beacon

Date: 2026-08-24

Result: **CONSUMED; MULTIPLE UDC CANDIDATES.** Never retry or flash.

Generation 113 proved release and command-line validation pass. Generation 114
proved the guarded platform `mode` path is absent/no-op in this mainline tree.
The remaining pre-target-USB boundary is immediate ConfigFS gadget construction
or UDC discovery/binding.

Generation 115 reuses the exact Image and DTB and has no UFS, block-device,
storage, SSH, or installer execution surface. It assigns distinct bootloader
return delays to ConfigFS mount, gadget directories, descriptors, function
creation, links, UDC absence, UDC identity, and UDC binding. Successful binding
exposes the exact `ROG5 local image stage` NCM/ACM product for 30 seconds.

Identities:

- Image: `a7e0cd84238d9e0c399a6c93d3c7a5996571dc3536b10c7323cbe1455dbad01e`;
- DTB: `4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8`;
- clean-twin initramfs: `2a1312e0e7a5dcc829bb8df056af99c38b6098b085a11b9868e95400695ea352`;
- signed manifest: `e68acce824da7be10502fff08522857bfc59ad5c2e53defe5e50fac802d620f3`;
- Generation 115 wrapper: `6b376583a52eebec18ba8a20deb26c7c560cacb7784285173e6c4585713a818f`.

The candidate is RAM-only, one-use, and flash-forbidden.

Live result: recovery USB departed at 08:18:19.903 and exact fastboot appeared
at 08:19:11.784, a 51.961-second interval. This exactly selects the 45-second
UDC-identity branch plus measured bootloader overhead. The expected
`a600000.usb` path exists, but `/sys/class/udc` contains at least one additional
candidate. The selector correctly refused to bind. No UFS, block device,
storage, SSH, or installer surface ran.
