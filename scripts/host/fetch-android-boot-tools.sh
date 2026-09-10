#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output_root=${1:-$repo/artifacts/android-boot-tools-v1}
mkboot_commit=d2bb0af5ba6d3198a3e99529c97eda1be0b5a093
mkbootimg_blob=ec2958179691a434df917cd1b6f196edaa80e31d
mkbootimg_lf_sha=37d84b3d162e0bc62e36c1f4e1c63c85ea0caa9f29be023eb2f8efe006ad948c
mkbootimg_size=27333
mkbootimg_sha=d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a
unpack_blob=a3f1a508796b5af54216397b05637f1f5e692a3d
unpack_lf_sha=a9d260978a63bd06a24b6347e7dee8a28ff96639793caea15dff6aa491316308
unpack_size=23786
unpack_sha=7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef
gki_blob=739c61b04a9dbd95cafa5196533e3a472c31f2d9
gki_lf_sha=1bb1feec68a13da18d581aa2c631798f86f6bc10b55d587b2dd31446a0f8a203
gki_size=3082
gki_sha=367858be999c3013d44450a91bde0067f0530857b5a95fbf5858c62477bcaf36
avb_commit=a4a2d67bcfe479adb3d54d6127abb11afbc76701
avb_blob=9c437c76d112662810ea1c14be122bbe8592fec5
avb_lf_sha=da733b43019931f1dd5d62a0e856bc769acbd7034dd8d376582881f42a9a83c3
avb_size=247851
avb_sha=6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff
mkboot_origin=https://android.googlesource.com/platform/system/tools/mkbootimg
avb_origin=https://android.googlesource.com/platform/external/avb
report_name=bootstrap-provenance.txt

for command_name in base64 basename chmod curl cut dirname find git grep \
	mkdir mktemp mv od python3 realpath sed sha256sum stat tail tr; do
	command -v "$command_name" >/dev/null ||
		fail "missing Android boot-tool bootstrap command: $command_name"
done
case $output_root in
	''|/|/dev|/dev/*|/proc|/proc/*|/sys|/sys/*|/run|/run/*)
		fail 'unsafe Android boot-tool output root'
		;;
esac
output_parent=$(dirname "$output_root")
mkdir -p "$output_parent"
output_parent=$(realpath -e "$output_parent")
output_root=$output_parent/$(basename "$output_root")
[[ ! -e $output_root && ! -L $output_root ]] ||
	fail 'refusing existing Android boot-tool output root'

work=$(mktemp -d)
publish=$(mktemp -d "$output_parent/.android-boot-tools-v1.XXXXXX")
cleanup() {
	find "$work" -depth -delete 2>/dev/null || true
	if [[ -n ${publish:-} && -e $publish ]]; then
		find "$publish" -depth -delete 2>/dev/null || true
	fi
}
trap cleanup EXIT HUP INT TERM

fetch_one() {
	origin=$1
	commit=$2
	path=$3
	expected_blob=$4
	expected_lf_sha=$5
	expected_size=$6
	expected_crlf_sha=$7
	output=$8
	label=$9
	encoded=$work/$(basename "$path").b64
	source=$work/$(basename "$path").lf

	curl --fail --location --proto '=https' --tlsv1.2 \
		--retry 3 --output "$encoded" \
		"$origin/+/$commit/$path?format=TEXT"
	base64 --decode "$encoded" >"$source" ||
		fail "invalid Gitiles base64 response for $label"
	[[ $(git hash-object "$source") == "$expected_blob" ]] ||
		fail "$label Git blob identity changed"
	[[ $(sha256sum "$source" | cut -d ' ' -f 1) == \
		"$expected_lf_sha" ]] ||
		fail "$label LF source hash changed"
	[[ $(tail -c 1 "$source" | od -An -tuC | tr -d ' ') == 10 ]] ||
		fail "$label LF source lacks its final newline"
	if grep -q $'\r' "$source"; then
		fail "$label LF source unexpectedly contains carriage returns"
	fi
	sed 's/$/\r/' "$source" >"$output"
	chmod 0755 "$output"
	[[ $(stat -c %s "$output") == "$expected_size" ]] ||
		fail "$label CRLF size changed"
	[[ $(sha256sum "$output" | cut -d ' ' -f 1) == \
		"$expected_crlf_sha" ]] ||
		fail "$label CRLF historical hash changed"
}

fetch_one "$mkboot_origin" "$mkboot_commit" mkbootimg.py \
	"$mkbootimg_blob" "$mkbootimg_lf_sha" "$mkbootimg_size" \
	"$mkbootimg_sha" "$publish/mkbootimg.py" mkbootimg.py
fetch_one "$mkboot_origin" "$mkboot_commit" unpack_bootimg.py \
	"$unpack_blob" "$unpack_lf_sha" "$unpack_size" \
	"$unpack_sha" "$publish/unpack_bootimg.py" unpack_bootimg.py
mkdir "$publish/gki"
fetch_one "$mkboot_origin" "$mkboot_commit" gki/generate_gki_certificate.py \
	"$gki_blob" "$gki_lf_sha" "$gki_size" "$gki_sha" \
	"$publish/gki/generate_gki_certificate.py" generate_gki_certificate.py
fetch_one "$avb_origin" "$avb_commit" avbtool.py \
	"$avb_blob" "$avb_lf_sha" "$avb_size" "$avb_sha" \
	"$publish/avbtool.py" avbtool.py

python3 "$publish/mkbootimg.py" --help >/dev/null
python3 "$publish/unpack_bootimg.py" --help >/dev/null
[[ $(python3 "$publish/avbtool.py" version) == 'avbtool 1.4.0' ]] ||
	fail 'bootstrapped avbtool does not report version 1.4.0'
{
	printf '%s\n' \
		'schema=rog5-android-boot-tools-bootstrap-v1' \
		'state=exact-historical-bytes-recovered' \
		'authority=none' \
		"mkboot_origin=$mkboot_origin" \
		"mkboot_commit=$mkboot_commit" \
		"mkbootimg_blob=$mkbootimg_blob" \
		"mkbootimg_lf_sha256=$mkbootimg_lf_sha" \
		"mkbootimg_crlf_sha256=$mkbootimg_sha" \
		"unpack_bootimg_blob=$unpack_blob" \
		"unpack_bootimg_lf_sha256=$unpack_lf_sha" \
		"unpack_bootimg_crlf_sha256=$unpack_sha" \
		"gki_certificate_blob=$gki_blob" \
		"gki_certificate_lf_sha256=$gki_lf_sha" \
		"gki_certificate_crlf_sha256=$gki_sha" \
		"avb_origin=$avb_origin" \
		"avb_commit=$avb_commit" \
		"avbtool_blob=$avb_blob" \
		"avbtool_lf_sha256=$avb_lf_sha" \
		"avbtool_crlf_sha256=$avb_sha" \
		'line_ending_transform=lf-to-crlf'
} >"$publish/$report_name"
chmod 0644 "$publish/$report_name"

mv -T -- "$publish" "$output_root"
publish=
trap - EXIT HUP INT TERM
find "$work" -depth -delete

sha256sum "$output_root/mkbootimg.py" \
	"$output_root/unpack_bootimg.py" \
	"$output_root/gki/generate_gki_certificate.py" \
	"$output_root/avbtool.py"
echo 'PASS recovered exact historical Android boot tools from pinned authoritative Git blobs'
