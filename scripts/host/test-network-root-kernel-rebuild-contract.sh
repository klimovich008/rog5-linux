#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
fetcher=$repo/scripts/host/fetch-linux-stable-v7.1.4.sh
builder=$repo/scripts/host/build-network-root-kernel-offline.sh
device_builder=$repo/scripts/device/build-mainline-network-root.sh
device_verifier=$repo/scripts/device/verify-mainline-network-root-build.sh
historical_recipe=$repo/containers/kernel-builder/Dockerfile.historical-20260724
historical_verifier=$repo/scripts/host/verify-historical-network-root-builder.sh

for path in \
	"$fetcher" "$builder" "$device_builder" "$device_verifier" \
	"$historical_verifier"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable network-root rebuild contract: ${path#"$repo"/}"
	bash -n "$path"
done
[[ -f $historical_recipe && ! -L $historical_recipe ]] ||
	fail 'missing regular historical network-root builder recipe'

for token in \
	https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git \
	114456a9c542d933387517bb22561668c25a5b59 \
	7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 \
	2ea2be38c5e4dc9aafffbbc0db5aae0f6513a1d9 \
	'--depth=1 --no-tags' \
	'checkout --quiet -B "$expected_branch" FETCH_HEAD' \
	'Linux historical source unexpectedly retains the release tag ref' \
	'7.1.4-g7a5cef0db479' \
	'setlocalversion --no-local' \
	'fsck --strict --no-dangling' \
	'mv -T -- "$temporary" "$output"'; do
	grep -Fq -- "$token" "$fetcher" ||
		fail "Linux source fetcher omits contract token: $token"
done

for token in \
	'7.1.4-g7a5cef0db479' \
	'setlocalversion --no-local' \
	'FAIL source Git state yields kernel release' \
	'FAIL built kernel release changed' \
	'KBUILD_BUILD_USER=rog5-linux' \
	'KBUILD_BUILD_HOST=rog5-builder' \
	'KBUILD_BUILD_TIMESTAMP=' \
	'PYTHONHASHSEED=0' \
	'output directory is not empty' \
	'tar --sort=name --mtime=' \
	'--owner=0 --group=0' \
	'gzip -n'; do
	grep -Fq -- "$token" "$device_builder" ||
		fail "device network-root builder omits release gate: $token"
done

for token in \
	'7.1.4-g7a5cef0db479' \
	'include/config/kernel.release' \
	'Linux version $expected_release' \
	'module archive release changed' \
	'lib/modules/$expected_release/modules.dep'; do
	grep -Fq -- "$token" "$device_verifier" ||
		fail "device network-root verifier omits release gate: $token"
done

for token in \
	'verify-historical-network-root-builder.sh' \
	'localhost/rog5-kernel-builder:historical-20260724' \
	'--network=none' \
	'/root/src/linux-7.1.4:ro' \
	'/workspace/repo:ro' \
	'jobs_a=6' \
	'jobs_b=6' \
	'network-root kernel release changed' \
	'Linux historical source unexpectedly retains the release tag ref' \
	'7.1.4-g7a5cef0db479' \
	'setlocalversion --no-local' \
	'build-mainline-network-root.sh' \
	'verify-mainline-network-root-build.sh' \
	349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf \
	a1756e36f42a57c90bd85ef33d68aa1424768a45f272cc0514c2992ace0ae6e5 \
	68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f \
	5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9 \
	1cd315745755394ffceea7a2124800c63f8f67ca776fe4bdf47f9b296e1a4ecf \
	'independent network-root kernel builds differ' \
	'find "$output_root/a" -depth -delete'; do
	grep -Fq -- "$token" "$builder" ||
		fail "network-root kernel builder omits contract token: $token"
done

for token in \
	20260724T020000Z \
	2.39-0ubuntu8.7 \
	34ecc17078b364df195ad61253520b1cac487dca05773dc4b2fc2bacb0941941 \
	sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c \
	9310a47eab66545b98d69d5522313d064bfad17c80e1716f73e01119b83d4e22; do
	grep -Fq -- "$token" "$historical_recipe" "$historical_verifier" ||
		fail "historical network-root builder omits contract token: $token"
done

if grep -Eq \
	'\b(fastboot|adb|sudo|pkexec)\b|/dev/(sd|nvme|ufs)' \
	"$fetcher" "$builder" "$historical_recipe" "$historical_verifier"; then
	fail 'network-root rebuild contains phone, privilege, or storage transport'
fi

echo 'PASS network-root source and twin-build contracts are exact and host-isolated'
