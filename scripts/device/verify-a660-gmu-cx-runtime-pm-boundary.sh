#!/bin/sh
set -eu

source_dir=${1:?usage: verify-a660-gmu-cx-runtime-pm-boundary.sh PINNED_SOURCE}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
v9_report=$repo/test-results/2026-07-27-a660-gmu-resume-entry-v9-live-accepted.md
v9_contract=$repo/scripts/device/test-a660-gmu-resume-entry-v9-root-contract.sh

expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
expected_v9_report=57af6b4d0ddf6faaa708e7b409197dcf7aa8fcdb52a5a9612b59094aebc9dd2c
expected_v9_contract=9d3ec22867f175831716c7742c6fe89b796e704594790844a5e419a8466b9d0e

a6xx_gmu=$source_dir/drivers/gpu/drm/msm/adreno/a6xx_gmu.c
pm_runtime_h=$source_dir/include/linux/pm_runtime.h
runtime_c=$source_dir/drivers/base/power/runtime.c
pmdomain_core=$source_dir/drivers/pmdomain/core.c
rpmhpd=$source_dir/drivers/pmdomain/qcom/rpmhpd.c

fail() {
	echo "FAIL $*" >&2
	exit 1
}

check_hash() {
	file=$1
	expected=$2
	label=$3
	[ -f "$file" ] && [ ! -L "$file" ] && [ -r "$file" ] ||
		fail "$label is missing, linked, or unreadable"
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] ||
		fail "$label hash mismatch: expected $expected, got $actual"
}

line_once() {
	text=$1
	needle=$2
	label=$3
	stats=$(printf '%s\n' "$text" |
		awk -v needle="$needle" '
			index($0, needle) { count++; line = NR }
			END { print count + 0 ":" line + 0 }
		')
	count=${stats%%:*}
	line=${stats#*:}
	[ "$count" -eq 1 ] ||
		fail "$label count is $count, expected 1"
	printf '%s\n' "$line"
}

require_text() {
	text=$1
	needle=$2
	label=$3
	printf '%s\n' "$text" | grep -Fq "$needle" ||
		fail "$label is missing"
}

require_file_text() {
	file=$1
	needle=$2
	label=$3
	grep -Fq "$needle" "$file" ||
		fail "$label is missing"
}

for command in awk cut git grep sed sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done

[ -d "$source_dir" ] || fail "missing source directory: $source_dir"
[ "$(git -C "$source_dir" rev-parse --is-inside-work-tree)" = true ] ||
	fail 'source is not a Git worktree'
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ] ||
	fail 'pinned source commit changed'
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ] ||
	fail 'pinned source tree changed'
[ -z "$(git -C "$source_dir" status --porcelain)" ] ||
	fail 'pinned source worktree is not clean'

check_hash "$v9_report" "$expected_v9_report" \
	'accepted A660 GMU resume-entry v9 report'
check_hash "$v9_contract" "$expected_v9_contract" \
	'A660 GMU resume-entry v9 root contract'
if [ "${SKIP_V9_UMBRELLA_RUN:-0}" != 1 ]; then
	"$v9_contract" >/dev/null
fi

check_hash "$a6xx_gmu" \
	97b2fc130862f00445b509855b16121b2eba6e5a5228f92457c2923297fd4999 \
	'a6xx_gmu.c'
check_hash "$pm_runtime_h" \
	1c1383101d72ce3028df6d9ad3640c2020a041f5c1820b1698d1657b648b04f6 \
	'pm_runtime.h'
check_hash "$runtime_c" \
	86a4ab8982d610b0ff1a1eb998adaf99a5f914833a56e70fb62efda2764af566 \
	'runtime.c'
check_hash "$pmdomain_core" \
	2326e3de634eefe0468dfe03e5c11650f5e014fda08923861154d9a19d7f9d8e \
	'pmdomain core.c'
check_hash "$rpmhpd" \
	b8ad1677950edd4f8e372a59b8027282751434afb52f71f89151b978c89c6d18 \
	'rpmhpd.c'

gmu_init=$(sed -n '/^int a6xx_gmu_init(/,/^}/p' "$a6xx_gmu")
gmu_resume=$(sed -n '/^int a6xx_gmu_resume(/,/^}/p' "$a6xx_gmu")
rpm_get_suppliers=$(sed -n '/^static int rpm_get_suppliers(/,/^}/p' \
	"$runtime_c")
rpm_release_supplier=$(sed -n \
	'/^void pm_runtime_release_supplier(/,/^}/p' "$runtime_c")
rpm_put_suppliers=$(sed -n \
	'/^static void __rpm_put_suppliers(/,/^}/p' "$runtime_c")
rpm_suspend_suppliers=$(sed -n \
	'/^static void rpm_suspend_suppliers(/,/^}/p' "$runtime_c")
rpm_callback=$(sed -n '/^static int __rpm_callback(/,/^}/p' "$runtime_c")
rpm_suspend=$(sed -n \
	'/^static int rpm_suspend(struct device \*dev, int rpmflags)$/,/^}/p' \
	"$runtime_c")
runtime_resume_core=$(sed -n '/^int __pm_runtime_resume(/,/^}/p' "$runtime_c")
runtime_suspend_core=$(sed -n \
	'/^int __pm_runtime_suspend(/,/^}/p' "$runtime_c")
genpd_attach=$(sed -n \
	'/^struct device \*genpd_dev_pm_attach_by_id(/,/^}/p' "$pmdomain_core")
genpd_resume=$(sed -n \
	'/^static int genpd_runtime_resume(/,/^}/p' "$pmdomain_core")
genpd_suspend=$(sed -n \
	'/^static int genpd_runtime_suspend(struct device \*dev)$/,/^}/p' \
	"$pmdomain_core")
rpmhpd_on=$(sed -n '/^static int rpmhpd_power_on(/,/^}/p' "$rpmhpd")
rpmhpd_off=$(sed -n '/^static int rpmhpd_power_off(/,/^}/p' "$rpmhpd")

for block in "$gmu_init" "$gmu_resume" "$rpm_get_suppliers" \
	"$rpm_release_supplier" "$rpm_put_suppliers" \
	"$rpm_suspend_suppliers" "$rpm_callback" "$rpm_suspend" \
	"$runtime_resume_core" "$runtime_suspend_core" "$genpd_attach" \
	"$genpd_resume" "$genpd_suspend" "$rpmhpd_on" "$rpmhpd_off"
do
	[ -n "$block" ] || fail 'one or more runtime-PM blocks are missing'
done

a660_line=$(line_once "$gmu_init" \
	'adreno_is_a660_family(adreno_gpu)' 'A660 full-GMU selection')
enable_line=$(line_once "$gmu_init" 'pm_runtime_enable(gmu->dev);' \
	'GMU runtime-PM enable')
cx_attach_line=$(line_once "$gmu_init" \
	'dev_pm_domain_attach_by_name(gmu->dev, "cx");' \
	'GMU CX-domain attachment')
cx_link_line=$(line_once "$gmu_init" \
	'device_link_add(gmu->dev, gmu->cxpd, DL_FLAG_PM_RUNTIME);' \
	'GMU-to-CX runtime-PM device link')
gx_attach_line=$(line_once "$gmu_init" \
	'dev_pm_domain_attach_by_name(gmu->dev, "gx");' \
	'separate GMU GX-domain attachment')
initialized_line=$(line_once "$gmu_init" 'gmu->initialized = true;' \
	'GMU initialized state')
if [ "$enable_line" -ge "$cx_attach_line" ] ||
	[ "$cx_attach_line" -ge "$cx_link_line" ] ||
	[ "$cx_link_line" -ge "$gx_attach_line" ] ||
	[ "$gx_attach_line" -ge "$initialized_line" ] ||
	[ "$a660_line" -ge "$initialized_line" ]
then
	fail 'A660 GMU CX/GX initialization topology changed'
fi
if printf '%s\n' "$gmu_init" |
	grep -Fq 'device_link_add(gmu->dev, gmu->gxpd'
then
	fail 'GX unexpectedly became a runtime-PM supplier of the GMU device'
fi

guard_line=$(line_once "$gmu_resume" 'if (WARN(!gmu->initialized,' \
	'GMU initialized guard')
hung_line=$(line_once "$gmu_resume" 'gmu->hung = false;' \
	'first GMU software mutation')
consumer_get_line=$(line_once "$gmu_resume" \
	'pm_runtime_get_sync(gmu->dev);' 'GMU/CX runtime-PM get')
gx_get_line=$(line_once "$gmu_resume" \
	'pm_runtime_get_sync(gmu->gxpd);' 'GMU GX runtime-PM get')
rate_line=$(line_once "$gmu_resume" \
	'clk_set_rate(gmu->core_clk, 200000000);' 'GMU clock rate')
clocks_line=$(line_once "$gmu_resume" \
	'clk_bulk_prepare_enable(gmu->nr_clocks, gmu->clocks);' \
	'GMU clock enable')
secure_line=$(line_once "$gmu_resume" \
	'ret = a6xx_gmu_secure_init(a6xx_gpu);' 'GMU secure init')
irq_line=$(line_once "$gmu_resume" 'enable_irq(gmu->gmu_irq);' \
	'GMU IRQ enable')
firmware_line=$(line_once "$gmu_resume" \
	'ret = a6xx_gmu_fw_start(gmu, status);' 'GMU firmware start')
hfi_line=$(line_once "$gmu_resume" \
	'ret = a6xx_hfi_start(gmu, status);' 'GMU HFI start')
if [ "$guard_line" -ge "$hung_line" ] ||
	[ "$hung_line" -ge "$consumer_get_line" ] ||
	[ "$consumer_get_line" -ge "$gx_get_line" ] ||
	[ "$gx_get_line" -ge "$rate_line" ] ||
	[ "$rate_line" -ge "$clocks_line" ] ||
	[ "$clocks_line" -ge "$secure_line" ] ||
	[ "$secure_line" -ge "$irq_line" ] ||
	[ "$irq_line" -ge "$firmware_line" ] ||
	[ "$firmware_line" -ge "$hfi_line" ]
then
	fail 'GMU resume resource order changed'
fi

get_sync=$(sed -n \
	'/^static inline int pm_runtime_get_sync(/,/^}/p' "$pm_runtime_h")
put_noidle=$(sed -n \
	'/^static inline void pm_runtime_put_noidle(/,/^}/p' "$pm_runtime_h")
put_sync_suspend=$(sed -n \
	'/^static inline int pm_runtime_put_sync_suspend(/,/^}/p' "$pm_runtime_h")
plain_suspend=$(sed -n \
	'/^static inline int pm_runtime_suspend(/,/^}/p' "$pm_runtime_h")
suspended_check=$(sed -n \
	'/^static inline bool pm_runtime_suspended(/,/^}/p' "$pm_runtime_h")

require_text "$get_sync" \
	'return __pm_runtime_resume(dev, RPM_GET_PUT);' \
	'get-sync usage increment'
require_file_text "$pm_runtime_h" \
	'incremented in all cases, even if it returns an error code.' \
	'get-sync error-count contract'
require_text "$put_noidle" \
	'atomic_add_unless(&dev->power.usage_count, -1, 0);' \
	'get-error no-idle balance'
require_text "$put_sync_suspend" \
	'return __pm_runtime_suspend(dev, RPM_GET_PUT);' \
	'synchronous consumer put-and-suspend'
require_text "$plain_suspend" \
	'return __pm_runtime_suspend(dev, 0);' \
	'non-counted synchronous supplier suspend'
require_text "$suspended_check" \
	'dev->power.runtime_status == RPM_SUSPENDED' \
	'runtime-suspended state check'

require_text "$runtime_resume_core" \
	'atomic_inc(&dev->power.usage_count);' \
	'runtime-core get increment'
require_text "$runtime_resume_core" \
	'retval = rpm_resume(dev, rpmflags);' \
	'runtime-core synchronous resume'
require_text "$runtime_suspend_core" \
	'retval = rpm_drop_usage_count(dev);' \
	'runtime-core put decrement'
require_text "$runtime_suspend_core" \
	'retval = rpm_suspend(dev, rpmflags);' \
	'runtime-core synchronous suspend'

supplier_get_line=$(line_once "$rpm_get_suppliers" \
	'retval = pm_runtime_get_sync(link->supplier);' \
	'linked CX supplier get')
supplier_error_line=$(line_once "$rpm_get_suppliers" \
	'if (retval < 0 && retval != -EACCES)' \
	'linked CX supplier get-error test')
supplier_balance_line=$(line_once "$rpm_get_suppliers" \
	'pm_runtime_put_noidle(link->supplier);' \
	'linked CX supplier get-error balance')
supplier_ref_line=$(line_once "$rpm_get_suppliers" \
	'refcount_inc(&link->rpm_active);' \
	'linked CX supplier active reference')
if [ "$supplier_get_line" -ge "$supplier_error_line" ] ||
	[ "$supplier_error_line" -ge "$supplier_balance_line" ] ||
	[ "$supplier_balance_line" -ge "$supplier_ref_line" ]
then
	fail 'linked-supplier get/error/refcount order changed'
fi
require_text "$rpm_release_supplier" \
	'pm_runtime_put_noidle(supplier);' \
	'linked-supplier reference release'
require_text "$rpm_put_suppliers" \
	'pm_runtime_release_supplier(link);' \
	'consumer-suspend supplier release'
require_text "$rpm_callback" \
	'__rpm_put_suppliers(dev, false);' \
	'consumer callback supplier rollback'
require_text "$rpm_suspend_suppliers" \
	'pm_request_idle(link->supplier);' \
	'asynchronous supplier idle request'
require_text "$rpm_suspend" 'rpm_suspend_suppliers(dev);' \
	'post-consumer supplier idle scheduling'

require_text "$genpd_attach" 'pm_runtime_enable(virt_dev);' \
	'virtual CX/GX runtime-PM enable'
require_text "$genpd_resume" 'ret = genpd_power_on(genpd, 0);' \
	'generic-domain power on'
require_text "$genpd_suspend" 'genpd_power_off(genpd, true, 0);' \
	'generic-domain power off'
require_text "$rpmhpd_on" 'ret = rpmhpd_aggregate_corner(pd, corner);' \
	'RPMh domain on vote'
require_text "$rpmhpd_on" 'pd->enabled = true;' \
	'RPMh domain enabled state'
require_text "$rpmhpd_off" 'ret = rpmhpd_aggregate_corner(pd, 0);' \
	'RPMh domain zero vote'
require_text "$rpmhpd_off" 'pd->enabled = false;' \
	'RPMh domain disabled state'

# The patch contract built on this boundary must use these exact operations:
# pm_runtime_get_sync(gmu->dev)
# pm_runtime_put_noidle(gmu->dev)
# pm_runtime_put_sync_suspend(gmu->dev)
# pm_runtime_suspend(gmu->cxpd)
# pm_runtime_suspended(gmu->dev)
# pm_runtime_suspended(gmu->cxpd)

printf '%s\n' \
	'PASS A660 GMU/CX runtime-PM has a source-pinned pre-mutation seam for one linked-CX get, get-error balance, synchronous consumer rollback, explicit non-counted CX suspend, and settled-state checks before GX, clocks, secure init, IRQ, firmware start, or HFI'
