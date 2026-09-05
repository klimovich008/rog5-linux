#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
project_root=$(dirname "$repo")
p2_kernel=${1:-$project_root/p2-kernel-release.dhCvZt}
p2_osrelease=${2:-$project_root/p2-osrelease.mCnixe}
config_output=$repo/artifacts/recovery-stage-v18/config-5.4.210-kexec-stage-builtin-recovery
v18r=$repo/artifacts/recovery-inputs-v18r/rog5-recovery-base-v18r.cpio.gz
package_root=$repo/artifacts/recovery-inputs
static_image=localhost/rog5-persistent-root-verifier:alpine-3.24-deck-v1
arm64_runner=$repo/scripts/host/run-private-arm64-binfmt.sh

for command_name in cmp cp curl cut dirname install mkdir mktemp mv podman \
	rm sha256sum stat; do
	command -v "$command_name" >/dev/null ||
		fail "missing recovery-input restoration command: $command_name"
done
[[ -f $arm64_runner && ! -L $arm64_runner && -x $arm64_runner ]] ||
	fail 'missing private ARM64 execution helper'

check_exact() {
	path=$1
	size=$2
	hash=$3
	label=$4
	[[ -f $path && ! -L $path && -r $path ]] ||
		fail "missing, linked, or unreadable $label"
	[[ $(stat -c %s "$path") == "$size" ]] ||
		fail "$label size changed"
	[[ $(sha256sum "$path" | cut -d ' ' -f 1) == "$hash" ]] ||
		fail "$label hash changed"
}

restore_exact() {
	first=$1
	second=$2
	output=$3
	size=$4
	hash=$5
	label=$6
	check_exact "$first" "$size" "$hash" "$label first lineage"
	check_exact "$second" "$size" "$hash" "$label second lineage"
	cmp "$first" "$second" ||
		fail "$label retained lineages differ"
	if [[ -e $output || -L $output ]]; then
		check_exact "$output" "$size" "$hash" "$label output"
		return
	fi
	mkdir -p "$(dirname "$output")"
	temporary=$(mktemp "$(dirname "$output")/.${output##*/}.tmp.XXXXXX")
	cp --reflink=never -- "$first" "$temporary"
	chmod 0644 "$temporary"
	check_exact "$temporary" "$size" "$hash" "$label temporary output"
	mv -T -- "$temporary" "$output"
}

restore_exact \
	"$p2_kernel/wrapper-a.config" \
	"$p2_osrelease/wrapper-a.config" \
	"$config_output" \
	185763 \
	df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f \
	'accepted ASUS wrapper config'

if [[ ! -e $v18r && ! -L $v18r ]]; then
	"$repo/scripts/host/reconstruct-recovery-base-v18r.sh"
fi
check_exact "$v18r" 5838975 \
	da573d089cd617e088624b6d6bf711e193a4df5367843293e2e5ba543556e51d \
	'reconstructed v18r recovery base'

mkdir -p "$package_root"
download_exact() {
	name=$1
	url=$2
	size=$3
	hash=$4
	output=$package_root/$name
	if [[ -e $output || -L $output ]]; then
		check_exact "$output" "$size" "$hash" "$name"
		return
	fi
	partial=$package_root/.$name.part
	[[ ! -e $partial && ! -L $partial ]] ||
		fail "refusing stale partial package: $name"
	curl --fail --location --retry 3 --proto '=https' --tlsv1.2 \
		--output "$partial" "$url"
	check_exact "$partial" "$size" "$hash" "$name downloaded package"
	chmod 0644 "$partial"
	mv -T -- "$partial" "$output"
}

download_exact \
	kexec-tools-2.0.32-r2.apk \
	https://dl-cdn.alpinelinux.org/alpine/v3.24/community/aarch64/kexec-tools-2.0.32-r2.apk \
	80911 \
	bd8b6951f862af1123972b521c355c655b7a2f40c2bf9cfe700edd590a101c94
download_exact \
	xz-libs-5.8.3-r0.apk \
	https://dl-cdn.alpinelinux.org/alpine/v3.24/main/aarch64/xz-libs-5.8.3-r0.apk \
	118819 \
	76dce86852903fef7adba0285d816e5ce9ffbe9fb3ca86bbb349b97afaba1f63
download_exact \
	zstd-libs-1.5.7-r2.apk \
	https://dl-cdn.alpinelinux.org/alpine/v3.24/main/aarch64/zstd-libs-1.5.7-r2.apk \
	365383 \
	2bb5136c89f5b0bbe1554c8915a3b520d5aa63ae2a51d4d821eb81698db5a818

podman image exists "$static_image" ||
	fail 'missing exact static-verifier image; run build-persistent-root-verifier-image.sh first'
[[ $(podman image inspect "$static_image" --format '{{.Id}}') == \
	a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e ]] ||
	fail 'unexpected static-verifier image identity during APK verification'
"$arm64_runner" podman run --rm --network=none --platform linux/arm64 \
	-v "$package_root:/input:ro" \
	"$static_image" apk --no-network verify \
	"/input/kexec-tools-2.0.32-r2.apk" \
	"/input/xz-libs-5.8.3-r0.apk" \
	"/input/zstd-libs-1.5.7-r2.apk"

sha256sum "$config_output" "$v18r" \
	"$package_root/kexec-tools-2.0.32-r2.apk" \
	"$package_root/xz-libs-5.8.3-r0.apk" \
	"$package_root/zstd-libs-1.5.7-r2.apk"
echo 'PASS restored minimal exact stable-recovery inputs; APK signatures verified offline'
