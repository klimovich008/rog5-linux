#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-persistent-root-entry-kexec-stage-initramfs.sh
base=$repo/artifacts/ufs-discovery-v2/rog5-ufs-discovery-kexec-stage-initramfs.cpio.gz
image=$repo/artifacts/persistent-root-p2/Image-7.1.4-persistent-root
dtb=$repo/artifacts/persistent-root-p2/sm8350-asus-rog-phone5-persistent-root.dtb
initramfs=$repo/artifacts/persistent-root-entry-v1/rog5-persistent-root-entry-initramfs.cpio.gz
loader=$repo/scripts/device/load-mainline-persistent-root-entry.sh

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ -x "$builder" ] ||
	fail "missing executable P2 entry stage builder: $builder"
sh -n "$builder"
for input in "$base" "$image" "$dtb" "$initramfs" "$loader"; do
	[ -s "$input" ] || fail "missing P2 entry stage input: $input"
done

for contract in \
	'fcf147c4dc91323caaed4be8767545441f9df31323e4513e62c99ac20ac789e9' \
	'832757fc6b97554813a14049123667bc6f5b225e6204ca048d73c3a36c76469f' \
	'36802458928e2970a0043f6a27d106e6aa4911fd89b2f548e7c08275d164aaf0' \
	'09f7e69daf270c584b1947f41872a9af512c47e26fb2e8a30d3cdfb2fcc5d7a5' \
	'a21f2a653c6237253cd0039fec2e15c9348afe714ec3e77b9e2c7b5baf78f8af' \
	'/opt/rog5-recovery' \
	'/usr/local/sbin/rog5-load-mainline-recovery'; do
	grep -Fq "$contract" "$builder" ||
		fail "P2 entry stage builder omits contract: $contract"
done

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
"$builder" "$base" "$image" "$dtb" "$initramfs" "$loader" \
	"$stage/a.cpio.gz" >/dev/null
"$builder" "$base" "$image" "$dtb" "$initramfs" "$loader" \
	"$stage/b.cpio.gz" >/dev/null
cmp "$stage/a.cpio.gz" "$stage/b.cpio.gz"

if "$builder" "$base" "$image" "$dtb" "$initramfs" "$loader" \
	"$stage/a.cpio.gz" >/dev/null 2>&1; then
	fail 'P2 entry stage builder overwrote an existing output'
fi

mkdir "$stage/root"
gzip -dc "$stage/a.cpio.gz" |
	(cd "$stage/root" && cpio -idm --quiet --no-absolute-filenames)
cmp "$stage/root/opt/rog5-recovery/Image" "$image"
cmp "$stage/root/opt/rog5-recovery/board.dtb" "$dtb"
cmp "$stage/root/opt/rog5-recovery/initramfs.cpio.gz" "$initramfs"
cmp "$stage/root/usr/local/sbin/rog5-load-mainline-recovery" "$loader"
(cd "$stage/root/opt/rog5-recovery" &&
	sha256sum -c SHA256SUMS >/dev/null)
[ "$(grep -Fo 'rog5.p2_entry_diag=1' \
	"$stage/root/usr/local/sbin/rog5-load-mainline-recovery" |
	wc -l)" -eq 2 ]
[ ! -e "$stage/root/root/.ssh/authorized_keys" ]
[ -z "$(find "$stage/root/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit)" ]
! find "$stage/root" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .

echo 'PASS deterministic credential-free P2 early-entry staging archive carries only the exact RAM oracle payload'
