#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
restorer=$repo/scripts/host/restore-stable-recovery-inputs.sh
image_builder=$repo/scripts/host/build-persistent-root-verifier-image.sh

for path in "$restorer" "$image_builder"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable recovery-input contract: ${path#"$repo"/}"
	bash -n "$path"
done

for token in \
	df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f \
	da573d089cd617e088624b6d6bf711e193a4df5367843293e2e5ba543556e51d \
	bd8b6951f862af1123972b521c355c655b7a2f40c2bf9cfe700edd590a101c94 \
	76dce86852903fef7adba0285d816e5ce9ffbe9fb3ca86bbb349b97afaba1f63 \
	2bb5136c89f5b0bbe1554c8915a3b520d5aa63ae2a51d4d821eb81698db5a818 \
	"curl --fail --location --retry 3 --proto '=https' --tlsv1.2" \
	'apk --no-network verify' \
	'--network=none' \
	'run-private-arm64-binfmt.sh' \
	'retained lineages differ' \
	'mv -T -- "$temporary" "$output"'; do
	grep -Fq -- "$token" "$restorer" ||
		fail "recovery-input restorer omits contract token: $token"
done

for token in \
	3d074a3e8b7bc81f96086aa633b132a897ededa4349f88aa77be5fbea2e237f0 \
	a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e \
	'sha256:ab143fea42bd7780c2b69512397f9a33251ef9218c3258e5dd2995a905abddaa' \
	'--no-cache' \
	'--platform linux/arm64' \
	'--timestamp "$epoch"'; do
	grep -Fq -- "$token" "$image_builder" ||
		fail "static-verifier image builder omits contract token: $token"
done

if grep -Eq \
	'\b(fastboot|adb|sudo|pkexec)\b|/dev/(sd|nvme|ufs)' \
	"$restorer" "$image_builder"; then
	fail 'recovery-input restoration contains phone, privilege, or storage transport'
fi

echo 'PASS minimal recovery-input restoration is exact, atomic, and signature-gated'
