# Generation 128 host-fixed full staging successor

Result: **CONSUMED; FALSE POST-BIND UDC-CLASS INVARIANT.** Never retry or flash.

Primary question: can the unchanged UFS-capable charging kernel reach exact
NCM, key-only SSH, and stage the 16 GiB Arch image after the proven R7 host
model filter and post-COMMIT cleanup defects are fixed?

The target initramfs twins are byte-identical at
`271665889d342806e4db5c259f97c9b76171d115e30e818df4988badb018cc77`.
Image and DTB are unchanged. Signed bundle twins verify with manifest
`d5022e9a967bda3171492caba4e4ddf1d5d22bca022cf2b27d2fa1f9e7ef911c`
and trust root `cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054`.
The generation-128 AVB wrapper is
`f1cbb906fdf1ebff9f79ecebabc9775a630bf9ca923bf1206dcacdb87ce262d0`;
its raw recovery bytes remain `4f9ac4e7...d9f8`.

Focused host, exact sealed-BusyBox, target-initramfs, and live-gate tests pass.
No phone contact or storage write occurred while creating this successor.

Live result: recovery USB departed at `14:55:00.337539`; exact slot-A fastboot
appeared at `14:55:07.241499`, 6.903960 seconds later. No target USB product,
SSH, installer, or storage write occurred; fallback and intent resolution
passed. The 25-second bind retry cannot have expired. Linux 7.1
`gadget_dev_desc_UDC_store()` clears ConfigFS `udc_name` on every failed store,
so the retry path cannot produce this immediate return. A successful store
retains exact ConfigFS readback; the next statement is the one-shot
`/sys/class/udc` inventory assertion. Generation 123 already proved that class
alternates between empty and exact after ConfigFS setup, while Generation 127
proved stable NCM enumeration without the post-bind assertion. This closes the
root cause without another discriminator boot.
