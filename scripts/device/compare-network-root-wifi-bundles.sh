#!/bin/sh
set -eu

bundle_a=${1:?usage: compare-network-root-wifi-bundles.sh BUNDLE_A BUNDLE_B}
bundle_b=${2:?missing second Wi-Fi bundle}
[ "$(stat -Lc '%d:%i' "$bundle_a")" != \
	"$(stat -Lc '%d:%i' "$bundle_b")" ] || {
	echo 'FAIL Wi-Fi bundle directories must be distinct' >&2
	exit 1
}

for directory in "$bundle_a" "$bundle_b"; do
	[ -d "$directory" ] && [ ! -L "$directory" ]
	(cd "$directory" && sha256sum -c SHA256SUMS >/dev/null)
done

for file in \
	Image-5.4.210-network-root-stage \
	config-5.4.210-network-root-stage \
	embedded-kexec-stage-initramfs.cpio.gz \
	build-meta-5.4.210-network-root-stage.txt \
	Image-7.1.4-network-root \
	Image.gz-7.1.4-network-root \
	config-7.1.4-network-root \
	modules-7.1.4-network-root.tar.gz \
	build-meta-7.1.4-network-root.txt \
	sm8350-asus-rog-phone5-recovery.dtb \
	rog5-network-root-initramfs.cpio.gz \
	rog5-network-root-kexec-stage-initramfs.cpio.gz \
	boot-5.4.210-network-root-stage.raw.img \
	boot-5.4.210-network-root-stage.avb.img \
	rog5-wifi-root-overlay.tar.gz \
	SHA256SUMS
do
	[ -f "$bundle_a/$file" ] && [ ! -L "$bundle_a/$file" ]
	[ -f "$bundle_b/$file" ] && [ ! -L "$bundle_b/$file" ]
	cmp "$bundle_a/$file" "$bundle_b/$file" || {
		echo "FAIL clean Wi-Fi bundle mismatch: $file" >&2
		exit 1
	}
done

echo 'PASS two complete WCN6855 network-root bundles are byte-identical'
