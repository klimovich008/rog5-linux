#!/bin/sh
set -eu

base=${1:?usage: build-persistent-root-standalone-initramfs.sh BASE OUTPUT [UFS_MODULES]}
output=${2:?missing output}
ufs_modules=${3:-}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/persistent-root-init
shutdown=$repo/initramfs/persistent-root-shutdown-standalone
state_helper=$repo/initramfs/persistent-service-state
ssh_identity=$repo/initramfs/persistent-ssh-identity
ufs_module_verifier=$repo/scripts/device/verify-persistent-ufs-module-profile.sh
expected_base=cf3f6dadfb7567da064b27ce341d2224328c8046e3bef870424dbe8ddf471827
expected_release=7.1.4-g359318de534f
storage_mode=read-only
probe_boot_id=staged-seal
native_root_mode=1
ssh_diagnostic_mode=0
epoch=1681862400

[ -f "$base" ] && [ ! -L "$base" ] &&
	[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ]
[ -x "$init" ] && [ -x "$shutdown" ] && [ -x "$state_helper" ] &&
	[ -x "$ssh_identity" ] && [ -x "$ufs_module_verifier" ]
[ ! -e "$output" ]
if [ -n "$ufs_modules" ]; then
	"$ufs_module_verifier" "$ufs_modules" "$expected_release" local-write
fi

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
root=$work/root
mkdir "$root"
gzip -dc "$base" | (cd "$root" && cpio -idm --quiet --no-absolute-filenames)
[ -x "$root/init" ] && [ -x "$root/shutdown" ]

(cd "$root" && find . -type f ! -path ./init ! -path ./shutdown \
	! -path ./usr/local/sbin/rog5-persistent-state \
	! -path ./usr/local/sbin/rog5-persistent-ssh-identity \
	! -path ./rog5-ufs-modules/ufshcd-core.ko -print0 | sort -z |
	xargs -0 sha256sum) >"$work/before"
install -m 0755 "$init" "$root/init"
for placeholder in \
	EXPECTED_KERNEL_RELEASE EXPECTED_UFS_STORAGE_MODE \
	EXPECTED_PROBE_BOOT_ID EXPECTED_NATIVE_ROOT_MODE \
	EXPECTED_SSH_DIAGNOSTIC_MODE; do
	[ "$(grep -Fc "@$placeholder@" "$root/init")" -eq 1 ]
done
sed -i \
	-e "s/@EXPECTED_KERNEL_RELEASE@/$expected_release/" \
	-e "s/@EXPECTED_UFS_STORAGE_MODE@/$storage_mode/" \
	-e "s/@EXPECTED_PROBE_BOOT_ID@/$probe_boot_id/" \
	-e "s/@EXPECTED_NATIVE_ROOT_MODE@/$native_root_mode/" \
	-e "s/@EXPECTED_SSH_DIAGNOSTIC_MODE@/$ssh_diagnostic_mode/" \
	"$root/init"
! grep -Fq '@EXPECTED_' "$root/init"
install -m 0755 "$shutdown" "$root/shutdown"
install -D -m 0755 "$state_helper" \
	"$root/usr/local/sbin/rog5-persistent-state"
install -D -m 0755 "$ssh_identity" \
	"$root/usr/local/sbin/rog5-persistent-ssh-identity"
if [ -n "$ufs_modules" ]; then
	for module in phy-qcom-qmp-ufs.ko ufs-qcom.ko ufshcd-pltfrm.ko; do
		cmp "$root/rog5-ufs-modules/$module" "$ufs_modules/$module"
	done
	install -m 0644 "$ufs_modules/ufshcd-core.ko" \
		"$root/rog5-ufs-modules/ufshcd-core.ko"
fi
(cd "$root" && find . -type f ! -path ./init ! -path ./shutdown \
	! -path ./usr/local/sbin/rog5-persistent-state \
	! -path ./usr/local/sbin/rog5-persistent-ssh-identity \
	! -path ./rog5-ufs-modules/ufshcd-core.ko -print0 | sort -z |
	xargs -0 sha256sum) >"$work/after"
cmp "$work/before" "$work/after"

find "$root" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output")"
(cd "$root" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output.tmp"
mv -T "$output.tmp" "$output"
gzip -t "$output"
sha256sum "$output"
