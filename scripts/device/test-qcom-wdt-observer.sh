#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
source=$repo/tools/qcom_wdt_observer/rog5-qcom-wdt-observer.c
builder=$repo/scripts/device/build-qcom-wdt-observer-module.sh
dtb_builder=$repo/scripts/device/build-qcom-wdt-observer-dtb.sh

sh -n "$builder" "$dtb_builder"
for contract in \
	'compatible = "rog5,sm8350-wdt-observer"' \
	'reg-names = "wdt-base"' \
	'readl_relaxed(base + WDT_EN)' \
	'readl_relaxed(base + WDT_STS)' \
	'readl_relaxed(base + WDT_BARK_TIME)' \
	'readl_relaxed(base + WDT_BITE_TIME)' \
	'ROG5_WDT_OBSERVER_V1'; do
	grep -Fq "$contract" "$source" "$dtb_builder" || exit 1
done
! grep -Eq '\b(write[blq]?|writel|watchdog_register_device|request_irq|enable_irq)\b' "$source"
grep -Fq 'expected_module=b06271c62e22292e043b082c3c5f2da46f8d98f36f3521c16ec389dcb40036d1' "$builder"
grep -Fq 'observer struct module size changed' "$builder"

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
"$dtb_builder" "$repo/artifacts/local-image-stage-v1/board.dtb" "$work/a.dtb" >/dev/null
"$dtb_builder" "$repo/artifacts/local-image-stage-v1/board.dtb" "$work/b.dtb" >/dev/null
cmp "$work/a.dtb" "$work/b.dtb"
[ "$(fdtget "$work/a.dtb" /soc@0/watchdog-observer@17c10000 compatible)" = \
	rog5,sm8350-wdt-observer ]

echo 'PASS watchdog observer is exact-ABI, deterministic, and MMIO-read-only'
