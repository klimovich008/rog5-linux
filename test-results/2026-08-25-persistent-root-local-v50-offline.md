# Persistent-root local V50 offline checkpoint

Result: **OFFLINE PASS; ADMITTED ONCE; UNBOOTED.** No phone contact or claim.

Generation 158 published the exact 16 GiB image with target fsync, read-only
e2fsck, atomic rename, directory sync, unmount and relock. V50 boots that image
read-only and requires its exact UUID, label, source seal, local seal and tree
identity. The historical phone-write probe must be absent under the new sealed
`staged-seal` policy.

Target initramfs twins match at SHA-256
`a22224d24b56adfd134c9085d0a55ee29afd1c77776e84e22d31824493d77cbd`,
size 23,810,585 bytes. Signed bundle manifest SHA-256 is
`b5f3c2665a5ac68d255449102c06d210348b4c88c1457c762e31ec58d1febe03`.
Generation-159 wrapper SHA-256 is
`cca9661162c335d0dcd774bf55544acee3cc8d8950f8ddd96a2979ee2b6f076a`.

One cycle must prove local image mount, OverlayFS/systemd, power/USB readiness,
strict key-only SSH, systemd timing, controlled shutdown and exact fastboot
fallback. No phone storage write is allowed.
