#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
extractor=$repo/scripts/host/extract-qualified-qemu-aarch64-static.sh
runner=$repo/scripts/host/run-private-arm64-binfmt.sh
sealed_runner=$repo/scripts/host/run-sealed-arm64-binfmt.py
responder_test=$repo/scripts/host/test-recovery-control-aarch64.sh

for script in "$extractor" "$runner" "$sealed_runner" "$responder_test"; do
	[[ -f $script && ! -L $script && -x $script ]] ||
		fail "missing executable private ARM64 helper: ${script#"$repo"/}"
done

for token in \
	'run-private-arm64-binfmt.sh' \
	'run_arm64() {' \
	'"$arm64_runner" podman run' \
	'test-recovery-control-build-record.py' \
	'--emit-build-fields' \
	"mapfile -d '' -t contract_fields"; do
	grep -Fq -- "$token" "$responder_test" ||
		fail "recovery responder test omits private ARM64 execution: $token"
done
[ "$(grep -Fc 'podman run' "$responder_test")" -eq 1 ] ||
	fail 'recovery responder test retains an unsealed Podman execution path'
if grep -Fq 'json.loads' "$responder_test"; then
	fail 'recovery responder test bypasses the strict build-record parser'
fi
bash -n "$extractor" "$runner" "$responder_test"
python3 -m py_compile "$sealed_runner"

for token in \
	localhost/rog5-kernel-builder:historical-20260724 \
	verify-historical-network-root-builder.sh \
	'realpath -m -- "$output"' \
	'revalidate_output_parent' \
	'mv -T --no-clobber' \
	6245816 \
	bfcd46c842441912baed36158569ac29a7fb656684ca73c1b3b2f0f3971e9bec \
	'qemu-aarch64 version 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.17)' \
	'podman create --network=none' \
	'podman cp'; do
	grep -Fq -- "$token" "$extractor" ||
		fail "QEMU extractor omits contract token: $token"
done

for token in \
	'podman unshare unshare --mount' \
	'ROG5_PRIVATE_BINFMT_GUARD' \
	'/proc/self/uid_map' \
	'findmnt -n -o PROPAGATION /' \
	'mount --make-rprivate /' \
	'private ARM64 binfmt mount inherited a host registration' \
	"private_entries=\$(find /proc/sys/fs/binfmt_misc" \
	'run-sealed-arm64-binfmt.py' \
	'mount -t binfmt_misc none /proc/sys/fs/binfmt_misc' \
	bfcd46c842441912baed36158569ac29a7fb656684ca73c1b3b2f0f3971e9bec; do
	grep -Fq -- "$token" "$runner" ||
		fail "private ARM64 runner omits contract token: $token"
done
grep -Fq \
	'for command_name in cut find findmnt id mount python3 sha256sum sort stat; do' \
		"$runner" ||
	fail 'private ARM64 inside branch no longer has a podman-free dependency set'

for token in \
	'os.memfd_create' \
	'os.MFD_ALLOW_SEALING' \
	'F_SEAL_SEAL' \
	'F_SEAL_SHRINK' \
	'F_SEAL_GROW' \
	'F_SEAL_WRITE' \
	'/proc/self/fd/' \
	'/proc/sys/fs/binfmt_misc/register' \
	'f"{interpreter}:POF\n"' \
	'prove_sealed'; do
	grep -Fq -- "$token" "$sealed_runner" ||
		fail "sealed ARM64 runner omits contract token: $token"
done

if grep -Eq '\b(sudo|pkexec|fastboot|adb|ssh|scp)\b|/dev/(sd|nvme|ufs)' \
	"$extractor" "$runner" "$sealed_runner"; then
	fail 'private ARM64 helpers contain privilege, phone, or storage transport'
fi

escape_output=$repo/scripts/.qemu-contract-escape-$$
if "$extractor" "$repo/build/../scripts/.qemu-contract-escape-$$" \
	>/dev/null 2>&1; then
	fail 'QEMU extractor accepted a parent-traversal output'
fi
[[ ! -e $escape_output && ! -L $escape_output ]] ||
	fail 'QEMU extractor wrote through a parent-traversal output'

mkdir -p "$repo/build"
test_root=$(mktemp -d "$repo/build/private-arm64-contract.XXXXXX")
cleanup() {
	rm -f -- "$test_root/runner.out" "$test_root/escape"
	rmdir -- "$test_root"
}
trap cleanup EXIT HUP INT TERM
ln -s "$repo/scripts" "$test_root/escape"
if "$extractor" "$test_root/escape/.qemu-contract-symlink-$$" \
	>/dev/null 2>&1; then
	fail 'QEMU extractor accepted a symlink-parent output escape'
fi
[[ ! -e $repo/scripts/.qemu-contract-symlink-$$ ]] ||
	fail 'QEMU extractor wrote through a symlink-parent output'

read -r test_inside_id test_outside_id test_map_length _ \
	</proc/self/uid_map ||
	fail 'could not read contract-test user-namespace mapping'
if [[ $(id -u) == 0 && $test_inside_id == 0 &&
	$test_outside_id != 0 && $test_map_length -gt 0 ]]; then
	fail 'contract test must not run inside a rootless user namespace'
fi

if "$runner" --inside-private-mount true >"$test_root/runner.out" 2>&1; then
	fail 'private ARM64 runner accepted a direct internal-branch invocation'
fi
grep -Fq 'lacks its outer-runner guard' "$test_root/runner.out" ||
	fail 'direct internal-branch rejection was not fail-closed'

if ROG5_PRIVATE_BINFMT_GUARD=forged \
	"$runner" --inside-private-mount forged true \
	>"$test_root/runner.out" 2>&1; then
	fail 'private ARM64 runner accepted a forged internal-branch guard'
fi
grep -Eq \
	'requires root inside a rootless user namespace|not inside a rootless user namespace' \
	"$test_root/runner.out" ||
	fail 'forged internal-branch guard did not reach a real user-namespace gate'

sealed_size=$(stat -c %s "$sealed_runner")
sealed_sha=$(sha256sum "$sealed_runner" | cut -d ' ' -f 1)
"$sealed_runner" "$sealed_runner" "$sealed_size" "$sealed_sha" --self-test \
	>"$test_root/runner.out"
grep -Fxq 'PASS exact ARM64 emulator bytes are held in a sealed memfd' \
	"$test_root/runner.out" ||
	fail 'sealed ARM64 memfd self-test lacked exact success evidence'
if "$sealed_runner" "$sealed_runner" "$sealed_size" \
	0000000000000000000000000000000000000000000000000000000000000000 \
	--self-test >"$test_root/runner.out" 2>&1; then
	fail 'sealed ARM64 runner accepted the wrong source hash'
fi
grep -Fxq 'FAIL qualified ARM64 emulator bytes changed' \
	"$test_root/runner.out" ||
	fail 'sealed ARM64 runner did not fail closed on the wrong source hash'

trap - EXIT HUP INT TERM
cleanup
echo 'PASS ARM64 emulation is hash-pinned, rootless, private, and reboot-repeatable'
