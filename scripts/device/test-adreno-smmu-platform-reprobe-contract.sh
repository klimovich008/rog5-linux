#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-adreno-smmu-platform-reprobe-contract.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing executable Adreno SMMU platform-reprobe verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	ca5c7869054b603b64c21df45279decf32f540c2f29c801e851e94fe2f788a4a \
	8810cf8a16706ef8f86fcc4944e1bfd8158012af415a6ec2e47a9bf02d9a3b09 \
	950d0a64be85b106837298a1c38ee4124e99071ca1f80b5f3a5184b14a4f152f \
	5169854996f5ea801f7df1d4714604483be925335f07f5f036e9ab5f50106db4 \
	580bcc9326837da0607e45843f4906694c28a0a5b68ca9297bc516747704d55f \
	68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f \
	'drivers_probe_store' \
	'bus_find_device_by_name(bus, NULL, buf)' \
	'bus_rescan_devices_helper(dev, NULL)' \
	'device_attach(dev)' \
	'device_match_name' \
	'sysfs_streq(dev_name(dev), name)' \
	'waiting_for_supplier' \
	'deferred_devs_show' \
	'CONFIG_DRIVER_DEFERRED_PROBE_TIMEOUT=10' \
	'.suppress_bind_attrs    = true' \
	'devm_clk_bulk_get_all'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL platform-reprobe verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'fastboot|adb|ssh|scp|insmod|rmmod|modprobe|/sys/bus/platform/drivers_probe|[[:space:]]mount[[:space:]]|[[:space:]]dd[[:space:]]' \
	"$verifier"
then
	echo 'FAIL platform-reprobe verifier contains a live-control path' >&2
	exit 1
fi

if [ -n "${SOURCE_DIR:-}" ] && [ -n "${KERNEL_CONFIG:-}" ]; then
	"$verifier" "$SOURCE_DIR" "$KERNEL_CONFIG"
fi

echo 'PASS exact-device platform reprobe is pinned to reviewed Linux 7.1.4 driver-core source'
