#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
baseline=$repo/scripts/device/check-network-root-gpucc-confirmation-baseline.sh

[ -x "$baseline" ]
sh -n "$baseline"

for contract in \
	'7.1.4-g7a5cef0db479' \
	'systemd-udev-trigger.service' \
	'systemd-modules-load.service' \
	'/run/rog5-network-root-watchdog.pid' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'rog5_qcom_cc_probe_trace' \
	'rog5_ccf_register_trace' \
	'rog5_rcg2_parent_trace' \
	'trace_prefix=$parameter=' \
	'[ "$trace_count" -eq 0 ]' \
	'[ "$(cat "$trace_path")" = N ]' \
	'[ "$(stat -c %a "$trace_path")" = 400 ]' \
	'findmnt -n -o SOURCE /.rog5/root-ro' \
	'169.254.77.1:/' \
	'physical block device is present' \
	'block-backed mount is present' \
	'/sys/class/net/usb0/carrier' \
	'/soc@0/clock-controller@3d90000' \
	'soc@0/gpu@3d00000' \
	'soc@0/gmu@3d6a000' \
	'soc@0/iommu@3da0000' \
	'soc@0/ufshc@1d84000' \
	'soc@0/remoteproc@3000000' \
	'/sys/module/gpucc_sm8350' \
	'/dev/dri' \
	'Kernel panic|Oops:|BUG:' \
	'thermal_count' \
	'module_files' \
	'sleep 12' \
	'pstore_records'
do
	grep -Fq "$contract" "$baseline" || {
		echo "FAIL confirmation baseline omits: $contract" >&2
		exit 1
	}
done

trace_line=$(grep -n 'trace_prefix=$parameter=' "$baseline" |
	head -n1 | cut -d: -f1)
storage_line=$(grep -n 'physical block device is present' "$baseline" |
	head -n1 | cut -d: -f1)
quiet_line=$(grep -n '^sleep 12$' "$baseline" | cut -d: -f1)
[ "$trace_line" -lt "$storage_line" ]
[ "$storage_line" -lt "$quiet_line" ]

if grep -Eq '^[[:space:]]*(fastboot|mount|umount|modprobe|insmod|rmmod)([[:space:]]|$)|fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|echo[[:space:]].*>[[:space:]]*/(sys|proc|dev)/|tee[[:space:]].*/(sys|proc|dev)/' \
	"$baseline"
then
	echo 'FAIL confirmation baseline contains a control or persistent-write path' >&2
	exit 1
fi

echo 'PASS trace-free confirmation baseline is read-only, watchdog-first, zero-storage, and consumer-isolated'
