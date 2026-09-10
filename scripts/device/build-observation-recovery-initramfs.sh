#!/bin/sh
set -eu

full_archive=${1:?usage: build-observation-recovery-initramfs.sh FULL_ARCHIVE INIT CONTROL FETCHER VERIFIER PUBLIC_KEY OUTPUT}
init=${2:?missing recovery init}
control=${3:?missing recovery responder}
fetcher=${4:?missing recovery bundle fetcher}
verifier=${5:?missing recovery bundle verifier}
public_key=${6:?missing recovery public key}
output=${7:?missing output}
epoch=1681862400
export LC_ALL=C
export TZ=UTC

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "$0")/../.." && pwd -P)
for command in basename chmod cpio cut dirname find gzip mkdir mktemp mv rm \
	sha256sum sort touch; do
	command -v "$command" >/dev/null ||
		fail "missing observation-recovery build command: $command"
done
for input in "$full_archive" "$init" "$control" "$fetcher" \
	"$verifier" "$public_key"; do
	[ -f "$input" ] && [ -r "$input" ] && [ ! -L "$input" ] ||
		fail "unsafe observation-recovery input: $(basename "$input")"
done
[ ! -e "$output" ] && [ ! -L "$output" ] ||
	fail 'observation-recovery output already exists'

"$repo/scripts/device/verify-stable-recovery-initramfs.sh" \
	"$full_archive" "$init" "$control" "$fetcher" "$verifier" \
	"$public_key" exact-a600000-v1 -

stage=$(mktemp -d)
output_directory=$(dirname "$output")
mkdir -p "$output_directory"
output_name=$(basename "$output")
temporary=$(mktemp "$output_directory/.${output_name}.tmp.XXXXXX")
cleanup() {
	rm -rf -- "$stage"
	rm -f -- "$temporary"
}
trap cleanup EXIT HUP INT TERM

gzip -dc "$full_archive" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
[ "$(sha256sum "$stage/bin/busybox" | cut -d ' ' -f 1)" = \
	97d52efa149563c8d886e3670e2496d4140d3c54138017afd3a105e0397fae2e ] ||
	fail 'observation-recovery BusyBox identity mismatch'

rm -f -- \
	"$stage/usr/libexec/rog5-bundle-fetch" \
	"$stage/usr/libexec/rog5-bundle-verify" \
	"$stage/usr/sbin/kexec" \
	"$stage/etc/rog5/recovery-bundle-ed25519.pub"
chmod 0600 "$stage/etc/rog5/recovery-mode"
printf '%s\n' observation-only-v1 >"$stage/etc/rog5/recovery-mode"
chmod 0444 "$stage/etc/rog5/recovery-mode"

find "$stage" -exec touch -h -d "@$epoch" {} +
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$temporary"
gzip -t "$temporary"
"$repo/scripts/device/verify-stable-recovery-initramfs.sh" \
	"$temporary" "$init" "$control" - - - \
	observation-only-a600000-v1 -
mv -T -- "$temporary" "$output"
trap - EXIT HUP INT TERM
rm -rf -- "$stage"

sha256sum "$init" "$control" "$output"
echo 'PASS deterministic observation-only recovery initramfs; no fetcher, verifier, trust key, or kexec entry point'
