#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
gate=$repo/scripts/device/run-network-root-adreno-smmu-gate.sh

[ -x "$gate" ] || {
	echo 'FAIL missing compound Adreno-SMMU live gate' >&2
	exit 1
}
sh -n "$gate"

for contract in \
	'ALLOW_MAINLINE_ADRENO_SMMU_GATE' \
	'ALLOW_MAINLINE_ADRENO_SMMU_REBOOT' \
	'7.1.4-g7a5cef0db479' \
	'/run/rog5-network-root-watchdog.pid' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'/run/rog5-gpucc-diagnostic/gpucc-sm8350.ko' \
	'/run/rog5-gpucc-diagnostic/check-network-root-adreno-smmu-baseline.sh' \
	'/run/rog5-gpucc-diagnostic/disarm-network-root-watchdog.sh' \
	'/run/rog5-gpucc-diagnostic/probe-network-root-adreno-smmu.sh' \
	9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a \
	cf08ada160359b7f193b6d4d0d8eb721a95788195432a488d383c1db498771db \
	b126182b615831e6f39784e4a2657cc60096ff906c26f1458be7d9a0d3ea065a \
	220b40676269cf36c5159a8c5fcda99512bc910c56fb2bbd28b24f745b7cb985 \
	'transition_timeout=150' \
	'/run/rog5-adreno-smmu-transition.' \
	'exec 9>/proc/sysrq-trigger' \
	'echo b >&9' \
	'setsid sh -c' \
	'ALLOW_NETWORK_ROOT_WATCHDOG_DISARM=1 "$disarm"' \
	'ALLOW_MAINLINE_ADRENO_SMMU_PROBE=1 "$probe"' \
	'systemctl reboot --no-block' \
	'transition_watchdog=armed reboot=requested'
do
	grep -Fq "$contract" "$gate" || {
		echo "FAIL compound Adreno-SMMU gate omits: $contract" >&2
		exit 1
	}
done

baseline_line=$(grep -n '^"\$baseline"$' "$gate" | cut -d: -f1)
arm_line=$(grep -n '^transition_pid=\$!$' "$gate" | cut -d: -f1)
disarm_line=$(grep -n \
	'^ALLOW_NETWORK_ROOT_WATCHDOG_DISARM=1 "\$disarm"$' "$gate" |
	cut -d: -f1)
probe_line=$(grep -n \
	'^ALLOW_MAINLINE_ADRENO_SMMU_PROBE=1 "\$probe"$' "$gate" |
	cut -d: -f1)
reboot_line=$(grep -n '^systemctl reboot --no-block$' "$gate" |
	cut -d: -f1)
[ "$baseline_line" -lt "$arm_line" ]
[ "$arm_line" -lt "$disarm_line" ]
[ "$disarm_line" -lt "$probe_line" ]
[ "$probe_line" -lt "$reboot_line" ]
[ "$(grep -Fc 'ALLOW_NETWORK_ROOT_WATCHDOG_DISARM=1 "$disarm"' \
	"$gate")" -eq 1 ]
[ "$(grep -Fxc '"$baseline"' "$gate")" -eq 1 ]
[ "$(grep -Fc 'ALLOW_MAINLINE_ADRENO_SMMU_PROBE=1 "$probe"' \
	"$gate")" -eq 1 ]

if grep -Eq \
	'rmmod|modprobe[[:space:]].*(-r|--remove)|fastboot|adb|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$gate"
then
	echo 'FAIL compound Adreno-SMMU gate controls the host or writes storage' >&2
	exit 1
fi

set +e
"$gate" >/dev/null 2>&1
missing_guards=$?
ALLOW_MAINLINE_ADRENO_SMMU_GATE=1 \
	ALLOW_MAINLINE_ADRENO_SMMU_REBOOT=unsafe \
	"$gate" >/dev/null 2>&1
invalid_reboot_guard=$?
set -e
[ "$missing_guards" -ne 0 ]
[ "$invalid_reboot_guard" -ne 0 ]

echo 'PASS compound Adreno-SMMU gate overlaps rollback watchdogs, probes once, and reboots'
