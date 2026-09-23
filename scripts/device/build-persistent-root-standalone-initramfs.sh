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
power_loader=$repo/scripts/device/load-persistent-root-power-usb.sh
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
# Production mode replaces every loose release-bound module with one depmod
# tree for 7.1.4-rog5-production. The stage loaders then use modprobe. The
# native Wi-Fi payload carries its own release-bound modules and is removed:
# the first production boot is headless.
production_package=${PRODUCTION_MODULE_PACKAGE:-}
production_package_sha256=${PRODUCTION_MODULE_PACKAGE_SHA256:-}
production_no_autoload=etc/modprobe.d/rog5-production-no-autoload.conf
# Optional pinned firmware for explicit post-boot steps (e.g. the stock A660
# SQE/GMU/zap files). It lands in subdirectories of the charge firmware tree,
# which the power loader copies to firmware_class.path; its top-level
# 29-file ADSP inventory is unchanged.
production_firmware=${PRODUCTION_EXTRA_FIRMWARE:-}
production_firmware_sha256=${PRODUCTION_EXTRA_FIRMWARE_SHA256:-}
# Optional try-once commit kit that makes this bundle the phone's default:
# the 4-line trial descriptor (same identity as the installed selector), the
# tracked trial-state helper and the per-boot commit unit.
production_trial=${PRODUCTION_TRIAL_DESCRIPTOR:-}
production_wifi=${PRODUCTION_WIFI_KIT:-}
production_wifi_sha256=${PRODUCTION_WIFI_KIT_SHA256:-}
production_trial_sha256=${PRODUCTION_TRIAL_DESCRIPTOR_SHA256:-}
epoch=1681862400

case $persistent_overlay_mode in 0|1) ;; *)
	echo 'FAIL PERSISTENT_ROOT_OVERLAY must be 0 or 1' >&2
	exit 1
esac
# Exact production releases with a build policy in configs/kernel; an upgrade
# adds its release here. case matches the whole string (no newline tricks).
production_release() {
	case $1 in
		7.1.4-rog5-production|7.2.7-rog5-production) return 0 ;;
		*) return 1 ;;
	esac
}
production_release "$expected_release" ||
printf '%s\n' "$expected_release" | grep -Eq '^7[.]1[.]4-g[0-9a-f]{12}$' || {
	echo 'FAIL invalid expected standalone kernel release' >&2
	exit 1
}

install_platform_kit() {
	kit=$root/rog5-platform
	[ ! -e "$kit" ] && [ ! -L "$kit" ] || return 1
	install -d -m 0700 "$kit" &&
		install -m 0444 "$repo/configs/production/boot-modules.list" "$kit/boot-modules" &&
		install -m 0755 "$repo/initramfs/production-platform-modules" "$kit/modules" &&
		install -m 0755 "$repo/initramfs/production-rtc-time" "$kit/rtc-time" &&
		install -m 0644 "$repo/configs/systemd/rog5-watchdog.conf" "$kit/rog5-watchdog.conf" || return 1
	for unit in rog5-platform-modules.service rog5-rtc-time.service \
		rog5-rtc-time-save.service rog5-rtc-time-save.path; do
		install -m 0644 "$repo/configs/systemd/$unit" "$kit/$unit" || return 1
	done
	# Every listed boot module must exist in the production tree.
	sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "$kit/boot-modules" | while read -r name params; do
		# modprobe treats - and _ alike; match the file either way.
		[ -n "$(find "$root/lib/modules/$expected_release" -name "$(printf '%s' "$name" | tr _- '??').ko*" | head -n 1)" ] || {
			echo "FAIL boot module $name is not in the production tree" >&2
			exit 1
		}
	done
}

install_wifi_kit() {
	# The pinned Wi-Fi payload (firmware, musl wpa_supplicant and iw) plus the
	# repo's radio script and units. Every payload file is listed in SHA256SUMS.
	source_dir=$1
	[ -d "$source_dir" ] && [ ! -L "$source_dir" ] && [ -f "$source_dir/SHA256SUMS" ] || return 1
	[ "$(sha256sum "$source_dir/SHA256SUMS" | cut -d ' ' -f 1)" = "$production_wifi_sha256" ] || return 1
	[ -z "$(find "$source_dir" ! -type f ! -type d -print -quit)" ] || return 1
	[ -z "$(find "$source_dir" -perm /6000 -print -quit)" ] || return 1
	(cd "$source_dir" && sha256sum -c --quiet SHA256SUMS) || return 1
	[ "$(find "$source_dir" -type f ! -name SHA256SUMS | wc -l)" -eq "$(wc -l <"$source_dir/SHA256SUMS")" ] || return 1
	kit=$root/rog5-wifi
	[ ! -e "$kit" ] && [ ! -L "$kit" ] || return 1
	install -d -m 0700 "$kit" || return 1
	while read -r _ relative; do
		case $relative in
			firmware/*|wpa-userspace/*|wifi-userspace/*) ;;
			*) return 1 ;;
		esac
		case $relative in /*|*..*) return 1 ;; esac
		mode=0644
		[ -x "$source_dir/$relative" ] && mode=0755
		install -D -m "$mode" "$source_dir/$relative" "$kit/$relative" || return 1
	done <"$source_dir/SHA256SUMS"
	for dir in firmware wpa-userspace wifi-userspace; do
		[ -d "$kit/$dir" ] || return 1
	done
	install -m 0755 "$repo/initramfs/production-wifi" "$kit/wifi" || return 1
	for unit in rog5-wifi-radio.service rog5-wifi-wpa.service rog5-wifi-dhcp.service; do
		install -m 0644 "$repo/configs/systemd/$unit" "$kit/$unit" || return 1
	done
}

install_production_trial() {
	descriptor=$1
	[ -f "$descriptor" ] && [ ! -L "$descriptor" ] || return 1
	[ "$(sha256sum "$descriptor" | cut -d ' ' -f 1)" = "$production_trial_sha256" ] || return 1
	[ "$(wc -l <"$descriptor")" -eq 4 ] &&
		[ "$(sed -n 1p "$descriptor")" = format=rog5-persistent-wifi-health-v1 ] &&
		[ "$(sed -n 4p "$descriptor")" = mode=try-once ] || return 1
	sed -n 2p "$descriptor" | grep -Eqx 'trial_id=[0-9a-f]{64}' &&
		sed -n 3p "$descriptor" | grep -Eqx 'primary_bundle=[a-z0-9][a-z0-9._-]{0,63}' &&
		! grep -q '[.][.]' "$descriptor" || return 1
	helper=$repo/$(cat "$repo/configs/persistent-trial-helper.path")
	(cd "$(dirname "$helper")" && sha256sum -c --quiet SHA256SUMS) || return 1
	kit=$root/rog5-production-trial
	[ ! -e "$kit" ] && [ ! -L "$kit" ] || return 1
	install -d -m 0700 "$kit" &&
		install -m 0444 "$descriptor" "$kit/trial-descriptor" &&
		install -m 0755 "$helper" "$kit/trial-state" &&
		install -m 0755 "$repo/initramfs/production-trial-commit" "$kit/commit" &&
		install -m 0644 "$repo/configs/systemd/rog5-production-trial-commit.service" \
			"$kit/rog5-production-trial-commit.service"
}

if [ -n "$production_package" ]; then
	production_release "$expected_release" &&
		printf '%s\n' "$production_package_sha256" | grep -Eqx '[0-9a-f]{64}' &&
		[ -z "$ufs_modules" ] && [ -z "$power_modules" ] || {
		echo 'FAIL production module tree needs the production release, its pinned package hash and no loose module sets' >&2
		exit 1
	}
fi
[ -z "$production_wifi" ] || [ -n "$production_package" ] || {
	echo 'FAIL a production Wi-Fi kit needs the production module tree' >&2
	exit 1
}
[ -z "$production_trial" ] || [ -n "$production_package" ] || {
	echo 'FAIL a production trial kit needs the production module tree' >&2
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

install_production_module_tree() {
	package=$1
	[ -f "$package" ] && [ ! -L "$package" ] || return 1
	[ "$(sha256sum "$package" | cut -d ' ' -f 1)" = "$production_package_sha256" ] || return 1
	tree=$root/lib/modules/$expected_release
	[ ! -e "$tree" ] && [ ! -L "$tree" ] || return 1
	# Exactly one release tree of regular files; no links, devices or escapes.
	tar -tvzf "$package" >"$work/package-listing" || return 1
	! grep -Ev '^[-d]' "$work/package-listing" | grep -q . || return 1
	tar -tzf "$package" >"$work/package-members" || return 1
	! grep -Evx "(lib/|lib/modules/|lib/modules/$expected_release/.*)" \
		"$work/package-members" | grep -q . || return 1
	! grep -Fq '..' "$work/package-members" || return 1
	mkdir -p "$root/lib/modules" || return 1
	tar -xzf "$package" -C "$root" --no-same-owner || return 1
	[ -f "$tree/modules.dep" ] && [ ! -L "$tree/modules.dep" ] || return 1
	[ -z "$(find "$tree" ! -type f ! -type d -print -quit)" ] || return 1
	find "$tree" -type f -name '*.ko' >"$work/production-modules"
	[ -s "$work/production-modules" ] || return 1
	while IFS= read -r module; do
		readelf -h "$module" | grep -q 'Type:.*REL (Relocatable file)' || return 1
		readelf -h "$module" | grep -q 'Machine:.*AArch64' || return 1
		[ "$(modinfo -F vermagic "$module" | awk '{print $1}')" = "$expected_release" ] || return 1
		# Production profile: CONFIG_DEBUG_INFO_NONE, no MODVERSIONS.
		! readelf -SW "$module" | grep -Eq '[.]BTF[[:space:]]|__versions' || return 1
	done <"$work/production-modules"
	for loaded in mdt_loader qcom_q6v5_pas ufs_qcom ufshcd_core ufshcd_pltfrm \
		phy_qcom_qmp_ufs ucsi_glink qcom_battmgr; do
		grep -q "/$(printf '%s' "$loaded" | sed 's/_/[-_]/g')[.]ko:" "$tree/modules.dep" ||
			return 1
	done
	find "$tree" -exec chmod u=rwX,go=rX {} + || return 1
	install -d -m 0755 "$root/etc/modprobe.d" || return 1
	[ ! -e "$root/$production_no_autoload" ] || return 1
	cat >"$root/$production_no_autoload" <<'EOF_BLACKLIST' || return 1
# Display, GPU, touch and Wi-Fi drivers load only through explicit,
# supervised steps, never through alias autoloading of the production tree.
blacklist msm
blacklist gpucc_sm8350
blacklist panel_asus_rog5_ams678
blacklist qcom_refgen_regulator
blacklist rog5_fts3658u
blacklist ath11k_pci
blacklist ath11k_ahb
EOF_BLACKLIST
	chmod 0644 "$root/$production_no_autoload"
}

install_production_firmware() {
	source_dir=$1
	[ -d "$source_dir" ] && [ ! -L "$source_dir" ] && [ -f "$source_dir/SHA256SUMS" ] || return 1
	[ "$(sha256sum "$source_dir/SHA256SUMS" | cut -d ' ' -f 1)" = "$production_firmware_sha256" ] || return 1
	[ -z "$(find "$source_dir" ! -type f ! -type d -print -quit)" ] || return 1
	(cd "$source_dir" && sha256sum -c --quiet SHA256SUMS) || return 1
	[ "$(find "$source_dir" -type f ! -name SHA256SUMS | wc -l)" -eq \
		"$(wc -l <"$source_dir/SHA256SUMS")" ] || return 1
	target_dir=$root/opt/rog5-charge-firmware
	[ -d "$target_dir" ] && [ ! -L "$target_dir" ] || return 1
	while read -r _ relative; do
		case $relative in
			*/*) ;;
			*) return 1 ;;
		esac
		case $relative in /*|*..*) return 1 ;; esac
		[ ! -e "$target_dir/$relative" ] || return 1
		install -D -m 0644 "$source_dir/$relative" "$target_dir/$relative" || return 1
	done <"$source_dir/SHA256SUMS"
}

unchanged_files() {
	set -- ! -path ./init ! -path ./shutdown \
		! -path ./sbin/rog5-load-persistent-power-usb \
		! -path ./usr/local/sbin/rog5-p2-attest \
		! -path ./usr/local/sbin/rog5-persistent-state \
		! -path ./usr/local/sbin/rog5-persistent-ssh-identity \
		! -path ./usr/local/sbin/rog5-startup-observer \
		! -path ./usr/local/sbin/rog5-persistent-tailscale \
		! -path ./usr/local/sbin/rog5-persistent-keyring \
		! -path ./usr/local/share/rog5/rog5-package-keyring.service \
		! -path ./rog5-ufs-modules/ufshcd-core.ko
	if [ -n "$power_modules" ]; then
		set -- "$@" ! -path './rog5-ufs-modules/*' \
			! -path './rog5-power-usb-modules/*'
	fi
	if [ -n "$production_package" ]; then
		set -- "$@" ! -path './rog5-ufs-modules/*' \
			! -path './rog5-power-usb-modules/*' \
			! -path './rog5-reboot-mode-modules/*' \
			! -path './rog5-native-wifi/*' \
			! -path "./lib/modules/$expected_release/*" \
			! -path "./$production_no_autoload"
	fi
	if [ -n "$production_firmware" ]; then
		set -- "$@" ! -path './opt/rog5-charge-firmware/*/*'
	fi
	if [ -n "$production_trial" ]; then
		set -- "$@" ! -path './rog5-production-trial/*'
	fi
	if [ -n "$production_package" ]; then
		set -- "$@" ! -path './rog5-platform/*'
	fi
	if [ -n "$production_wifi" ]; then
		set -- "$@" ! -path './rog5-wifi/*'
	fi
	find . -type f "$@" -print0 | LC_ALL=C sort -z | xargs -0 sha256sum
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
	[ -x "$ufs_module_verifier" ] && [ -x "$power_loader" ]
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
# Existing qualified power firmware/modules are retained; pair the current
# early safety gate with the refreshed init/attestation instead of old script.
if [ -e "$root/sbin/rog5-load-persistent-power-usb" ]; then
	[ -f "$root/sbin/rog5-load-persistent-power-usb" ] &&
		[ ! -L "$root/sbin/rog5-load-persistent-power-usb" ]
	install -m 0755 "$power_loader" "$root/sbin/rog5-load-persistent-power-usb"
fi
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
install -D -m 0755 "$repo/initramfs/persistent-startup-observer" \
	"$root/usr/local/sbin/rog5-startup-observer"
install -D -m 0755 "$tailscale_runtime" \
	"$root/usr/local/sbin/rog5-persistent-tailscale"
# Refreshed init requires these paired inputs even when the retained base
# predates package-keyring startup. No key material is generated by packaging.
install -D -m 0755 "$repo/initramfs/persistent-package-keyring" \
	"$root/usr/local/sbin/rog5-persistent-keyring"
install -D -m 0644 "$repo/configs/systemd/rog5-package-keyring.service" \
	"$root/usr/local/share/rog5/rog5-package-keyring.service"
if [ -n "$production_package" ]; then
	rm -rf -- "$root/rog5-ufs-modules" "$root/rog5-power-usb-modules" \
		"$root/rog5-reboot-mode-modules" "$root/rog5-native-wifi"
	install_production_module_tree "$production_package" || {
		echo 'FAIL production module tree' >&2
		exit 1
	}
	if [ -n "$production_firmware" ]; then
		printf '%s\n' "$production_firmware_sha256" | grep -Eqx '[0-9a-f]{64}' &&
			install_production_firmware "$production_firmware" || {
			echo 'FAIL production extra firmware' >&2
			exit 1
		}
	fi
	install_platform_kit || {
		echo 'FAIL production platform kit' >&2
		exit 1
	}
	if [ -n "$production_wifi" ]; then
		install_wifi_kit "$production_wifi" || {
			echo 'FAIL production Wi-Fi kit' >&2
			exit 1
		}
	fi
	if [ -n "$production_trial" ]; then
		install_production_trial "$production_trial" || {
			echo 'FAIL production trial kit' >&2
			exit 1
		}
	fi
elif [ -n "$power_modules" ]; then
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
# The bundle verifier requires strcmp member order (C collation).
(cd "$root" && find . -mindepth 1 -print0 | LC_ALL=C sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output.tmp"
mv -T "$output.tmp" "$output"
gzip -t "$output"
sha256sum "$output"
