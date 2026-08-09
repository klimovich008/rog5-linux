#!/usr/bin/env bash
set -euo pipefail
umask 077

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
initramfs_a=${1:?usage: build-observation-recovery-wrapper-offline.sh INITRAMFS_A INITRAMFS_B RECOVERY_INIT CONTROL OUTPUT_ROOT}
initramfs_b=${2:?missing second observation-only initramfs}
recovery_init=${3:?missing recovery init source}
control=${4:?missing observation-only recovery responder}
output_root=${5:?missing ignored output root}
jobs=${ROG5_OBSERVATION_WRAPPER_JOBS:-8}
initramfs_verifier=$repo/scripts/device/verify-stable-recovery-initramfs.sh
wrapper_gate=$repo/scripts/host/test-stable-recovery-wrapper-offline.sh
wrapper_verifier=$repo/scripts/host/verify-observation-recovery-wrapper.py

for command in cmp mv python3 rm; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
[[ $jobs =~ ^[1-9][0-9]*$ && $jobs -le 16 ]] ||
	fail 'ROG5_OBSERVATION_WRAPPER_JOBS must be between 1 and 16'
for input in "$initramfs_a" "$initramfs_b" "$recovery_init" "$control" \
	"$initramfs_verifier" "$wrapper_gate" "$wrapper_verifier"; do
	[[ -f $input && ! -L $input ]] || fail "unsafe or missing input: $input"
done

"$initramfs_verifier" "$initramfs_a" "$recovery_init" "$control" \
	- - - observation-only-a600000-v1 -
"$initramfs_verifier" "$initramfs_b" "$recovery_init" "$control" \
	- - - observation-only-a600000-v1 -
cmp "$initramfs_a" "$initramfs_b" ||
	fail 'observation-only initramfs twins differ'

ROG5_WRAPPER_BUILDER_PROFILE=steam-deck-asus-5.4-v1 \
	JOBS="$jobs" \
	"$wrapper_gate" "$initramfs_a" "$initramfs_b" "$output_root"

evidence_temp=$output_root/.observation-wrapper-evidence.$$.tmp
trap 'rm -f -- "$evidence_temp"' EXIT HUP INT TERM
python3 "$wrapper_verifier" "$initramfs_a" "$initramfs_b" \
	"$output_root" >"$evidence_temp"
mv -T --no-clobber "$evidence_temp" \
	"$output_root/observation-wrapper-evidence.txt"
trap - EXIT HUP INT TERM
cat "$output_root/observation-wrapper-evidence.txt"
echo 'PASS observation-only ASUS wrapper twins built and verified offline'
