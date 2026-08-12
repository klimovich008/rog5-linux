# Generation 24 precheck-USB persistent-root successor

Status: **OFFLINE-READY; unbooted; RAM-only; never flash**.

Generation 24 fixes the concrete Generation-23 observation defect: NCM setup
was described as early but still followed command-line and release validation.
The target now parses only the bounded rollback timeout, arms its 600-second
emergency reset, and configures the same exact `a600000.usb` NCM gadget before
either target-identity check and before every userspace UFS operation.

A fail-first ordering test rejected the Generation-23 source in 0.390 seconds.
After the correction, the hostile storage/UDC suite passed in 0.391 seconds and
the deterministic initramfs contract passed. The initramfs clean twins built
in 0.866 and 0.890 seconds and are byte-identical: 6,121,343 bytes, SHA-256
`908f18f752962fae798249060aa8ee4c45673d8795571fbb8883ac4ed8d9e19e`.

The Image remains `854397a7…b4a13`; the DTB remains
`72c0db7c…f48c2`. Signed bundle twins reproduce with manifest
`3bc4b40f…b8ed73`. The byte-distinct Generation-24 AVB wrapper is
`6850d79a…e9f6bca`; its raw recovery payload remains unchanged at
`06732992…c4aff`.

The cycle remains read-only: it can force physical nodes read-only and mount
exact userdata only `ro,noload`, but cannot create or write the planned local
filesystem image. Candidate execution remains one-use and RAM-only.
