#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-a660-gmu-cx-runtime-pm-boundary.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 GMU/CX runtime-PM boundary verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	57af6b4d0ddf6faaa708e7b409197dcf7aa8fcdb52a5a9612b59094aebc9dd2c \
	9d3ec22867f175831716c7742c6fe89b796e704594790844a5e419a8466b9d0e \
	97b2fc130862f00445b509855b16121b2eba6e5a5228f92457c2923297fd4999 \
	1c1383101d72ce3028df6d9ad3640c2020a041f5c1820b1698d1657b648b04f6 \
	86a4ab8982d610b0ff1a1eb998adaf99a5f914833a56e70fb62efda2764af566 \
	2326e3de634eefe0468dfe03e5c11650f5e014fda08923861154d9a19d7f9d8e \
	b8ad1677950edd4f8e372a59b8027282751434afb52f71f89151b978c89c6d18 \
	'test-a660-gmu-resume-entry-v9-root-contract.sh' \
	'adreno_is_a660_family(adreno_gpu)' \
	'pm_runtime_enable(gmu->dev)' \
	'dev_pm_domain_attach_by_name(gmu->dev, "cx")' \
	'device_link_add(gmu->dev, gmu->cxpd, DL_FLAG_PM_RUNTIME)' \
	'dev_pm_domain_attach_by_name(gmu->dev, "gx")' \
	'pm_runtime_get_sync(link->supplier)' \
	'pm_runtime_put_noidle(link->supplier)' \
	'__rpm_put_suppliers(dev, false)' \
	'pm_request_idle(link->supplier)' \
	'pm_runtime_get_sync(gmu->dev)' \
	'pm_runtime_put_noidle(gmu->dev)' \
	'pm_runtime_put_sync_suspend(gmu->dev)' \
	'pm_runtime_suspend(gmu->cxpd)' \
	'pm_runtime_suspended(gmu->dev)' \
	'pm_runtime_suspended(gmu->cxpd)' \
	'gmu->hung = false' \
	'pm_runtime_get_sync(gmu->gxpd)' \
	'clk_set_rate(gmu->core_clk, 200000000)' \
	'clk_bulk_prepare_enable' \
	'a6xx_gmu_secure_init' \
	'enable_irq(gmu->gmu_irq)' \
	'a6xx_gmu_fw_start' \
	'a6xx_hfi_start' \
	'PASS A660 GMU/CX runtime-PM has a source-pinned'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL GMU/CX runtime-PM boundary verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp|pkexec|sudo)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL GMU/CX runtime-PM boundary verifier controls a device or privileges' >&2
	exit 1
fi

set +e
"$verifier" /nonexistent >/dev/null 2>&1
missing_source=$?
set -e
[ "$missing_source" -ne 0 ]

if [ -n "${SOURCE_DIR:-}" ]; then
	"$verifier" "$SOURCE_DIR"
fi

echo 'PASS A660 GMU/CX runtime-PM boundary is accepted-v9-dependent, source-pinned, get-error-balanced, synchronously rolled back, CX-only, and pre-GX'
