#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
verifier=$repo/scripts/device/verify-power-usb-active-dtb.sh
builder=$repo/scripts/device/build-stock-reserved-memory-candidate-dtb.sh
base=$repo/artifacts/network-root-v3/sm8350-asus-rog-phone5-recovery.dtb
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-stock-reserved-memory.dtso
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM

for command in dtc fdtget fdtput fdtoverlay; do
	command -v "$command" >/dev/null || {
		echo "FAIL missing active-DTB test command: $command" >&2
		exit 1
	}
done

if "$verifier" "$base" >"$stage/missing.log" 2>&1; then
	echo 'FAIL historical DTB without stock-owned RAM passed' >&2
	exit 1
fi
grep -Fq 'lacks /reserved-memory/memory@cbc00000' "$stage/missing.log"

"$builder" "$base" "$overlay" "$stage/corrected.dtb" >/dev/null
"$verifier" "$stage/corrected.dtb" >/dev/null

cp -- "$stage/corrected.dtb" "$stage/wrong-reg.dtb"
fdtput -t x "$stage/wrong-reg.dtb" \
	/reserved-memory/memory@edc00000 reg 0 edc00000 0 11000000
if "$verifier" "$stage/wrong-reg.dtb" >"$stage/wrong-reg.log" 2>&1; then
	echo 'FAIL wrong stock-owned RAM geometry passed' >&2
	exit 1
fi
grep -Fq 'wrong /reserved-memory/memory@edc00000 geometry' \
	"$stage/wrong-reg.log"

cp -- "$stage/corrected.dtb" "$stage/wrong-map.dtb"
fdtput -d "$stage/wrong-map.dtb" \
	/reserved-memory/memory@d8000000 no-map
if "$verifier" "$stage/wrong-map.dtb" >"$stage/wrong-map.log" 2>&1; then
	echo 'FAIL mapped memshare RAM passed' >&2
	exit 1
fi
grep -Fq 'stock memshare RAM span must be no-map' "$stage/wrong-map.log"

echo 'PASS active power/USB DTB rejects the V16 PAS-memory regression and hostile geometry'
