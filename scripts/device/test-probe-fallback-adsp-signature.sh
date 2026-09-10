#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
probe=$repo/scripts/device/probe-fallback-adsp-signature.sh

[ -x "$probe" ]
sh -n "$probe"

for contract in \
	'ALLOW_FALLBACK_ADSP_PROBE' \
	'5.4.134-qgki-perf-00001-g6c308144c23e' \
	'/dev/subsys_adsp' \
	'/sys/devices/platform/soc/17300000.qcom,lpass/subsys5' \
	'30889541' \
	'8628' \
	'15473660' \
	'/run/rog5-fallback-adsp-probe.XXXXXX' \
	'exec 9>/proc/sysrq-trigger' \
	'echo b >&9' \
	'kill -STOP "-$watchdog_pid"' \
	'kill -KILL "-$watchdog_pid"' \
	'exec 9</dev/subsys_adsp' \
	'exec 9<&-' \
	'stock ADSP did not reach ONLINE' \
	'stock ADSP did not return to OFFLINE' \
	'probe_safe=1'
do
	grep -Fq "$contract" "$probe" || {
		echo "FAIL fallback ADSP probe contract missing: $contract" >&2
		exit 1
	}
done

guard_line=$(grep -n 'ALLOW_FALLBACK_ADSP_PROBE' "$probe" |
	head -n1 | cut -d: -f1)
watchdog_line=$(grep -n '^setsid sh -c' "$probe" | cut -d: -f1)
open_line=$(grep -n '^if ! exec 9</dev/subsys_adsp' "$probe" | cut -d: -f1)
close_line=$(grep -n '^exec 9<&-$' "$probe" | cut -d: -f1)
safe_line=$(grep -n '^probe_safe=1$' "$probe" | cut -d: -f1)
[ "$guard_line" -lt "$watchdog_line" ]
[ "$watchdog_line" -lt "$open_line" ]
[ "$open_line" -lt "$close_line" ]
[ "$close_line" -lt "$safe_line" ]

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount|umount|hwclock|/dev/rtc|/dev/block|/sys/module/firmware_class/parameters/path|cp[[:space:]]|mv[[:space:]]' \
	"$probe"; then
	echo 'FAIL fallback ADSP probe can flash, mount, write storage/RTC, or replace firmware' >&2
	exit 1
fi

set +e
"$probe" >/dev/null 2>&1
missing_guard=$?
ALLOW_FALLBACK_ADSP_PROBE=1 ROG5_PROBE_TIMEOUT=invalid \
	"$probe" >/dev/null 2>&1
invalid_timeout=$?
set -e
[ "$missing_guard" -ne 0 ]
[ "$invalid_timeout" -ne 0 ]

echo 'PASS fallback ADSP probe is exact-kernel, exact-firmware, open/close-only, and rollback-guarded'
