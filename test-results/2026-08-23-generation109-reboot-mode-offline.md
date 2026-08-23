# Generation 109 reboot-mode successor

Date: 2026-08-23

Result: **OFFLINE PASS; NO BOOT AUTHORITY.** No phone contact, claim, flash, or
storage access occurred.

Primary question: can mainline prove the standard Qualcomm bootloader reboot
reason path before any persistent-root failure relies on restart2?

The minimal config delta changes only these existing drivers from modules to
built-ins:

- `CONFIG_NVMEM_SPMI_SDAM=y`
- `CONFIG_NVMEM_REBOOT_MODE=y`

The unchanged DTB already contains `/reboot-mode`, compatible
`nvmem-reboot-mode`, `mode-bootloader = <2>`, and the PMK8350 SDAM
`reboot-reason@48` cell. The target now waits at a fixed sysfs path for the
bound reboot-mode platform device and rejects the boot before UFS if it is not
available.

Two fresh, isolated Clang 18 container builds took approximately 20 minutes
each and are byte-identical across config, Image, Image.gz, build metadata,
all 15 charging modules, and all four deferred UFS modules. Final identities:

- config: `15e1ea493ac1e654ef9f162ec9134207522ead67660dc16ab62771d9a9e638d6`
- Image: `1a1958fe72201a3cb1fa7bdfc203ab5132cd236c5e4f95cdd13cc825bdf9ce22`
- Image.gz: `f27630445a58aabd369222af41c3de211223a98c6cb99c5373757c0465e19eca`
- target initramfs: `b5f322533b358856336466d893c04dd36624b194cc0190b09d1eb23ef80cae62`
- signed bundle manifest: `3c0e549c62f3c41c5385987ae6cef76d14e7b8c4d1475b367f85251409cfdadf`
- Generation 109 RAM-only wrapper: `900449001d9e30358ac1bd934ea6fe8e83b2bbfa63cadd2176761f5107e14955`

The two kernel outputs occupy 3.0 GiB each; the signed target/wrapper state is
164 MiB. Generation 109 remains absent from temporary-boot policy, claim
consumers, and the live runner. Restoring and verifying the userdata payload
is a separate prerequisite before admission.
