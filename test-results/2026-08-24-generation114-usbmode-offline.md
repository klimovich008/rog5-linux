# Generation 114 USB-mode parity staging

Date: 2026-08-24

Result: **OFFLINE PASS; ADMITTED ONCE.** Generation 114 remains unbooted.

Generation 113 proved that the exact target kernel release and all required
command-line tokens pass. The next difference from the repeatedly working
mature persistent-root USB path is that mature init writes `peripheral` to
`/sys/bus/platform/devices/a600000.ssusb/mode` before ConfigFS, while the
minimal staging init omitted the transition.

Generation 114 adds only that exact mature-path step. It otherwise reuses the
Generation 112 full writer target and preserves the exact compressed source,
userdata-23-only image path, charging stack, UFS module closure, relock, key-only
SSH, restart2 helper, and RAM-only wrapper.

Identities:

- Image: `a7e0cd84238d9e0c399a6c93d3c7a5996571dc3536b10c7323cbe1455dbad01e`;
- DTB: `4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8`;
- clean-twin initramfs: `5cf22d30cc3d2cae98c700b749ebdeb3c0f74376b7246ea57cf004f17cfc8e55`;
- signed manifest: `78091cdfd341367996b258ebdd12ac447dfe7ab2d2e38101580bf5fc98315fe7`;
- Generation 114 wrapper: `b4334d2729d876270ec86ecf955aee4f2c104dea2c9f650019dc64528d646c7e`.

No phone partition flash is authorized. The single RAM-only cycle may write
only the exact final 16 GiB Arch image file after authenticated SSH and all
power, identity, UFS, filesystem, and empty-content gates pass.
