#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "$#" -eq 2 ] ||
	fail 'usage: build-network-root-initramfs.sh BASE OUTPUT'
base=$1
output=$2
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
init=$repo/initramfs/network-root-init
shutdown=$repo/initramfs/network-root-shutdown
charging_probe=$repo/scripts/device/probe-network-root-battery-telemetry.sh
power_observer=$repo/scripts/device/observe-early-mainline-power.sh
power_usb_profile=$repo/initramfs/generated-power-usb-active.sh
xattr_projection=$repo/configs/network-roots/rog5-nfs4-xattr-projection-v1
verifier_builder=$repo/scripts/device/build-persistent-root-verifier-static.sh
reviewed_verifier=${NETWORK_ROOT_VERIFIER:-}
reviewed_verifier_hash=2bcead5ca06751d2744cdf0199802ba7ea089257ff383301d1c371f1ef60e28f
reviewed_reporter=${NETWORK_ROOT_DIAGNOSTIC_REPORTER:-}
charge_firmware_archive=${NETWORK_ROOT_CHARGE_FIRMWARE_ARCHIVE:-}
charge_firmware_tree_sha=52442f69be8a91347499bc7a5c45060ad2458bb711cf51f8a7fdd64c5d2d412b
pdr_module=${NETWORK_ROOT_PDR_MODULE:-}
charge_modules_root=${NETWORK_ROOT_CHARGE_MODULES_ROOT:-}
charge_modules_release=7.1.4-g7a5cef0db479
pdr_module_sha=0b7df05e9fa0bfe224fc74ac93997bb1ee74ab5371bde172c3b0a2fcfe19601b
reviewed_reporter_size=67288
reviewed_reporter_hash=fbbeaf880ea595d9f00b0a19b582dc11911a3a8c025e6aae1ee469d6886da604
accepted_base=4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
epoch=1681862400
export LC_ALL=C

for command in cpio cut dirname find grep gzip install ln mktemp readelf rm \
	sha256sum sort stat touch; do
	command -v "$command" >/dev/null ||
		fail "missing network-root initramfs build command: $command"
done
if [ -n "$charge_firmware_archive" ]; then
	case $charge_firmware_archive in /*) ;; *) fail 'charge firmware archive must be absolute' ;; esac
	[ -f "$charge_firmware_archive" ] && [ ! -L "$charge_firmware_archive" ] ||
		fail 'charge firmware archive is absent or linked'
	command -v tar >/dev/null || fail 'missing network-root initramfs build command: tar'
fi
if [ -n "$pdr_module" ]; then
	case $pdr_module in /*) ;; *) fail 'PDR module must be absolute' ;; esac
	[ -f "$pdr_module" ] && [ ! -L "$pdr_module" ] ||
		fail 'reviewed PDR module is absent or linked'
	[ "$(sha256sum "$pdr_module" | cut -d ' ' -f 1)" = "$pdr_module_sha" ] ||
		fail 'reviewed PDR module hash changed'
	for command in modinfo readelf; do
		command -v "$command" >/dev/null || fail "missing PDR verifier command: $command"
	done
	[ "$(modinfo -F name "$pdr_module")" = pdr_interface ] &&
		[ "$(modinfo -F depends "$pdr_module")" = qcom_pdr_msg ] &&
		[ "$(modinfo -F vermagic "$pdr_module")" = \
		'7.1.4-g7a5cef0db479 SMP preempt mod_unload aarch64' ] ||
		fail 'reviewed PDR module ABI changed'
	readelf -h "$pdr_module" | grep -q 'Machine:.*AArch64' ||
		fail 'reviewed PDR module is not AArch64'
	! readelf -S "$pdr_module" | grep -q '[.]BTF' ||
		fail 'reviewed PDR module still contains rejected BTF'
fi
for path in "$init" "$shutdown" "$charging_probe" "$power_observer"; do
	[ -x "$path" ] && [ -f "$path" ] && [ ! -L "$path" ] ||
		fail "missing initramfs source: $path"
done
if [ -n "$charge_modules_root" ]; then
	case $charge_modules_root in /*) ;; *) fail 'charge modules root must be absolute' ;; esac
	[ -d "$charge_modules_root/lib/modules/$charge_modules_release" ] &&
		[ ! -L "$charge_modules_root" ] ||
		fail 'charge modules root is absent or linked'
	[ -n "$pdr_module" ] || fail 'early charge modules require the reviewed PDR override'
	for command in depmod modprobe; do
		command -v "$command" >/dev/null ||
			fail "missing network-root initramfs build command: $command"
	done
fi
[ -r "$power_usb_profile" ] && [ -f "$power_usb_profile" ] &&
	[ ! -L "$power_usb_profile" ] ||
	fail 'generated power/USB identity is absent or linked'
sh -n "$power_usb_profile"
[ -r "$xattr_projection" ] && [ -f "$xattr_projection" ] &&
	[ ! -L "$xattr_projection" ] ||
	fail "missing xattr projection: $xattr_projection"
if [ -z "$reviewed_verifier" ]; then
	[ -x "$verifier_builder" ] && [ -f "$verifier_builder" ] &&
		[ ! -L "$verifier_builder" ] ||
		fail 'reviewed static verifier builder is absent or linked'
else
	case $reviewed_verifier in
		/*) ;;
		*) fail 'NETWORK_ROOT_VERIFIER must be an absolute path' ;;
	esac
	[ -x "$reviewed_verifier" ] && [ -f "$reviewed_verifier" ] &&
		[ ! -L "$reviewed_verifier" ] ||
		fail 'reviewed static verifier artifact is absent or linked'
	[ "$(sha256sum "$reviewed_verifier" | cut -d ' ' -f 1)" = \
		"$reviewed_verifier_hash" ] ||
		fail 'reviewed static verifier artifact hash changed'
fi
if [ -n "$reviewed_reporter" ]; then
	case $reviewed_reporter in
		/*) ;;
		*) fail 'NETWORK_ROOT_DIAGNOSTIC_REPORTER must be an absolute path' ;;
	esac
	[ -x "$reviewed_reporter" ] && [ -f "$reviewed_reporter" ] &&
		[ ! -L "$reviewed_reporter" ] ||
		fail 'reviewed diagnostic reporter artifact is absent or linked'
	[ "$(stat -c %s "$reviewed_reporter")" -eq "$reviewed_reporter_size" ] ||
		fail 'reviewed diagnostic reporter artifact size changed'
	[ "$(sha256sum "$reviewed_reporter" | cut -d ' ' -f 1)" = \
		"$reviewed_reporter_hash" ] ||
		fail 'reviewed diagnostic reporter artifact hash changed'
	readelf -h "$reviewed_reporter" | grep -q 'Machine:.*AArch64' ||
		fail 'diagnostic reporter is not AArch64'
	if readelf -l "$reviewed_reporter" |
		grep -q 'Requesting program interpreter'; then
		fail 'diagnostic reporter is dynamically linked'
	fi
	if readelf -d "$reviewed_reporter" 2>/dev/null |
		grep -q 'Shared library:'; then
		fail 'diagnostic reporter has a shared-library dependency'
	fi
fi
[ -f "$base" ] && [ ! -L "$base" ] ||
	fail 'accepted network-root base is absent or linked'
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$accepted_base" ] ||
	fail 'accepted network-root base hash changed'
case $output in
	/*) ;;
	*) fail 'output path must be absolute' ;;
esac
output_parent=$(dirname -- "$output")
[ -d "$output_parent" ] && [ ! -L "$output_parent" ] ||
	fail 'output parent is absent or linked'
[ ! -e "$output" ] && [ ! -L "$output" ] ||
	fail 'output already exists'

stage=$(mktemp -d)
output_stage=
cleanup() {
	[ -z "$output_stage" ] || rm -f -- "$output_stage"
	rm -rf -- "$stage"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
verifier=$stage/.reviewed-persistent-root-verify
if [ -z "$reviewed_verifier" ]; then
	"$verifier_builder" "$verifier" >"$stage/.verifier-build-record" ||
		fail 'reviewed static verifier build failed'
else
	install -m 0755 "$reviewed_verifier" "$verifier"
	{
		printf 'format=rog5-reviewed-verifier-artifact-v1\n'
		printf 'sha256=%s\n' "$reviewed_verifier_hash"
	} >"$stage/.verifier-build-record"
fi
[ "$(sha256sum "$verifier" | cut -d ' ' -f 1)" = \
	"$reviewed_verifier_hash" ] ||
	fail 'selected static verifier hash changed'
readelf -h "$verifier" | grep -q 'Machine:.*AArch64' ||
	fail 'persistent-root verifier is not AArch64'
if readelf -l "$verifier" | grep -q 'Requesting program interpreter'; then
	fail 'persistent-root verifier is dynamically linked'
fi
if readelf -d "$verifier" 2>/dev/null | grep -q 'Shared library:'; then
	fail 'persistent-root verifier has a shared-library dependency'
fi
gzip -dc "$base" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
install -m 0755 "$init" "$stage/init"
install -m 0755 "$shutdown" "$stage/shutdown"
install -D -m 0755 "$charging_probe" \
	"$stage/sbin/rog5-early-charging-probe"
install -D -m 0755 "$power_observer" \
	"$stage/sbin/rog5-early-power-observer"
install -D -m 0444 "$power_usb_profile" \
	"$stage/etc/rog5/power-usb-active.sh"
if [ -n "$charge_firmware_archive" ]; then
	install -d -m 0755 "$stage/opt/rog5-charge-firmware"
	tar -xzf "$charge_firmware_archive" -C "$stage/opt/rog5-charge-firmware" \
		--no-same-owner --no-same-permissions
	firmware_manifest=$stage/.charge-firmware-manifest
	(
		cd "$stage/opt/rog5-charge-firmware"
		find . -mindepth 1 -maxdepth 1 -type f -printf '%f\n' | sort |
			while IFS= read -r name; do
				case $name in ''|*[!A-Za-z0-9._-]*) exit 1 ;; esac
				sha256sum "$name"
			done
	) >"$firmware_manifest" || fail 'charge firmware inventory is unsafe'
	[ "$(sha256sum "$firmware_manifest" | cut -d ' ' -f 1)" = \
		"$charge_firmware_tree_sha" ] || fail 'charge firmware content changed'
	rm -f "$firmware_manifest"
fi
if [ -n "$pdr_module" ]; then
	install -D -m 0644 "$pdr_module" \
		"$stage/opt/rog5-charge-modules/pdr_interface.ko"
fi
if [ -n "$charge_modules_root" ]; then
	module_list=$stage/.charge-module-list
	for module in qcom_q6v5_pas qrtr_smd qcom_pd_mapper qcom_pdr_msg \
		pmic_glink qcom_battmgr typec typec_ucsi ucsi_glink
	do
		modprobe -d "$charge_modules_root" -S "$charge_modules_release" \
			--show-depends "$module" ||
			fail "cannot resolve early charge module: $module"
	done | awk '$1 == "insmod" { print $2 }' | sort -u >"$module_list"
	[ "$(wc -l <"$module_list")" -ge 13 ] ||
		fail 'early charge module closure is incomplete'
	while IFS= read -r module_path; do
		case $module_path in "$charge_modules_root"/*) ;; *) fail 'charge module escaped its root' ;; esac
		[ -f "$module_path" ] && [ ! -L "$module_path" ] ||
			fail 'charge module is absent or linked'
		relative=${module_path#"$charge_modules_root"/}
		install -D -m 0644 "$module_path" "$stage/$relative"
	done <"$module_list"
	pdr_target=$(find "$stage/lib/modules/$charge_modules_release" -type f \
		-name pdr_interface.ko -print)
	[ "$(printf '%s\n' "$pdr_target" | awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] ||
		fail 'early charge module closure lacks one PDR path'
	install -m 0644 "$pdr_module" "$pdr_target"
	depmod -b "$stage" "$charge_modules_release"
	rm -f "$module_list"
fi
install -D -m 0755 "$verifier" "$stage/sbin/persistent-root-verify"
install -D -m 0444 "$xattr_projection" \
	"$stage/etc/rog5/nfs4-xattr-projection"
rm -f "$stage/sbin/rog5-early-target-diag"
if [ -n "$reviewed_reporter" ]; then
	install -D -m 0755 "$reviewed_reporter" \
		"$stage/sbin/rog5-early-target-diag"
fi
rm -f "$verifier" "$stage/.verifier-build-record"
rm -f "$stage"/etc/ssh/ssh_host_* "$stage/etc/machine-id" \
	"$stage/var/lib/dbus/machine-id" "$stage/root/.ssh/authorized_keys"
[ ! -e "$stage/root/.ssh/authorized_keys" ]
[ -z "$(find "$stage/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit 2>/dev/null)" ]
private_key_scan=$stage/.private-key-scan
if grep -rIl 'BEGIN .*PRIVATE KEY' "$stage" >"$private_key_scan"; then
	rm -f "$private_key_scan"
	fail 'network-root initramfs contains private key material'
else
	scan_status=$?
	rm -f "$private_key_scan"
	[ "$scan_status" -eq 1 ] ||
		fail 'network-root private-key scan failed'
fi

find "$stage" -exec touch -h -d "@$epoch" {} +
output_stage=$(mktemp "$output_parent/.network-root-initramfs.XXXXXX")
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output_stage"
NETWORK_ROOT_DIAGNOSTIC_REPORTER="$reviewed_reporter" \
	NETWORK_ROOT_EXPECT_CHARGE_FIRMWARE="$([ -n "$charge_firmware_archive" ] && printf 1 || printf 0)" \
NETWORK_ROOT_EXPECT_PDR_MODULE="$([ -n "$pdr_module" ] && printf 1 || printf 0)" \
	NETWORK_ROOT_EXPECT_CHARGE_MODULES="$([ -n "$charge_modules_root" ] && printf 1 || printf 0)" \
	"$repo/scripts/device/verify-network-root-initramfs.sh" "$output_stage"
ln "$output_stage" "$output" 2>/dev/null ||
	fail 'output appeared during build'
rm -f -- "$output_stage"
output_stage=
printf 'format=rog5-network-root-initramfs-build-v1\n'
printf 'size=%s\n' "$(stat -c %s "$output")"
printf 'sha256=%s\n' "$(sha256sum "$output" | cut -d ' ' -f 1)"
