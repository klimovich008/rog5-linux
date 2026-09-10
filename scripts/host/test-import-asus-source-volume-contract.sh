#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
importer=$repo/scripts/host/import-asus-source-volume.sh
verifier=$repo/scripts/host/verify-asus-source-tree.py
profile=$repo/configs/recovery-wrapper-cache/asus-5.4-stable-recovery-v1.json

for path in "$importer" "$verifier" "$profile"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing regular ASUS source-volume input: ${path#"$repo"/}"
done
[[ -x $importer && -x $verifier ]] ||
	fail 'ASUS source-volume tools are not executable'
bash -n "$importer"
python3 -m py_compile "$verifier"

for token in \
	rog5-asus-v12a-source \
	592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a \
	'podman volume exists' \
	'podman volume create' \
	'podman volume inspect' \
	'podman volume rm' \
	'org.rog5.import-id' \
	'owns_volume' \
	'{{.Host.Security.Rootless}}' \
	'{{.Store.GraphRoot}}' \
	'{{.Mountpoint}}' \
	'/volumes/$volume/_data' \
	'! -L $source_argument' \
	'cp -a' \
	'verify-asus-source-tree.py'; do
	grep -Fq -- "$token" "$importer" ||
		fail "source-volume importer lost contract token: $token"
done

for token in \
	c6b06b44561506d3adfd7c3d49ef5d3476356d8aa0061fc3dec11bbf8496a4c7 \
	'/workspace/repo/patches/asus-5.4.210' \
	'ASUS source tree seal changed' \
	'ASUS source marker does not bind the tracked patch set'; do
	grep -Fq -- "$token" "$verifier" ||
		fail "source verifier lost contract token: $token"
done

if grep -Eq '\bsudo\b|fastboot|adb|/dev/(sd|nvme|ufs)' \
	"$importer" "$verifier"; then
	fail 'ASUS source-volume tooling contains privilege, phone, or raw-storage actions'
fi
if grep -Eq 'podman volume rm[^"$]*--force|podman system (prune|reset)' \
	"$importer"; then
	fail 'ASUS source-volume cleanup is unbounded'
fi
if grep -Eq 'podman run|podman image|bootstrap-kernel-builder' "$importer"; then
	fail 'ASUS source import depends on a kernel-builder image'
fi

grep -Fq '"source_marker_sha256": "e75e158352a6b58fb68ccb89f40f17d00555a0ea0525334b0d67146cf58b00cc"' \
	"$profile" ||
	fail 'source-volume profile marker identity changed'
grep -Fq '"source_tree_sha256": "592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a"' \
	"$profile" ||
	fail 'source-volume profile tree identity changed'

echo 'PASS accepted ASUS source verification and volume-import contract'
