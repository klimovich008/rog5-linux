#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-network-root-wifi-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256 BASE_ARTIFACT_DIR BASE_SHA256 WIFI_BUILD WIFI_DTB BASE_ROOTFS}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing candidate SHA-256 manifest}
base_artifact_dir=${5:?missing accepted v8 artifact directory}
base_sums=${6:?missing accepted v8 SHA-256 manifest}
wifi_build=${7:?missing accepted WCN6855 kernel build}
wifi_dtb=${8:?missing accepted WCN6855 DTB}
base_rootfs=${9:?missing accepted Arch successor v3 root}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
base_verifier=$repo/scripts/device/verify-network-root-bundle.sh
build_verifier=$repo/scripts/device/verify-mainline-wifi-build.sh
dt_test=$repo/scripts/device/test-wifi-candidate-dtb.sh
overlay_verifier=$repo/scripts/device/verify-wifi-root-overlay.sh
overlay_test=$repo/scripts/device/test-wifi-root-overlay-contract.sh
stage_builder=$repo/scripts/device/build-wifi-kexec-stage-initramfs.sh
gate_test=$repo/scripts/device/test-run-network-root-wifi-gate.sh

check_hash() {
	file=$1
	expected=$2
	[ -f "$file" ] && [ ! -L "$file" ] && [ -s "$file" ] || {
		echo "FAIL missing or linked Wi-Fi bundle input: $file" >&2
		exit 1
	}
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ] || {
		echo "FAIL Wi-Fi bundle input hash mismatch: $file" >&2
		exit 1
	}
}

check_hash "$mkbootimg_dir/mkbootimg.py" \
	d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a
check_hash "$mkbootimg_dir/unpack_bootimg.py" \
	7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef
check_hash "$avbtool" \
	6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff
check_hash "$base_sums" \
	014ad7322adddfa6f2a91a26d47fe0916e0110d628b934d96bfd8c998457a7a7
check_hash "$base_rootfs" \
	a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7

EXPECTED_NETWORK_ROOT_LOADER_SHA256=3a432a2dd0821a1722491faa1631cd0ad35b828cbe26f50581655c89e1613f10 \
	"$base_verifier" "$base_artifact_dir" "$mkbootimg_dir" "$avbtool" \
	"$base_sums" disabled disabled >/dev/null

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
rog5-wifi-root-overlay.tar.gz
'
[ -f "$expected_sums" ] && [ ! -L "$expected_sums" ]
[ "$(awk 'NF { count++ } END { print count + 0 }' "$expected_sums")" \
	-eq 15 ] || {
	echo 'FAIL expected exactly fifteen WCN6855 manifest entries' >&2
	exit 1
}

check_manifest_hash() {
	file=$1
	expected=$(awk -v file="$file" '$2 == file { print $1 }' "$expected_sums")
	[ "$(printf '%s\n' "$expected" |
		awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] || {
		echo "FAIL WCN6855 manifest entry count for $file" >&2
		exit 1
	}
	case $expected in
		*[!0-9a-f]*|'') exit 1 ;;
	esac
	[ "${#expected}" -eq 64 ]
	check_hash "$artifact_dir/$file" "$expected"
}
for file in $required_files; do
	check_manifest_hash "$file"
done

check_hash "$artifact_dir/Image-7.1.4-network-root" \
	a4edaee34dca66534cf886fd0daa6068273d4fd722b63960d517ef17699af43e
check_hash "$artifact_dir/Image.gz-7.1.4-network-root" \
	53fc7f458ba203089355ad913f599dcf1505bb211e17206d17ab8e279cfce858
check_hash "$artifact_dir/config-7.1.4-network-root" \
	79ea41dd4c4e2080923ad0cf855b6d847b09736d82a857546640f0cf26fa5380
check_hash "$artifact_dir/modules-7.1.4-network-root.tar.gz" \
	e7a2eed91e20742012cc0a1fb893545fc61870ec94ca0ca4add3ee6c41e5300d
check_hash "$artifact_dir/build-meta-7.1.4-network-root.txt" \
	7cd6e03913b9ded82870e4b7f65825db38368374a06adb7b2f3fa090769ef9f9
check_hash "$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb" \
	15acdcd6fad910f105047ef53de08b47cafadbbf94827e123931408d92310d89
check_hash "$artifact_dir/rog5-network-root-initramfs.cpio.gz" \
	4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
check_hash "$artifact_dir/rog5-wifi-root-overlay.tar.gz" \
	4e2de54fad3476c950cfc1a97ad30d38a8d03810e66665747adc85762faa6025

cmp "$artifact_dir/Image-7.1.4-network-root" \
	"$wifi_build/arch/arm64/boot/Image"
cmp "$artifact_dir/Image.gz-7.1.4-network-root" \
	"$wifi_build/arch/arm64/boot/Image.gz"
cmp "$artifact_dir/config-7.1.4-network-root" "$wifi_build/.config"
cmp "$artifact_dir/modules-7.1.4-network-root.tar.gz" \
	"$wifi_build/modules.tar.gz"
cmp "$artifact_dir/build-meta-7.1.4-network-root.txt" \
	"$wifi_build/build-meta.txt"
cmp "$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb" "$wifi_dtb"
cmp "$artifact_dir/rog5-network-root-initramfs.cpio.gz" \
	"$base_artifact_dir/rog5-network-root-initramfs.cpio.gz"

config=$artifact_dir/config-7.1.4-network-root
if grep -Eq '^CONFIG_SCSI_UFSHCD=(y|m)$' "$config"; then
	echo 'FAIL WCN6855 bundle enables CONFIG_SCSI_UFSHCD' >&2
	exit 1
fi
"$build_verifier" "$wifi_build" >/dev/null
BASE_DTB=$base_artifact_dir/sm8350-asus-rog-phone5-recovery.dtb \
	"$dt_test" >/dev/null
"$overlay_test" >/dev/null
"$overlay_verifier" "$base_rootfs" "$wifi_build/modules.tar.gz" \
	"$artifact_dir/rog5-wifi-root-overlay.tar.gz" >/dev/null
"$gate_test" >/dev/null

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
core_sums=$stage/SHA256SUMS.core
awk '$2 != "rog5-wifi-root-overlay.tar.gz"' "$expected_sums" >"$core_sums"
[ "$(awk 'NF { count++ } END { print count + 0 }' "$core_sums")" -eq 14 ]
ALLOW_QMP_PCIE=m \
	EXPECTED_NETWORK_ROOT_LOADER_SHA256=3a432a2dd0821a1722491faa1631cd0ad35b828cbe26f50581655c89e1613f10 \
	"$base_verifier" "$artifact_dir" "$mkbootimg_dir" \
	"$avbtool" "$core_sums" disabled disabled >/dev/null

"$stage_builder" \
	"$base_artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz" \
	"$artifact_dir/Image-7.1.4-network-root" \
	"$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb" \
	"$stage/rebuilt-stage.cpio.gz" >/dev/null
cmp "$stage/rebuilt-stage.cpio.gz" \
	"$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz"

dtb=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb
for node in /soc@0/pcie@1c00000 /soc@0/phy@1c06000; do
	[ "$(fdtget -t s "$dtb" "$node" status)" = okay ]
done
[ "$(fdtget -t s "$dtb" /wcn6855-pmu compatible)" = \
	qcom,wcn6855-pmu ]
[ "$(fdtget -t s "$dtb" \
	/soc@0/pcie@1c00000/pcie@0/wifi@0 compatible)" = pci17cb,1103 ]

mkdir -p "$stage/overlay"
tar -xzf "$artifact_dir/rog5-wifi-root-overlay.tar.gz" -C "$stage/overlay"
if find "$stage/overlay" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .
then
	echo 'FAIL private key exists in WCN6855 root overlay' >&2
	exit 1
fi
if find "$stage/overlay" -path '*/NetworkManager/system-connections/*' \
	-type f | grep -q .
then
	echo 'FAIL connection credential exists in WCN6855 root overlay' >&2
	exit 1
fi

python3 "$avbtool" info_image \
	--image "$artifact_dir/boot-5.4.210-network-root-stage.avb.img" \
	>"$stage/avb-info"
grep -q '^Algorithm:[[:space:]]*NONE$' "$stage/avb-info"

echo 'PASS reproducible WCN6855 network-root bundle; PCIe/QMP/power/ath11k exact, storage disabled, credentials absent, offline validation only'
