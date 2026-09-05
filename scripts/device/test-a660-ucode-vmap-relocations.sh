#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-a660-ucode-vmap-relocations.sh
module=$repo/artifacts/a660-ucode-allocation-build-a/drivers/gpu/drm/msm/msm.ko

[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 ucode vmap-relocation verifier' >&2
	exit 1
}
bash -n "$verifier"

for contract in \
	fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
	'msm_gem_kernel_new' \
	'msm_gem_kernel_put' \
	'adreno_fw_create_bo' \
	'a6xx_ucode_load' \
	'a6xx_ucode_unload' \
	'R_AARCH64_CALL26' \
	'logical_gets=4' \
	'logical_puts=4' \
	'wrapper_gets=1' \
	'wrapper_puts=2' \
	'kernel_news=3' \
	'kernel_puts=2' \
	'snapshot=still-required'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL vmap-relocation verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[^[:alnum:]_])(fastboot|adb|ssh|scp|pkexec|sudo)([^[:alnum:]_]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL vmap-relocation verifier controls a device or privileges' >&2
	exit 1
fi

set +e
"$verifier" /nonexistent >/dev/null 2>&1
missing_module=$?
set -e
[ "$missing_module" -ne 0 ]

if [ -f "$module" ]; then
	"$verifier" "$module"

	tmp=$(mktemp -d)
	trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
	mutated=$tmp/msm.ko
	cp -- "$module" "$mutated"
	truncate -s +1 "$mutated"
	set +e
	"$verifier" "$mutated" >/dev/null 2>&1
	mutated_result=$?
	set -e
	[ "$mutated_result" -ne 0 ] || {
		echo 'FAIL vmap-relocation verifier accepts a changed module' >&2
		exit 1
	}
fi

echo 'PASS accepted A660 MSM module has an offline-tested compiler-relocation contract'
