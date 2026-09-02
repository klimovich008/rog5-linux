#!/bin/sh
set -eu

base=${1:?usage: build-persistent-root-standalone-initramfs.sh BASE OUTPUT [UFS_MODULES [POWER_MODULES]]}
output=${2:?missing output}
ufs_modules=${3:-}
power_modules=${4:-}
[ "$#" -le 4 ]
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/persistent-root-init
attest=$repo/initramfs/persistent-root-attest
shutdown=$repo/initramfs/persistent-root-shutdown-standalone
state_helper=$repo/initramfs/persistent-service-state
ssh_identity=$repo/initramfs/persistent-ssh-identity
tailscale_runtime=$repo/initramfs/persistent-tailscale-runtime
ufs_module_verifier=$repo/scripts/device/verify-persistent-ufs-module-profile.sh
expected_base=cf3f6dadfb7567da064b27ce341d2224328c8046e3bef870424dbe8ddf471827
expected_v10=db249f8cf242046c88ff8587355ea0eb89005b2bdafa57de8ddad43f1fe802fb
expected_external_base=${EXPECTED_STANDALONE_BASE_SHA256:-}
expected_release=${EXPECTED_RELEASE:-7.1.4-g359318de534f}
storage_mode=read-only
probe_boot_id=staged-seal
native_root_mode=1
ssh_diagnostic_mode=0
persistent_overlay_mode=${PERSISTENT_ROOT_OVERLAY:-0}
epoch=1681862400

case $persistent_overlay_mode in 0|1) ;; *)
	echo 'FAIL PERSISTENT_ROOT_OVERLAY must be 0 or 1' >&2
	exit 1
esac
printf '%s\n' "$expected_release" | grep -Eq '^7[.]1[.]4-g[0-9a-f]{12}$' || {
	echo 'FAIL invalid expected standalone kernel release' >&2
	exit 1
}

# Full module refresh is for an exact rebuilt kernel/BTF closure. The caller
# must independently prove code equivalence and load the closure with its Image.
# Keep the input inventory identical to the already authenticated base archive.
refresh_module_set() {
	module_source=$1
	module_target=$2
	module_count=$3
	[ -d "$module_source" ] && [ ! -L "$module_source" ] || return 1
	[ -d "$module_target" ] && [ ! -L "$module_target" ] || return 1
	source_inventory=$(find "$module_source" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)
	target_inventory=$(find "$module_target" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)
	[ "$source_inventory" = "$target_inventory" ] || return 1
	[ "$(printf '%s\n' "$source_inventory" | wc -l)" -eq "$module_count" ] || return 1
	for module in "$module_source"/*; do
		case $module in *.ko) ;; *) return 1 ;; esac
		[ -f "$module" ] && [ ! -L "$module" ] || return 1
		readelf -h "$module" | grep -q 'Type:.*REL (Relocatable file)' || return 1
		readelf -h "$module" | grep -q 'Machine:.*AArch64' || return 1
		[ "$(modinfo -F vermagic "$module" | awk '{print $1}')" = "$expected_release" ] || return 1
		case ${module##*/} in
			pdr_interface.ko) ! readelf -SW "$module" | grep -q '[.]BTF[[:space:]]' || return 1 ;;
			*) readelf -SW "$module" | grep -q '[.]BTF[[:space:]]' || return 1 ;;
		esac
	done
	for module in "$module_source"/*; do
		install -m 0644 "$module" "$module_target/${module##*/}" || return 1
	done
}

unchanged_files() {
	set -- ! -path ./init ! -path ./shutdown \
		! -path ./usr/local/sbin/rog5-p2-attest \
		! -path ./usr/local/sbin/rog5-persistent-state \
		! -path ./usr/local/sbin/rog5-persistent-ssh-identity \
		! -path ./usr/local/sbin/rog5-persistent-tailscale \
		! -path ./rog5-ufs-modules/ufshcd-core.ko
	if [ -n "$power_modules" ]; then
		set -- "$@" ! -path './rog5-ufs-modules/*' \
			! -path './rog5-power-usb-modules/*'
	fi
	find . -type f "$@" -print0 | sort -z | xargs -0 sha256sum
}

[ -f "$base" ] && [ ! -L "$base" ]
base_sha256=$(sha256sum "$base" | cut -d ' ' -f 1)
case $base_sha256 in
	"$expected_base"|"$expected_v10") ;;
	*)
		printf '%s\n' "$expected_external_base" | grep -Eq '^[0-9a-f]{64}$' &&
			[ "$base_sha256" = "$expected_external_base" ] || {
			echo 'FAIL unreviewed standalone base' >&2
			exit 1
		}
		;;
esac
[ -x "$init" ] && [ -x "$attest" ] && [ -x "$shutdown" ] && [ -x "$state_helper" ] &&
	[ -x "$ssh_identity" ] && [ -x "$tailscale_runtime" ] &&
	[ -x "$ufs_module_verifier" ]
[ ! -e "$output" ]
[ -z "$power_modules" ] || [ -n "$ufs_modules" ] || {
	echo 'FAIL full module refresh needs matching UFS and power sets' >&2
	exit 1
}
if [ -n "$ufs_modules" ]; then
	"$ufs_module_verifier" "$ufs_modules" "$expected_release" local-write
fi

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
root=$work/root
mkdir "$root"
gzip -dc "$base" | (cd "$root" && cpio -idm --quiet --no-absolute-filenames)
[ -x "$root/init" ] && [ -x "$root/shutdown" ]

(cd "$root" && unchanged_files) >"$work/before"
install -m 0755 "$init" "$root/init"
for placeholder in \
	EXPECTED_KERNEL_RELEASE EXPECTED_UFS_STORAGE_MODE \
	EXPECTED_PROBE_BOOT_ID EXPECTED_NATIVE_ROOT_MODE \
	EXPECTED_SSH_DIAGNOSTIC_MODE EXPECTED_PERSISTENT_OVERLAY_MODE; do
	[ "$(grep -Fc "@$placeholder@" "$root/init")" -eq 1 ]
done
sed -i \
	-e "s/@EXPECTED_KERNEL_RELEASE@/$expected_release/" \
	-e "s/@EXPECTED_UFS_STORAGE_MODE@/$storage_mode/" \
	-e "s/@EXPECTED_PROBE_BOOT_ID@/$probe_boot_id/" \
	-e "s/@EXPECTED_NATIVE_ROOT_MODE@/$native_root_mode/" \
	-e "s/@EXPECTED_SSH_DIAGNOSTIC_MODE@/$ssh_diagnostic_mode/" \
	-e "s/@EXPECTED_PERSISTENT_OVERLAY_MODE@/$persistent_overlay_mode/" \
	"$root/init"
! grep -Fq '@EXPECTED_' "$root/init"
install -D -m 0755 "$attest" "$root/usr/local/sbin/rog5-p2-attest"
for placeholder in EXPECTED_UFS_STORAGE_MODE EXPECTED_PROBE_BOOT_ID \
	EXPECTED_NATIVE_ROOT_MODE EXPECTED_PERSISTENT_OVERLAY_MODE; do
	[ "$(grep -Fc "@$placeholder@" \
		"$root/usr/local/sbin/rog5-p2-attest")" -eq 1 ]
done
sed -i \
	-e "s/@EXPECTED_UFS_STORAGE_MODE@/$storage_mode/" \
	-e "s/@EXPECTED_PROBE_BOOT_ID@/$probe_boot_id/" \
	-e "s/@EXPECTED_NATIVE_ROOT_MODE@/$native_root_mode/" \
	-e "s/@EXPECTED_PERSISTENT_OVERLAY_MODE@/$persistent_overlay_mode/" \
	"$root/usr/local/sbin/rog5-p2-attest"
! grep -Fq '@EXPECTED_' "$root/usr/local/sbin/rog5-p2-attest"
install -m 0755 "$shutdown" "$root/shutdown"
install -D -m 0755 "$state_helper" \
	"$root/usr/local/sbin/rog5-persistent-state"
install -D -m 0755 "$ssh_identity" \
	"$root/usr/local/sbin/rog5-persistent-ssh-identity"
install -D -m 0755 "$tailscale_runtime" \
	"$root/usr/local/sbin/rog5-persistent-tailscale"
if [ -n "$power_modules" ]; then
	refresh_module_set "$ufs_modules" "$root/rog5-ufs-modules" 4
	refresh_module_set "$power_modules" "$root/rog5-power-usb-modules" 15
elif [ -n "$ufs_modules" ]; then
	for module in phy-qcom-qmp-ufs.ko ufs-qcom.ko ufshcd-pltfrm.ko; do
		cmp "$root/rog5-ufs-modules/$module" "$ufs_modules/$module"
	done
	install -m 0644 "$ufs_modules/ufshcd-core.ko" \
		"$root/rog5-ufs-modules/ufshcd-core.ko"
fi
(cd "$root" && unchanged_files) >"$work/after"
cmp "$work/before" "$work/after"

find "$root" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output")"
(cd "$root" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output.tmp"
mv -T "$output.tmp" "$output"
gzip -t "$output"
sha256sum "$output"
