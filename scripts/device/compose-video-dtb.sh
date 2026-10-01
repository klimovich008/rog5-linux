#!/bin/sh
# Compose the hardware-video DTB (d15) from the default main DTB d13
# (platform-d10-memslim-all-dtb-d13, d10 + compose-memslim-dtb.sh
# stockcma,ionpool,pil): adds the SM8350 Iris v2 video core, its video
# clock controller and its IOVA reservation (/iris-iova: iommu-addresses
# only, no physical memory; a root child because the slot-B loader's bundle
# verifier refuses /reserved-memory children without reg) from
# dts/qcom/sm8350-asus-rog-phone5-video.dtso and nothing else.
#
#   compose-video-dtb.sh BASE_DTB KERNEL_SOURCE OUTPUT
#
# KERNEL_SOURCE is a v7.2.7 tree (for scripts/dtc/include-prefixes). The base
# is pinned to d13's SHA-256 so the memslim composition below it keeps its
# own base check (d10); another base must be requalified first
# (EXPECTED_VIDEO_BASE_SHA256 overrides the pin for a reviewed one).
#
# Checks before: the base has neither node, the video PIL carve-out
# memory@85700000 (pil_video_mem) is still reserved, no-map and active, at
# exactly 0x85700000 + 5 MiB (memslim keeps it on purpose), and the labels
# the overlay uses exist. Checks after: the new nodes carry the expected
# compatible, firmware path, stream ID, carve-out, IOVA reservation and
# clock-controller phandles; removing them (and their __symbols__ entries
# and the two markers) gives back the base tree byte for byte as dts. Markers:
# / rog5,video = iris-v2, / rog5,video-base = production-dtb-d13.
# Prints the output's SHA-256.
set -eu
base=${1:?usage: compose-video-dtb.sh BASE_DTB KERNEL_SOURCE OUTPUT}
source=${2:?missing kernel source}
output=${3:?missing output}
# production DTB d13 (main-k113-d13-261001a)
expected_base=${EXPECTED_VIDEO_BASE_SHA256:-1d690d392baa94ff03933763397adbb163b4f953ab25ccb2cb262ffcf9187119}
base_name=production-dtb-d13
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-video.dtso
iris=/soc@0/video-codec@aa00000
videocc=/soc@0/clock-controller@abf0000
carveout=/reserved-memory/memory@85700000
iova=/iris-iova
firmware=qcom/sm8350/vpu20_4v.mbn

fail() { echo "FAIL $*" >&2; exit 1; }
[ -f "$base" ] && [ ! -L "$base" ] || fail 'base DTB'
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] || fail 'base DTB is not the reviewed d13'
[ -d "$source/scripts/dtc/include-prefixes" ] || fail 'kernel source'
[ ! -e "$output" ] && [ ! -L "$output" ] || fail 'output exists'

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

get() { fdtget "$@" 2>/dev/null; }
# before
! get "$base" "$iris" compatible >/dev/null || fail "$iris already exists"
! get "$base" "$videocc" compatible >/dev/null || fail "$videocc already exists"
! get "$base" "$iova" iommu-addresses >/dev/null || fail "$iova already exists"
[ "$(get -t x "$base" "$carveout" reg)" = '0 85700000 0 500000' ] || fail "$carveout reg"
get "$base" "$carveout" no-map >/dev/null || fail "$carveout is not no-map"
case $(get "$base" "$carveout" status || echo okay) in okay) ;; *) fail "$carveout is not active" ;; esac
[ "$(get "$base" /__symbols__ pil_video_mem)" = "$carveout" ] || fail 'pil_video_mem label'
for label in gcc rpmhcc rpmhpd sleep_clk gem_noc config_noc mmss_noc mc_virt apps_smmu \
	rpmhpd_opp_low_svs rpmhpd_opp_svs rpmhpd_opp_svs_l1 rpmhpd_opp_nom; do
	get "$base" /__symbols__ "$label" >/dev/null || fail "label $label missing in the base"
done
[ "$(get "$base" "$(get "$base" /__symbols__ rpmhpd)" compatible)" = qcom,sm8350-rpmhpd ] || fail 'rpmhpd'
[ "$(get "$base" "$(get "$base" /__symbols__ apps_smmu)" compatible | head -c 19)" = qcom,sm8350-smmu-50 ] || fail 'apps_smmu'

cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
	-I "$source/scripts/dtc/include-prefixes" -o "$work/video.pp" "$overlay"
dtc -@ -q -I dts -O dtb -o "$work/video.dtbo" "$work/video.pp"
fdtoverlay -i "$base" -o "$work/composed.dtb" "$work/video.dtbo"
dtb=$work/composed.dtb
fdtput -t s "$dtb" / rog5,video iris-v2
fdtput -t s "$dtb" / rog5,video-base "$base_name"

# after
[ "$(get "$dtb" "$iris" compatible)" = 'qcom,sm8350-iris qcom,sm8250-venus' ] || fail 'iris compatible'
[ "$(get "$dtb" "$iris" status)" = okay ] || fail 'iris status'
[ "$(get "$dtb" "$iris" firmware-name)" = "$firmware" ] || fail 'firmware-name'
[ "$(get -t x "$dtb" "$iris" reg)" = '0 aa00000 0 100000' ] || fail 'iris reg'
# the firmware carve-out first (the driver loads into index 0), then the IOVA hole
iova_ph=$(get -t u "$dtb" "$iova" phandle) || fail 'iris-iova phandle'
[ "$(get -t u "$dtb" "$iris" memory-region)" = "$(get -t u "$dtb" "$carveout" phandle) $iova_ph" ] || fail 'memory-region'
! get "$dtb" "$iova" reg >/dev/null || fail 'iris-iova must not reserve physical memory'
! get "$dtb" "$iova" compatible >/dev/null || fail 'iris-iova must not create a device'
# every /reserved-memory child keeps a reg (rog5-bundle-verify refuses others)
for child in $(fdtget -l "$dtb" /reserved-memory); do
	get "$dtb" "/reserved-memory/$child" reg >/dev/null || fail "/reserved-memory/$child has no reg"
done
[ "$(get -t x "$dtb" "$iova" iommu-addresses)" = "$(printf '%x 0 0 0 25800000' "$(get -t u "$dtb" "$iris" phandle)")" ] ||
	fail 'iris-iova iommu-addresses'
smmu=$(get -t u "$dtb" "$(get "$dtb" /__symbols__ apps_smmu)" phandle)
[ "$(get -t x "$dtb" "$iris" iommus)" = "$(printf '%x 2100 400' "$smmu")" ] || fail 'iommus'
vcc=$(get -t u "$dtb" "$videocc" phandle) || fail 'videocc phandle'
[ "$(get "$dtb" "$videocc" compatible)" = qcom,sm8350-videocc ] || fail 'videocc compatible'
set -- $(get -t u "$dtb" "$iris" power-domains)
[ "$#" = 8 ] && [ "$1" = "$vcc" ] && [ "$3" = "$vcc" ] || fail 'power-domains'
[ "$(get "$dtb" "$iris" power-domain-names)" = 'venus vcodec0 mx mmcx' ] || fail 'power-domain-names'
[ "$(get "$dtb" "$iris/opp-table/opp-444000000" required-opps >/dev/null && echo ok)" = ok ] || fail 'opp table'

# Nothing else changed: drop what the overlay added and compare with the base.
cp "$dtb" "$work/strip.dtb"
fdtput -r "$work/strip.dtb" "$iris" "$videocc" "$iova"
fdtput -d "$work/strip.dtb" / rog5,video rog5,video-base
for label in iris videocc iris_opp_table iris_iova; do
	! get "$work/strip.dtb" /__symbols__ "$label" >/dev/null || fdtput -d "$work/strip.dtb" /__symbols__ "$label"
done
dtc -q -I dtb -O dts "$base" >"$work/a"
dtc -q -I dtb -O dts "$work/strip.dtb" >"$work/b"
cmp -s "$work/a" "$work/b" || { diff "$work/a" "$work/b" | head -20 >&2; fail 'the tree changed outside the three video nodes'; }

dtc -q -I dtb -O dtb -o "$output.tmp.$$" "$dtb"
mv "$output.tmp.$$" "$output"
sha256sum "$output" | cut -d ' ' -f 1
