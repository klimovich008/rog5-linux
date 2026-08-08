#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
helper=$repo/scripts/device/kernel-build-contract.sh
builder=$repo/scripts/device/build-mainline.sh
container=$repo/containers/kernel-builder/Dockerfile
test_tmp=$(mktemp -d)
trap 'rm -rf -- "$test_tmp"' 0 HUP INT TERM

fail() {
	echo "FAIL $*" >&2
	exit 1
}

expect_failure() {
	if "$@" >"$test_tmp/expected-failure.out" 2>&1; then
		fail "unexpected success: $*"
	fi
}

prepare() {
	incremental=$1
	output=$2
	state=$3
	INCREMENTAL_BUILD=$incremental sh -c \
		'. "$1"; rog5_kernel_prepare_output "$2" "$3"' \
		sh "$helper" "$output" "$state"
}

[ -f "$helper" ] && [ ! -L "$helper" ] && [ -x "$helper" ] ||
	fail 'missing executable kernel build contract'
sh -n "$helper"
sh -n "$builder"
grep -Eq '^[[:space:]]*bc bison build-essential ca-certificates ccache clang ' \
	"$container" ||
	fail 'pinned kernel-builder image does not install optional ccache'

state='format=rog5-kbuild-inputs-v1
source_commit=0123456789abcdef
fragment_sha256=abcdef0123456789
compiler_cache=disabled'
output=$test_tmp/output
prepare 0 "$output" "$state"
[ "$(stat -c '%a' "$output/.rog5-kbuild-inputs-v1")" = 600 ] ||
	fail 'new build state is not private'
[ "$(stat -c '%a' "$output/.rog5-kbuild.lock")" = 600 ] ||
	fail 'output lock file is not private'
printf '%s\n' payload >"$output/object.o"

expect_failure prepare 0 "$output" "$state"
prepare 1 "$output" "$state"
grep -qx payload "$output/object.o" ||
	fail 'incremental preparation modified an existing output'
expect_failure prepare 1 "$output" "$state.changed"

chmod 666 "$output/.rog5-kbuild-inputs-v1"
expect_failure prepare 1 "$output" "$state"
chmod 600 "$output/.rog5-kbuild-inputs-v1"

rm -f "$output/.rog5-kbuild-inputs-v1"
printf '%s\n' "$state" >"$test_tmp/outside-state"
ln -s "$test_tmp/outside-state" "$output/.rog5-kbuild-inputs-v1"
expect_failure prepare 1 "$output" "$state"

lock_output=$test_tmp/locked
mkdir -p "$lock_output"
INCREMENTAL_BUILD=0 sh -c \
	'. "$1"; rog5_kernel_prepare_output "$2" "$3"; kill -STOP "$$"' \
	sh "$helper" "$lock_output" "$state" &
lock_holder=$!
for _ in 1 2 3 4 5 6 7 8 9 10; do
	[ -e "$lock_output/.rog5-kbuild.lock" ] && break
	sleep 0.1
done
[ -e "$lock_output/.rog5-kbuild.lock" ] ||
	fail 'lock holder did not publish its lock'
expect_failure prepare 1 "$lock_output" "$state"
{
	kill -KILL "$lock_holder"
	wait "$lock_holder" || :
} 2>/dev/null
prepare 1 "$lock_output" "$state"

fake_bin=$test_tmp/fake-bin
mkdir -p "$fake_bin"
for tool in clang clang++ ld.lld llvm-ar llvm-nm; do
	printf '#!/bin/sh\nexit 0\n' >"$fake_bin/$tool"
	chmod 755 "$fake_bin/$tool"
done
identity_a=$(PATH="$fake_bin:/usr/bin:/bin" sh -c \
	'. "$1"; rog5_kernel_toolchain_identity clang clang++ ld.lld llvm-ar llvm-nm' \
	sh "$helper")
identity_b=$(PATH="$fake_bin:/usr/bin:/bin" sh -c \
	'. "$1"; rog5_kernel_toolchain_identity clang clang++ ld.lld llvm-ar llvm-nm' \
	sh "$helper")
[ "$identity_a" = "$identity_b" ] ||
	fail 'unchanged toolchain identity is unstable'
printf '#!/bin/sh\nexit 1\n' >"$fake_bin/clang"
chmod 755 "$fake_bin/clang"
identity_c=$(PATH="$fake_bin:/usr/bin:/bin" sh -c \
	'. "$1"; rog5_kernel_toolchain_identity clang clang++ ld.lld llvm-ar llvm-nm' \
	sh "$helper")
[ "$identity_a" != "$identity_c" ] ||
	fail 'toolchain binary mutation did not change identity'

printf '#!/bin/sh\nprintf "%%s\\n" "$*" >"$MAKE_LOG"\nprintf "%%s\\n" "${CCACHE_COMPILERCHECK-}|${CCACHE_NODEPEND-}|${CCACHE_SLOPPINESS-unset}|${CCACHE_CONFIGPATH-unset}" >"$MAKE_ENV_LOG"\nprintf stable >"$MAKE_ARTIFACT"\n' \
	>"$fake_bin/make"
printf '#!/bin/sh\nif [ "${1-}" = --show-config ]; then printf "%%s\\n" "cache_dir = /tmp/rog5-test-cache"; exit 0; fi\nexec "$@"\n' >"$fake_bin/ccache"
chmod 755 "$fake_bin/make" "$fake_bin/ccache"

MAKE_LOG=$test_tmp/uncached.log
MAKE_ARTIFACT=$test_tmp/uncached.bin
MAKE_ENV_LOG=$test_tmp/uncached.env
export MAKE_LOG MAKE_ARTIFACT MAKE_ENV_LOG
PATH="$fake_bin:/usr/bin:/bin" KBUILD_CCACHE=0 sh -c \
	'. "$1"; rog5_kernel_make -C source O=output LLVM=1 Image' \
	sh "$helper"
if grep -q 'ccache' "$MAKE_LOG"; then
	fail 'default make path unexpectedly enabled ccache'
fi

MAKE_LOG=$test_tmp/cached.log
MAKE_ARTIFACT=$test_tmp/cached.bin
MAKE_ENV_LOG=$test_tmp/cached.env
export MAKE_LOG MAKE_ARTIFACT MAKE_ENV_LOG
PATH="$fake_bin:/usr/bin:/bin" KBUILD_CCACHE=1 sh -c \
	'. "$1"; rog5_kernel_cache_identity >/dev/null; rog5_kernel_make -C source O=output LLVM=1 Image' \
	sh "$helper"
grep -Fq 'CC=ccache clang' "$MAKE_LOG" ||
	fail 'cached make path did not wrap the target compiler'
grep -Fq 'HOSTCC=ccache clang' "$MAKE_LOG" ||
	fail 'cached make path did not wrap the host compiler'
grep -Fq 'HOSTCXX=ccache clang++' "$MAKE_LOG" ||
	fail 'cached make path did not wrap the host C++ compiler'
grep -Fxq 'content|true||/dev/null' "$MAKE_ENV_LOG" ||
	fail 'cached make path did not enforce safe ccache environment'
cmp "$test_tmp/uncached.bin" "$test_tmp/cached.bin" ||
	fail 'cached and uncached fixture artifacts differ'

no_cache_bin=$test_tmp/no-cache-bin
mkdir "$no_cache_bin"
expect_failure env PATH="$no_cache_bin" KBUILD_CCACHE=1 /bin/sh -c \
	'. "$1"; rog5_kernel_cache_identity' sh "$helper"

grep -Fq '. "$kernel_contract"' "$builder" ||
	fail 'active mainline builder does not source the output contract'
grep -Fq 'rog5_kernel_prepare_output "$output_dir" "$build_state"' "$builder" ||
	fail 'active mainline builder does not prepare its output identity'
grep -Fq 'rog5_kernel_make -C "$source_dir"' "$builder" ||
	fail 'active mainline builder does not use the cache-aware make wrapper'
if grep -Eq '^[[:space:]]*make -C ' "$builder"; then
	fail 'active mainline builder bypasses the make wrapper'
fi
for required_state in \
	'format=rog5-kbuild-inputs-v1' \
	'source_path=%s' \
	'output_path=%s' \
	'source_commit=%s' \
	'source_tree=%s' \
	'fragment_sha256=%s' \
	'builder_sha256=%s' \
	'contract_sha256=%s'; do
	grep -Fq "$required_state" "$builder" ||
		fail "active mainline state omits $required_state"
done
grep -Fq 'llvm-readelf pahole' "$builder" ||
	fail 'active mainline state omits llvm-readelf'
grep -Fq 'kernel output must be outside the source tree' "$builder" ||
	fail 'active mainline builder permits output inside source'
grep -Fq '[ "$(stat -c '\''%a'\'' "$kernel_contract")" = 755 ]' "$builder" ||
	fail 'active mainline builder executes an unsafe contract file'

echo 'PASS kernel builds default clean, reuse only exact private state, and enable ccache explicitly without changing fixture bytes'
