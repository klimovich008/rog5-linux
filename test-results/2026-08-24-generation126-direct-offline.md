# Generation 126 direct transient-UDC bind

Result: **CONSUMED; EXACT BIND WRITE REFUSED.** Never retry or flash.

The target polls the exact expected UDC path every 10 ms, attempts the exact
bind immediately, retries only a vanished path, then validates the bound name
and complete inventory. Twin initramfs SHA-256 is
`fbea476c906764e6cceb912ae1617706e829495effa056a0987625b79dce7138`;
manifest is `e183d08e4814d5751c8bb4cc0e7f900cc1e030bc18335cc63c0dc821de2453eb`;
recovery is `4e8985de4d8f1a2a2c98541f9d6db683335a2c1018966dfdbedb22b2b7135d89`.

Recovery USB departed at `13:55:59.036497`; fastboot appeared at
`13:56:05.937510`, 6.901013 seconds later. The direct exact bind write failed
while `/sys/class/udc/a600000.usb` remained present. No target USB, SSH,
installer, or storage write ran; fallback passed.

The next classifier maps the synchronous ConfigFS/DWC3 kernel error number
(`failed to start configfs-gadget: -errno`) before any bind or storage retry.
