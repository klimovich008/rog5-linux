#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
builder=$repo/scripts/device/build-persistent-root-power-usb-dtb.sh
verifier=$repo/scripts/device/verify-persistent-root-power-usb-dtb.sh
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM

"$builder" "$stage/a.dtb" >/dev/null
"$builder" "$stage/b.dtb" >/dev/null
cmp "$stage/a.dtb" "$stage/b.dtb"
"$verifier" "$stage/a.dtb" >/dev/null

cp "$stage/a.dtb" "$stage/ufs-disabled.dtb"
fdtput -t s "$stage/ufs-disabled.dtb" /soc@0/ufshc@1d84000 status disabled
if "$verifier" "$stage/ufs-disabled.dtb" >"$stage/out" 2>"$stage/err"; then
	echo 'FAIL composed-DTB verifier accepted disabled UFS' >&2
	exit 1
fi
grep -Fq 'does not enable /soc@0/ufshc@1d84000' "$stage/err"

cp "$stage/a.dtb" "$stage/pas-regression.dtb"
fdtput -t x "$stage/pas-regression.dtb" \
	/reserved-memory/memory@edc00000 reg 0 edc00000 0 11000000
if "$verifier" "$stage/pas-regression.dtb" >"$stage/out" 2>"$stage/err"; then
	echo 'FAIL composed-DTB verifier accepted a PAS-memory regression' >&2
	exit 1
fi
grep -Fq 'wrong /reserved-memory/memory@edc00000 geometry' "$stage/err"

if "$builder" "$stage/a.dtb" >"$stage/out" 2>"$stage/err"; then
	echo 'FAIL composed-DTB builder overwrote an existing output' >&2
	exit 1
fi
grep -Fq 'output already exists' "$stage/err"

echo 'PASS deterministic DTB composition preserves power/UCSI and enables only read-only UFS plus side USB2'
