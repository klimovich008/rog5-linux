#!/bin/sh
# Build the x86_64 and i686 Turnip (libvulkan_freedreno.so) for FEX's x86
# guest root with the 8-bit storage patch (see README.md), in a podman
# container frozen at the guest's Arch package set, then check the result
# offline against the guest root image.
#
#   packages/mesa-fex/build.sh [release]      (default release 1; no root)
#
# Output (not in git): ${ROG5_MESA_FEX_DIR:-~/.local/state/rog5-mesa-fex}/
#   r<release>/usr/lib/libvulkan_freedreno.so, usr/lib32/libvulkan_freedreno.so,
#   SHA256SUMS, BUILDINFO, s8test/  -- copy that directory to the phone and
#   run steam-fex-turnip-8bit install on it.
set -eu
rel=${1:-1}
case $rel in *[!0-9]*|'') echo "build.sh: release must be a number" >&2; exit 1 ;; esac
here=$(CDPATH='' cd -- "$(dirname "$0")" && pwd)
top=${ROG5_MESA_FEX_DIR:-$HOME/.local/state/rog5-mesa-fex}
image=localhost/rog5-mesa-fex-builder:arch-20260812
tarball_sha256=efd4bb08cdb7c365a812cd4e6c9202ab55b2f22cdcd13c7d6c4f9647b799a4ef  # docs/relnotes/26.2.0.rst
out=$top/r$rel
[ ! -e "$out" ] || { echo "build.sh: $out exists; pick another release or remove it" >&2; exit 1; }
mkdir -p "$top/src" "$top/work"

tb=$top/src/mesa-26.2.0.tar.xz
if [ ! -f "$tb" ]; then
	curl -fsSL --retry 3 https://archive.mesa3d.org/mesa-26.2.0.tar.xz -o "$tb.part"
	mv "$tb.part" "$tb"
fi
echo "$tarball_sha256  $tb" | sha256sum -c --quiet || { echo "build.sh: bad mesa-26.2.0.tar.xz" >&2; exit 1; }

podman image exists "$image" || podman build -t "$image" -f "$here/Containerfile" "$here"

podman run --rm --network=none --userns=keep-id --user "$(id -u):$(id -g)" \
	-v "$here:/pkg:ro" -v "$here/../mesa:/patch:ro" -v "$top/src:/src:ro" -v "$top/work:/work:rw" \
	-e HOME=/work -e TMPDIR=/work \
	"$image" sh /pkg/container-build.sh "$rel"

w=$top/work/out
mkdir -p "$out.part"
cp -a "$w/payload/usr" "$w/s8test" "$out.part/"
cp "$w/build-packages.txt" "$w/toolchain.txt" "$w/storage_8bit.txt" "$out.part/"
{
	echo "release=$rel"
	echo "mesa=26.2.0 (tag mesa-26.2.0, 9f0a761020) + packages/mesa/0001-tu-enable-storageBuffer8BitAccess-on-a6xx-gen4.patch"
	echo "mesa_tarball_sha256=$tarball_sha256"
	echo "repo_commit=$(git -C "$here" rev-parse HEAD 2>/dev/null || echo unknown)$([ -z "$(git -C "$here" status --porcelain -- . ../mesa ../../scripts/device/steam-fex-turnip-8bit 2>/dev/null)" ] || echo -dirty)"
	echo "builder_image=$image $(podman image inspect "$image" --format '{{.Id}}')"
	echo "built=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
	sed 's/^/toolchain: /' "$w/toolchain.txt"
} >"$out.part/BUILDINFO"
(cd "$out.part" && sha256sum usr/lib/libvulkan_freedreno.so usr/lib32/libvulkan_freedreno.so >SHA256SUMS)
# the guest root's own drivers that this build replaces (FEX ArchLinux 2026-08-11)
cp "$here/BASE.SHA256SUMS" "$out.part/"
cp "$here/../../scripts/device/steam-fex-turnip-8bit" "$out.part/"
mv "$out.part" "$out"
echo "built: $out"
cat "$out/SHA256SUMS"

if [ -d "$top/rootfs/guest/usr/lib" ]; then
	sh "$here/check-offline.sh" "$out" "$top/rootfs/guest" "$top/work"
else
	echo "build.sh: no guest root at $top/rootfs/guest; run check-offline.sh after unpacking FEX's ArchLinux image there" >&2
fi
