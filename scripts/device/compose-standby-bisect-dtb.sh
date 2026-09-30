#!/bin/sh
# Compose a standby-bisect DTB for ONE RAM trial from the production board.dtb
# r9 (platform-cpucap-dp4-btmtc-memx-dtb-r9, bundle production-7.2.7-r207).
# Never install one as the default.
#
#   compose-standby-bisect-dtb.sh BASE_DTB OUTPUT VARIANT[,VARIANT...]
#
# r9 is compose-production-dtb.sh with the features
#   touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg,
#   osi,aoss,qupicc,dp,l3,skin,acd,cpucap,usbbtm,mic,usbbtmtc,memx
# (V9 board.dtb + kernel r110 source reproduce it byte for byte: 4a919c15...).
# Every variant starts from those bytes, so all of them keep every production
# feature they do not name below, memx included (checked in the output).
#
# Variants (combine with commas; order does not matter):
#   baseline  no change but the markers: the matched control, booted through
#           the same RAM-trial path as the other variants. Cannot be combined.
#   noslpi  SLPI remoteproc@5c00000 disabled (feature slpi off): no SLPI
#           firmware runs in this Linux session (the ASUS 5.4 wrapper never
#           boots it either). rog5-sensors.service skips itself (ExecCondition
#           on this status); no sensors, no auto-rotate.
#   noadsp  ADSP remoteproc@3000000 disabled and marked rog5,standby-bisect,
#           together with everything whose only provider is the ADSP:
#           - pmic-glink (battmgr, UCSI, altmode): features usbotg/dp lose
#             their Type-C side; the side port stays in its default
#             peripheral role (NCM gadget), no battery/charger readings or
#             charge control. The ramdisk's power gate boots without battery
#             telemetry only with this marker (load-persistent-root-power-usb.sh).
#           - the DP controller (HPD comes from the ADSP through pmic-glink).
#           - /sound, the VA macro (codec@3370000, feature mic) and the LPASS
#             LPI pinctrl (pinctrl@33c0000): their clocks are the ADSP's
#             q6afe clock controller (features audio, mic).
#           - usbbtmtc/usbbtm's 5 V: regulator-rog5-btm-vbus takes its input
#             from btm-otg-boost, which qcom_battmgr (pmic-glink, OEM 0x2102
#             to the ADSP) registers. Without the ADSP the bottom port can
#             never switch its 5 V, so the fixed regulator and the RT1715 TCPC
#             (typec@4e, its only consumer) are disabled instead of left
#             deferring. The bottom xHCI stays enabled as in production (no
#             VBUS: nothing enumerates there). Keep the bottom port empty.
#           ONLY on battery, one boot, then back to the default bundle.
#   cdsp    CDSP remoteproc@a300000 enabled with the vendor_a firmware
#           (qcom/sm8350/cdsp.mdt, staged by fetch-vendor-cdsp-firmware.py in
#           the extra firmware kit of the trial's ramdisk); its fastrpc
#           channel disabled so no HLOS client or SMMU context is created: the
#           CDSP boots and idles, as on stock before an app uses it.
#
# Markers: / rog5,standby-bisect = VARIANTS and
# / rog5,standby-bisect-base = production-dtb-r9 (rog5-standby-bisect-measure
# records both). Prints the output's SHA-256. Checks every property it changed.
set -eu
base=${1:?usage: compose-standby-bisect-dtb.sh BASE_DTB OUTPUT VARIANT[,VARIANT]}
output=${2:?missing output}
variants=${3:?missing variant}
# production DTB r9 (installed with r207); another base must be requalified
# (features, node paths, phandle chains below) and reviewed first.
expected_base=${EXPECTED_BISECT_BASE_SHA256:-4a919c152c678d27b9e0f7fe0d337f63384069227acf4167ad7f176a66168d39}
base_name=production-dtb-r9
[ -f "$base" ] && [ ! -L "$base" ] || { echo 'FAIL base DTB' >&2; exit 1; }
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] ||
	{ echo 'FAIL base DTB is not the reviewed production DTB' >&2; exit 1; }
[ ! -e "$output" ] || { echo 'FAIL output exists' >&2; exit 1; }
baseline=0 noslpi=0 noadsp=0 cdsp=0 count=0
for variant in $(printf '%s\n' "$variants" | tr ',' ' '); do
	case $variant in
		baseline) baseline=1 ;;
		noslpi) noslpi=1 ;;
		noadsp) noadsp=1 ;;
		cdsp) cdsp=1 ;;
		*) echo "FAIL unknown variant $variant" >&2; exit 1 ;;
	esac
	count=$((count + 1))
done
[ "$count" -gt 0 ] || { echo 'FAIL missing variant' >&2; exit 1; }
[ "$((baseline + noslpi + noadsp + cdsp))" = "$count" ] || { echo 'FAIL repeated variant' >&2; exit 1; }
[ "$baseline" = 0 ] || [ "$count" = 1 ] || { echo 'FAIL baseline cannot be combined' >&2; exit 1; }

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
dtb=$work/bisect.dtb
# Room for the new properties.
dtc -q -I dtb -O dtb -p 4096 -o "$dtb" "$base"
fdtput -t s "$dtb" / rog5,standby-bisect "$variants"
fdtput -t s "$dtb" / rog5,standby-bisect-base "$base_name"

slpi=/soc@0/remoteproc@5c00000
adsp=/soc@0/remoteproc@3000000
cdsp_node=/soc@0/remoteproc@a300000
dp=/soc@0/display-subsystem@ae00000/displayport-controller@ae90000
va=/soc@0/codec@3370000
lpi=/soc@0/pinctrl@33c0000
q6afecc=$adsp/glink-edge/apr/service@4/clock-controller
vbus=/regulator-rog5-btm-vbus
boost=$vbus/btm-otg-boost
tcpc=/soc@0/geniqup@ac0000/i2c@a94000/typec@4e
memx=/reserved-memory/memory@34a000000

expect() {
	[ "$(fdtget "$dtb" "$1" "$2" 2>/dev/null)" = "$3" ] ||
		{ echo "FAIL $1 $2 is not $3" >&2; exit 1; }
}
# Enabled: no status property, or "okay".
enabled() {
	case $(fdtget "$dtb" "$1" status 2>/dev/null || echo okay) in okay) ;; *)
		echo "FAIL $1 is not enabled" >&2; exit 1 ;; esac
	fdtget "$dtb" "$1" compatible >/dev/null 2>&1 || { echo "FAIL $1 missing" >&2; exit 1; }
}
phandle() { fdtget -t x "$dtb" "$1" phandle 2>/dev/null || echo none; }
# Every clocks entry of $1 is <q6afecc id attr> (3 cells, provider first).
only_q6afe_clocks() {
	fdtget -t x "$dtb" "$1" clocks 2>/dev/null | awk -v p="$2" '{ if (NF % 3) exit 1
		for (i = 1; i <= NF; i += 3) if ($i != p) exit 1; ok = 1 } END { exit !ok }'
}
# memx: the no-map hole the ASUS wrapper leaves at 0x34a000000 (production
# feature memx) must survive every variant.
check_memx() {
	[ "$(fdtget -t x "$dtb" "$memx" reg 2>/dev/null)" = '3 4a000000 0 4000000' ] &&
		fdtget "$dtb" "$memx" no-map >/dev/null 2>&1 ||
		{ echo 'FAIL memx reservation missing' >&2; exit 1; }
}

# -- requalify the base: the r9 features the variants depend on
check_memx
expect "$slpi" status okay
expect "$slpi" firmware-name qcom/sm8350/slpi.mdt
expect "$adsp" status okay
expect "$cdsp_node" status disabled
enabled /pmic-glink
expect "$dp" status okay
fdtget "$dtb" /sound compatible >/dev/null 2>&1 || { echo 'FAIL no /sound (feature audio)' >&2; exit 1; }
expect "$tcpc" compatible richtek,rt1715
expect "$vbus" compatible regulator-fixed
[ "$(fdtget -t x "$dtb" "$tcpc" vbus-supply 2>/dev/null)" = "$(phandle "$vbus")" ] &&
	[ "$(fdtget -t x "$dtb" "$vbus" vin-supply 2>/dev/null)" = "$(phandle "$boost")" ] &&
	[ "$(fdtget -t x "$dtb" /pmic-glink asus,btm-otg-boost 2>/dev/null)" = "$(phandle "$boost")" ] ||
	{ echo 'FAIL bottom-port 5 V chain is not TCPC -> btm_vbus -> btm_otg_boost (pmic-glink)' >&2; exit 1; }
! fdtget "$dtb" /rog5-btm-vbus-output compatible >/dev/null 2>&1 ||
	{ echo 'FAIL stage-A 5 V switch present (not a usbbtmtc base)' >&2; exit 1; }
expect "$va" compatible qcom,sm8250-lpass-va-macro
expect "$lpi" compatible qcom,sm8350-lpass-lpi-pinctrl
for node in "$va" "$lpi" "$vbus" "$tcpc"; do enabled "$node"; done
only_q6afe_clocks "$va" "$(phandle "$q6afecc")" && only_q6afe_clocks "$lpi" "$(phandle "$q6afecc")" ||
	{ echo 'FAIL VA macro / LPI pinctrl clocks are not all from the ADSP q6afe clock controller' >&2; exit 1; }

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
	fdtput -t s "$dtb" /pmic-glink status disabled
	expect /pmic-glink status disabled
	# The DP bridge chain ends at the pmic-glink connector (HPD from the
	# ADSP); disable the DP controller like the non-DP DTBs so the msm KMS
	# master never waits for it and the panel still comes up.
	fdtput -t s "$dtb" "$dp" status disabled
	expect "$dp" status disabled
	# rog5-audio.service runs only when /proc/device-tree/sound exists; the
	# q6 DAIs it needs are children of the disabled ADSP.
	fdtput -r "$dtb" /sound
	! fdtget "$dtb" /sound compatible >/dev/null 2>&1 ||
		{ echo 'FAIL /sound still present' >&2; exit 1; }
	# Clocked only by q6afecc (checked above): they would defer forever.
	for node in "$va" "$lpi"; do
		fdtput -t s "$dtb" "$node" status disabled
		expect "$node" status disabled
	done
	# btm_otg_boost exists only through battmgr (pmic-glink): the 5 V chain
	# and its only consumer go with it.
	for node in "$vbus" "$tcpc"; do
		fdtput -t s "$dtb" "$node" status disabled
		expect "$node" status disabled
	done
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
check_memx
expect / rog5,standby-bisect "$variants"
expect / rog5,standby-bisect-base "$base_name"
# The result must still be a valid tree (no dangling phandle from /sound).
dtc -q -I dtb -O dts -o /dev/null "$dtb"
mv "$dtb" "$output"
sha256sum "$output"
