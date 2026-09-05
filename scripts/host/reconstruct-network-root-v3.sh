#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
source_archive=${1:-$repo/artifacts/recovery-inputs-v18r/rog5-recovery-base-v18r.cpio.gz}
output_root=${2:-$repo/artifacts/network-root-v3}
source_size=5838975
source_sha=da573d089cd617e088624b6d6bf711e193a4df5367843293e2e5ba543556e51d
source_report=$repo/artifacts/recovery-inputs-v18r/reconstruction-provenance.txt
source_report_sha=768bf860fefc94af5620506df0e398a4bf5ff1eb0c0961692c5e0efb7d5a2448
ufs_commit=1cc4bc1e4a9e3be19e9c7c669cebee24b508fd68
ufs_path=initramfs/recovery-init
ufs_blob=260e386875d2677b77667c38f39eb1b3be2db9e9
ufs_size=11602
ufs_source_sha=2996b867931df1ad632bf143879e15a61d6505159821d971bacda5da8b624cfc
ufs_archive_size=5841750
ufs_archive_sha=df1d0cdb95513d7ef6d772a3a6165d37b3b226682d92e30a2143409341bbefb1
network_commit=adb50a98fe5fe79453d9adfb0b49f0c5bad4f617
network_init_path=initramfs/network-root-init
network_init_blob=a2c9753310c4f5dbb801bd0b0c655f3d0b860647
network_init_size=7201
network_init_sha=15ce6f3e3b9cd746ecbf78dad20970b6c692c5801002b27533c7cdc8fce6452f
network_shutdown_path=initramfs/network-root-shutdown
network_shutdown_blob=56c4a643e66fdc96b8754c46bcd8af0bb2f1da47
network_shutdown_size=2041
network_shutdown_sha=74a574c64b0b20133dc0dceeff4f6d543d6eaf2326334efc5ae0ad7c32401cb2
output_name=rog5-network-root-initramfs.cpio.gz
report_name=network-root-initramfs-reconstruction.txt
output_size=5840728
output_sha=4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
epoch=1681862400
cpio_tool=$repo/scripts/host/qualified-tool-shims/cpio
gzip_tool=$repo/scripts/host/qualified-tool-shims/gzip
builder_image=localhost/rog5-kernel-builder:ubuntu-24.04
builder_verifier=$repo/scripts/host/verify-steam-deck-builder.sh

for command_name in basename chmod cmp cut dirname find git grep install \
	ln mkdir mktemp readlink realpath rmdir sha256sum sort stat touch; do
	command -v "$command_name" >/dev/null ||
		fail "missing network-root reconstruction command: $command_name"
done
for tool in "$cpio_tool" "$gzip_tool" "$builder_verifier"; do
	[[ -f $tool && ! -L $tool && -x $tool ]] ||
		fail "missing executable reconstruction tool: ${tool#"$repo"/}"
done

check_file() {
	path=$1
	expected_size=$2
	expected_sha=$3
	label=$4
	[[ -f $path && ! -L $path && -r $path ]] ||
		fail "missing, linked, or unreadable $label"
	[[ $(stat -c %s "$path") == "$expected_size" ]] ||
		fail "$label size changed"
	[[ $(sha256sum "$path" | cut -d ' ' -f 1) == "$expected_sha" ]] ||
		fail "$label hash changed"
}

check_git_source() {
	commit=$1
	path=$2
	blob=$3
	size=$4
	sha=$5
	output=$6
	label=$7
	[[ $(git -C "$repo" cat-file -t "$commit") == commit ]] ||
		fail "missing exact $label commit"
	[[ $(git -C "$repo" rev-parse "$commit:$path") == "$blob" ]] ||
		fail "$label blob identity changed"
	[[ $(git -C "$repo" cat-file -s "$blob") == "$size" ]] ||
		fail "$label source size changed"
	[[ $(git -C "$repo" ls-tree "$commit" "$path") == \
		"100755 blob $blob"$'\t'"$path" ]] ||
		fail "$label source mode or path changed"
	git -C "$repo" cat-file blob "$blob" >"$output"
	chmod 0755 "$output"
	check_file "$output" "$size" "$sha" "$label source"
}

repack() {
	root=$1
	output=$2
	expected_size=$3
	expected_sha=$4
	label=$5
	find "$root" -exec touch -h -d "@$epoch" {} +
	(
		cd "$root"
		find . -mindepth 1 -print0 | LC_ALL=C sort -z |
			"$cpio_tool" --null -o --quiet --format=newc \
				--owner=0:0 --reproducible
	) | "$gzip_tool" -n >"$output"
	gzip -t "$output"
	check_file "$output" "$expected_size" "$expected_sha" "$label"
}

check_file "$source_archive" "$source_size" "$source_sha" \
	'reconstructed v18r source archive'
gzip -t "$source_archive" ||
	fail 'reconstructed v18r source archive is not a valid gzip stream'
check_file "$source_report" 921 "$source_report_sha" \
	'v18r reconstruction provenance'
grep -Fqx 'state=reconstructed-successor' "$source_report" ||
	fail 'v18r source is not identified as a reconstructed successor'
grep -Fqx 'boot_authority=none' "$source_report" ||
	fail 'v18r source provenance grants unexpected boot authority'

source_archive=$(realpath -e "$source_archive")
case $output_root in
	''|/|/dev|/dev/*|/proc|/proc/*|/sys|/sys/*|/run|/run/*)
		fail 'unsafe network-root reconstruction output root'
		;;
esac
output_parent=$(dirname "$output_root")
mkdir -p "$output_parent"
output_parent=$(realpath -e "$output_parent")
output_root=$output_parent/$(basename "$output_root")
[[ ! -L $output_root ]] ||
	fail 'network-root reconstruction output root is linked'
mkdir -p "$output_root"
output_archive=$output_root/$output_name
output_report=$output_root/$report_name
[[ ! -e $output_archive && ! -L $output_archive ]] ||
	fail 'refusing existing network-root reconstruction archive'
[[ ! -e $output_report && ! -L $output_report ]] ||
	fail 'refusing existing network-root reconstruction report'
[[ $output_archive != "$source_archive" ]] ||
	fail 'network-root reconstruction output aliases its source'

export GIT_NO_REPLACE_OBJECTS=1
work=$(mktemp -d)
archive_stage=$(mktemp "$output_root/.network-root-v3.XXXXXX")
report_stage=$(mktemp "$output_root/.network-root-v3-report.XXXXXX")
cleanup() {
	find "$work" -depth -delete 2>/dev/null || true
	[[ -z ${archive_stage:-} ]] ||
		find "$archive_stage" -maxdepth 0 -delete 2>/dev/null || true
	[[ -z ${report_stage:-} ]] ||
		find "$report_stage" -maxdepth 0 -delete 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM

"$builder_verifier" "$builder_image" >"$work/builder-qualification.txt"
mkdir "$work/root" "$work/verify"
gzip -dc "$source_archive" |
	(cd "$work/root" &&
		"$cpio_tool" -idm --quiet --no-absolute-filenames)

check_file "$work/root/init" 6325 \
	063f9277bffb61df6128ebd5228bfcc0582170633625776006186d125ece756a \
	'v18r init'
[[ -d $work/root/usr/local/sbin && ! -L $work/root/usr/local/sbin ]] ||
	fail 'expected P2-created usr/local/sbin directory is absent or linked'
[[ -z $(find "$work/root/usr/local/sbin" -mindepth 1 -maxdepth 1 \
	-print -quit) ]] ||
	fail 'P2-created usr/local/sbin directory is not empty'
rmdir "$work/root/usr/local/sbin"

check_git_source "$ufs_commit" "$ufs_path" "$ufs_blob" "$ufs_size" \
	"$ufs_source_sha" "$work/ufs-init" 'accepted UFS-v2 init'
install -m 0755 "$work/ufs-init" "$work/root/init"
repack "$work/root" "$work/ufs-v2.cpio.gz" "$ufs_archive_size" \
	"$ufs_archive_sha" 'accepted UFS-v2 intermediate archive'

check_git_source "$network_commit" "$network_init_path" \
	"$network_init_blob" "$network_init_size" "$network_init_sha" \
	"$work/network-init" 'accepted network-root-v3 init'
check_git_source "$network_commit" "$network_shutdown_path" \
	"$network_shutdown_blob" "$network_shutdown_size" \
	"$network_shutdown_sha" "$work/network-shutdown" \
	'accepted network-root-v3 shutdown'
install -m 0755 "$work/network-init" "$work/root/init"
install -m 0755 "$work/network-shutdown" "$work/root/shutdown"
repack "$work/root" "$archive_stage" "$output_size" "$output_sha" \
	'accepted network-root-v3 archive'

[[ ! -e $work/root/root/.ssh/authorized_keys ]] ||
	fail 'authorization material survived network-root reconstruction'
if find "$work/root" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .; then
	fail 'private-key material survived network-root reconstruction'
fi
gzip -dc "$archive_stage" |
	(cd "$work/verify" &&
		"$cpio_tool" -idm --quiet --no-absolute-filenames)
cmp "$work/verify/init" "$work/network-init"
cmp "$work/verify/shutdown" "$work/network-shutdown"
[[ ! -e $work/verify/usr/local/sbin ]] ||
	fail 'P2-created directory survived the accepted network-root archive'

builder_report_sha=$(
	sha256sum "$work/builder-qualification.txt" | cut -d ' ' -f 1
)
{
	printf '%s\n' \
		'schema=rog5-network-root-v3-reconstruction-v1' \
		'state=exact-historical-bytes-recovered' \
		'boot_authority=none' \
		"source_archive_size=$source_size" \
		"source_archive_sha256=$source_sha" \
		"source_provenance_sha256=$source_report_sha" \
		"ufs_commit=$ufs_commit" \
		"ufs_blob=$ufs_blob" \
		"ufs_source_sha256=$ufs_source_sha" \
		"ufs_archive_size=$ufs_archive_size" \
		"ufs_archive_sha256=$ufs_archive_sha" \
		"network_commit=$network_commit" \
		"network_init_blob=$network_init_blob" \
		"network_init_sha256=$network_init_sha" \
		"network_shutdown_blob=$network_shutdown_blob" \
		"network_shutdown_sha256=$network_shutdown_sha" \
		"qualified_builder_report_sha256=$builder_report_sha" \
		'transform=remove-empty-p2-created-usr-local-sbin-then-restore-exact-git-blobs' \
		"archive_size=$output_size" \
		"archive_sha256=$output_sha"
} >"$report_stage"
chmod 0644 "$archive_stage" "$report_stage"

ln "$archive_stage" "$output_archive" ||
	fail 'network-root reconstruction archive appeared during publication'
ln "$report_stage" "$output_report" || {
	find "$output_archive" -maxdepth 0 -delete 2>/dev/null || true
	fail 'network-root reconstruction report appeared during publication'
}
find "$archive_stage" "$report_stage" -maxdepth 0 -delete
archive_stage=
report_stage=
trap - EXIT HUP INT TERM
find "$work" -depth -delete

sha256sum "$output_archive"
echo 'PASS recovered exact accepted network-root-v3 bytes through the exact UFS-v2 intermediate'
