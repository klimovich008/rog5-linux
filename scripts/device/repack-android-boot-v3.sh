#!/usr/bin/env bash
set -euo pipefail

template=${1:?usage: repack-android-boot-v3.sh TEMPLATE KERNEL RAMDISK MKBOOTIMG_DIR AVBTOOL RAW AVB PARTITION_SIZE [EXTRA_CMDLINE]}
kernel=${2:?missing kernel}
ramdisk=${3:?missing ramdisk}
mkbootimg_dir=${4:?missing mkbootimg directory}
avbtool=${5:?missing avbtool}
raw=${6:?missing raw output}
avb=${7:?missing AVB output}
partition_size=${8:?missing partition size}
extra_cmdline=${9:-}

unpack=$mkbootimg_dir/unpack_bootimg.py
mkbootimg=$mkbootimg_dir/mkbootimg.py
[[ -s $template && -s $kernel && -s $ramdisk && -r $unpack && -r $mkbootimg && -r $avbtool ]]
[[ $partition_size =~ ^[0-9]+$ ]]

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
info=$(python3 "$unpack" --boot_img "$template" --out "$stage/template")
grep -qx 'boot image header version: 3' <<<"$info"

python3 "$unpack" --boot_img "$template" --out "$stage/template-args" \
	--format=mkbootimg --null >"$stage/args"
mapfile -d '' -t args <"$stage/args"

kernel_args=0
ramdisk_args=0
cmdline_args=0
for ((index = 0; index < ${#args[@]}; index++)); do
	case ${args[$index]} in
		--kernel)
			((index + 1 < ${#args[@]}))
			args[$((index + 1))]=$kernel
			kernel_args=$((kernel_args + 1))
			;;
		--ramdisk)
			((index + 1 < ${#args[@]}))
			args[$((index + 1))]=$ramdisk
			ramdisk_args=$((ramdisk_args + 1))
			;;
		--cmdline)
			((index + 1 < ${#args[@]}))
			[[ -z $extra_cmdline ]] || args[$((index + 1))]="${args[$((index + 1))]} $extra_cmdline"
			cmdline_args=$((cmdline_args + 1))
			;;
	esac
done
((kernel_args == 1))
((ramdisk_args == 1))
((cmdline_args <= 1))
[[ -z $extra_cmdline || $cmdline_args == 1 ]]

mkdir -p "$(dirname "$raw")" "$(dirname "$avb")"
python3 "$mkbootimg" "${args[@]}" --output "$raw.tmp"
mv "$raw.tmp" "$raw"

verify_info=$(python3 "$unpack" --boot_img "$raw" --out "$stage/verify")
grep -qx 'boot image header version: 3' <<<"$verify_info"
[[ $(sha256sum "$stage/verify/kernel" | cut -d ' ' -f 1) == \
	$(sha256sum "$kernel" | cut -d ' ' -f 1) ]]
[[ $(sha256sum "$stage/verify/ramdisk" | cut -d ' ' -f 1) == \
	$(sha256sum "$ramdisk" | cut -d ' ' -f 1) ]]

cp "$raw" "$avb.tmp"
salt=$(sha256sum "$raw" | cut -d ' ' -f 1)
python3 "$avbtool" add_hash_footer \
	--image "$avb.tmp" \
	--partition_name boot \
	--partition_size "$partition_size" \
	--algorithm NONE \
	--salt "$salt"
mv "$avb.tmp" "$avb"
[[ $(stat -c %s "$avb") == "$partition_size" ]]
python3 "$avbtool" info_image --image "$avb" | grep -q '^Algorithm:[[:space:]]*NONE$'

sha256sum "$raw" "$avb"
echo 'PASS header-v3 kernel/ramdisk repack and unsigned AVB footer; compile-only'
