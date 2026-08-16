#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
init=$repo/initramfs/alpine-charging-rescue-init
builder=$repo/scripts/host/build-alpine-charging-rescue.sh

fail() {
	echo "FAIL $*" >&2
	exit 1
}

sh -n "$init"
bash -n "$builder"

for required in \
	'expected_release=5.4.210-qgki-perf' \
	'rollback_seconds=180' \
	"grep -Fxc 'rog5.charging_rescue=1'" \
	'echo b >/proc/sysrq-trigger' \
	'mkdir -p /run/sshd' \
	'expected_udc=a600000.dwc3' \
	'ip addr add 169.254.77.2/30 dev usb0' \
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

diagnostic_line=$(grep -nF "log 'RAM-only diagnostic transport ready" "$init" |
	cut -d: -f1)
charger_line=$(grep -nF 'load_extra q6_pdr_dlkm q6_pdr_dlkm.ko' "$init" |
	cut -d: -f1)
[[ -n $diagnostic_line && -n $charger_line && $diagnostic_line -lt $charger_line ]] ||
	fail 'diagnostic transport is not ready before charger activation'

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
adsp_loader_dlkm
qti_battery_charger_main'
actual_order=$(sed -n 's/^load_extra \([^ ]*\) .*/\1/p' "$init")
[[ $actual_order == "$expected_order" ]] || fail 'charger module order changed'

for identity in \
	'6dff1ff234fab4fa37f30ad5862cd58b693c9f4441d9ed242acbe285d559c78f' \
	'5e1512ed8d7fcc0279c5a0b8c7b0b23be0c843cc5479c596c128c5fdcd2bbc8d' \
	'64db1bf572e2fb8ac77a8a79ea283e81a57ff8a9a319f0cba68da18f6a8c9841' \
	'c37d9212ee56dc4ee9d14f4a66fd0e85f8532217d145c92e0fbe44323139654b'; do
	grep -Fq "$identity" "$builder" || fail "builder lacks exact identity $identity"
done

grep -Fq "file \"\$dtb\" | grep -q 'Device Tree Blob version 17'" "$builder" ||
	fail 'builder lacks FDT v17 validation'
grep -Fq "[[ ! -e \$output && ! -e \$output.tmp ]]" "$builder" ||
	fail 'builder does not refuse output replacement'
grep -Fq 'vermagic=5.4.210-qgki-perf SMP preempt mod_unload modversions aarch64' "$builder" ||
	fail 'builder lacks exact module vermagic gate'

echo 'PASS charging rescue is RAM-only, headless, bounded, exact-stack, and telemetry-capable'
