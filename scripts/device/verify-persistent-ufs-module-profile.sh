#!/bin/sh
set -eu

module_dir=${1:?usage: verify-persistent-ufs-module-profile.sh MODULE_DIR RELEASE MODE}
expected_release=${2:?missing expected kernel release}
storage_mode=${3:?missing UFS storage mode}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

case $storage_mode in
	read-only | local-write) ;;
	*) fail 'UFS storage mode must be read-only or local-write' ;;
esac

[ -d "$module_dir" ] && [ ! -L "$module_dir" ] ||
	fail 'unsafe deferred UFS module directory'

for command in find modinfo readelf strings; do
	command -v "$command" >/dev/null ||
		fail "missing UFS module verifier command: $command"
done

inventory=$(find "$module_dir" -mindepth 1 -maxdepth 1 -type f \
	-printf '%f\n' | sort | tr '\n' ' ')
[ "$inventory" = \
	'phy-qcom-qmp-ufs.ko ufs-qcom.ko ufshcd-core.ko ufshcd-pltfrm.ko ' ] ||
	fail 'deferred UFS module inventory changed'

for module in phy-qcom-qmp-ufs.ko ufshcd-core.ko ufshcd-pltfrm.ko \
	ufs-qcom.ko; do
	path=$module_dir/$module
	[ -f "$path" ] && [ ! -L "$path" ] ||
		fail "unsafe deferred UFS module: $module"
	readelf -h "$path" | grep -q 'Type:.*REL (Relocatable file)' ||
		fail "deferred UFS module is not relocatable: $module"
	readelf -h "$path" | grep -q 'Machine:.*AArch64' ||
		fail "deferred UFS module is not AArch64: $module"
	[ "$(modinfo -F vermagic "$path" | awk '{ print $1 }')" = \
		"$expected_release" ] ||
		fail "deferred UFS module release changed: $module"
	readelf -SW "$path" | grep -q '[.]BTF[[:space:]]' ||
		fail "deferred UFS module lacks BTF: $module"
	module_struct_size=$(readelf -SW "$path" | awk '
		$2 == ".gnu.linkonce.this_module" { print $6 }
	')
	[ "$module_struct_size" = 000500 ] ||
		fail "deferred UFS module ABI size changed: $module"

	case $module in
		phy-qcom-qmp-ufs.ko)
			expected_name=phy_qcom_qmp_ufs
			expected_depends=
			;;
		ufshcd-core.ko)
			expected_name=ufshcd_core
			expected_depends=
			;;
		ufshcd-pltfrm.ko)
			expected_name=ufshcd_pltfrm
			expected_depends=ufshcd-core
			;;
		ufs-qcom.ko)
			expected_name=ufs_qcom
			expected_depends=ufshcd-pltfrm,ufshcd-core
			;;
	esac
	[ "$(modinfo -F name "$path")" = "$expected_name" ] ||
		fail "deferred UFS module name changed: $module"
	[ "$(modinfo -F depends "$path")" = "$expected_depends" ] ||
		fail "deferred UFS module closure changed: $module"
done

core=$module_dir/ufshcd-core.ko
enabled_marker='ROG5 UFS bounded data-write high-speed gear switch enabled'
disabled_marker='ROG5 UFS discovery: optional device writes and high-speed gear switch disabled'
enabled_count=$(strings "$core" | grep -Fxc "$enabled_marker" || true)
disabled_count=$(strings "$core" | grep -Fxc "$disabled_marker" || true)

case $storage_mode in
	local-write)
		[ "$enabled_count" -eq 1 ] && [ "$disabled_count" -eq 0 ] ||
			fail 'local-write UFS core lacks the exact high-speed implementation'
		;;
	read-only)
		[ "$enabled_count" -eq 0 ] && [ "$disabled_count" -eq 1 ] ||
			fail 'read-only UFS core is not the exact discovery implementation'
		;;
esac

echo "PASS exact $storage_mode persistent UFS module profile"
