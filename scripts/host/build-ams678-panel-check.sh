#!/usr/bin/env bash
# Offline exact-base applicability and one affected ARM64 object, not a phone build.
set -euo pipefail
kernel_git() {
 local ceiling=$1
 shift
 (
  # A caller's repository/index/object-store settings must not redirect the
  # isolated archive or patch application. Keep the caller's shell unchanged.
  for git_name in "${!GIT_@}"; do unset "$git_name"; done
  export GIT_CEILING_DIRECTORIES="$ceiling"
  command git "$@"
 )
}
apply_panel_patch() {
 kernel_git "$(dirname "$1")" -C "$1" apply --check "$2"
 kernel_git "$(dirname "$1")" -C "$1" apply "$2"
}
[[ $# == 2 ]] || { echo 'usage: build-ams678-panel-check.sh LINUX_GIT OUTPUT_DIRECTORY' >&2; exit 2; }
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
linux_git=$(realpath -e -- "$1")
output=$(realpath -m -- "$2")
base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
patch=$repo/patches/linux-7.1.4/0037-drm-panel-add-ASUS-ROG-Phone-5-AMS678-ER2.patch
[[ ! -e $output && ! -L $output ]] || { echo 'FAIL output already exists' >&2; exit 1; }
[[ $(kernel_git "$(dirname "$linux_git")" -C "$linux_git" rev-parse "$base^{commit}") == "$base" ]]
# Archive immutable Git bytes; neither checkout cleanliness nor HEAD implies
# these inputs, and the supplied checkout/worktrees are never modified.
mkdir -p "$output/source" "$output/objects"
kernel_git "$(dirname "$linux_git")" -C "$linux_git" archive "$base" | tar -x -C "$output/source"
apply_panel_patch "$output/source" "$patch"
echo "PASS applicability: exact Linux base $base"
python3 "$repo/scripts/device/test-ams678-lifecycle.py" --linux-source "$output/source"
python3 "$repo/scripts/device/test-ams678-regulator-errors.py" --linux-source "$output/source"
export KBUILD_BUILD_TIMESTAMP='2026-07-18 00:00:00 UTC'
export KBUILD_BUILD_USER=rog5 KBUILD_BUILD_HOST=panel-check
make -s -C "$output/source" O="$output/objects" ARCH=arm64 LLVM=1 defconfig
"$output/source/scripts/config" --file "$output/objects/.config" \
 --enable OF --enable GPIOLIB --enable REGULATOR --enable DRM \
 --enable DRM_MIPI_DSI --enable BACKLIGHT_CLASS_DEVICE \
 --enable DRM_PANEL_ASUS_ROG5_AMS678
make -s -C "$output/source" O="$output/objects" ARCH=arm64 LLVM=1 olddefconfig
grep -Fqx 'CONFIG_DRM_PANEL_ASUS_ROG5_AMS678=y' "$output/objects/.config"
make -s -C "$output/source" O="$output/objects" ARCH=arm64 LLVM=1 -j2 \
 drivers/gpu/drm/panel/panel-asus-rog5-ams678.o
object=$output/objects/drivers/gpu/drm/panel/panel-asus-rog5-ams678.o
llvm-readelf -h "$object" | grep -q 'Machine:.*AArch64'
{
 printf 'base=%s\n' "$base"
 printf 'scope=affected ARM64 object, ARM64 defconfig plus panel\n'
 clang --version | head -1
 sha256sum "$patch" "$output/source/drivers/gpu/drm/drm_panel.c" \
  "$output/source/drivers/gpu/drm/bridge/panel.c" \
  "$output/source/drivers/gpu/drm/panel/panel-asus-rog5-ams678.c" \
  "$output/objects/.config" "$object"
} > "$output/identity.txt"
cat "$output/identity.txt"
echo 'PASS compilation: affected ARM64 panel object on exact base'
echo 'NOT RUN full phone configuration, linking/module load, physical panel validation'
