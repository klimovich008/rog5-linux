#!/bin/sh
# Runs inside localhost/rog5-mesa-fex-builder (see build.sh): builds only
# Turnip (libvulkan_freedreno.so) from mesa-26.2.0 plus the 8-bit storage
# patch, for x86_64 (gcc) and i686 (clang -m32), with FEX-Emu's options for
# its ArchLinux root (buildtype release, b_ndebug, SSE math, kmds
# msm,virtio,kgsl, x11+wayland WSI, shader cache).
#
#   /pkg     packages/mesa-fex (ro)     /patch  packages/mesa (ro)
#   /src     mesa-26.2.0.tar.xz (ro)    /work   build tree and output (rw)
set -eu
rel=$1
cd /work
rm -rf mesa-26.2.0 build-x86_64 build-i686 out
tar -xf /src/mesa-26.2.0.tar.xz
cd mesa-26.2.0
patch -Np1 </patch/0001-tu-enable-storageBuffer8BitAccess-on-a6xx-gen4.patch
# driverInfo becomes "Mesa 26.2.0-rog5.<rel> (git-9f0a761020)": the base is
# the mesa-26.2.0 tag (9f0a761020), the suffix marks this build. The numeric
# driverVersion stays 26.2.0 (vk_get_driver_version stops at the '-').
echo "26.2.0-rog5.$rel" >VERSION
export MESA_GIT_SHA1_OVERRIDE=9f0a761020
cd /work

common="-Dbuildtype=release -Db_ndebug=true -Dprefix=/usr
  -Dvulkan-drivers=freedreno -Dgallium-drivers= -Dvulkan-layers= -Dtools=
  -Dfreedreno-kmds=msm,virtio,kgsl -Dplatforms=x11,wayland -Dshader-cache=enabled
  -Dopengl=false -Dgles1=disabled -Dgles2=disabled -Degl=disabled -Dglx=disabled
  -Dgbm=disabled -Dglvnd=disabled -Dllvm=disabled -Dvideo-codecs=
  -Dlibunwind=disabled -Dvalgrind=disabled -Dlmsensors=disabled
  -Dbuild-tests=false -Dhtml-docs=disabled -Dvulkan-manifest-per-architecture=true"
sse="-mfpmath=sse -msse -msse2 -mstackrealign"

# shellcheck disable=SC2086
meson setup build-x86_64 mesa-26.2.0 $common -Dlibdir=/usr/lib \
	-Dc_args="$sse" -Dcpp_args="$sse"
meson compile -C build-x86_64
DESTDIR=/work/out/stage-x86_64 meson install -C build-x86_64 --no-rebuild >/dev/null

# shellcheck disable=SC2086
meson setup build-i686 mesa-26.2.0 $common -Dlibdir=/usr/lib32 --cross-file /pkg/cross-i686.ini
meson compile -C build-i686
DESTDIR=/work/out/stage-i686 meson install -C build-i686 --no-rebuild >/dev/null

# The payload: the two drivers only. The guest keeps its own ICD manifests
# (same library paths) and drirc files (from the same 26.2.0 tree).
p=/work/out/payload
install -Dm755 out/stage-x86_64/usr/lib/libvulkan_freedreno.so "$p/usr/lib/libvulkan_freedreno.so"
install -Dm755 out/stage-i686/usr/lib32/libvulkan_freedreno.so "$p/usr/lib32/libvulkan_freedreno.so"
for a in x86_64 i686; do
	cp out/stage-$a/usr/share/vulkan/icd.d/freedreno_icd.$a.json out/
	cp out/stage-$a/usr/share/drirc.d/00-turnip-defaults.conf out/00-turnip-defaults.conf
done

# Proof that the a6xx gen4 props (A660) carry storage_8bit in this build.
grep -n 'storage_8bit' mesa-26.2.0/src/freedreno/common/freedreno_devices.py >out/storage_8bit.txt

# s8test (packages/mesa/s8test) for x86_64 and i686, to run under FEX.
t=/work/out/s8test; mkdir -p "$t"
glslangValidator --target-env vulkan1.3 -V /patch/s8test/s8test.comp -o "$t/s8test.spv" >/dev/null
glslangValidator --target-env vulkan1.3 -DRMW -V /patch/s8test/s8test.comp -o "$t/s8rmw.spv" >/dev/null
gcc -O2 -Imesa-26.2.0/include /patch/s8test/s8test.c -o "$t/s8test.x86_64" -lvulkan
clang -m32 -O2 -Imesa-26.2.0/include /patch/s8test/s8test.c -o "$t/s8test.i686" -L/usr/lib32 -lvulkan

pacman -Q >out/build-packages.txt
{ gcc --version | head -1; clang --version | head -1; meson --version; } >out/toolchain.txt
