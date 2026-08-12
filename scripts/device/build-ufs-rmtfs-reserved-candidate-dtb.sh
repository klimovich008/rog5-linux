#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

base=${1:?usage: build-ufs-rmtfs-reserved-candidate-dtb.sh BASE_DTB OUTPUT_DTB}
output=${2:?missing output DTB}
node=/reserved-memory/memory@9b800000

[ -f "$base" ] && [ ! -L "$base" ] && [ -s "$base" ] ||
	fail 'missing fixed UFS DTB input'
[ "$(fdtget -t s "$base" "$node" status 2>/dev/null)" = disabled ] ||
	fail 'input does not contain the reviewed disabled RMTFS node'
[ "$(fdtget -t s "$base" "$node" compatible 2>/dev/null)" = qcom,rmtfs-mem ] ||
	fail 'input RMTFS compatible is not exact'
[ "$(fdtget -t x "$base" "$node" reg 2>/dev/null)" = '0 9b800000 0 400000' ] ||
	fail 'input RMTFS reservation is not exact'
fdtget "$base" "$node" no-map >/dev/null 2>&1 ||
	fail 'input RMTFS reservation lacks no-map'

stage=$(mktemp -d)
publish_stage=
cleanup() {
	rm -rf "$stage"
	if [ -n "$publish_stage" ]; then
		rm -rf "$publish_stage"
	fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cp "$base" "$stage/candidate.dtb"
chmod 0600 "$stage/candidate.dtb"
fdtput -t s "$stage/candidate.dtb" "$node" status okay
dtc -q -I dtb -O dts -o "$stage/base.dts" "$base"
dtc -q -I dtb -O dts -o "$stage/candidate.dts" "$stage/candidate.dtb"
changes=$(diff -u "$stage/base.dts" "$stage/candidate.dts" |
	sed -n '/^[-+][^-+]/p' || true)
[ "$changes" = "-			status = \"disabled\";
+			status = \"okay\";" ] ||
	fail 'RMTFS correction changed more than the one reviewed status property'

[ "$(fdtget -t s "$stage/candidate.dtb" "$node" status)" = okay ]
[ "$(fdtget -t s "$stage/candidate.dtb" "$node" compatible)" = qcom,rmtfs-mem ]
[ "$(fdtget -t x "$stage/candidate.dtb" "$node" reg)" = '0 9b800000 0 400000' ]
fdtget "$stage/candidate.dtb" "$node" no-map >/dev/null

output_parent=$(dirname "$output")
mkdir -p "$output_parent"
publish_stage=$(mktemp -d "$output_parent/.rog5-ufs-rmtfs.XXXXXX")
mv "$stage/candidate.dtb" "$publish_stage/candidate.dtb"
chmod 0444 "$publish_stage/candidate.dtb"
mv "$publish_stage/candidate.dtb" "$output"
rm -rf "$publish_stage"
publish_stage=
sha256sum "$output"
echo 'PASS UFS DTB restores the exact RMTFS reservation with one property change'
