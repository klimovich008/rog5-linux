#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/persistent-slotb-loader-init
shutdown=$repo/initramfs/persistent-root-shutdown-standalone
target_init=$repo/initramfs/persistent-root-init
loader_builder=$repo/scripts/device/build-persistent-slotb-loader-initramfs.sh
target_builder=$repo/scripts/device/build-persistent-root-standalone-initramfs.sh
state_helper=$repo/initramfs/persistent-service-state
ssh_identity=$repo/initramfs/persistent-ssh-identity
ufs_module_verifier=$repo/scripts/device/verify-persistent-ufs-module-profile.sh
trial_helper=$repo/artifacts/persistent-trial-state-v1/rog5-persistent-trial-state
base=$repo/build/persistent-native-root-v8-generation233-20260828-r1/wrapper-a/rog5-kexec-stage-initramfs.cpio.gz
target_base=${1:-$repo/artifacts/persistent-native-root-v4/initramfs.cpio.gz}
high_speed_base=$repo/artifacts/local-image-direct-v49/initramfs.cpio.gz

for path in "$init" "$shutdown" "$target_init" "$loader_builder" "$target_builder" \
	"$state_helper" "$ssh_identity"; do
	[ -x "$path" ]
	sh -n "$path"
done
[ -x "$ufs_module_verifier" ]
[ -x "$trial_helper" ]
if grep -qx 'set -f' "$init"; then
	echo 'FAIL slot-B loader disables required fixed-path glob expansion' >&2
	exit 1
fi

for contract in \
	'existing-recovery' \
	'24:arch_root_a' \
	'23:userdata' \
	'18821440' \
	'408997568' \
	'209406754816' \
	'427819008' \
	'67108824' \
	'253403070464' \
	'34359717888' \
	'mount -t ext4 -o ro,noload' \
	'format=rog5-slotb-selector-v1' \
	'format=rog5-slotb-selector-v2' \
	'mode=try-once' \
	'/usr/libexec/rog5-persistent-trial-state' \
	'verify_trial_write_window' \
	'relock_all_storage' \
	'/usr/libexec/rog5-bundle-verify' \
	'/usr/sbin/kexec -c -l' \
	'disable_haven_watchdog' \
	'Failed to deactivate secure wdog' \
	'"$reboot_helper"' \
	'watchdog_seconds=180'; do
	grep -Fq "$contract" "$init"
done
grep -Fq '[ "$loader_mode" = existing-recovery ]' "$init"
grep -Fq '[ "$loader_mode" = standalone ]' "$init"
grep -Fq 'configure_loader_usb || fail usb_setup' "$init"
! grep -Eq 'curl|wget|169[.]254[.]77|ssh|scp|fastboot|adb' "$init"
for contract in \
	'format=rog5-slotb-loader-progress-v1' \
	'ROG5 slot B loader' \
	'expected_udc=a600000.dwc3' \
	'udc_class=/sys/class/udc' \
	'usb_mode=/sys/bus/platform/devices/a600000.ssusb/mode' \
	'echo peripheral >"$usb_mode"' \
	'single_expected_udc' \
	'[ "$first" = "$second" ]' \
	'[ "$(cat "$gadget/UDC")" = "$expected_udc" ]' \
	'set_stage S20 PASS storage_resolved' \
	'set_stage S40 PASS selector_verified' \
	'set_stage S65 PASS "$trial_selection_detail"' \
	'while [ "$trial_attempt" -lt 3 ]; do' \
	'# Never retry after this exact helper may publish or observe state.' \
	'set_stage S60 PASS bundle_verified' \
	'set_stage S70 PASS kexec_loaded' \
	'set_stage S80 PASS haven_disabled' \
	'set_stage S90 PASS execute' \
	'set_stage terminal FAIL "$1"'; do
	grep -Fq "$contract" "$init"
done
mode_line=$(grep -n 'echo peripheral >"$usb_mode"' "$init" | cut -d: -f1)
configfs_line=$(grep -n 'mount -t configfs configfs /sys/kernel/config' "$init" | cut -d: -f1)
bind_line=$(grep -n 'printf.*>"$gadget/UDC"' "$init" | cut -d: -f1)
[ "$mode_line" -lt "$configfs_line" ]
[ "$configfs_line" -lt "$bind_line" ]
grep -Fq '"$bb" reboot -f' "$shutdown"
! grep -Fq 'rog5-reboot-bootloader' "$shutdown"

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
awk '
	/^single_expected_udc\(\) \{/ { copy=1 }
	copy { print }
	copy && /^}/ { exit }
' "$init" >"$work/single-expected-udc.sh"
# shellcheck disable=SC1090
. "$work/single-expected-udc.sh"
expected_udc=a600000.dwc3
udc_class=$work/udc
mkdir "$udc_class"
mkdir "$udc_class/a600000.dwc3"
[ "$(single_expected_udc)" = a600000.dwc3 ]
mkdir "$udc_class/a800000.dwc3"
[ "$(single_expected_udc)" = a600000.dwc3 ]
set -f
! single_expected_udc >/dev/null
set +f
[ "$(single_expected_udc)" = a600000.dwc3 ]
mkdir "$udc_class/other-a600000.dwc3"
! single_expected_udc >/dev/null
rmdir "$udc_class/other-a600000.dwc3" "$udc_class/a600000.dwc3"
mkdir "$udc_class/a600000.usb"
! single_expected_udc >/dev/null
rmdir "$udc_class/a600000.usb"
mkdir "$udc_class/renamed-a600000.dwc3"
! single_expected_udc >/dev/null
rmdir "$udc_class/renamed-a600000.dwc3"
! single_expected_udc >/dev/null
mkdir "$udc_class/a600000.dwc3"
first=$(single_expected_udc)
rmdir "$udc_class/a600000.dwc3"
mkdir "$udc_class/a600000.usb"
! second=$(single_expected_udc)
[ "$first" = a600000.dwc3 ]

awk '
	/^select_trial_bundle\(\) \{/ { copy=1 }
	copy { print }
	copy && /^}/ { exit }
' "$init" >"$work/select-trial.sh"
cat >"$work/trial-helper" <<'EOF'
#!/bin/sh
[ "$#" -eq 6 ]
[ "$1" = decide ]
printf 'helper\n' >>"${MOCK_HELPER_LOG:?}"
case ${MOCK_DECISION:?} in
primary) printf '%s\n' "$3" ;;
fallback) printf '%s\n' "$5" ;;
fail) exit 1 ;;
*) exit 2 ;;
esac
EOF
chmod 0700 "$work/trial-helper"
run_trial_case() (
	case_name=$1
	# shellcheck disable=SC1090
	. "$work/select-trial.sh"
	disk=/dev/sda
	userdata=/dev/sda23
	userdata_mount=$work/userdata
	trial_helper=$work/trial-helper
	trial_id=1111111111111111111111111111111111111111111111111111111111111111
	primary_bundle=persistent-native-root-wifi
	primary_manifest_hash=2222222222222222222222222222222222222222222222222222222222222222
	fallback_bundle=persistent-native-root-v11
	fallback_manifest_hash=a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2
	relock_count=0
	mount_count=0
	helper_log=$work/helper-$case_name.log
	: >"$helper_log"
	MOCK_HELPER_LOG=$helper_log
	export MOCK_HELPER_LOG
	relock_all_storage() {
		relock_count=$((relock_count + 1))
		[ "$case_name:$relock_count" != cleanup-fail:2 ]
	}
	verify_trial_write_window() { :; }
	blockdev() { :; }
	mkdir() { :; }
	mount() {
		mount_count=$((mount_count + 1))
		case $case_name in
			mount-fail) return 1 ;;
			mount-retry) [ "$mount_count" -ge 3 ] ;;
			*) return 0 ;;
		esac
	}
	blkid() {
		printf '%s\n' '/dev/sda23: LABEL="rog5-linux" UUID="0892bacf-3e02-41b0-84a4-5f05c2df7ce5" TYPE="ext4"'
	}
	sync() { :; }
	umount() { :; }
	rmdir() { :; }
	log() { :; }
	sleep() { [ "$1" = 0.25 ]; }
	case $case_name in
		primary) MOCK_DECISION=primary; export MOCK_DECISION ;;
		helper-fail) MOCK_DECISION=fail; export MOCK_DECISION ;;
		mount-fail|mount-retry|cleanup-fail) MOCK_DECISION=primary; export MOCK_DECISION ;;
	esac
	if select_trial_bundle; then
		[ "$case_name" != cleanup-fail ]
		case $case_name in
			primary)
				[ "$bundle" = "$primary_bundle" ]
				[ "$trial_selection_detail" = trial-primary-a1 ]
				[ "$(wc -l <"$helper_log")" -eq 1 ]
				;;
			mount-retry)
				[ "$bundle" = "$primary_bundle" ]
				[ "$trial_selection_detail" = trial-primary-a3 ]
				[ "$mount_count" -eq 3 ]
				[ "$(wc -l <"$helper_log")" -eq 1 ]
				;;
			helper-fail)
				[ "$bundle" = "$fallback_bundle" ]
				[ "$trial_selection_detail" = trial-fallback-helper-a1 ]
				[ "$(wc -l <"$helper_log")" -eq 1 ]
				;;
			mount-fail)
				[ "$bundle" = "$fallback_bundle" ]
				[ "$trial_selection_detail" = trial-fallback-prep-mount-a3 ]
				[ "$mount_count" -eq 3 ]
				[ ! -s "$helper_log" ]
				;;
			*) [ "$bundle" = "$fallback_bundle" ] ;;
		esac
	else
		[ "$case_name" = cleanup-fail ]
	fi
)
for trial_case in primary helper-fail mount-fail mount-retry cleanup-fail; do
	run_trial_case "$trial_case"
done

if [ -f "$base" ] && [ -f "$target_base" ] && [ -f "$high_speed_base" ]; then
	: >"$work/read-selector.sh"
	for function in valid_bundle_name valid_hash read_selector; do
		awk -v fn="$function" '
		$0 == fn "() {" { copy=1 }
		copy { print }
		copy && /^}/ { exit }
		' "$init" >>"$work/read-selector.sh"
	done
	# shellcheck disable=SC1090
	. "$work/read-selector.sh"
	selector=$work/selector
	stat() {
		if [ "$1" = -c ] && [ "$2" = '%u:%g:%a:%h' ] &&
			[ "$3" = "$selector" ]; then
			mode=$(command stat -c %a "$3")
			printf '0:0:%s:1\n' "$mode"
		else
			command stat "$@"
		fi
	}
	write_selector() {
		printf '%s\n' \
			'format=rog5-slotb-selector-v1' \
			'bundle=persistent-native-root-release-v1' \
			'manifest_sha256=2b259a6e5912549dc2210d12c5f3b4da5422817720addc85e660bf9d3edf75ec' \
			>"$selector"
		chmod 0600 "$selector"
	}
	write_trial_selector() {
		printf '%s\n' \
			'format=rog5-slotb-selector-v2' \
			'trial_id=1111111111111111111111111111111111111111111111111111111111111111' \
			'primary_bundle=persistent-native-root-wifi' \
			'primary_manifest_sha256=2222222222222222222222222222222222222222222222222222222222222222' \
			'fallback_bundle=persistent-native-root-v11' \
			'fallback_manifest_sha256=a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2' \
			'mode=try-once' >"$selector"
		chmod 0600 "$selector"
	}
	write_selector
	read_selector
	[ "$bundle" = persistent-native-root-release-v1 ]
	[ "$manifest_hash" = 2b259a6e5912549dc2210d12c5f3b4da5422817720addc85e660bf9d3edf75ec ]
	write_trial_selector
	read_selector
	[ "$selector_format" = format=rog5-slotb-selector-v2 ]
	[ "$trial_id" = 1111111111111111111111111111111111111111111111111111111111111111 ]
	[ "$bundle" = persistent-native-root-wifi ]
	[ "$fallback_bundle" = persistent-native-root-v11 ]
	[ "$manifest_hash" = 2222222222222222222222222222222222222222222222222222222222222222 ]
	for mutation in duplicate-trial reordered same-bundle bad-mode; do
		write_trial_selector
		case $mutation in
			duplicate-trial) printf '%s\n' 'trial_id=3333333333333333333333333333333333333333333333333333333333333333' >>"$selector" ;;
			reordered) sed -i '3h;4{G;d};3d' "$selector" ;;
			same-bundle) sed -i 's/^fallback_bundle=.*/fallback_bundle=persistent-native-root-wifi/' "$selector" ;;
			bad-mode) sed -i 's/^mode=.*/mode=always/' "$selector" ;;
		esac
		if read_selector; then
			echo "FAIL hostile trial selector accepted: $mutation" >&2
			exit 1
		fi
	done
	for mutation in traversal zero duplicate writable; do
		write_selector
		case $mutation in
			traversal) sed -i 's/^bundle=.*/bundle=..\/escape/' "$selector" ;;
			zero) sed -i 's/^manifest_sha256=.*/manifest_sha256=0000000000000000000000000000000000000000000000000000000000000000/' "$selector" ;;
			duplicate) printf '%s\n' 'bundle=second' >>"$selector" ;;
			writable) chmod 0644 "$selector" ;;
		esac
		if read_selector; then
			echo "FAIL hostile selector accepted: $mutation" >&2
			exit 1
		fi
	done

	"$loader_builder" "$base" "$work/loader.cpio.gz" >/dev/null
	"$target_builder" "$target_base" "$work/target.cpio.gz" >/dev/null
	mkdir "$work/loader" "$work/target" "$work/high-speed-source" \
		"$work/target-high-speed"
	gzip -dc "$work/loader.cpio.gz" | (cd "$work/loader" && cpio -idm --quiet --no-absolute-filenames)
	gzip -dc "$work/target.cpio.gz" | (cd "$work/target" && cpio -idm --quiet --no-absolute-filenames)
	gzip -dc "$high_speed_base" |
		(cd "$work/high-speed-source" && cpio -idm --quiet --no-absolute-filenames)
	high_speed_modules=$work/high-speed-source/rog5-ufs-modules
	"$ufs_module_verifier" "$high_speed_modules" \
		7.1.4-g359318de534f local-write >/dev/null
	"$target_builder" "$target_base" "$work/target-high-speed.cpio.gz" \
		"$high_speed_modules" >/dev/null
	gzip -dc "$work/target-high-speed.cpio.gz" |
		(cd "$work/target-high-speed" && cpio -idm --quiet --no-absolute-filenames)
	cp "$target_init" "$work/expected-target-init"
	sed -i \
		-e 's/@EXPECTED_KERNEL_RELEASE@/7.1.4-g359318de534f/' \
		-e 's/@EXPECTED_UFS_STORAGE_MODE@/read-only/' \
		-e 's/@EXPECTED_PROBE_BOOT_ID@/staged-seal/' \
		-e 's/@EXPECTED_NATIVE_ROOT_MODE@/1/' \
		-e 's/@EXPECTED_SSH_DIAGNOSTIC_MODE@/0/' \
		-e 's/@EXPECTED_PERSISTENT_OVERLAY_MODE@/0/' \
		"$work/expected-target-init"
	! grep -Fq '@EXPECTED_' "$work/expected-target-init"
	cmp "$work/loader/init" "$init"
	cmp "$work/loader/usr/libexec/rog5-persistent-trial-state" "$trial_helper"
	cmp "$work/target/init" "$work/expected-target-init"
	! grep -Fq '@EXPECTED_' "$work/target/init"
	cmp "$work/target/shutdown" "$shutdown"
	cmp "$work/target/usr/local/sbin/rog5-persistent-state" "$state_helper"
	cmp "$work/target/usr/local/sbin/rog5-persistent-ssh-identity" "$ssh_identity"
	for module in phy-qcom-qmp-ufs.ko ufs-qcom.ko ufshcd-pltfrm.ko; do
		cmp "$work/target/rog5-ufs-modules/$module" \
			"$work/target-high-speed/rog5-ufs-modules/$module"
	done
	! cmp "$work/target/rog5-ufs-modules/ufshcd-core.ko" \
		"$work/target-high-speed/rog5-ufs-modules/ufshcd-core.ko" \
		>/dev/null 2>&1
	cmp "$work/target-high-speed/rog5-ufs-modules/ufshcd-core.ko" \
		"$high_speed_modules/ufshcd-core.ko"
	strings "$work/target-high-speed/rog5-ufs-modules/ufshcd-core.ko" |
		grep -Fqx 'ROG5 UFS bounded data-write high-speed gear switch enabled'
	[ -x "$work/loader/usr/libexec/rog5-reboot-bootloader" ]
	[ "$(stat -c %s "$work/loader.cpio.gz")" -lt 8388608 ]
fi

echo 'PASS persistent slot-B loader is local, signed-bundle-only, p24-read-only, watchdog-bounded, and standalone-reboot capable'
