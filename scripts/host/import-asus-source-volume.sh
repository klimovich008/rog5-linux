#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
source_argument=${1:?usage: import-asus-source-volume.sh SOURCE_DIR [VOLUME]}
volume=${2:-rog5-asus-v12a-source}
expected_tree=592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a
verifier=$repo/scripts/host/verify-asus-source-tree.py

for command in cp find install podman python3 realpath; do
	command -v "$command" >/dev/null ||
		fail "missing source-volume command: $command"
done
[[ $volume =~ ^rog5-[A-Za-z0-9_.-]+$ ]] ||
	fail 'source volume must have a bounded rog5-* name'
[[ -d $source_argument && ! -L $source_argument ]] ||
	fail 'ASUS source argument must be a real directory, not a symlink'
source_dir=$(realpath -e -- "$source_argument")
[[ -x $verifier ]] ||
	fail 'missing executable ASUS source-volume input'

"$verifier" "$source_dir"
[[ $(podman info --format '{{.Host.Security.Rootless}}') == true ]] ||
	fail 'ASUS source-volume import requires rootless Podman'
graph_root=$(realpath -e -- "$(podman info --format '{{.Store.GraphRoot}}')")
if podman volume exists "$volume"; then
	fail "refusing existing Podman volume: $volume"
fi

created=false
published=false
import_id=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
owns_volume() {
	podman volume exists "$volume" &&
		[[ $(podman volume inspect --format \
			'{{ index .Labels "org.rog5.import-id" }}' "$volume" 2>/dev/null) == \
			"$import_id" ]]
}
cleanup() {
	if [[ $created == true && $published != true ]] && owns_volume; then
		podman volume rm "$volume" >/dev/null
	fi
}
trap cleanup EXIT HUP INT TERM

podman volume create \
	--label org.rog5.purpose=accepted-asus-5.4-source \
	--label org.rog5.source-tree-sha256="$expected_tree" \
	--label org.rog5.import-id="$import_id" \
	"$volume" >/dev/null
created=true
owns_volume || fail 'new ASUS source volume lost its importer identity'

mountpoint=$(
	podman volume inspect --format '{{.Mountpoint}}' "$volume"
)
mountpoint=$(realpath -e -- "$mountpoint")
expected_mountpoint=$graph_root/volumes/$volume/_data
[[ $mountpoint == "$expected_mountpoint" ]] ||
	fail 'new ASUS source volume escaped the rootless local store'
[[ -z $(find "$mountpoint" -mindepth 1 -print -quit) ]] ||
	fail 'new ASUS source volume is unexpectedly nonempty'
install -d -m 0755 "$mountpoint/msm-5.4"
cp -a "$source_dir/." "$mountpoint/msm-5.4/"

seal=$("$verifier" "$mountpoint/msm-5.4")

published=true
trap - EXIT HUP INT TERM
printf '%s\n' "$seal"
printf 'volume=%s\n' "$volume"
echo 'PASS imported accepted ASUS source into a new rootless Podman volume'
