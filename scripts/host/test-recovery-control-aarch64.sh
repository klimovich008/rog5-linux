#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
arm64_runner=$repo/scripts/host/run-private-arm64-binfmt.sh
for command in awk cmp file podman python3 qemu-aarch64-static sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing AArch64-test command: $command"
done
[[ -f $arm64_runner && ! -L $arm64_runner && -x $arm64_runner ]] ||
	fail 'missing sealed private ARM64 runner'
mapfile -d '' -t contract_fields < <(
	python3 "$repo/scripts/host/test-recovery-control-build-record.py" \
		--emit-build-fields
)
[ "${#contract_fields[@]}" -eq 17 ] ||
	fail 'recovery responder build contract is incomplete'
source_path=${contract_fields[0]}
source_size=${contract_fields[1]}
source_sha256=${contract_fields[2]}
source_mode=${contract_fields[3]}
builder_path=${contract_fields[4]}
builder_size=${contract_fields[5]}
builder_sha256=${contract_fields[6]}
builder_mode=${contract_fields[7]}
contract_image=${contract_fields[8]}
expected_image_id=${contract_fields[9]}
expected_image_digest=${contract_fields[10]}
expected_architecture=${contract_fields[11]}
expected_compiler=${contract_fields[12]}
expected_epoch=${contract_fields[13]}
output_size=${contract_fields[14]}
output_sha256=${contract_fields[15]}
output_mode=${contract_fields[16]}

[ "$source_path" = tools/recovery_control/rog5-recovery-control.c ] ||
	fail 'recovery responder source path is not exact'
[ "$builder_path" = scripts/device/build-recovery-control.sh ] ||
	fail 'recovery responder builder path is not exact'
[ "$expected_architecture" = arm64 ] ||
	fail 'recovery responder build architecture is not exact'
[ "$expected_epoch" = 1681862400 ] ||
	fail 'recovery responder build epoch is not exact'
check_input() {
	local input_path=$1
	local input_size=$2
	local input_sha256=$3
	local input_mode=$4
	[ "$(stat -c %s "$repo/$input_path")" = "$input_size" ] ||
		fail "recovery responder input size changed: $input_path"
	[ "$(sha256sum "$repo/$input_path" | awk '{print $1}')" = \
		"$input_sha256" ] ||
		fail "recovery responder input identity changed: $input_path"
	[ "$(stat -c %a "$repo/$input_path")" = "${input_mode#0}" ] ||
		fail "recovery responder input mode changed: $input_path"
}
check_input "$source_path" "$source_size" "$source_sha256" "$source_mode"
check_input "$builder_path" "$builder_size" "$builder_sha256" "$builder_mode"

image=${ROG5_AARCH64_BUILD_IMAGE:-$contract_image}
podman image exists "$image" ||
	fail "missing pinned local AArch64 build image: $image"
[ "$(podman image inspect "$image" --format '{{.Architecture}}')" = "$expected_architecture" ] ||
	fail 'recovery responder build image is not arm64'
actual_image_id=$(podman image inspect "$image" --format '{{.Id}}')
actual_image_digest=$(podman image inspect "$image" --format '{{.Digest}}')
[ "$actual_image_id" = "$expected_image_id" ] ||
	fail "unexpected AArch64 build image ID: $actual_image_id"
[ "$actual_image_digest" = "$expected_image_digest" ] ||
	fail "unexpected AArch64 build image digest: $actual_image_digest"
run_arm64() {
	"$arm64_runner" podman run --rm --network=none --platform linux/arm64 "$@"
}

actual_compiler=$(run_arm64 \
	"$image" cc -dumpfullversion)
[ "$actual_compiler" = "$expected_compiler" ] ||
	fail "unexpected recovery responder compiler: $actual_compiler"

test_tmp=$(mktemp -d)
trap 'rm -rf -- "$test_tmp"' EXIT HUP INT TERM

build_one() {
	output=$1
	run_arm64 \
		-v "$repo:/workspace:ro,Z" \
		-v "$test_tmp:/out:Z" \
		"$image" \
		/workspace/scripts/device/build-recovery-control.sh \
		/workspace/tools/recovery_control/rog5-recovery-control.c \
		"/out/$output"
}

build_one rog5-recovery-control-a
build_one rog5-recovery-control-b
cmp "$test_tmp/rog5-recovery-control-a" \
	"$test_tmp/rog5-recovery-control-b"

run_arm64 \
	-v "$repo:/workspace:ro,Z" \
	-v "$test_tmp:/out:Z" \
	"$image" \
	cc -std=c11 -O2 -static -fPIE -pie -fstack-protector-strong \
	-Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none \
	-DROG5_CONTROL_TESTING=1 \
	/workspace/tools/recovery_control/rog5-recovery-control.c \
	-o /out/rog5-recovery-control-test

run_arm64 \
	-v "$repo:/workspace:ro,Z" \
	-v "$test_tmp:/out:Z" \
	"$image" \
	sh -eu -c '
		cp /workspace/tools/recovery_control/rog5-recovery-control.c \
			/out/contaminated-responder.c
		printf "%s\n" \
			"const char rog5_contamination[] __attribute__((used)) = \"ROG5_TEST_CONTAMINATION\";" \
			>>/out/contaminated-responder.c
		if /workspace/scripts/device/build-recovery-control.sh \
			/out/contaminated-responder.c \
			/out/contaminated-responder \
			>/out/contaminated-responder-build.log 2>&1; then
			echo "FAIL contaminated production responder passed" >&2
			exit 1
		fi
		grep -qx \
			"FAIL production responder contains a test interface" \
			/out/contaminated-responder-build.log
	'

ROG5_CONTROL_TEST_BINARY=$test_tmp/rog5-recovery-control-test \
ROG5_CONTROL_TEST_RUNNER=$(command -v qemu-aarch64-static) \
	python3 "$repo/scripts/host/test-recovery-control-native.py"

file "$test_tmp/rog5-recovery-control-a" |
	grep -q 'ARM aarch64.*static-pie linked, stripped'
[ "$(stat -c %s "$test_tmp/rog5-recovery-control-a")" = "$output_size" ] ||
	fail 'recovery responder output size does not match its build contract'
[ "$(sha256sum "$test_tmp/rog5-recovery-control-a" | awk '{print $1}')" = "$output_sha256" ] ||
	fail 'recovery responder output identity does not match its build contract'
[ "$(stat -c %a "$test_tmp/rog5-recovery-control-a")" = "${output_mode#0}" ] ||
	fail 'recovery responder output mode does not match its build contract'
sha256sum "$test_tmp/rog5-recovery-control-a" \
	"$test_tmp/rog5-recovery-control-b"
printf 'build_image_id=%s build_image_digest=%s\n' \
	"$actual_image_id" "$actual_image_digest"
echo 'PASS reproducible production AArch64 responder and QEMU PTY suite'
