# iw 6.9 for the sealed Wi-Fi userspace

The unmodified `iw-6.9-r0.apk` is the official Alpine v3.22 main/aarch64
package, not a phone firmware blob. Source package metadata:
<https://pkgs.alpinelinux.org/package/v3.22/main/aarch64/iw>.
Download: <https://dl-cdn.alpinelinux.org/alpine/v3.22/main/aarch64/iw-6.9-r0.apk>.
Alpine packaging commit: `8eb8183bdae879445973711fb2466397753d7e43`.
Upstream source: <https://www.kernel.org/pub/software/network/iw/iw-6.9.tar.xz>.
COPYING is the unmodified upstream ISC license and accompanies the target tool.

The APK signature was verified using Alpine's public key
`alpine-devel@lists.alpinelinux.org-616ae350.rsa.pub`, obtained from
<https://alpinelinux.org/keys/>. The independently verified apk-tools static
verifier also accepted the package. The builder owns the single archive hash
pin and derives the executable hash while generating the target file manifest.
No network fetch or install scripts run during composition.

Only `usr/sbin/iw` and COPYING enter the initramfs. Its three dependencies
(musl, libnl-3 and libnl-genl-3) already exist in the qualified WPA kit; their
bytes are unchanged. QEMU verified loading against those exact libraries and
the phone verified get/off/get/on/get with a disposable tmpfs copy. This is
compatibility evidence, not endurance or release qualification.
