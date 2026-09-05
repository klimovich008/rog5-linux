#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch
verifier=$repo/scripts/device/verify-a660-gmu-pwrlevels-patch.sh

[ -r "$patch" ] || {
	echo 'FAIL missing A660 GMU power-level error patch' >&2
	exit 1
}
[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 GMU power-level patch verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	97b2fc130862f00445b509855b16121b2eba6e5a5228f92457c2923297fd4999 \
	'a6xx_gmu_pwrlevels_probe(gmu)' \
	'goto detach_gxpd;' \
	'a6xx_gmu_acd_probe(gmu)' \
	'a6xx_gmu_rpmh_init(gmu)' \
	'git apply --check' \
	'patched_a6xx_gmu_sha256='
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL GMU patch verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot|adb|/dev/(block|disk)|[[:space:]]mount[[:space:]]|[[:space:]]dd[[:space:]]' \
	"$patch" "$verifier"
then
	echo 'FAIL GMU patch contract contains a device-control path' >&2
	exit 1
fi

if [ -n "${SOURCE_DIR:-}" ]; then
	"$verifier" "$SOURCE_DIR"
fi

echo 'PASS A660 GMU power-level errors are propagated before ACD, HFI, or RSCC/PDC setup'
