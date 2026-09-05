#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
init=$repo/initramfs/alpine-charging-rescue-init
firmware_helper=$repo/initramfs/rog5-charging-firmware.sh
builder=$repo/scripts/host/build-alpine-charging-rescue.sh
bundle_verifier=$repo/tools/recovery_control/rog5-bundle-verify.c

fail() {
	echo "FAIL $*" >&2
	exit 1
}

sh -n "$init"
[[ -f $firmware_helper ]] || fail 'charging firmware helper is missing'
sh -n "$firmware_helper"
bash -n "$builder"

for required in \
	'expected_release=5.4.210-qgki-perf-gc89cd02a7dfe' \
	'rollback_seconds=30' \
	"grep -Fxc 'rog5.charging_rescue=1'" \
	"grep -Fxc 'androidboot.slot_suffix=_b'" \
	'echo b >/proc/sysrq-trigger' \
	'mkdir -p /run/sshd' \
	'expected_udc=a600000.dwc3' \
	'ip addr add 169.254.77.2/30 dev usb0' \
	'. /libexec/rog5-charging-firmware.sh' \
	'rog5_resolve_exact_partition /sys/class/block /dev modem_b 1704888 450560' \
	'expected_modem_uuid=00BC-614E' \
	'mount -t vfat -o ro,nodev,nosuid,noexec,shortname=lower,uid=1000,gid=1000,dmask=227,fmask=337' \
	'ln -s /vendor/firmware_mnt /firmware' \
	'/sys/class/power_supply/battery' \
	'current_now' \
	'voltage_now'; do
	grep -Fq "$required" "$init" || fail "init lacks $required"
done

run_mount_line=$(grep -nF 'mount -t tmpfs -o mode=0755,nosuid,nodev tmpfs /run' "$init" |
	cut -d: -f1)
run_sshd_line=$(grep -nF 'mkdir -p /run/sshd' "$init" | cut -d: -f1)
[[ -n $run_mount_line && -n $run_sshd_line && $run_mount_line -lt $run_sshd_line ]] ||
	fail '/run/sshd is hidden by the tmpfs mount'

rollback_line=$(grep -nF 'log "rollback armed for ${rollback_seconds}s"' "$init" |
	cut -d: -f1)
first_mdev_line=$(grep -nF 'mdev -s' "$init" | head -n 1 | cut -d: -f1)
[[ -n $rollback_line && -n $first_mdev_line && $rollback_line -lt $first_mdev_line ]] ||
	fail 'rollback is not armed before the first modalias scan'

diagnostic_line=$(grep -nF "log 'RAM-only diagnostic transport ready" "$init" |
	cut -d: -f1)
firmware_line=$(grep -nF 'log '\''exact modem_b firmware mounted read-only'\''' "$init" |
	cut -d: -f1)
charger_line=$(grep -nF 'load_extra q6_pdr_dlkm q6_pdr_dlkm.ko' "$init" |
	cut -d: -f1)
[[ -n $diagnostic_line && -n $charger_line && $diagnostic_line -lt $charger_line ]] ||
	fail 'diagnostic transport is not ready before charger activation'
[[ -n $firmware_line && $diagnostic_line -lt $firmware_line &&
	$firmware_line -lt $charger_line ]] ||
	fail 'exact modem firmware is not mounted between diagnostics and ADSP activation'

for forbidden in \
	'switch_root' \
	'/newroot' \
	'PARTNAME=userdata' \
	'rog5-desktop-start' \
	'NetworkManager' \
	'wifi'; do
	! grep -Fq "$forbidden" "$init" || fail "init contains forbidden $forbidden"
done

expected_order='q6_pdr_dlkm
q6_notifier_dlkm
snd_event_dlkm
apr_dlkm
adsp_loader_dlkm'
actual_order=$(sed -n 's/^load_extra \([^ ]*\) .*/\1/p' "$init")
[[ $actual_order == "$expected_order" ]] || fail 'charger module order changed'

! grep -Fq 'load_extra qti_battery_charger_main' "$init" ||
	fail 'built-in WW33 battery charger is incorrectly treated as a module'

for identity in \
	'54b8d9d23ace1126bf1059f1ab483c027b50865695c7b305a15311e30a217b33' \
	'c6dd3e4ab60f54a88cccf68f445d694449674ed4c91f777ed57fbdc0cce6befd' \
	'64db1bf572e2fb8ac77a8a79ea283e81a57ff8a9a319f0cba68da18f6a8c9841' \
	'4a62a4b83ff8948667732e55d8f2e57e575e05e9d3a3aa64b3da1dc58fd78065'; do
	grep -Fq "$identity" "$builder" || fail "builder lacks exact identity $identity"
done

for identity in \
	'rog5.charging_rescue=1' \
	'4a62a4b83ff8948667732e55d8f2e57e575e05e9d3a3aa64b3da1dc58fd78065' \
	'22bccf4d3a138cc09c1120d787a0a67a5079c6d7c78dd579468498077c58f639'; do
	grep -Fq "$identity" "$bundle_verifier" ||
		fail "stable-recovery verifier lacks exact rescue identity $identity"
done

grep -Fq "file \"\$dtb\" | grep -q 'Device Tree Blob version 17'" "$builder" ||
	fail 'builder lacks FDT v17 validation'
grep -Fq "[[ ! -e \$output && ! -e \$output.tmp ]]" "$builder" ||
	fail 'builder does not refuse output replacement'
! grep -Fq 'vermagic=5.4.210-qgki-perf SMP preempt mod_unload modversions aarch64' "$builder" ||
	fail 'builder still carries the retired build-21 module identity'
grep -Fq 'vermagic=5.4.210-qgki-perf-gc89cd02a7dfe SMP preempt mod_unload modversions aarch64' "$builder" ||
	fail 'builder lacks exact WW33 module vermagic gate'
grep -Fq 'debugfs -R "dump /lib/modules/$name' "$builder" ||
	fail 'builder does not extract exact WW33 vendor modules'

echo 'PASS charging rescue is RAM-only, headless, bounded, exact-stack, and telemetry-capable'
