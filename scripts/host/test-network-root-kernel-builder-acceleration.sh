#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/device/build-mainline-network-root.sh
contract=$repo/scripts/device/kernel-build-contract.sh
work=$(mktemp -d)
holder_pid=
cleanup() {
	[[ -z ${holder_pid:-} ]] || kill "$holder_pid" 2>/dev/null || true
	rm -rf -- "$work"
}
trap cleanup EXIT HUP INT TERM

source_dir=$work/source
device_dir=$work/device
fake_bin=$work/bin
base_fragment=$work/base.fragment
network_fragment=$work/network.fragment
make_log=$fake_bin/make.log
release=7.1.4-gfake
mkdir -p "$source_dir/scripts/kconfig" "$device_dir" "$fake_bin"
cp -- "$builder" "$device_dir/build-mainline-network-root.sh"
cp -- "$contract" "$device_dir/kernel-build-contract.sh"
chmod 0755 "$device_dir"/*.sh
printf '%s\n' 'CONFIG_BASE_TEST=y' >"$base_fragment"
printf '%s\n' 'CONFIG_NETWORK_ROOT_TEST=y' >"$network_fragment"

cat >"$source_dir/scripts/setlocalversion" <<'EOF'
#!/bin/sh
printf '%s\n' '7.1.4-gfake'
EOF
cat >"$source_dir/scripts/kconfig/merge_config.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
output=
arguments=("$@")
for ((index = 0; index < ${#arguments[@]}; index++)); do
	if [[ ${arguments[$index]} == -O ]]; then
		output=${arguments[$((index + 1))]}
	fi
done
[[ -n $output ]]
count=${#arguments[@]}
cat -- "${arguments[$((count - 2))]}" "${arguments[$((count - 1))]}" \
	>>"$output/.config"
EOF
chmod 0755 "$source_dir/scripts/setlocalversion" \
	"$source_dir/scripts/kconfig/merge_config.sh"

cat >"$fake_bin/make" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
output=
modules_stage=
for argument in "$@"; do
	case $argument in
		O=*) output=${argument#O=} ;;
		INSTALL_MOD_PATH=*) modules_stage=${argument#INSTALL_MOD_PATH=} ;;
	esac
done
[[ -n $output ]]
printf '%s\n' "$*" >>"$(dirname "$0")/make.log"
case " $* " in
	*' defconfig '*)
		mkdir -p "$output"
		printf '%s\n' 'CONFIG_FAKE_DEFCONFIG=y' >"$output/.config"
		;;
	*' Image.gz modules '*)
		mkdir -p "$output/arch/arm64/boot" "$output/include/config"
		printf '%s\n' 'deterministic fake kernel image' \
			>"$output/arch/arm64/boot/Image"
		gzip -n -c "$output/arch/arm64/boot/Image" \
			>"$output/arch/arm64/boot/Image.gz"
		printf '%s\n' '7.1.4-gfake' >"$output/include/config/kernel.release"
		;;
	*' modules_install '*)
		[[ -n $modules_stage ]]
		mkdir -p "$modules_stage/lib/modules/7.1.4-gfake/kernel"
		printf '%s\n' 'fake module' \
			>"$modules_stage/lib/modules/7.1.4-gfake/kernel/fake.ko"
		printf '%s\n' 'kernel/fake.ko:' \
			>"$modules_stage/lib/modules/7.1.4-gfake/modules.dep"
		;;
esac
EOF
cat >"$fake_bin/clang" <<'EOF'
#!/bin/sh
printf '%s\n' 'clang version rog5-fake-1'
EOF
cat >"$fake_bin/ccache" <<'EOF'
#!/bin/sh
if [ "${1:-}" = --show-stats ]; then
	printf '%s\n' 'Cacheable calls: 0 / 0'
	exit 0
fi
if [ "${1:-}" = --show-config ]; then
	printf '%s\n' 'cache_dir = /tmp/rog5-fake-cache'
	exit 0
fi
exit 0
EOF
cat >"$fake_bin/tool-stub" <<'EOF'
#!/bin/sh
exit 0
EOF
chmod 0755 "$fake_bin/make" "$fake_bin/clang" "$fake_bin/ccache" \
	"$fake_bin/tool-stub"
for tool in clang++ ld.lld llvm-ar llvm-nm llvm-objcopy llvm-strip \
	llvm-objdump llvm-readelf pahole bc bison flex depmod; do
	cp -- "$fake_bin/tool-stub" "$fake_bin/$tool"
done

git -C "$source_dir" init -q
git -C "$source_dir" config user.name 'ROG5 Test'
git -C "$source_dir" config user.email 'rog5-test@example.invalid'
git -C "$source_dir" add scripts
GIT_AUTHOR_DATE='2026-01-01T00:00:00+00:00' \
GIT_COMMITTER_DATE='2026-01-01T00:00:00+00:00' \
	git -C "$source_dir" commit -q -m 'fake source'
commit=$(git -C "$source_dir" rev-parse HEAD)

export PATH="$fake_bin:/usr/bin:/bin"

if env ROG5_NETWORK_ROOT_CLEAN_ENV=1 KCFLAGS=-DHOSTILE \
	SOURCE_DIR="$source_dir" OUTPUT_DIR="$work/marker-bypass" \
	BASE_FRAGMENT="$base_fragment" NETWORK_FRAGMENT="$network_fragment" \
	LINUX_COMMIT="$commit" EXPECTED_RELEASE="$release" JOBS=1 \
	INCREMENTAL_BUILD=0 KBUILD_CCACHE=0 \
	"$device_dir/build-mainline-network-root.sh" \
	>$work/marker-bypass.out 2>$work/marker-bypass.err; then
	fail 'caller-supplied clean-environment marker bypassed sanitization'
fi
grep -Fq 'network-root builder environment is not the exact allowlist' \
	"$work/marker-bypass.err" || fail 'marker bypass returned the wrong refusal'
if /usr/bin/env -i PATH="$PATH" HOME="$HOME" LC_ALL=C.UTF-8 \
	SOURCE_DIR="$source_dir" OUTPUT_DIR="$work/locale-bypass" \
	BASE_FRAGMENT="$base_fragment" NETWORK_FRAGMENT="$network_fragment" \
	LINUX_COMMIT="$commit" EXPECTED_RELEASE="$release" JOBS=1 \
	INCREMENTAL_BUILD=0 KBUILD_CCACHE=0 ROG5_NETWORK_ROOT_CLEAN_ENV=1 \
	"$device_dir/build-mainline-network-root.sh" \
	>$work/locale-bypass.out 2>$work/locale-bypass.err; then
	fail 'caller-supplied clean marker accepted a noncanonical locale'
fi
grep -Fq 'network-root builder environment is not the exact allowlist' \
	"$work/locale-bypass.err" || fail 'locale bypass returned the wrong refusal'

run_builder() {
	output=$1
	shift
	env SOURCE_DIR="$source_dir" OUTPUT_DIR="$output" \
		BASE_FRAGMENT="$base_fragment" NETWORK_FRAGMENT="$network_fragment" \
		LINUX_COMMIT="$commit" EXPECTED_RELEASE="$release" "$@" \
		"$device_dir/build-mainline-network-root.sh"
}

clean_a=$work/clean-a
clean_b=$work/clean-b
cached=$work/clean-ccache
run_builder "$clean_a" JOBS=1 INCREMENTAL_BUILD=0 KBUILD_CCACHE=0 \
	>$work/clean-a.out
state_before=$(sha256sum "$clean_a/.rog5-kbuild-inputs-v1")
printf '%s\n' keep >"$clean_a/reuse-marker"
run_builder "$clean_a" JOBS=4 INCREMENTAL_BUILD=1 KBUILD_CCACHE=0 \
	>$work/incremental.out
[[ -f $clean_a/reuse-marker &&
	$(sha256sum "$clean_a/.rog5-kbuild-inputs-v1") == "$state_before" ]] ||
	fail 'exact-state incremental build did not reuse its output tree'
image_before=$(sha256sum "$clean_a/arch/arm64/boot/Image")
run_builder "$clean_a" JOBS=2 INCREMENTAL_BUILD=1 KBUILD_CCACHE=0 \
	KCFLAGS=-DHOSTILE KBUILD_MODPOST_NOFINAL=1 KRUSTFLAGS=-DHOSTILE \
	KCPPFLAGS=-DHOSTILE KBUILD_BUILD_VERSION=999 GNUMAKEFLAGS=-k \
	CCACHE_PREFIX=hostile MAKEFLAGS=-k >"$work/sanitized-environment.out"
[[ $(sha256sum "$clean_a/arch/arm64/boot/Image") == "$image_before" ]] ||
	fail 'sanitized Kbuild environment changed release output'

printf '%s\n' 'CONFIG_INPUT_CHANGED=y' >>"$network_fragment"
if run_builder "$clean_a" JOBS=2 INCREMENTAL_BUILD=1 KBUILD_CCACHE=0 \
	>$work/mismatch.out 2>$work/mismatch.err; then
	fail 'mismatched incremental input was accepted'
fi
grep -Fq 'incremental output does not match current build inputs' \
	"$work/mismatch.err" || fail 'mismatched input returned the wrong refusal'
sed -i '$d' "$network_fragment"

printf '%s\n' '# tool identity changed' >>"$fake_bin/llvm-objdump"
if run_builder "$clean_a" JOBS=2 INCREMENTAL_BUILD=1 KBUILD_CCACHE=0 \
	>$work/tool-mismatch.out 2>$work/tool-mismatch.err; then
	fail 'changed LLVM tool identity was accepted for incremental reuse'
fi
grep -Fq 'incremental output does not match current build inputs' \
	"$work/tool-mismatch.err" || fail 'tool change returned the wrong refusal'
cp -- "$fake_bin/tool-stub" "$fake_bin/llvm-objdump"
chmod 0755 "$fake_bin/llvm-objdump"

lock_fifo=$work/lock-fifo
mkfifo "$lock_fifo"
(
	exec 8<>"$clean_a/.rog5-kbuild.lock"
	flock -x 8
	: >"$work/lock-ready"
	read -r _ <"$lock_fifo"
) &
holder_pid=$!
for _ in {1..200}; do
	[[ -e $work/lock-ready ]] && break
	sleep 0.01
done
[[ -e $work/lock-ready ]] || fail 'output-lock fixture did not start'
if run_builder "$clean_a" JOBS=2 INCREMENTAL_BUILD=1 KBUILD_CCACHE=0 \
	>$work/locked.out 2>$work/locked.err; then
	fail 'concurrent network-root builder acquired a locked output'
fi
grep -Fq 'another kernel builder owns this output directory' \
	"$work/locked.err" || fail 'output lock returned the wrong refusal'
printf '%s\n' release >"$lock_fifo"
wait "$holder_pid"
holder_pid=

run_builder "$clean_b" JOBS=4 INCREMENTAL_BUILD=0 KBUILD_CCACHE=0 \
	>$work/clean-b.out
run_builder "$cached" JOBS=3 INCREMENTAL_BUILD=0 KBUILD_CCACHE=1 \
	>$work/cached.out
for artifact in arch/arm64/boot/Image arch/arm64/boot/Image.gz \
	modules.tar.gz build-meta.txt; do
	cmp "$clean_a/$artifact" "$clean_b/$artifact" ||
		fail "clean release identity changed across JOBS for $artifact"
	cmp "$clean_b/$artifact" "$cached/$artifact" ||
		fail "ccache changed clean release identity for $artifact"
done
grep -Fq 'INFO ccache statistics' "$work/cached.out" ||
	fail 'KBUILD_CCACHE=1 did not expose bounded cache statistics'

echo 'PASS network-root builder dynamically proves exact reuse, invalidation, locking, ccache, and clean identities'
