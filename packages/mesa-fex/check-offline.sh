#!/bin/sh
# Offline checks of a packages/mesa-fex build against FEX's x86 guest root,
# on an x86_64 host (no Adreno needed):
#
#   check-offline.sh OUT GUEST [WORK]
#     OUT    build.sh output (r<N>/)
#     GUEST  the unpacked guest root: unsquashfs -d GUEST ArchLinux.sqsh
#            (the image in RootFS_links.json; mountpoints dev/proc/tmp are
#            created in it)
#     WORK   build tree (optional: checks the generated A660 device table)
#
# - both drivers are ELF of the right class and export the same symbols as
#   the guest's own drivers, with the same NEEDED libraries;
# - inside the guest root (bwrap), `ldd -r` resolves every library, symbol
#   and symbol version (so nothing needs a newer glibc/libstdc++/libdrm than
#   the guest has);
# - inside the guest root, the Vulkan loader loads each driver through
#   VK_DRIVER_FILES and Turnip creates an instance (TU_DEBUG=startup; with no
#   Adreno it then finds no device; the guest's own drivers are the control);
# - the ICD manifests and 00-turnip-defaults.conf built with it equal the
#   guest's, so only the two libraries need replacing;
# - the generated device table gives the A660 storage_8bit.
set -eu
out=$(CDPATH='' cd -- "$1" && pwd) guest=$(CDPATH='' cd -- "$2" && pwd) work=${3-}
L64=usr/lib/libvulkan_freedreno.so L32=usr/lib32/libvulkan_freedreno.so
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
fail() { echo "FAIL $*"; exit 1; }
mkdir -p "$guest/dev" "$guest/proc" "$guest/tmp"
in_guest() { bwrap --ro-bind "$guest" / --dev /dev --proc /proc --tmpfs /tmp --ro-bind "$out" /tmp/t --ro-bind "$t" /tmp/c --unshare-all "$@"; }

(cd "$out" && sha256sum -c --quiet SHA256SUMS) || fail "SHA256SUMS"
(cd "$guest" && sha256sum -c --quiet "$out/BASE.SHA256SUMS") ||
	fail "the guest root's drivers are not the ones in BASE.SHA256SUMS (another FEX image?)"

file -b "$out/$L64" | grep -q '^ELF 64-bit LSB shared object, x86-64' || fail "$L64: $(file -b "$out/$L64")"
file -b "$out/$L32" | grep -q '^ELF 32-bit LSB shared object, Intel' || fail "$L32: $(file -b "$out/$L32")"
for f in $L64 $L32; do
	readelf -d "$out/$f" | awk '/NEEDED/ {print $NF}' | sort >"$t/new.needed"
	readelf -d "$guest/$f" | awk '/NEEDED/ {print $NF}' | sort >"$t/old.needed"
	cmp -s "$t/new.needed" "$t/old.needed" || fail "$f: NEEDED differs from the guest's: $(diff "$t/old.needed" "$t/new.needed" | grep '^[<>]' | tr '\n' ' ')"
	nm -D --defined-only "$out/$f" | awk '{print $NF}' | sort >"$t/new.syms"
	nm -D --defined-only "$guest/$f" | awk '{print $NF}' | sort >"$t/old.syms"
	cmp -s "$t/new.syms" "$t/old.syms" || fail "$f: exported symbols differ from the guest's"
	in_guest /usr/bin/ldd -r "/tmp/t/$f" >"$t/ldd" 2>&1 || fail "$f: ldd -r failed in the guest root: $(cat "$t/ldd")"
	! grep -Eq 'not found|undefined symbol' "$t/ldd" || fail "$f: unresolved in the guest root: $(grep -E 'not found|undefined symbol' "$t/ldd" | head -5)"
	strings -a "$out/$f" | grep -q "^Mesa 26.2.0-rog5\.[0-9]* (git-9f0a761020)\$\|26.2.0-rog5\.[0-9]*" || fail "$f: no 26.2.0-rog5 version string"
done
echo "PASS ELF class, NEEDED and exported symbols as the guest's; ldd -r resolves everything in the guest root"

# Vulkan loader + vkCreateInstance in the guest root, new and original drivers
for a in x86_64 i686; do
	case $a in x86_64) f=$L64 ;; i686) f=$L32 ;; esac
	for which in new orig; do
		lib=/tmp/t/$f; [ $which = new ] || lib=/$f
		printf '{"ICD":{"api_version":"1.4.354","library_path":"%s"},"file_format_version":"1.0.1"}\n' "$lib" >"$t/$which.$a.json"
		in_guest env VK_DRIVER_FILES="/tmp/c/$which.$a.json" VK_LOADER_DEBUG=driver TU_DEBUG=startup \
			"/tmp/t/s8test/s8test.$a" features >"$t/run" 2>&1 && st=0 || st=$?
		# no Adreno here: Turnip creates the instance, then finds no device
		grep -q 'TU: info: Created an instance' "$t/run" && [ "$st" = 2 ] ||
			fail "$a $which driver: Turnip did not create an instance in the guest root (exit $st): $(grep -iE 'error|fail|undefined' "$t/run" | head -5)"
		! grep -qiE 'failed to (open|load)|undefined symbol|wrong ELF' "$t/run" || fail "$a $which driver: loader: $(grep -iE 'failed|undefined|wrong ELF' "$t/run" | head -3)"
		grep -q "$lib" "$t/run" || fail "$a $which: the loader did not use $lib"
	done
done
echo "PASS the guest's Vulkan loader loads both drivers (x86_64 and i686) and creates an instance"

for a in x86_64 i686; do
	cmp -s "$guest/usr/share/vulkan/icd.d/freedreno_icd.$a.json" "$work/out/freedreno_icd.$a.json" 2>/dev/null ||
		{ [ -z "$work" ] || fail "freedreno_icd.$a.json differs from the guest's"; }
done
if [ -n "$work" ]; then
	cmp -s "$guest/usr/share/drirc.d/00-turnip-defaults.conf" "$work/out/00-turnip-defaults.conf" ||
		fail "00-turnip-defaults.conf differs from the guest's"
	echo "PASS ICD manifests and 00-turnip-defaults.conf equal the guest's"
	# The generated props of the FD660 entry.
	for b in build-x86_64 build-i686; do
		h=$work/$b/src/freedreno/common/freedreno_devices.h
		[ -f "$h" ] || fail "no $h"
		python3 - "$h" <<'PY' || fail "$b: A660 has no storage_8bit in the generated device table"
import re, sys
s = open(sys.argv[1]).read()
# table entry { {660, 0x60600ff}, "FD660", &__infoN }; __infoN is one line
m = re.search(r'"FD660"', s) or re.search(r'"Adreno \(TM\) 660"', s)
if not m:
    sys.exit("FD660 not in table")
# find the props struct the entry points at, then its storage_8bit field
entry = s[s.rfind('{', 0, m.start()) : s.find('}', m.end()) + 1]
ref = re.findall(r'&(\w+)', entry)
if not ref:
    sys.exit("no props reference in " + entry)
body = re.search(r'^static const struct fd_dev_info ' + re.escape(ref[-1]) + r' = (.*)$', s, re.M)
if not body or not re.search(r'\.storage_8bit\s*=\s*(True|true)\b', body.group(1)):
    sys.exit("storage_8bit not true for " + ref[-1])
PY
	done
	echo "PASS generated device table: FD660 has storage_8bit = true (x86_64 and i686 builds)"
fi
