# Generation 124 two-sample exact UDC staging

Date: 2026-08-24

Result: **OFFLINE PASS; ADMITTED ONCE.** Generation 124 remains unbooted.

Generation 123 proved post-ConfigFS UDC inventory alternates only between empty
and exact `a600000.usb`, with no wrong basename. The new selector tolerates
absence while polling, requires two consecutive exact samples, rejects every
wrong or multiple candidate, and revalidates exact identity immediately before
and after binding. All later staging behavior remains unchanged.

Clean-twin target initramfs SHA-256:
`4edaf3a8668049e33b26da504f2ae3d216a32dc412175224be7b9386526101e0`.
Signed runtime manifest SHA-256:
`df525ae6794d14b6aa8ee9d3076490ad8bfb47e25b792e15e4e7c7f461d48020`.
Generation-124 recovery SHA-256:
`921173ef862bc69b0e578ffc91c97194cc00d4872e94d12eb0872d91e3807727`.
