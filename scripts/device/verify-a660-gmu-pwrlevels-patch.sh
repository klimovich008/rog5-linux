#!/bin/sh
set -eu

source_dir=${1:?usage: verify-a660-gmu-pwrlevels-patch.sh PINNED_SOURCE}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch
source_file=$source_dir/drivers/gpu/drm/msm/adreno/a6xx_gmu.c
expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
patched_a6xx_gmu_sha256=126d1011942083ad63516de0bee1d62f18db4752199a1cbc6cfb5be3230e4ace

[ -d "$source_dir/.git" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ]
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ -f "$source_file" ] && [ ! -L "$source_file" ]
[ -f "$patch" ] && [ ! -L "$patch" ]
[ "$(sha256sum "$source_file" | cut -d ' ' -f 1)" = \
	97b2fc130862f00445b509855b16121b2eba6e5a5228f92457c2923297fd4999 ]
[ "$(sha256sum "$patch" | cut -d ' ' -f 1)" = \
	0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637 ]
[ "$(git -C "$source_dir" apply --numstat "$patch")" = \
	"3	1	drivers/gpu/drm/msm/adreno/a6xx_gmu.c" ]

gmu_init=$(sed -n '/^int a6xx_gmu_init(/,/^}/p' "$source_file")
printf '%s\n' "$gmu_init" |
	grep -Fqx '	a6xx_gmu_pwrlevels_probe(gmu);'
if printf '%s\n' "$gmu_init" |
	grep -Fq 'ret = a6xx_gmu_pwrlevels_probe(gmu);'
then
	echo 'FAIL pinned source unexpectedly contains the GMU error fix' >&2
	exit 1
fi

git -C "$source_dir" apply --check "$patch"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/drivers/gpu/drm/msm/adreno"
cp "$source_file" "$stage/drivers/gpu/drm/msm/adreno/a6xx_gmu.c"
(cd "$stage" && git apply --check "$patch" && git apply "$patch")
patched_file=$stage/drivers/gpu/drm/msm/adreno/a6xx_gmu.c
[ "$(sha256sum "$patched_file" | cut -d ' ' -f 1)" = \
	"$patched_a6xx_gmu_sha256" ]

patched_init=$(sed -n '/^int a6xx_gmu_init(/,/^}/p' "$patched_file")
for line in \
	'	ret = a6xx_gmu_pwrlevels_probe(gmu);' \
	'	if (ret)' \
	'		goto detach_gxpd;' \
	'	ret = a6xx_gmu_acd_probe(gmu);' \
	'	a6xx_hfi_init(gmu);' \
	'	a6xx_gmu_rpmh_init(gmu);'
do
	printf '%s\n' "$patched_init" | grep -Fqx "$line"
done

numbered=$(printf '%s\n' "$patched_init" | nl -ba)
pwrlevels_line=$(printf '%s\n' "$numbered" |
	awk '/ret = a6xx_gmu_pwrlevels_probe/ { print $1; exit }')
error_line=$(printf '%s\n' "$numbered" |
	awk '/ret = a6xx_gmu_pwrlevels_probe/ { after_probe = 1 }
		after_probe && /goto detach_gxpd/ { print $1; exit }')
acd_line=$(printf '%s\n' "$numbered" |
	awk '/ret = a6xx_gmu_acd_probe/ { print $1; exit }')
hfi_line=$(printf '%s\n' "$numbered" |
	awk '/a6xx_hfi_init/ { print $1; exit }')
rpmh_line=$(printf '%s\n' "$numbered" |
	awk '/a6xx_gmu_rpmh_init/ { print $1; exit }')
[ "$pwrlevels_line" -lt "$error_line" ]
[ "$error_line" -lt "$acd_line" ]
[ "$acd_line" -lt "$hfi_line" ]
[ "$hfi_line" -lt "$rpmh_line" ]

echo 'PASS exact A660 GMU power-level failure propagates before ACD, HFI, or RSCC/PDC setup'
