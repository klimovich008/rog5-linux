#!/bin/sh
set -eu

artifact_dir=${1:?usage: write-ufs-discovery-manifest.sh ARTIFACT_DIR}
required_files='
Image-5.4.210-ufs-discovery-stage
config-5.4.210-ufs-discovery-stage
embedded-kexec-stage-initramfs.cpio.gz
build-meta-5.4.210-ufs-discovery-stage.txt
Image-7.1.4-ufs-discovery
config-7.1.4-ufs-discovery
build-meta-7.1.4-ufs-discovery.txt
sm8350-asus-rog-phone5-base.dtb
sm8350-asus-rog-phone5-ufs-discovery.dtb
rog5-ufs-discovery-initramfs.cpio.gz
rog5-ufs-discovery-kexec-stage-initramfs.cpio.gz
boot-5.4.210-ufs-discovery-stage.raw.img
boot-5.4.210-ufs-discovery-stage.avb.img
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
[ "$(awk 'NF { count++ } END { print count + 0 }' "$temporary")" -eq 13 ]
mv "$temporary" "$artifact_dir/SHA256SUMS"
trap - EXIT INT TERM

cat "$artifact_dir/SHA256SUMS"
echo 'PASS exact thirteen-file UFS discovery manifest'
