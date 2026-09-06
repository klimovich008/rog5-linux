#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-a660-registration-kexec-stage-initramfs.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -x "$builder" ] || {
	echo 'FAIL missing executable A660 registration stage builder' >&2
	exit 1
}
sh -n "$builder"

for contract in \
	85f764dd206afd3a2b652c7119eb266f62d687a02b1c32a5d303a51d012157b4 \
	52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db \
	b96f4350b35ff3bfc987ce97828e22bd7136100323752c2ac68c537580bd35d6 \
	4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac \
	'opt/rog5-recovery/Image' \
	'opt/rog5-recovery/board.dtb' \
	'opt/rog5-recovery/initramfs.cpio.gz' \
	'BEGIN .*PRIVATE KEY' \
	'a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn' \
	"name '*.ko'" \
	'--owner=0:0' \
	'--reproducible'
do
	grep -Fq -- "$contract" "$builder" || {
		echo "FAIL A660 registration stage builder omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot|adb|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$builder"
then
	echo 'FAIL A660 registration stage builder controls a device or storage' >&2
	exit 1
fi

printf 'wrong\n' >"$stage/wrong"
for input in BASE_STAGE IMAGE CANDIDATE_DTB; do
	base=${BASE_STAGE:-$stage/wrong}
	image=${IMAGE:-$stage/wrong}
	dtb=${CANDIDATE_DTB:-$stage/wrong}
	case $input in
		BASE_STAGE) base=$stage/wrong ;;
		IMAGE) image=$stage/wrong ;;
		CANDIDATE_DTB) dtb=$stage/wrong ;;
	esac
	if "$builder" "$base" "$image" "$dtb" "$stage/rejected.cpio.gz" \
		>/dev/null 2>&1
	then
		echo "FAIL stage builder accepted a wrong $input" >&2
		exit 1
	fi
done

if [ -n "${BASE_STAGE:-}" ] || [ -n "${IMAGE:-}" ] ||
	[ -n "${CANDIDATE_DTB:-}" ]
then
	[ -s "${BASE_STAGE:-}" ]
	[ -s "${IMAGE:-}" ]
	[ -s "${CANDIDATE_DTB:-}" ]
	"$builder" "$BASE_STAGE" "$IMAGE" "$CANDIDATE_DTB" \
		"$stage/one.cpio.gz" >/dev/null
	"$builder" "$BASE_STAGE" "$IMAGE" "$CANDIDATE_DTB" \
		"$stage/two.cpio.gz" >/dev/null
	cmp "$stage/one.cpio.gz" "$stage/two.cpio.gz"
fi

echo 'PASS A660 registration stage is deterministic, credential-free, firmware-free, module-free, and input-pinned'
