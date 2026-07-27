#!/bin/sh
set -eu

linux_source=${1:?usage: validate-wifi-candidate-dtb.sh LINUX_SOURCE BASE_DTB OUTPUT_DIR}
base=${2:?missing accepted network-root v8 DTB}
output_dir=${3:?missing empty output directory}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-wifi.dtso
builder=$repo/scripts/device/build-wifi-candidate-dtb.sh
image=${DTSCHEMA_IMAGE:-localhost/rog5-dtschema:2026.6}
expected_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_base=0fb6d415597630508779263693803af40f35496adee17e82995b0189b2aa9c78
schema_limit=qcom,qca6390-pmu:qcom,ath11k-pci:qcom,pcie-sm8350:qcom,sc8280xp-qmp-pcie-phy:qcom,rpmh-regulator:qcom,sm8350-tlmm

for tool in git podman readlink sha256sum cmp mkdir mv; do
	command -v "$tool" >/dev/null
done
[ -x "$builder" ] && [ -r "$overlay" ] && [ -s "$base" ]
[ -d "$linux_source/.git" ] || {
	echo 'FAIL missing pinned Linux source' >&2
	exit 1
}
[ "$(git -C "$linux_source" rev-parse HEAD)" = "$expected_commit" ] || {
	echo 'FAIL Linux source is not the pinned v7.1.4 commit' >&2
	exit 1
}
[ -z "$(git -C "$linux_source" status --porcelain)" ] || {
	echo 'FAIL Linux source is dirty' >&2
	exit 1
}
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] || {
	echo 'FAIL DT schema input is not the accepted network-root v8 DTB' >&2
	exit 1
}
podman image exists "$image" || {
	echo "FAIL missing $image; build containers/dtschema/Dockerfile first" >&2
	exit 1
}
[ "$(podman run --rm --network=none "$image" dt-validate --version)" = 2026.6 ]

source_real=$(readlink -f -- "$linux_source")
base_real=$(readlink -f -- "$base")
output_real=$(readlink -m -- "$output_dir")
[ ! -d "$output_real" ] ||
	[ -z "$(find "$output_real" -mindepth 1 -maxdepth 1 -print -quit)" ] || {
		echo 'FAIL DT schema output directory is not empty' >&2
		exit 1
	}
mkdir -p "$output_real"

base_hash=$(sha256sum "$base_real" | cut -d ' ' -f 1)
"$builder" "$base_real" "$overlay" "$output_real/candidate-a.dtb" >/dev/null
"$builder" "$base_real" "$overlay" "$output_real/candidate-b.dtb" >/dev/null
cmp "$output_real/candidate-a.dtb" "$output_real/candidate-b.dtb"
[ "$(sha256sum "$base_real" | cut -d ' ' -f 1)" = "$base_hash" ]

podman run --rm --network=none \
	--mount "type=bind,src=$source_real,target=/linux,ro" \
	--mount "type=bind,src=$output_real,target=/out,rw" \
	"$image" dt-mk-schema -j -o /out/processed-schema.json \
	/linux/Documentation/devicetree/bindings
podman run --rm --network=none \
	--mount "type=bind,src=$output_real,target=/work,ro" \
	"$image" dt-validate -s /work/processed-schema.json \
	-l "$schema_limit" /work/candidate-a.dtb

image_id=$(podman image inspect --format '{{.Id}}' "$image")
{
	printf 'kernel_commit=%s\n' "$expected_commit"
	printf 'dtschema_version=2026.6\n'
	printf 'dtschema_image=%s\n' "$image"
	printf 'dtschema_image_id=%s\n' "$image_id"
	printf 'base_sha256=%s\n' "$base_hash"
	printf 'overlay_sha256=%s\n' \
		"$(sha256sum "$overlay" | cut -d ' ' -f 1)"
	printf 'candidate_sha256=%s\n' \
		"$(sha256sum "$output_real/candidate-a.dtb" | cut -d ' ' -f 1)"
	printf 'processed_schema_sha256=%s\n' \
		"$(sha256sum "$output_real/processed-schema.json" | cut -d ' ' -f 1)"
	printf 'schema_limit=%s\n' "$schema_limit"
} >"$output_real/schema-meta.txt.tmp"
mv "$output_real/schema-meta.txt.tmp" "$output_real/schema-meta.txt"

cat "$output_real/schema-meta.txt"
echo 'PASS two identical Wi-Fi DTBs satisfy pinned WCN6855, PCIe0, QMP PHY, RPMh regulator, and SM8350 pinctrl schemas'
