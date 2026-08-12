#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-ufs-rmtfs-reserved-candidate-dtb.sh
base=$repo/artifacts/buttons-indicator-v1/sm8350-asus-rog-phone5-buttons-indicator.dtb
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -x "$builder" ]
for command in dtc fdtget fdtput; do
	command -v "$command" >/dev/null
done

"$builder" "$base" "$stage/candidate.dtb" >/dev/null
[ "$(fdtget -t s "$stage/candidate.dtb" \
	/reserved-memory/memory@9b800000 status)" = okay ]

cp "$base" "$stage/wrong-status.dtb"
chmod 0600 "$stage/wrong-status.dtb"
fdtput -t s "$stage/wrong-status.dtb" \
	/reserved-memory/memory@9b800000 status okay
if "$builder" "$stage/wrong-status.dtb" "$stage/rejected.dtb" \
	>"$stage/rejected.log" 2>&1; then
	echo 'FAIL builder accepted an unreviewed RMTFS input state' >&2
	exit 1
fi
grep -Fxq 'FAIL input does not contain the reviewed disabled RMTFS node' \
	"$stage/rejected.log"

cp "$base" "$stage/wrong-range.dtb"
chmod 0600 "$stage/wrong-range.dtb"
fdtput -t x "$stage/wrong-range.dtb" \
	/reserved-memory/memory@9b800000 reg 0 9b800000 0 300000
if "$builder" "$stage/wrong-range.dtb" "$stage/rejected.dtb" \
	>"$stage/rejected.log" 2>&1; then
	echo 'FAIL builder accepted an unreviewed RMTFS range' >&2
	exit 1
fi
grep -Fxq 'FAIL input RMTFS reservation is not exact' "$stage/rejected.log"

echo 'PASS exact one-property UFS RMTFS reservation correction contract'
