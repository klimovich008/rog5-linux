#!/bin/sh
# Compose a standby-bisect DTB for ONE RAM trial from the production board.dtb
# (platform-cpucap-dp-sbumux-dtb-r5). Never install one as the default.
#
#   compose-standby-bisect-dtb.sh BASE_DTB OUTPUT VARIANT[,VARIANT...]
#
# Variants (combine with commas; order does not matter):
#   noslpi  SLPI remoteproc@5c00000 disabled: mainline never boots the SLPI
#           (neither does the ASUS 5.4 wrapper), so no SLPI firmware runs in
#           this power cycle's Linux session. rog5-sensors.service skips itself
#           (ExecCondition on this status); no sensors, no auto-rotate.
#   noadsp  ADSP remoteproc@3000000 disabled and marked
#           rog5,standby-bisect; pmic-glink, the sound card and the DP
#           controller removed/disabled with it (their only provider is the
#           ADSP). The ramdisk's power gate boots without battery telemetry
#           only with this marker. No battery/charger readings, no charge
#           control, no USB-C role switching or PD (the side port stays in
#           its default peripheral role), no DP alt mode, no audio.
#           ONLY on battery, one boot, then back to the default bundle.
#   cdsp    CDSP remoteproc@a300000 enabled with the vendor_a firmware
#           (qcom/sm8350/cdsp.mdt, staged by fetch-vendor-cdsp-firmware.py in
#           the extra firmware kit); its fastrpc channel disabled so no HLOS
#           client or SMMU context is created: the CDSP boots and idles, as on
#           stock before an app uses it.
#
# Prints the output's SHA-256. Checks every property it changed.
set -eu
base=${1:?usage: compose-standby-bisect-dtb.sh BASE_DTB OUTPUT VARIANT[,VARIANT]}
output=${2:?missing output}
variants=${3:?missing variant}
# production DTB r5 (installed with r197); another base must be reviewed first.
expected_base=${EXPECTED_BISECT_BASE_SHA256:-34f12b3837333c33b8b096e12c05520595f4f8280219709a198aa45ab6724cbd}
[ -f "$base" ] && [ ! -L "$base" ] || { echo 'FAIL base DTB' >&2; exit 1; }
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] ||
	{ echo 'FAIL base DTB is not the reviewed production DTB' >&2; exit 1; }
[ ! -e "$output" ] || { echo 'FAIL output exists' >&2; exit 1; }
noslpi=0 noadsp=0 cdsp=0
for variant in $(printf '%s\n' "$variants" | tr ',' ' '); do
	case $variant in
		noslpi) noslpi=1 ;;
		noadsp) noadsp=1 ;;
		cdsp) cdsp=1 ;;
		*) echo "FAIL unknown variant $variant" >&2; exit 1 ;;
	esac
done

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
dtb=$work/bisect.dtb
cp "$base" "$dtb"
# Room for the new properties.
fdtput -t s "$dtb" / rog5,standby-bisect "$variants" 2>/dev/null ||
	{ dtc -q -I dtb -O dtb -p 4096 -o "$work/padded.dtb" "$dtb" && mv "$work/padded.dtb" "$dtb" &&
	  fdtput -t s "$dtb" / rog5,standby-bisect "$variants"; }

slpi=/soc@0/remoteproc@5c00000
adsp=/soc@0/remoteproc@3000000
cdsp_node=/soc@0/remoteproc@a300000
dp=/soc@0/display-subsystem@ae00000/displayport-controller@ae90000

expect() {
	[ "$(fdtget "$dtb" "$1" "$2" 2>/dev/null)" = "$3" ] ||
		{ echo "FAIL $1 $2 is not $3" >&2; exit 1; }
}

expect "$slpi" status okay
expect "$adsp" status okay
expect "$cdsp_node" status disabled

if [ "$noslpi" = 1 ]; then
	fdtput -t s "$dtb" "$slpi" status disabled
	expect "$slpi" status disabled
fi
if [ "$noadsp" = 1 ]; then
	fdtput -t s "$dtb" "$adsp" status disabled
	fdtput -t s "$dtb" "$adsp" rog5,standby-bisect noadsp
	expect "$adsp" status disabled
	expect "$adsp" rog5,standby-bisect noadsp
	# pmic_glink talks only to the ADSP: without it battmgr would register
	# power supplies whose every read times out, and UCSI never comes up.
	fdtget "$dtb" /pmic-glink compatible >/dev/null
	fdtput -t s "$dtb" /pmic-glink status disabled
	expect /pmic-glink status disabled
	# The DP bridge chain ends at the pmic-glink connector (HPD from the
	# ADSP); disable the DP controller like the non-DP DTBs so the msm KMS
	# master never waits for it and the panel still comes up.
	expect "$dp" status okay
	fdtput -t s "$dtb" "$dp" status disabled
	expect "$dp" status disabled
	# rog5-audio.service runs only when /proc/device-tree/sound exists; the
	# q6 DAIs it needs are children of the disabled ADSP.
	fdtget "$dtb" /sound compatible >/dev/null
	fdtput -r "$dtb" /sound
	! fdtget "$dtb" /sound compatible >/dev/null 2>&1 ||
		{ echo 'FAIL /sound still present' >&2; exit 1; }
fi
if [ "$cdsp" = 1 ]; then
	fdtput -t s "$dtb" "$cdsp_node" firmware-name qcom/sm8350/cdsp.mdt
	fdtput -t s "$dtb" "$cdsp_node" status okay
	fdtput -t s "$dtb" "$cdsp_node/glink-edge/fastrpc" status disabled
	expect "$cdsp_node" status okay
	expect "$cdsp_node" firmware-name qcom/sm8350/cdsp.mdt
	expect "$cdsp_node/glink-edge/fastrpc" status disabled
	# Stock pil_cdsp_region: 0x89700000 + 0x1e00000, no-map (stock FDT
	# pil_cdsp_region@89700000); refuse a base that moved it.
	region=$(fdtget -t x "$dtb" "$cdsp_node" memory-region)
	path=
	for name in $(fdtget -l "$dtb" /reserved-memory); do
		if [ "$(fdtget -t x "$dtb" "/reserved-memory/$name" phandle 2>/dev/null || :)" = "$region" ]; then
			path=/reserved-memory/$name
		fi
	done
	[ -n "$path" ] || { echo 'FAIL CDSP memory-region not found' >&2; exit 1; }
	[ "$(fdtget -t x "$dtb" "$path" reg)" = '0 89700000 0 1e00000' ] &&
		fdtget "$dtb" "$path" no-map >/dev/null 2>&1 ||
		{ echo 'FAIL CDSP region is not the stock 0x89700000/0x1e00000 no-map' >&2; exit 1; }
fi
# The result must still be a valid tree (no dangling phandle from /sound).
dtc -q -I dtb -O dts -o /dev/null "$dtb"
mv "$dtb" "$output"
sha256sum "$output"
