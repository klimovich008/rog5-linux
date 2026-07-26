#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-adreno-smmu-kexec-stage-initramfs.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -x "$builder" ] || {
	echo 'FAIL missing executable Adreno SMMU staging-initramfs builder' >&2
	exit 1
}
sh -n "$builder"

for contract in \
	68b8729c5aef7f9a3eacba07685fe952f4df6cac29eb8c35d9559fda98722fab \
	d30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b \
	e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5 \
	da471966073cfb26581b4a5224218904162c5925155b0aa8c24a2b3e4ad0526f \
	4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac \
	'opt/rog5-recovery/board.dtb' \
	'opt/rog5-recovery/SHA256SUMS' \
	'BEGIN .*PRIVATE KEY' \
	'a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn' \
	'find . -mindepth 1 -print0 | sort -z' \
	'--reproducible' \
	'gzip -n'
do
	grep -Fq -- "$contract" "$builder" || {
		echo "FAIL staging-initramfs builder omits: $contract" >&2
		exit 1
	}
done

printf 'wrong\n' >"$stage/wrong-base.cpio.gz"
printf 'wrong\n' >"$stage/wrong.dtb"
if "$builder" "$stage/wrong-base.cpio.gz" "$stage/wrong.dtb" \
	"$stage/output.cpio.gz" >/dev/null 2>&1
then
	echo 'FAIL staging-initramfs builder accepted unreviewed inputs' >&2
	exit 1
fi

if [ -n "${BASE_STAGE:-}" ] && [ -n "${CANDIDATE_DTB:-}" ]; then
	[ -s "$BASE_STAGE" ] && [ -s "$CANDIDATE_DTB" ]
	"$builder" "$BASE_STAGE" "$CANDIDATE_DTB" \
		"$stage/one.cpio.gz" >/dev/null
	"$builder" "$BASE_STAGE" "$CANDIDATE_DTB" \
		"$stage/two.cpio.gz" >/dev/null
	cmp "$stage/one.cpio.gz" "$stage/two.cpio.gz"
fi

echo 'PASS Adreno SMMU staging initramfs changes only the pinned DT payload and checksum'
