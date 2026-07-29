#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
archive=$repo/artifacts/a660-runtime-builder/rog5-a660-runtime-builder-arch-2026.07.24.oci.tar
manifest=$repo/manifests/artifacts.tsv
image=localhost/rog5-a660-runtime-builder:arch-2026.07.24
expected_size=931880960
expected_hash=c38d64ea0642d659c66022a638167284876b804e8120a83304284a0d2b7af3a2
expected_id=8c84a3b902803fafcc2d9ab4671e6ff9b3ca1b9297cee55cdc4caad34b895e91
expected_layers='["sha256:622a01d66d32793ccf4a4198a7f76bd145b66558605171d51b4c15ff661ae715","sha256:88a5a305621e113fb7ee16a53dda1d0a477eb0aacd3d28216738e01d35e053b1"]'
expected_config='{"Env":["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin","LANG=C","LC_ALL=C","TZ=UTC"],"WorkingDir":"/workspace"}'
expected_packages=$'gcc 16.1.1+r12+g301eb08fa2c5-1\nlibisl 0.28-1\nlibmpc 1.4.1-1\npkgconf 3.0.4-1\nvulkan-headers 1:1.4.350.1-1\nvulkan-icd-loader 1.4.350.1-1'

for command in awk cut podman sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing A660 builder-image command: $command"
done
[[ -f $archive && ! -L $archive ]] ||
	fail 'pinned A660 runtime-builder OCI archive is absent or linked'
record=$(awk -F $'\t' \
	'$1 == "artifacts/a660-runtime-builder/rog5-a660-runtime-builder-arch-2026.07.24.oci.tar" {
		count++
		size=$2
		hash=$3
	}
	END {
		if (count == 1)
			print size "\t" hash
	}' "$manifest")
[[ $record == "$expected_size"$'\t'"$expected_hash" ]] ||
	fail 'A660 runtime-builder archive manifest identity changed'
[[ $(stat -c %s "$archive") == "$expected_size" ]] ||
	fail 'A660 runtime-builder archive size changed'
[[ $(sha256sum "$archive" | cut -d ' ' -f 1) == "$expected_hash" ]] ||
	fail 'A660 runtime-builder archive hash changed'

if podman image exists "$image"; then
	[[ $(podman image inspect "$image" --format '{{.Id}}') == "$expected_id" ]] ||
		fail 'canonical A660 runtime-builder tag is occupied'
else
	podman load --input "$archive" >/dev/null ||
		fail 'cannot load the pinned A660 runtime-builder archive'
fi
podman image exists "$image" ||
	fail 'pinned A660 runtime-builder image was not materialized'
[[ $(podman image inspect "$image" --format '{{.Architecture}}') == arm64 ]] ||
	fail 'A660 runtime-builder image is not arm64'
[[ $(podman image inspect "$image" --format '{{.Id}}') == "$expected_id" ]] ||
	fail 'A660 runtime-builder image identity changed'
[[ $(podman image inspect "$image" \
	--format '{{json .RootFS.Layers}}') == "$expected_layers" ]] ||
	fail 'A660 runtime-builder layer identity changed'
[[ $(podman image inspect "$image" --format '{{json .Config}}') == \
	"$expected_config" ]] ||
	fail 'A660 runtime-builder configuration changed'
observed_packages=$(podman run --rm --network none \
	--entrypoint /bin/cat "$image" \
	/usr/share/rog5-a660-builder-packages)
[[ $observed_packages == "$expected_packages" ]] ||
	fail 'A660 runtime-builder package identity changed'

printf 'format=rog5-a660-runtime-builder-image-v1\n'
printf 'image=%s\n' "$image"
printf 'image_id=%s\n' "$expected_id"
printf 'archive_sha256=%s\n' "$expected_hash"
printf 'packages_sha256=%s\n' \
	"$(printf '%s\n' "$observed_packages" | sha256sum | cut -d ' ' -f 1)"
