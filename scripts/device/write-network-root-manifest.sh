#!/bin/sh
set -eu

artifact_dir=${1:?usage: write-network-root-manifest.sh ARTIFACT_DIR}
required_files='
Image-5.4.210-network-root-stage
config-5.4.210-network-root-stage
embedded-kexec-stage-initramfs.cpio.gz
build-meta-5.4.210-network-root-stage.txt
Image-7.1.4-network-root
Image.gz-7.1.4-network-root
config-7.1.4-network-root
modules-7.1.4-network-root.tar.gz
build-meta-7.1.4-network-root.txt
sm8350-asus-rog-phone5-recovery.dtb
rog5-network-root-initramfs.cpio.gz
rog5-network-root-kexec-stage-initramfs.cpio.gz
boot-5.4.210-network-root-stage.raw.img
boot-5.4.210-network-root-stage.avb.img
'

for file in $required_files; do
	[ -f "$artifact_dir/$file" ] && [ ! -L "$artifact_dir/$file" ] || {
		echo "FAIL missing regular artifact: $file" >&2
		exit 1
	}
done

temporary=$artifact_dir/.SHA256SUMS.$$
trap 'rm -f "$temporary"' EXIT INT TERM
(
	cd "$artifact_dir"
	sha256sum $required_files
) >"$temporary"
[ "$(awk 'NF { count++ } END { print count + 0 }' "$temporary")" -eq 14 ]
mv "$temporary" "$artifact_dir/SHA256SUMS"
trap - EXIT INT TERM

cat "$artifact_dir/SHA256SUMS"
echo 'PASS exact fourteen-file network-root manifest'
