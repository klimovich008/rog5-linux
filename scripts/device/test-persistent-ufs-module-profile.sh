#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-persistent-ufs-module-profile.sh
builder=$repo/scripts/device/build-persistent-root-initramfs.sh
read_only_archive=$repo/artifacts/persistent-native-root-v4/initramfs.cpio.gz
local_write_archive=$repo/artifacts/local-image-direct-v49/initramfs.cpio.gz
release=7.1.4-g359318de534f

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in cpio gzip mktemp; do
	command -v "$command" >/dev/null ||
		fail "missing UFS profile test command: $command"
done
for path in "$verifier" "$builder"; do
	[ -x "$path" ] || fail "missing executable UFS profile source: $path"
done
for path in "$read_only_archive" "$local_write_archive"; do
	[ -f "$path" ] && [ ! -L "$path" ] ||
		fail "missing retained UFS profile fixture: $path"
done

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
mkdir "$work/read-only" "$work/local-write"
gzip -dc "$read_only_archive" |
	(cd "$work/read-only" && cpio -idm --quiet --no-absolute-filenames)
gzip -dc "$local_write_archive" |
	(cd "$work/local-write" && cpio -idm --quiet --no-absolute-filenames)

read_only_modules=$work/read-only/rog5-ufs-modules
local_write_modules=$work/local-write/rog5-ufs-modules
"$verifier" "$read_only_modules" "$release" read-only >/dev/null
"$verifier" "$local_write_modules" "$release" local-write >/dev/null

if "$verifier" "$read_only_modules" "$release" local-write \
	>"$work/out" 2>"$work/err"; then
	fail 'local-write profile accepted the stale low-speed UFS core'
fi
grep -Fq 'local-write UFS core lacks the exact high-speed implementation' \
	"$work/err" || fail 'stale local-write profile returned the wrong reason'

if "$verifier" "$local_write_modules" "$release" read-only \
	>"$work/out" 2>"$work/err"; then
	fail 'read-only profile accepted the writable high-speed UFS core'
fi
grep -Fq 'read-only UFS core is not the exact discovery implementation' \
	"$work/err" || fail 'writable read-only profile returned the wrong reason'

grep -Fq 'verify-persistent-ufs-module-profile.sh' "$builder" ||
	fail 'persistent initramfs builder does not invoke the UFS profile verifier'
grep -Fq '"$ufs_module_verifier" "$ufs_modules" "$expected_release" "$storage_mode"' \
	"$builder" || fail 'persistent initramfs builder omits the exact UFS profile'

echo 'PASS persistent initramfs rejects cross-profile UFS module composition'
