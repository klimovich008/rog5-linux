#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/host/reconstruct-network-root-v3.sh
source_archive=${1:-$repo/artifacts/recovery-inputs-v18r/rog5-recovery-base-v18r.cpio.gz}
cpio_tool=$repo/scripts/host/qualified-tool-shims/cpio
expected_sha=4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac

for path in "$builder" "$cpio_tool"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable network-root-v3 test input: ${path#"$repo"/}"
done
[[ -f $source_archive && ! -L $source_archive ]] ||
	fail 'missing exact reconstructed v18r source archive'

work=$(mktemp -d)
cleanup() {
	find "$work" -depth -delete 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM

"$builder" "$source_archive" "$work/output-a"
"$builder" "$source_archive" "$work/output-b"
archive_a=$work/output-a/rog5-network-root-initramfs.cpio.gz
archive_b=$work/output-b/rog5-network-root-initramfs.cpio.gz
report_a=$work/output-a/network-root-initramfs-reconstruction.txt
report_b=$work/output-b/network-root-initramfs-reconstruction.txt
cmp "$archive_a" "$archive_b"
cmp "$report_a" "$report_b"
[[ $(stat -c %s "$archive_a") == 5840728 &&
	$(sha256sum "$archive_a" | cut -d ' ' -f 1) == "$expected_sha" ]] ||
	fail 'network-root-v3 integration archive identity changed'
grep -Fqx 'state=exact-historical-bytes-recovered' "$report_a"
grep -Fqx 'boot_authority=none' "$report_a"
grep -Fqx "archive_sha256=$expected_sha" "$report_a"
if grep -Fq "$repo" "$report_a"; then
	fail 'network-root-v3 provenance leaked an absolute host path'
fi

mkdir "$work/root"
gzip -dc "$archive_a" |
	(cd "$work/root" &&
		"$cpio_tool" -idm --quiet --no-absolute-filenames)
git -C "$repo" show \
	adb50a98fe5fe79453d9adfb0b49f0c5bad4f617:initramfs/network-root-init \
	>"$work/expected-init"
git -C "$repo" show \
	adb50a98fe5fe79453d9adfb0b49f0c5bad4f617:initramfs/network-root-shutdown \
	>"$work/expected-shutdown"
cmp "$work/root/init" "$work/expected-init"
cmp "$work/root/shutdown" "$work/expected-shutdown"
[[ ! -e $work/root/usr/local/sbin ]] ||
	fail 'P2-created directory survived network-root-v3 integration'
[[ ! -e $work/root/root/.ssh/authorized_keys ]] ||
	fail 'authorization material survived network-root-v3 integration'

if "$builder" "$source_archive" "$work/output-a" \
	>"$work/existing.log" 2>&1; then
	fail 'network-root-v3 builder overwrote an accepted archive'
fi
grep -Fqx \
	'FAIL refusing existing network-root reconstruction archive' \
	"$work/existing.log"

cp --reflink=auto "$source_archive" "$work/tampered.cpio.gz"
printf X | dd of="$work/tampered.cpio.gz" bs=1 seek=0 \
	conv=notrunc status=none
if "$builder" "$work/tampered.cpio.gz" "$work/tampered-output" \
	>"$work/tampered.log" 2>&1; then
	fail 'tampered v18r source passed network-root-v3 reconstruction'
fi
grep -Eq '^FAIL reconstructed v18r source archive (hash changed|is not a valid gzip stream)$' \
	"$work/tampered.log"
[[ ! -e $work/tampered-output ]] ||
	fail 'tampered v18r source published network-root-v3 output'

ln -s "$source_archive" "$work/linked.cpio.gz"
if "$builder" "$work/linked.cpio.gz" "$work/linked-output" \
	>"$work/linked.log" 2>&1; then
	fail 'linked v18r source passed network-root-v3 reconstruction'
fi
grep -Fqx \
	'FAIL missing, linked, or unreadable reconstructed v18r source archive' \
	"$work/linked.log"
[[ ! -e $work/linked-output ]] ||
	fail 'linked v18r source published network-root-v3 output'

echo 'PASS exact network-root-v3 reconstruction, twin convergence, and hostile rejection integration'
