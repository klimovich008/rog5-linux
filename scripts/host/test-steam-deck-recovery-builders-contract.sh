#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
profile=$repo/configs/kernel-builder/steam-deck-recovery-arm64-v1.json
verifier=$repo/scripts/host/verify-steam-deck-recovery-builders.sh
responder_builder=$repo/scripts/host/build-persistent-root-verifier-image.sh
responder_recipe=$repo/containers/persistent-root-verifier/Dockerfile
bundle_recipe=$repo/containers/recovery-bundle-verifier/Dockerfile

for input in "$profile" "$verifier" "$responder_builder" "$responder_recipe" \
	"$bundle_recipe"; do
	[[ -f $input && ! -L $input ]] ||
		fail "missing recovery-builder contract input: ${input#"$repo"/}"
done
for script in "$verifier" "$responder_builder"; do
	[[ -x $script ]] ||
		fail "recovery-builder helper is not executable: ${script#"$repo"/}"
	bash -n "$script"
done

for token in \
	steam-deck-recovery-arm64-v1 \
	'"authority": "none"' \
	bfcd46c842441912baed36158569ac29a7fb656684ca73c1b3b2f0f3971e9bec \
	354ea9b62a7ec9f19501858e3e0d2c4f848faa93e639dccc36bb23f5a016c301 \
	a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e \
	13d758cd4c708ddb798dd539d1b6c4e3546ea5ef9129ed309c74bd8f4e620689 \
	89fde8f4651efe47ce5b2e78d44307520547f7e693ec8e2b2672e1a979119fcd \
	e6ab755c445f3388ccc04717346337f65c8d24ee892e078977b6bbe99f0b26b3 \
	c1e1b7b58f36b9ff091bed3b5de463d6239031729a49e12c07064c410de43fd0 \
	becc3fc1442823118fa75e79a9b756395df9f1b5b7df37440d4e2c8c5b4ef89c \
	374900be5769eee074820007ab2e335d4c033c500da7a480cc88f9a70137029b; do
	grep -Fq -- "$token" "$profile" "$verifier" ||
		fail "recovery-builder profile omits contract token: $token"
done

for recipe in "$responder_recipe" "$bundle_recipe"; do
	grep -Fq "&& : >/var/log/apk.log" "$recipe" ||
		fail "recovery-builder recipe retains volatile APK log: ${recipe#"$repo"/}"
	grep -Fq "printf 'localhost" "$recipe" ||
		fail "recovery-builder recipe lacks hostname normalization: ${recipe#"$repo"/}"
done

grep -Fq \
	'expected_recipe_sha=3d074a3e8b7bc81f96086aa633b132a897ededa4349f88aa77be5fbea2e237f0' \
	"$responder_builder" ||
	fail 'persistent verifier builder lacks its recipe identity gate'

if grep -Eq '\b(sudo|pkexec|fastboot|adb|ssh|scp)\b|/dev/(sd|nvme|ufs)' \
	"$profile" "$verifier" "$responder_builder" "$responder_recipe" \
	"$bundle_recipe"; then
	fail 'recovery-builder profile contains privilege, phone, or storage transport'
fi

echo 'PASS Steam Deck recovery builders are normalized, identity-bound, and host-only'
