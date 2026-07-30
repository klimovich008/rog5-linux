#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
project_root=$(dirname "$repo")
builder=$repo/scripts/host/reconstruct-recovery-base-v18r.sh
cpio_tool=$repo/scripts/host/qualified-tool-shims/cpio
target=${1:-$project_root/p2-kernel-release.dhCvZt/validation/fresh-target.cpio.gz}
stage=${2:-$project_root/p2-kernel-release.dhCvZt/validation/fresh-stage.cpio.gz}
expected_sha=da573d089cd617e088624b6d6bf711e193a4df5367843293e2e5ba543556e51d

for path in "$builder" "$cpio_tool"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable v18r test input: ${path#"$repo"/}"
done
for path in "$target" "$stage"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing exact retained v18r integration input: $path"
done

work=$(mktemp -d)
cleanup() {
	find "$work" -depth -delete 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM

"$builder" "$target" "$stage" "$work/output"
archive=$work/output/rog5-recovery-base-v18r.cpio.gz
report=$work/output/reconstruction-provenance.txt
[[ -f $archive && ! -L $archive &&
	$(stat -c %s "$archive") == 5838975 ]] ||
	fail 'v18r integration produced an unexpected archive'
[[ $(sha256sum "$archive" | cut -d ' ' -f 1) == "$expected_sha" ]] ||
	fail 'v18r integration archive identity changed'
grep -Fqx 'state=reconstructed-successor' "$report"
grep -Fqx 'boot_authority=none' "$report"
grep -Fqx "archive_sha256=$expected_sha" "$report"
if grep -Fq "$project_root" "$report"; then
	fail 'v18r provenance leaked an absolute host path'
fi

mkdir "$work/root"
gzip -dc "$archive" |
	(cd "$work/root" &&
		"$cpio_tool" -idm --quiet --no-absolute-filenames)
git -C "$repo" show \
	339bcfae13ca19dbcb38c1ee8f586988597355ec:initramfs/recovery-init \
	>"$work/expected-init"
cmp "$work/root/init" "$work/expected-init"
for removed in \
	shutdown \
	usr/local/sbin/rog5-p2-attest \
	usr/local/sbin/persistent-root-verify \
	usr/local/sbin/rog5-load-mainline-recovery \
	usr/sbin/kexec \
	usr/sbin/vmcore-dmesg \
	opt/rog5-recovery; do
	[[ ! -e $work/root/$removed && ! -L $work/root/$removed ]] ||
		fail "v18r integration retained P2-only path: $removed"
done
[[ ! -e $work/root/root/.ssh/authorized_keys ]] ||
	fail 'v18r integration retained authorization material'

if "$builder" "$target" "$stage" "$work/output" \
	>"$work/existing.log" 2>&1; then
	fail 'v18r builder overwrote an existing output root'
fi
grep -Fqx 'FAIL refusing existing v18r output root' "$work/existing.log"

cp --reflink=auto "$target" "$work/tampered-target.cpio.gz"
printf X | dd of="$work/tampered-target.cpio.gz" bs=1 seek=0 \
	conv=notrunc status=none
if "$builder" "$work/tampered-target.cpio.gz" "$stage" \
	"$work/tampered-output" >"$work/tampered.log" 2>&1; then
	fail 'tampered v18r lineage passed reconstruction'
fi
grep -Eq '^FAIL retained P2 target lineage (hash changed|is not a valid gzip stream)$' \
	"$work/tampered.log"
[[ ! -e $work/tampered-output ]] ||
	fail 'tampered v18r lineage published output'

ln -s "$target" "$work/linked-target.cpio.gz"
if "$builder" "$work/linked-target.cpio.gz" "$stage" \
	"$work/linked-output" >"$work/linked.log" 2>&1; then
	fail 'linked v18r lineage passed reconstruction'
fi
grep -Fqx \
	'FAIL missing, linked, or unreadable retained P2 target lineage' \
	"$work/linked.log"
[[ ! -e $work/linked-output ]] ||
	fail 'linked v18r lineage published output'

echo 'PASS v18r dual-lineage reconstruction and hostile rejection integration'
