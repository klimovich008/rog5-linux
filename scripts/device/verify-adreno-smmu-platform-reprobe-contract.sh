#!/bin/sh
set -eu

source_dir=${1:?usage: verify-adreno-smmu-platform-reprobe-contract.sh PINNED_SOURCE KERNEL_CONFIG}
kernel_config=${2:?missing accepted kernel config}
expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92

bus=$source_dir/drivers/base/bus.c
core=$source_dir/drivers/base/core.c
deferred=$source_dir/drivers/base/dd.c
bus_header=$source_dir/include/linux/device/bus.h
smmu=$source_dir/drivers/iommu/arm/arm-smmu/arm-smmu.c

[ -d "$source_dir/.git" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ]
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]

check_hash() {
	file=$1
	expected=$2
	[ -f "$file" ] && [ ! -L "$file" ]
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ]
}

check_hash "$bus" \
	ca5c7869054b603b64c21df45279decf32f540c2f29c801e851e94fe2f788a4a
check_hash "$core" \
	8810cf8a16706ef8f86fcc4944e1bfd8158012af415a6ec2e47a9bf02d9a3b09
check_hash "$deferred" \
	950d0a64be85b106837298a1c38ee4124e99071ca1f80b5f3a5184b14a4f152f
check_hash "$bus_header" \
	5169854996f5ea801f7df1d4714604483be925335f07f5f036e9ab5f50106db4
check_hash "$smmu" \
	580bcc9326837da0607e45843f4906694c28a0a5b68ca9297bc516747704d55f
check_hash "$kernel_config" \
	68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f

probe_store=$(sed -n \
	'/^static ssize_t drivers_probe_store(/,/^}$/p' "$bus")
for behavior in \
	'dev = bus_find_device_by_name(bus, NULL, buf);' \
	'if (!dev)' \
	'return -ENODEV;' \
	'if (bus_rescan_devices_helper(dev, NULL) == 0)' \
	'put_device(dev);'
do
	printf '%s\n' "$probe_store" | grep -Fq "$behavior"
done
[ "$(printf '%s\n' "$probe_store" |
	grep -Fc 'bus_rescan_devices_helper(dev, NULL)')" -eq 1 ]
if printf '%s\n' "$probe_store" |
	grep -Eq 'bus_for_each_dev|bus_rescan_devices[[:space:]]*\(|device_reprobe|device_driver_attach'
then
	echo 'FAIL drivers_probe_store acquired a broad or force-attach path' >&2
	exit 1
fi

rescan_helper=$(sed -n \
	'/^static int __must_check bus_rescan_devices_helper(/,/^}$/p' "$bus")
for behavior in \
	'if (!dev->driver)' \
	'ret = device_attach(dev);' \
	'return ret < 0 ? ret : 0;'
do
	printf '%s\n' "$rescan_helper" | grep -Fq "$behavior"
done
[ "$(printf '%s\n' "$rescan_helper" |
	grep -Fc 'device_attach(dev)')" -eq 1 ]
if printf '%s\n' "$rescan_helper" |
	grep -Eq 'bus_for_each_dev|device_driver_attach|device_reprobe|device_release_driver'
then
	echo 'FAIL exact-device rescan helper acquired a broad or detach path' >&2
	exit 1
fi

find_by_name=$(sed -n \
	'/^static inline struct device \*bus_find_device_by_name(/,/^}$/p' \
	"$bus_header")
printf '%s\n' "$find_by_name" |
	grep -Fq 'return bus_find_device(bus, start, name, device_match_name);'
match_name=$(sed -n '/^int device_match_name(/,/^}$/p' "$core")
printf '%s\n' "$match_name" |
	grep -Fq 'return sysfs_streq(dev_name(dev), name);'

for evidence in \
	'static ssize_t waiting_for_supplier_show' \
	'static DEVICE_ATTR_RO(waiting_for_supplier);' \
	'"supplier:%s:%s"' \
	'"consumer:%s:%s"'
do
	grep -Fq "$evidence" "$core"
done
for evidence in \
	'static int deferred_devs_show' \
	'dev_name(curr->device)' \
	'DEFINE_SHOW_ATTRIBUTE(deferred_devs);' \
	'CONFIG_DRIVER_DEFERRED_PROBE_TIMEOUT'
do
	grep -Fq "$evidence" "$deferred"
done

grep -Fq 'static BUS_ATTR_WO(drivers_probe);' "$bus"
grep -Fq 'if (!drv->suppress_bind_attrs)' "$bus"
grep -Fq '.suppress_bind_attrs    = true,' "$smmu"
grep -Fq 'devm_clk_bulk_get_all(dev, &smmu->clks);' "$smmu"
grep -qx 'CONFIG_DRIVER_DEFERRED_PROBE_TIMEOUT=10' "$kernel_config"
grep -qx 'CONFIG_DEBUG_FS=y' "$kernel_config"
grep -qx 'CONFIG_DEBUG_FS_ALLOW_ALL=y' "$kernel_config"

echo 'PASS pinned Linux 7.1.4 driver core exposes one exact-name unbound-device attach path; ARM SMMU force-bind is suppressed and deferred evidence is read-only'
