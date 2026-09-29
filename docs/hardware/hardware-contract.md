# Hardware contract discovered from the running device

This is a redacted engineering summary of the private running device tree. The raw DTB/DTS remains outside Git because it includes identifiers, Android boot arguments, proprietary command tables, and unrelated board variants.

## Board identity

- SoC family: Qualcomm SM8350 (`lahaina`).
- Vendor model string: ASUS MP2.
- The vendor tree still identifies as a generic Lahaina MTP, so the mainline port needs a new board-specific `asus,rog-phone5` compatible.
- UFS controller: SM8350 controller at `0x01d84000`.
- Android boot header v3 does not provide a normal boot-image DTB field; appended-DTB or vendor-boot handling must be proven before the first temporary mainline boot.

## Display chain

- Panel: Samsung AMS678 ER2 OLED, 1080x2448, command mode, DSC.
- Fixed profiles: 144, 120, 90, and 60 Hz.
- DSC: 8 bits/component, 8 bits/pixel, 540-pixel slice width, 48-line slice height.
- The path includes a Pixelworks Iris/i6 visual processor. The vendor tree references separate Iris light-up configurations for every refresh profile.
- Linux 7.1.4 has no matching Pixelworks Iris DRM/bridge driver, AMS678 panel driver, or exact ASUS panel binding. This makes the display a driver-porting project, not only a DTS translation. A passive/bypass mode may be possible, but must be demonstrated from hardware behavior or documented commands before use.

Pixelworks confirms that the ROG Phone 5 family uses its i6 visual processor: [Pixelworks ROG Phone 5 announcement](https://www.pixelworks.com/media/zh/1097.html).

## Input

- Main FocalTech touch controller is on I2C address `0x38` and reports the 1080x2448 display area.
- A second FocalTech-compatible controller is present for the rear touch surface.
- Linux 7.1.4 has no exact `focaltech,fts` binding/driver match; the generic EDT FocalTech driver is only a behavioral reference until protocol compatibility is tested.

## Reserved memory and remote processors

The vendor tree reserves distinct regions for ADSP, CDSP, SLPI, modem, camera/video, GPU, secure heaps, SMEM, command DB, logs, and hypervisor services. Addresses and sizes must be translated deliberately. Copying the generic MTP reserved-memory map risks DMA corruption and is prohibited.

The accepted board contract additionally excludes
`0xcbc00000+0x04400000`, `0xd8000000+0x00800000`, and
`0xedc00000+0x12000000` from ordinary allocation. Only the middle memshare
span is `no-map`, matching the stock runtime FDT. This contract is
live-validated by ADSP PAS/SCM startup; changing or deleting any span requires
a new RAM-only rollback-guarded test.

## Evidence policy

Only subsystem facts needed for the port are copied into this document. Do not commit `/proc/cmdline`, `/sys/firmware/fdt`, decompiled vendor DTS, serial numbers, partition GUIDs, Wi-Fi data, firmware blobs, or panel command payloads without a separate licensing and privacy review.
