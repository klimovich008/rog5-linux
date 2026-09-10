#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
name=rog5-a660-runtime-builder-arch-2026.07.24.oci.tar
url=https://github.com/klimovich008/rog5-linux/releases/download/a660-runtime-builder-v1/$name
output_parent=$repo/artifacts/a660-runtime-builder
output=$output_parent/$name
expected_size=931880960
expected_sha256=c38d64ea0642d659c66022a638167284876b804e8120a83304284a0d2b7af3a2

for command in chmod curl cut id ln mkdir mktemp realpath sha256sum stat \
	sync unlink; do
	command -v "$command" >/dev/null ||
		fail "missing A660 runtime-builder fetch command: $command"
done
mkdir -p "$output_parent"
[[ -d $output_parent && ! -L $output_parent ]] ||
	fail 'A660 runtime-builder artifact parent is unsafe'
output_parent=$(realpath -e "$output_parent")
[[ $output == "$output_parent/$name" ]] ||
	fail 'A660 runtime-builder output path is not canonical'
[[ $(stat -c %u "$output_parent") == "$EUID" ]] ||
	fail 'A660 runtime-builder artifact parent is not caller-owned'
parent_mode=$(stat -c %a "$output_parent")
(( (8#$parent_mode & 8#022) == 0 )) ||
	fail 'A660 runtime-builder artifact parent is group- or world-writable'

verify_archive() {
	local archive=$1

	[[ -f $archive && ! -L $archive ]] ||
		fail 'A660 runtime-builder archive is absent or linked'
	[[ $(stat -c '%u:%a:%h:%s' "$archive") == \
		"$EUID:444:1:$expected_size" ]] ||
		fail 'A660 runtime-builder archive metadata changed'
	[[ $(sha256sum "$archive" | cut -d ' ' -f 1) == \
		"$expected_sha256" ]] ||
		fail 'A660 runtime-builder archive hash changed'
}

if [[ -e $output || -L $output ]]; then
	verify_archive "$output"
	printf 'format=rog5-a660-runtime-builder-fetch-v1\n'
	printf 'archive=%s\n' "$output"
	printf 'sha256=%s\n' "$expected_sha256"
	exit 0
fi

stage=$(mktemp "$output_parent/.rog5-a660-runtime-builder.XXXXXX")
cleanup() {
	[[ ! -e $stage && ! -L $stage ]] || unlink "$stage"
}
trap cleanup EXIT HUP INT TERM
curl --fail --location --proto '=https' --tlsv1.2 --retry 3 \
	--output "$stage" "$url" ||
	fail 'A660 runtime-builder archive download failed'
chmod 0444 "$stage"
verify_archive "$stage"
sync -f "$stage"
ln "$stage" "$output" 2>/dev/null ||
	fail 'A660 runtime-builder archive output appeared during download'
sync -f "$output_parent"
unlink "$stage"
sync -f "$output_parent"
trap - EXIT HUP INT TERM
verify_archive "$output"

printf 'format=rog5-a660-runtime-builder-fetch-v1\n'
printf 'archive=%s\n' "$output"
printf 'sha256=%s\n' "$expected_sha256"
