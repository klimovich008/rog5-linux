# Generation 120 usb0 address-state discriminator

Date: 2026-08-24

Result: **OFFLINE PASS; ADMITTED ONCE.** Generation 120 remains unbooted.

Generation 119 proved that `ip address add 169.254.77.2/30 dev usb0` returned
nonzero after ConfigFS, UDC binding, `usb0`, and link-up passed. Generation 120
changes only that boundary and classifies five outcomes with fixed 70–90 second
delays: address-show/interface failure, exact address already present,
conflicting address, first-add failure, or first-add success.

It stops before carrier, power/USB, UFS, userdata, SSH, installer, or any
storage surface. Clean-twin target initramfs SHA-256 is
`697c5750fe7d4a95fc6908be2e362e7feaa7a7ef5086755c76925e0169f6d278`;
signed bundle manifest is
`fda8afcc23cdb35c782b72bc91c1975138dd8f7404acb40c7744badc03825678`;
Generation-120 recovery is
`6bd965cf81d976d76f27b90b43d102a4e6d514285d89fdf5ec8664a17897a621`.
