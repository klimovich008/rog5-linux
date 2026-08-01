#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
artifact=$repo/artifacts/qemu-systemd-arm64-v1/runtime.cpio.gz
checksums=$repo/artifacts/qemu-systemd-arm64-v1/SHA256SUMS
readme=$repo/artifacts/qemu-systemd-arm64-v1/README.md
builder=$repo/scripts/host/build-qemu-systemd-runtime.sh
verifier=$repo/scripts/host/verify-qemu-systemd-runtime.sh
for path in "$artifact" "$checksums" "$readme" "$builder" "$verifier"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing or linked systemd runtime input: $path"
done
[[ -x $builder && -x $verifier ]] ||
	fail 'systemd runtime builder or verifier is not executable'
bash -n "$builder" "$verifier"

for token in \
	'expected_source_size=536747283' \
	'expected_source_sha256=60fed48c8714a3f3b2082f95a04e913f32dfc74ed4c262e5b3d6e924a39a9c3b' \
	'closure=recursive-dt-needed+required-dlopen' \
	'elf_count=17' \
	'systemd-executor' \
	'source / "usr/lib/libmount.so.1"' \
	'libgcc=16.1.1+r12+g301eb08fa2c5-1' \
	'util-linux-libs=2.42.1-1' \
	'LGPL-2.1-or-later.txt' \
	'root/usr/share/licenses/libgcc/*' \
	'root/usr/share/licenses/util-linux-libs/*' \
	'boot_authority=none' \
	'phone_storage=absent' \
	'--reproducible'; do
	grep -Fq -- "$token" "$builder" ||
		fail "systemd runtime builder contract changed: $token"
done
grep -Fqx \
	'5011267029d8da251c20e66f232cce2f36530e09d18a36e0a492018255f178f7  runtime.cpio.gz' \
	"$checksums" || fail 'systemd runtime checksum file changed'
"$verifier" "$artifact"

work=$(mktemp -d)
trap 'find "$work" -depth -delete 2>/dev/null || true' EXIT HUP INT TERM
cp "$artifact" "$work/mutated.cpio.gz"
printf '\000' >>"$work/mutated.cpio.gz"
if "$verifier" "$work/mutated.cpio.gz" >"$work/mutation.log" 2>&1; then
	fail 'systemd runtime verifier accepted a mutated archive'
fi
grep -Fq 'systemd runtime archive size changed' "$work/mutation.log" ||
	fail 'systemd runtime mutation failed at an unexpected boundary'

echo 'PASS reproducible sealed ARM64 systemd QEMU runtime contract'
