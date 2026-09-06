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
platform=$source_dir/drivers/base/platform.c
device_header=$source_dir/include/linux/device.h
vsprintf=$source_dir/lib/vsprintf.c
of_platform=$source_dir/drivers/of/platform.c

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
check_hash "$platform" \
	c1967f53f66da20c515d32ca3242bd6f365b31f2678f7125bf71cc16ed56a258
check_hash "$device_header" \
	68ad17f3670b7fcedbfa70e8cab1b2044dff1e7525697efc953527fec2825fbe
check_hash "$vsprintf" \
	314241c733f99bf8b45e64c173d78b1449b4da3fdad90a63500166376d2774eb
check_hash "$of_platform" \
	821937acef295d986caa4470166571b0d18cef2a2f9d1a730e1d0cb4cec70131
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

override_show=$(sed -n \
	'/^static ssize_t driver_override_show(/,/^}$/p' "$bus")
printf '%s\n' "$override_show" |
	grep -Fq 'return sysfs_emit(buf, "%s\n", dev->driver_override.name);'
[ "$(printf '%s\n' "$override_show" |
	grep -Fc 'sysfs_emit(buf, "%s\n", dev->driver_override.name)')" -eq 1 ]

of_alloc=$(sed -n '/^struct platform_device \*of_device_alloc(/,/^}$/p' \
	"$of_platform")
printf '%s\n' "$of_alloc" |
	grep -Fq 'dev = platform_device_alloc("", PLATFORM_DEVID_NONE);'
platform_alloc=$(sed -n \
	'/^struct platform_device \*platform_device_alloc(/,/^}$/p' "$platform")
printf '%s\n' "$platform_alloc" |
	grep -Fq 'pa = kzalloc(sizeof(*pa) + strlen(name) + 1, GFP_KERNEL);'
if printf '%s\n' "$platform_alloc" | grep -Fq 'driver_override'; then
	echo 'FAIL platform allocation acquired an override initializer' >&2
	exit 1
fi

pointer_message=$(sed -n \
	'/^static const char \*check_pointer_msg(/,/^}$/p' "$vsprintf")
for behavior in \
	'if (!ptr)' \
	'return "(null)";'
do
	printf '%s\n' "$pointer_message" | grep -Fq "$behavior"
done
string_formatter=$(sed -n \
	'/^char \*string(char \*buf, char \*end, const char \*s,/,/^}$/p' \
	"$vsprintf")
printf '%s\n' "$string_formatter" |
	grep -Fq 'if (check_pointer(&buf, end, s, spec))'

has_override=$(sed -n \
	'/^static inline bool device_has_driver_override(/,/^}$/p' \
	"$device_header")
printf '%s\n' "$has_override" |
	grep -Fq 'return !!dev->driver_override.name;'
match_override=$(sed -n \
	'/^static inline int device_match_driver_override(/,/^}$/p' \
	"$device_header")
for behavior in \
	'if (dev->driver_override.name)' \
	'return !strcmp(dev->driver_override.name, drv->name);' \
	'return -1;'
do
	printf '%s\n' "$match_override" | grep -Fq "$behavior"
done
platform_match=$(sed -n '/^static int platform_match(/,/^}$/p' "$platform")
for behavior in \
	'ret = device_match_driver_override(dev, drv);' \
	'if (ret >= 0)' \
	'return ret;' \
	'if (of_driver_match_device(dev, drv))'
do
	printf '%s\n' "$platform_match" | grep -Fq "$behavior"
done

set_override=$(sed -n \
	'/^int __device_set_driver_override(/,/^}$/p' "$deferred")
for behavior in \
	'const char *new = NULL, *old;' \
	'if (len) {' \
	'new = kstrndup(s, len, GFP_KERNEL);' \
	'dev->driver_override.name = new;'
do
	printf '%s\n' "$set_override" | grep -Fq "$behavior"
done

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

echo 'PASS pinned Linux 7.1.4 source proves OF platform allocation starts with a NULL override, sysfs emits exact (null), normal OF matching remains enabled, and one exact-name unbound-device attach is available'
