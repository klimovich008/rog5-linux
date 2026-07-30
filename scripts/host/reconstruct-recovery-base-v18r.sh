#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
project_root=$(dirname "$repo")
target_input=${1:-$project_root/p2-kernel-release.dhCvZt/validation/fresh-target.cpio.gz}
stage_input=${2:-$project_root/p2-kernel-release.dhCvZt/validation/fresh-stage.cpio.gz}
output_root=${3:-$repo/artifacts/recovery-inputs-v18r}

target_size=5853822
target_sha=e2b58d50fae31509b8cd87ed01afbf25c90d49500e3d9d9691ecd77643fd434e
stage_size=26688093
stage_sha=438aaf1c99455e23ff27f758738e779b0fd318e68c58467eeae7b77c55a87520
source_commit=339bcfae13ca19dbcb38c1ee8f586988597355ec
source_path=initramfs/recovery-init
source_blob=563ba046ab6d481ec4eb425793f3df9b0d8c6ee4
source_size=6325
source_sha=063f9277bffb61df6128ebd5228bfcc0582170633625776006186d125ece756a
historical_v18_sha=852b02a2cbcb2dfd43598269ff1b2b10cb1542e90ab7a7aa32d1a26c7cc645fc
successor_size=5838975
successor_sha=da573d089cd617e088624b6d6bf711e193a4df5367843293e2e5ba543556e51d
epoch=1681862400
archive_name=rog5-recovery-base-v18r.cpio.gz
report_name=reconstruction-provenance.txt
builder_image=localhost/rog5-kernel-builder:ubuntu-24.04
builder_verifier=$repo/scripts/host/verify-steam-deck-builder.sh
cpio_tool=$repo/scripts/host/qualified-tool-shims/cpio
gzip_tool=$repo/scripts/host/qualified-tool-shims/gzip

for command_name in basename chmod cmp cut dirname find git grep gzip install \
	mkdir mktemp mv readlink realpath rm sha256sum sort stat touch; do
	command -v "$command_name" >/dev/null ||
		fail "missing v18r reconstruction command: $command_name"
done
for tool in "$builder_verifier" "$cpio_tool" "$gzip_tool"; do
	[[ -f $tool && ! -L $tool && -x $tool ]] ||
		fail "missing executable qualified reconstruction tool: ${tool#"$repo"/}"
done

check_input() {
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
	gzip -t "$path" || fail "$label is not a valid gzip stream"
}

check_file_hash() {
	path=$1
	expected=$2
	label=$3
	[[ -f $path && ! -L $path ]] ||
		fail "missing or linked $label"
	[[ $(sha256sum "$path" | cut -d ' ' -f 1) == "$expected" ]] ||
		fail "$label identity changed"
}

check_input "$target_input" "$target_size" "$target_sha" \
	'retained P2 target lineage'
check_input "$stage_input" "$stage_size" "$stage_sha" \
	'retained P2 outer-stage lineage'

target_input=$(realpath -e "$target_input")
stage_input=$(realpath -e "$stage_input")
[[ $target_input != "$stage_input" ]] ||
	fail 'the two retained lineages alias one file'

case $output_root in
	''|/|/dev|/dev/*|/proc|/proc/*|/sys|/sys/*|/run|/run/*)
		fail 'unsafe v18r output root'
		;;
esac
output_parent=$(dirname "$output_root")
mkdir -p "$output_parent"
output_parent=$(realpath -e "$output_parent")
output_root=$output_parent/$(basename "$output_root")
[[ ! -e $output_root && ! -L $output_root ]] ||
	fail 'refusing existing v18r output root'
for input in "$target_input" "$stage_input"; do
	[[ $output_root != "$input" ]] ||
		fail 'v18r output aliases an input'
done

export GIT_NO_REPLACE_OBJECTS=1
[[ $(git -C "$repo" cat-file -t "$source_commit") == commit ]] ||
	fail 'missing exact historical v18 source commit'
[[ $(git -C "$repo" rev-parse "$source_commit:$source_path") == \
	"$source_blob" ]] ||
	fail 'historical v18 source blob identity changed'
[[ $(git -C "$repo" cat-file -s "$source_blob") == "$source_size" ]] ||
	fail 'historical v18 source blob size changed'
[[ $(git -C "$repo" ls-tree "$source_commit" "$source_path") == \
	"100755 blob $source_blob"$'\t'"$source_path" ]] ||
	fail 'historical v18 source mode or path changed'

work=$(mktemp -d)
publish=$(mktemp -d "$output_parent/.recovery-inputs-v18r.publish.XXXXXX")
cleanup() {
	find "$work" -depth -delete 2>/dev/null || true
	if [[ -n ${publish:-} && -e $publish ]]; then
		find "$publish" -depth -delete 2>/dev/null || true
	fi
}
trap cleanup EXIT HUP INT TERM

"$builder_verifier" "$builder_image" >"$work/builder-qualification.txt"
git -C "$repo" cat-file blob "$source_blob" >"$work/recovery-init-v18"
chmod 0755 "$work/recovery-init-v18"
check_file_hash "$work/recovery-init-v18" "$source_sha" \
	'historical v18 init source'

mkdir "$work/from-target" "$work/from-stage" "$work/verify"
gzip -dc "$target_input" |
	(cd "$work/from-target" &&
		"$cpio_tool" -idm --quiet --no-absolute-filenames)
gzip -dc "$stage_input" |
	(cd "$work/from-stage" &&
		"$cpio_tool" -idm --quiet --no-absolute-filenames)

target_root=$work/from-target
check_file_hash "$target_root/init" \
	59bed686a4940718edd81169871425bc5bab81fc822101749f68b73f79c272e4 \
	'P2 target init'
check_file_hash "$target_root/shutdown" \
	63f987b56461dbe29068c1c098aa64d01fd8f9057cb87840f5c8b0c61ed78c0c \
	'P2 target shutdown'
check_file_hash "$target_root/usr/local/sbin/rog5-p2-attest" \
	304b07690357e9b972f4f92aceaba558abfcf2ffc2d1561d0c894a7198a83c4f \
	'P2 target attestor'
check_file_hash "$target_root/usr/local/sbin/persistent-root-verify" \
	6a67a4e0d228efab0d0e47ee4c5d6947af3df157e8110c6bf9c7444c1b4e71dd \
	'P2 target root verifier'
rm "$target_root/shutdown" \
	"$target_root/usr/local/sbin/rog5-p2-attest" \
	"$target_root/usr/local/sbin/persistent-root-verify"
install -m 0755 "$work/recovery-init-v18" "$target_root/init"

stage_root=$work/from-stage
check_file_hash "$stage_root/init" \
	2996b867931df1ad632bf143879e15a61d6505159821d971bacda5da8b624cfc \
	'P2 outer-stage init'
check_file_hash "$stage_root/usr/sbin/kexec" \
	5e5d0a78b3f0bcf3921ff060f4dce5011cbac24b5e12fedeb8ca03ea5b40d015 \
	'P2 outer-stage kexec'
check_file_hash "$stage_root/usr/sbin/vmcore-dmesg" \
	b0d09aec932acec532b9e1078265d4741b63ca34f1431b527101643ab0114160 \
	'P2 outer-stage vmcore-dmesg'
check_file_hash "$stage_root/usr/lib/liblzma.so.5.8.3" \
	a30eb437c4fb1fc99a14d8038ee5db824121e14579abff329831a9a1be0f5f37 \
	'P2 outer-stage liblzma'
check_file_hash "$stage_root/usr/lib/libzstd.so.1.5.7" \
	baeb93cf3904f55809f9229c7b0e9348bfe07b80d319a477df9ac63657a9fa55 \
	'P2 outer-stage libzstd'
check_file_hash "$stage_root/usr/local/sbin/rog5-load-mainline-recovery" \
	7a05fdbf513e845ec7baff7ed5324d8e6564901d3e9b21fb1a95caf2a7633177 \
	'P2 outer-stage loader'
check_file_hash "$stage_root/opt/rog5-recovery/Image" \
	832757fc6b97554813a14049123667bc6f5b225e6204ca048d73c3a36c76469f \
	'P2 embedded Image'
check_file_hash "$stage_root/opt/rog5-recovery/board.dtb" \
	36802458928e2970a0043f6a27d106e6aa4911fd89b2f548e7c08275d164aaf0 \
	'P2 embedded DTB'
check_file_hash "$stage_root/opt/rog5-recovery/initramfs.cpio.gz" \
	"$target_sha" 'P2 embedded target lineage'
check_file_hash "$stage_root/opt/rog5-recovery/SHA256SUMS" \
	7f38691316d19397a9c45db413d07fcbd5577c3139b01fdc83905efa78f6d550 \
	'P2 embedded payload manifest'
[[ -L $stage_root/usr/lib/liblzma.so.5 &&
	$(readlink "$stage_root/usr/lib/liblzma.so.5") == liblzma.so.5.8.3 ]] ||
	fail 'P2 outer-stage liblzma link changed'
[[ -L $stage_root/usr/lib/libzstd.so.1 &&
	$(readlink "$stage_root/usr/lib/libzstd.so.1") == libzstd.so.1.5.7 ]] ||
	fail 'P2 outer-stage libzstd link changed'
rm "$stage_root/usr/sbin/kexec" \
	"$stage_root/usr/sbin/vmcore-dmesg" \
	"$stage_root/usr/lib/liblzma.so.5" \
	"$stage_root/usr/lib/liblzma.so.5.8.3" \
	"$stage_root/usr/lib/libzstd.so.1" \
	"$stage_root/usr/lib/libzstd.so.1.5.7" \
	"$stage_root/usr/local/sbin/rog5-load-mainline-recovery"
find "$stage_root/opt/rog5-recovery" -depth -delete
install -m 0755 "$work/recovery-init-v18" "$stage_root/init"

for root in "$target_root" "$stage_root"; do
	cmp "$root/init" "$work/recovery-init-v18"
	for removed in \
		shutdown \
		usr/local/sbin/rog5-p2-attest \
		usr/local/sbin/persistent-root-verify \
		usr/local/sbin/rog5-load-mainline-recovery \
		usr/sbin/kexec \
		usr/sbin/vmcore-dmesg \
		usr/lib/liblzma.so.5 \
		usr/lib/liblzma.so.5.8.3 \
		usr/lib/libzstd.so.1 \
		usr/lib/libzstd.so.1.5.7 \
		opt/rog5-recovery; do
		[[ ! -e $root/$removed && ! -L $root/$removed ]] ||
			fail "P2-only member survived reverse transform: $removed"
	done
	[[ ! -e $root/root/.ssh/authorized_keys ]] ||
		fail 'credential material survived in reconstructed base'
	if find "$root" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
		grep -q .; then
		fail 'private-key material survived in reconstructed base'
	fi
done

repack() {
	root=$1
	output=$2
	find "$root" -exec touch -h -d "@$epoch" {} +
	(
		cd "$root"
		find . -mindepth 1 -print0 | LC_ALL=C sort -z |
			"$cpio_tool" --null -o --quiet --format=newc \
				--owner=0:0 --reproducible
	) | "$gzip_tool" -n >"$output"
	gzip -t "$output"
	[[ $(stat -c %s "$output") == "$successor_size" ]] ||
		fail 'v18r successor size changed'
	[[ $(sha256sum "$output" | cut -d ' ' -f 1) == \
		"$successor_sha" ]] ||
		fail 'v18r successor hash changed'
}

repack "$target_root" "$work/from-target.cpio.gz"
repack "$stage_root" "$work/from-stage.cpio.gz"
cmp "$work/from-target.cpio.gz" "$work/from-stage.cpio.gz" ||
	fail 'independent retained lineages did not converge byte-for-byte'
[[ $successor_sha != "$historical_v18_sha" ]] ||
	fail 'successor identity aliases the unrecovered historical v18 bytes'

gzip -dc "$work/from-target.cpio.gz" |
	(cd "$work/verify" &&
		"$cpio_tool" -idm --quiet --no-absolute-filenames)
cmp "$work/verify/init" "$work/recovery-init-v18"
[[ ! -e $work/verify/shutdown &&
	! -e $work/verify/usr/local/sbin/rog5-p2-attest &&
	! -e $work/verify/opt/rog5-recovery ]] ||
	fail 'published successor semantic verification failed'

install -m 0644 "$work/from-target.cpio.gz" "$publish/$archive_name"
builder_report_sha=$(
	sha256sum "$work/builder-qualification.txt" | cut -d ' ' -f 1
)
{
	printf '%s\n' \
		'schema=rog5-recovery-base-refreeze-v1' \
		'state=reconstructed-successor' \
		'boot_authority=none' \
		'historical_v18_state=original-bytes-unrecovered-and-not-reused' \
		"historical_v18_sha256=$historical_v18_sha" \
		"source_commit=$source_commit" \
		"source_blob=$source_blob" \
		"source_sha256=$source_sha" \
		"lineage_target_size=$target_size" \
		"lineage_target_sha256=$target_sha" \
		"lineage_stage_size=$stage_size" \
		"lineage_stage_sha256=$stage_sha" \
		"qualified_builder_report_sha256=$builder_report_sha" \
		'reconstruction=independent-target-and-outer-stage-reverse-transforms' \
		"archive_size=$successor_size" \
		"archive_sha256=$successor_sha"
} >"$publish/$report_name"
chmod 0644 "$publish/$report_name"

mv -T -- "$publish" "$output_root"
publish=
trap - EXIT HUP INT TERM
find "$work" -depth -delete

sha256sum "$output_root/$archive_name"
echo "PASS refroze v18r from two exact independent retained P2 lineages"
echo "OUTPUT $output_root"
