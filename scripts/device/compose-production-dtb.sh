#!/bin/sh
# Compose the default production board.dtb from the installed V9 headless DTB:
# the display/GPU composition (compose-production-display-dtb.sh), the SID 5
# PMIC disabled (display-dtb-r2), then the platform overlay (PMK8350 RTC) and
# ramoops in the 0x9b800000 reservation. Checks the r2 intermediate byte for byte before adding anything.
set -eu
base=${1:?usage: compose-production-dtb.sh BASE_DTB KERNEL_SOURCE OUTPUT [touch|touch,bluetooth|touch,bluetooth,cpuidle|touch,bluetooth,cpuidle,gpubw|touch,bluetooth,cpuidle,gpubw,bwmon|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,slpi|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg,osi|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg,osi,aoss|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg,osi,aoss,qupicc|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg,osi,aoss,qupicc,dp]}
source=${2:?missing kernel source}
output=${3:?missing output}
features=${4:-}
# l3 (CPU OPP tables voting the EPSS L3) may follow any feature list; needs a
# kernel with CONFIG_INTERCONNECT_QCOM_OSM_L3=y.
case ,$features, in *,l3,*) l3=1; features=$(printf %s "$features" | sed 's/^l3$//; s/,l3$//; s/,l3,/,/') ;; *) l3=0 ;; esac
# skin (board thermistors, skin thermal policy) likewise; needs the ADC7 and
# ADC-TM modules in boot-modules.
case ,$features, in *,skin,*) skin=1; features=$(printf %s "$features" | sed 's/^skin$//; s/,skin$//; s/,skin,/,/') ;; *) skin=0 ;; esac
# disprsc (display RSC node + zero-vote child, patch 0086) likewise.
case ,$features, in *,disprsc,*) disprsc=1; features=$(printf %s "$features" | sed 's/^disprsc$//; s/,disprsc$//; s/,disprsc,/,/') ;; *) disprsc=0 ;; esac
# acd (GPU adaptive clock distribution) likewise.
case ,$features, in *,acd,*) acd=1; features=$(printf %s "$features" | sed 's/^acd$//; s/,acd$//; s/,acd,/,/') ;; *) acd=0 ;; esac
# cpucap (CPU capacity + energy model from stock) likewise.
case ,$features, in *,cpucap,*) cpucap=1; features=$(printf %s "$features" | sed 's/^cpucap$//; s/,cpucap$//; s/,cpucap,/,/') ;; *) cpucap=0 ;; esac
# usbbtm (bottom USB-C port as a USB 2.0 host, 5 V by hand) likewise; needs a
# kernel with 0089 and CONFIG_REGULATOR_USERSPACE_CONSUMER=y.
case ,$features, in *,usbbtm,*) usbbtm=1; features=$(printf %s "$features" | sed 's/^usbbtm$//; s/,usbbtm$//; s/,usbbtm,/,/') ;; *) usbbtm=0 ;; esac
# mic (built-in DMICs on the LPASS VA macro) likewise; needs audio and a kernel
# with patch 0083 (the VA macro drops its LPASS core votes when idle).
case ,$features, in *,mic,*) mic=1; features=$(printf %s "$features" | sed 's/^mic$//; s/,mic$//; s/,mic,/,/') ;; *) mic=0 ;; esac
case $mic,$features, in 1,*,audio,*|0,*) ;; *) echo 'FAIL mic needs audio' >&2; exit 1 ;; esac
case $features in ''|touch|touch,bluetooth|touch,bluetooth,cpuidle|touch,bluetooth,cpuidle,gpubw|touch,bluetooth,cpuidle,gpubw,bwmon|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,slpi|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg,osi|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg,osi,aoss|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg,osi,aoss,qupicc|touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg,osi,aoss,qupicc,dp) ;; *) echo 'FAIL unknown feature' >&2; exit 1 ;; esac
feature=${features%%,*}
expected_r2=08d41d4dbb7e16984d0b45f776a9654e38ba9c9553fa1f3a315a0882a9850b66
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
[ ! -e "$output" ] || { echo 'FAIL output exists' >&2; exit 1; }
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

sh "$repo/scripts/device/compose-production-display-dtb.sh" "$base" "$source" "$work/display.dtb" >/dev/null
cp "$work/display.dtb" "$work/r2.dtb"
fdtput -t s "$work/r2.dtb" /soc@0/spmi@c440000/pmic@5 status disabled
[ "$(sha256sum "$work/r2.dtb" | cut -d ' ' -f 1)" = "$expected_r2" ] ||
	{ echo 'FAIL display-dtb-r2 is not reproduced' >&2; exit 1; }

cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
	-I "$source/scripts/dtc/include-prefixes" \
	-o "$work/platform.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-platform.dtso"
dtc -@ -q -I dts -O dtb -o "$work/platform.dtbo" "$work/platform.pp"
fdtoverlay -i "$work/r2.dtb" -o "$work/composed.dtb" "$work/platform.dtbo"
# ramoops takes over the 4 MiB stock debug region in place (same node, same reg).
node=/reserved-memory/memory@9b800000
[ "$(fdtget "$work/composed.dtb" "$node" status)" = disabled ] &&
	[ "$(fdtget "$work/composed.dtb" "$node" compatible)" = qcom,rmtfs-mem ] ||
	{ echo 'FAIL unexpected 0x9b800000 reservation' >&2; exit 1; }
for property in qcom,client-id qcom,vmid no-map; do
	fdtput -d "$work/composed.dtb" "$node" "$property"
done
fdtput -t s "$work/composed.dtb" "$node" compatible ramoops
fdtput -t s "$work/composed.dtb" "$node" status okay
# Exactly the layout the ASUS 5.4 wrapper kernel uses on its command line
# (1 MiB dump record, 3 MiB console, no pmsg/ftrace/ECC). It boots first after
# every reset; with a different layout its ramoops reinitializes the region
# (trial t5 found the t4 records corrupted). With the same one it only replaces
# the console zone, and a panic dump survives until our kernel reads it.
fdtput -t u "$work/composed.dtb" "$node" record-size 1048576
fdtput -t u "$work/composed.dtb" "$node" console-size 3145728
fdtput -t u "$work/composed.dtb" "$node" pmsg-size 0
fdtput -t u "$work/composed.dtb" "$node" ftrace-size 0
fdtput -t u "$work/composed.dtb" "$node" ecc-size 0

if [ "$feature" = touch ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/touch.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-touch.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/touch.dtbo" "$work/touch.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/touched.dtb" "$work/touch.dtbo"
	mv "$work/touched.dtb" "$work/composed.dtb"
	i2c=/soc@0/geniqup@9c0000/i2c@990000
	[ "$(fdtget "$work/composed.dtb" "$i2c" status)" = okay ] &&
		[ "$(fdtget "$work/composed.dtb" "$i2c/touchscreen@38" status)" = okay ] &&
		[ "$(fdtget "$work/composed.dtb" "$i2c/touchscreen@38" compatible)" = asus,rog5-mp2-fts3658u ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/geniqup@9c0000/spi@990000 status)" = disabled ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/dma-controller@900000 status)" = okay ] ||
		{ echo 'FAIL touch composition' >&2; exit 1; }
fi
case ,$features, in *,bluetooth,*) bluetooth=1 ;; *) bluetooth=0 ;; esac
case ,$features, in *,cpuidle,*) cpuidle=1 ;; *) cpuidle=0 ;; esac
case ,$features, in *,gpubw,*) gpubw=1 ;; *) gpubw=0 ;; esac
case ,$features, in *,bwmon,*) bwmon=1 ;; *) bwmon=0 ;; esac
case ,$features, in *,ddrscale,*) ddrscale=1 ;; *) ddrscale=0 ;; esac
case ,$features, in *,periph,*) periph=1 ;; *) periph=0 ;; esac
case ,$features, in *,audio,*) audio=1 ;; *) audio=0 ;; esac
case ,$features, in *,slpi,*) slpi=1 ;; *) slpi=0 ;; esac
case ,$features, in *,usbotg,*) usbotg=1 ;; *) usbotg=0 ;; esac
case ,$features, in *,dp,*) dp=1 ;; *) dp=0 ;; esac
case ,$features, in *,osi,*) osi=1 ;; *) osi=0 ;; esac
case ,$features, in *,aoss,*) aoss=1 ;; *) aoss=0 ;; esac
case ,$features, in *,qupicc,*) qupicc=1 ;; *) qupicc=0 ;; esac
if [ "$bluetooth" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/bluetooth.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-bluetooth.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/bluetooth.dtbo" "$work/bluetooth.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/bt.dtb" "$work/bluetooth.dtbo"
	mv "$work/bt.dtb" "$work/composed.dtb"
	uart=/soc@0/geniqup@8c0000/serial@890000
	[ "$(fdtget "$work/composed.dtb" /soc@0/geniqup@8c0000 status)" = disabled ] &&
		[ "$(fdtget "$work/composed.dtb" "$uart" status)" = okay ] &&
		[ "$(fdtget "$work/composed.dtb" "$uart/bluetooth" compatible)" = qcom,wcn6855-bt ] &&
		[ "$(fdtget "$work/composed.dtb" /aliases serial1)" = "$uart" ] ||
		{ echo 'FAIL bluetooth composition' >&2; exit 1; }
fi
if [ "$cpuidle" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/cpuidle.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-cpuidle.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/cpuidle.dtbo" "$work/cpuidle.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/idle.dtb" "$work/cpuidle.dtbo"
	mv "$work/idle.dtb" "$work/composed.dtb"
	little=$(fdtget "$work/composed.dtb" /cpus/idle-states/cpu-sleep-0-0 phandle)
	big=$(fdtget "$work/composed.dtb" /cpus/idle-states/cpu-sleep-1-0 phandle)
	for cpu in 0 100 200 300; do
		[ "$(fdtget "$work/composed.dtb" /cpus/cpu@$cpu cpu-idle-states)" = "$little" ] ||
			{ echo 'FAIL cpuidle composition' >&2; exit 1; }
	done
	for cpu in 400 500 600 700; do
		[ "$(fdtget "$work/composed.dtb" /cpus/cpu@$cpu cpu-idle-states)" = "$big" ] ||
			{ echo 'FAIL cpuidle composition' >&2; exit 1; }
	done
	# platform-coordinated only: no CPU power-domain references
	[ -z "$(fdtget "$work/composed.dtb" /cpus/cpu@0 power-domains 2>/dev/null)" ] ||
		{ echo 'FAIL cpuidle must not add OSI domains' >&2; exit 1; }
fi
# osi: OS-initiated PSCI with the upstream CPU/cluster domain hierarchy (the
# stock regime), restoring what the board DT deletes. Stage A offers the
# cluster only its APSS-off state (0x41000044); AOSS sleep stays out until
# APSS-off is qualified. apps_rsc hangs off the cluster domain again, so RPMh
# flushes sleep/wake votes before the cluster powers down. Needs a kernel
# with ARM_PSCI_CPUIDLE_DOMAIN. Overlays cannot delete properties, so fdtput.
[ "$aoss" = 0 ] || [ "$osi" = 1 ] || { echo 'FAIL aoss needs osi' >&2; exit 1; }
if [ "$osi" = 1 ]; then
	[ "$cpuidle" = 1 ] || { echo 'FAIL osi needs cpuidle' >&2; exit 1; }
	cluster=$(fdtget "$work/composed.dtb" /psci/power-domain-cpu-cluster0 phandle)
	apss_off=$(fdtget "$work/composed.dtb" /cpus/domain-idle-states/cluster-sleep-0 phandle)
	[ -n "$cluster" ] && [ -n "$apss_off" ] &&
		[ "$(fdtget -t x "$work/composed.dtb" /cpus/domain-idle-states/cluster-sleep-0 arm,psci-suspend-param)" = 41000044 ] ||
		{ echo 'FAIL osi: upstream cluster domain or APSS-off state missing' >&2; exit 1; }
	n=0
	for cpu in 0 100 200 300 400 500 600 700; do
		pd=$(fdtget "$work/composed.dtb" /psci/power-domain-cpu$n phandle) ||
			{ echo "FAIL osi: no power-domain-cpu$n" >&2; exit 1; }
		fdtput -d "$work/composed.dtb" /cpus/cpu@$cpu cpu-idle-states
		fdtput -t u "$work/composed.dtb" /cpus/cpu@$cpu power-domains "$pd"
		fdtput -t s "$work/composed.dtb" /cpus/cpu@$cpu power-domain-names psci
		n=$((n + 1))
	done
	cluster_states=$apss_off
	# Stage B (aoss): the cluster may also enter AOSS sleep (0x4100c344),
	# which lets RPMh apply the flushed sleep votes: CX collapse and DDR
	# self-refresh when no other master votes (qcom_stats cxsd/ddr).
	if [ "$aoss" = 1 ]; then
		aoss_sleep=$(fdtget "$work/composed.dtb" /cpus/domain-idle-states/cluster-sleep-1 phandle)
		[ "$(fdtget -t x "$work/composed.dtb" /cpus/domain-idle-states/cluster-sleep-1 arm,psci-suspend-param)" = 4100c344 ] ||
			{ echo 'FAIL osi: AOSS-sleep state missing' >&2; exit 1; }
		cluster_states="$apss_off $aoss_sleep"
	fi
	# shellcheck disable=SC2086 # one phandle per state
	fdtput -t u "$work/composed.dtb" /psci/power-domain-cpu-cluster0 domain-idle-states $cluster_states
	rsc=$(fdtget -l "$work/composed.dtb" /soc@0 | grep '^rsc@' | head -1)
	[ -n "$rsc" ] || { echo 'FAIL osi: apps_rsc not found' >&2; exit 1; }
	fdtput -t u "$work/composed.dtb" "/soc@0/$rsc" power-domains "$cluster"
	[ "$(fdtget "$work/composed.dtb" /cpus/cpu@700 power-domain-names)" = psci ] &&
		[ -z "$(fdtget "$work/composed.dtb" /cpus/cpu@0 cpu-idle-states 2>/dev/null)" ] &&
		[ "$(fdtget "$work/composed.dtb" /psci/power-domain-cpu-cluster0 domain-idle-states)" = "$cluster_states" ] ||
		{ echo 'FAIL osi composition' >&2; exit 1; }
fi
if [ "$gpubw" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/gpubw.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-gpu-bw.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/gpubw.dtbo" "$work/gpubw.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/bw.dtb" "$work/gpubw.dtbo"
	mv "$work/bw.dtb" "$work/composed.dtb"
	gpu=/soc@0/gpu@3d00000
	gem=$(fdtget "$work/composed.dtb" /soc@0/interconnect@9100000 phandle)
	mc=$(fdtget "$work/composed.dtb" /soc@0/interconnect@1580000 phandle)
	[ "$(fdtget "$work/composed.dtb" "$gpu" interconnects)" = "$gem 5 7 $mc 1 7" ] &&
		[ "$(fdtget "$work/composed.dtb" "$gpu" interconnect-names)" = gfx-mem ] ||
		{ echo 'FAIL gpubw interconnect' >&2; exit 1; }
	# every GPU OPP carries exactly one peak bandwidth
	for opp in $(fdtget -l "$work/composed.dtb" "$gpu/opp-table"); do
		[ -n "$(fdtget "$work/composed.dtb" "$gpu/opp-table/$opp" opp-peak-kBps)" ] ||
			{ echo "FAIL gpubw $opp has no opp-peak-kBps" >&2; exit 1; }
	done
	[ "$(fdtget "$work/composed.dtb" "$gpu/opp-table/opp-315000000" opp-peak-kBps)" = 1804000 ] &&
		[ "$(fdtget "$work/composed.dtb" /thermal-zones/gpu-top-thermal/trips/trip-point0 temperature)" = 95000 ] &&
		[ "$(fdtget "$work/composed.dtb" /thermal-zones/gpu-bottom-thermal/trips/trip-point0 temperature)" = 95000 ] ||
		{ echo 'FAIL gpubw composition' >&2; exit 1; }
fi
if [ "$bwmon" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/bwmon.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-bwmon.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/bwmon.dtbo" "$work/bwmon.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/mon.dtb" "$work/bwmon.dtbo"
	mv "$work/mon.dtb" "$work/composed.dtb"
	gem=$(fdtget "$work/composed.dtb" /soc@0/interconnect@9100000 phandle)
	mc=$(fdtget "$work/composed.dtb" /soc@0/interconnect@1580000 phandle)
	[ "$(fdtget -tx "$work/composed.dtb" /soc@0/pmu@9091000 reg)" = '0 9091000 0 1000' ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/pmu@9091000 interconnects)" = "$mc 0 3 $mc 1 3" ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/pmu@9091000 interrupts)" = '0 81 4' ] &&
		[ "$(fdtget -l "$work/composed.dtb" /soc@0/pmu@9091000/opp-table | wc -l)" = 11 ] &&
		[ "$(fdtget -tx "$work/composed.dtb" /soc@0/pmu@90b6400 reg)" = '0 90b6400 0 600' ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/pmu@90b6400 interconnects)" = "$gem 2 3 $gem 14 3" ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/pmu@90b6400 interrupts)" = '0 581 4' ] &&
		[ "$(fdtget -l "$work/composed.dtb" /soc@0/pmu@90b6400/opp-table | wc -l)" = 7 ] &&
		[ "$(fdtget "$work/composed.dtb" /rog5-input-boost interconnects)" = "$gem 2 3 $gem 14 3 $mc 0 3 $mc 1 3" ] &&
		[ "$(fdtget "$work/composed.dtb" /rog5-input-boost asus,llcc-ddr-kBps)" = 12784000 ] ||
		{ echo 'FAIL bwmon composition' >&2; exit 1; }
fi
if [ "$ddrscale" = 1 ]; then
	# The crypto engine has no driver in this kernel. As an enabled but
	# unprobed interconnect consumer it holds the aggre2/mc_virt providers'
	# sync_state, so every DDR/LLCC node stays at the boot-time maximum.
	# Disable it only with GPU (gpubw) and CPU (bwmon) votes in place, so
	# something asks for bandwidth once the hold is released.
	[ "$gpubw" = 1 ] && [ "$bwmon" = 1 ] || { echo 'FAIL ddrscale needs gpubw and bwmon' >&2; exit 1; }
	crypto=/soc@0/crypto@1dfa000
	[ "$(fdtget "$work/composed.dtb" "$crypto" compatible | cut -d ' ' -f 1)" = qcom,sm8350-qce ] ||
		{ echo 'FAIL unexpected crypto node' >&2; exit 1; }
	fdtput -t s "$work/composed.dtb" "$crypto" status disabled
fi
if [ "$periph" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/periph.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-peripherals.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/periph.dtbo" "$work/periph.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/per.dtb" "$work/periph.dtbo"
	mv "$work/per.dtb" "$work/composed.dtb"
	w0=/soc@0/geniqup@9c0000
	c2=$(fdtget "$work/composed.dtb" /soc@0/spmi@c440000/pmic@2/gpio@8800 phandle)
	[ "$(fdtget "$work/composed.dtb" $w0/i2c@998000 status)" = okay ] &&
		[ "$(fdtget "$work/composed.dtb" $w0/spi@998000 status)" = disabled ] &&
		[ "$(fdtget "$work/composed.dtb" $w0/serial@998000 status)" = disabled ] &&
		[ "$(fdtget "$work/composed.dtb" $w0/i2c@998000/haptics@5a compatible)" = awinic,aw8697 ] &&
		[ "$(fdtget "$work/composed.dtb" $w0/i2c@980000 status)" = okay ] &&
		[ "$(fdtget "$work/composed.dtb" $w0/spi@980000 status)" = disabled ] &&
		[ "$(fdtget "$work/composed.dtb" $w0/i2c@980000/light-sensor@60 compatible)" = vishay,vcnl36866 ] &&
		[ -z "$(fdtget -l "$work/composed.dtb" /soc@0/rsc@18200000/regulators-1 | grep -x ldo7)" ] &&
		[ "$(fdtget "$work/composed.dtb" $w0/i2c@980000/led-controller@16 enable-gpios)" = "$c2 2 0" ] &&
		[ "$(fdtget "$work/composed.dtb" $w0/i2c@980000/led-controller@16 function)" = logo ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/geniqup@8c0000 status)" = disabled ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/spmi@c440000/pmic@2/led-controller@ee00 status)" = okay ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/spmi@c440000/pmic@2/led-controller@ee00/led-0 led-sources)" = 1 ] ||
		{ echo 'FAIL periph composition' >&2; exit 1; }
fi
if [ "$audio" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/audio.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-audio.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/audio.dtbo" "$work/audio.pp"
	# mic goes first: fdtoverlay prepends new /sound children, so the audio
	# links keep PCM 0-2 and the mic front end becomes PCM 3.
	links='mm1-dai-link mm2-dai-link speaker-dai-link '
	if [ "$mic" = 1 ]; then
		grep -q 'Drop the LPASS macro/dcodec HW votes' "$source/sound/soc/codecs/lpass-va-macro.c" ||
			{ echo 'FAIL mic: kernel source lacks 0083' >&2; exit 1; }
		cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
			-I "$source/scripts/dtc/include-prefixes" \
			-o "$work/mic.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-microphones.dtso"
		dtc -@ -q -I dts -O dtb -o "$work/mic.dtbo" "$work/mic.pp"
		fdtoverlay -i "$work/composed.dtb" -o "$work/mic.dtb" "$work/mic.dtbo"
		mv "$work/mic.dtb" "$work/composed.dtb"
		links="${links}mm3-dai-link mic-dai-link "
	fi
	fdtoverlay -i "$work/composed.dtb" -o "$work/aud.dtb" "$work/audio.dtbo"
	mv "$work/aud.dtb" "$work/composed.dtb"
	i2c17=/soc@0/geniqup@8c0000/i2c@88c000
	afe=/soc@0/remoteproc@3000000/glink-edge/apr/service@4/dais
	# The amplifiers' bus is on wrapper 2: that wrapper must stay disabled at boot.
	[ "$(fdtget "$work/composed.dtb" /soc@0/geniqup@8c0000 status)" = disabled ] &&
		[ "$(fdtget "$work/composed.dtb" $i2c17 status)" = okay ] &&
		[ "$(fdtget "$work/composed.dtb" $i2c17/amplifier@30 compatible)" = cirrus,cs35l45 ] &&
		[ "$(fdtget "$work/composed.dtb" $i2c17/amplifier@31 sound-name-prefix)" = SPK ] &&
		[ "$(fdtget "$work/composed.dtb" $afe/dai@147 reg)" = 147 ] &&
		[ "$(fdtget "$work/composed.dtb" $afe/dai@147 qcom,sd-lines)" = 1 ] &&
		[ "$(fdtget "$work/composed.dtb" /sound compatible)" = qcom,sm8250-sndcard ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/remoteproc@3000000/glink-edge/apr/service@7/dais qcom,iova-bits)" = 29 ] &&
		[ "$(fdtget -l "$work/composed.dtb" /sound | tr '\n' ' ')" = "$links" ] ||
		{ echo 'FAIL audio composition' >&2; exit 1; }
fi
if [ "$mic" = 1 ]; then
	va=/soc@0/codec@3370000
	afe=/soc@0/remoteproc@3000000/glink-edge/apr/service@4
	l2c=/soc@0/rsc@18200000/regulators-1/ldo2
	lpi=/soc@0/pinctrl@33c0000
	# VA_CODEC_DMA_TX_0 = 110, LPASS_CLK_ID_TX_CORE_MCLK = 57, Q6ASM_DAI_TX = 1
	[ "$(fdtget "$work/composed.dtb" $va compatible)" = qcom,sm8250-lpass-va-macro ] &&
		[ "$(fdtget "$work/composed.dtb" $va clock-names)" = 'mclk macro dcodec' ] &&
		[ "$(fdtget "$work/composed.dtb" $va clocks | cut -d ' ' -f 1-3)" = \
			"$(fdtget "$work/composed.dtb" $afe/clock-controller phandle) 57 1" ] &&
		[ "$(fdtget "$work/composed.dtb" $va qcom,dmic-sample-rate)" = 2400000 ] &&
		[ "$(fdtget "$work/composed.dtb" $va vdd-micb-supply)" = "$(fdtget "$work/composed.dtb" $l2c phandle)" ] &&
		[ "$(fdtget "$work/composed.dtb" $l2c regulator-min-microvolt)" = 1800000 ] &&
		[ "$(fdtget "$work/composed.dtb" $l2c regulator-max-microvolt)" = 1800000 ] &&
		! fdtget "$work/composed.dtb" $l2c regulator-always-on >/dev/null 2>&1 &&
		[ "$(fdtget "$work/composed.dtb" $va pinctrl-0)" = \
			"$(fdtget "$work/composed.dtb" $lpi/rog5-dmic01-active-state phandle) $(fdtget "$work/composed.dtb" $lpi/rog5-dmic23-active-state phandle)" ] &&
		[ "$(fdtget "$work/composed.dtb" $lpi/rog5-dmic23-active-state/data-pins function)" = dmic2_data ] &&
		[ "$(fdtget "$work/composed.dtb" /sound/mic-dai-link/cpu sound-dai)" = \
			"$(fdtget "$work/composed.dtb" $afe/dais phandle) 110" ] &&
		[ "$(fdtget "$work/composed.dtb" /sound/mic-dai-link/codec sound-dai)" = \
			"$(fdtget "$work/composed.dtb" $va phandle) 0" ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/remoteproc@3000000/glink-edge/apr/service@7/dais/dai@2 direction)" = 1 ] &&
		[ "$(fdtget "$work/composed.dtb" /sound audio-routing | wc -w)" = 12 ] ||
		{ echo 'FAIL mic composition' >&2; exit 1; }
fi
if [ "$slpi" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/slpi.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-slpi.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/slpi.dtbo" "$work/slpi.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/sl.dtb" "$work/slpi.dtbo"
	mv "$work/sl.dtb" "$work/composed.dtb"
	[ "$(fdtget "$work/composed.dtb" /soc@0/remoteproc@5c00000 status)" = okay ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/remoteproc@5c00000 firmware-name)" = qcom/sm8350/slpi.mdt ] ||
		{ echo 'FAIL slpi composition' >&2; exit 1; }
fi
if [ "$usbotg" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/usbotg.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-usb-otg-side.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/usbotg.dtbo" "$work/usbotg.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/uo.dtb" "$work/usbotg.dtbo"
	mv "$work/uo.dtb" "$work/composed.dtb"
	# connector@0 must be the first child of /pmic-glink (UCSI matches by index).
	[ "$(fdtget -l "$work/composed.dtb" /pmic-glink | head -n 1)" = connector@0 ] &&
		[ "$(fdtget "$work/composed.dtb" /pmic-glink/connector@0 compatible)" = usb-c-connector ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/usb@a6f8800/usb@a600000 dr_mode)" = otg ] &&
		fdtget "$work/composed.dtb" /soc@0/usb@a6f8800 wakeup-source >/dev/null 2>&1 &&
		fdtget "$work/composed.dtb" /pmic-glink asus,cell-voltage-readonly >/dev/null 2>&1 ||
		{ echo 'FAIL usbotg composition' >&2; exit 1; }
fi
# dp: DisplayPort alt mode on the side port (stage 1, USB stays high-speed);
# needs usbotg's connector@0.
if [ "$dp" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/dp.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-displayport-side.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/dp.dtbo" "$work/dp.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/dp.dtb" "$work/dp.dtbo"
	mv "$work/dp.dtb" "$work/composed.dtb"
	# The Type-C port must not wait for the combo PHY (its module needs drm):
	# without orientation-switch the PHY registers no typec switch/mux and
	# stays in USB3+DP mode.
	fdtput -d "$work/composed.dtb" /soc@0/phy@88e8000 orientation-switch
	[ "$(fdtget "$work/composed.dtb" /soc@0/display-subsystem@ae00000/displayport-controller@ae90000 status)" = okay ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/phy@88e8000 status)" = okay ] &&
		! fdtget "$work/composed.dtb" /soc@0/phy@88e8000 orientation-switch >/dev/null 2>&1 &&
		! fdtget "$work/composed.dtb" /soc@0/phy@88e8000 mode-switch >/dev/null 2>&1 &&
		fdtget "$work/composed.dtb" /soc@0/pinctrl@f100000/rog5-dp-aux-en-hog gpio-hog >/dev/null &&
		fdtget "$work/composed.dtb" /pmic-glink/connector@0/ports/port@1 reg >/dev/null ||
		{ echo 'FAIL dp composition' >&2; exit 1; }
fi
# qupicc: the QUP0/1/2 core BCMs get a Linux provider (kernel patch 0066,
# qcom,sm8350-clk-virt), so sync_state clears the votes the ASUS wrapper left
# in the APPS DRV. Only with a 0066 kernel: an unbound provider node blocks the
# global interconnect sync_state.
if [ "$qupicc" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/qupicc.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-qup-icc.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/qupicc.dtbo" "$work/qupicc.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/qi.dtb" "$work/qupicc.dtbo"
	mv "$work/qi.dtb" "$work/composed.dtb"
	grep -q 'qcom,sm8350-clk-virt' "$source/drivers/interconnect/qcom/sm8350.c" ||
		{ echo 'FAIL qupicc: kernel source lacks 0066' >&2; exit 1; }
	[ "$(fdtget "$work/composed.dtb" /interconnect-clk-virt compatible)" = qcom,sm8350-clk-virt ] &&
		[ "$(fdtget "$work/composed.dtb" /interconnect-clk-virt qcom,bcm-voters)" = \
			"$(fdtget "$work/composed.dtb" /soc@0/rsc@18200000/bcm-voter phandle)" ] ||
		{ echo 'FAIL qupicc composition' >&2; exit 1; }
fi
if [ "$l3" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/l3.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-cpu-l3.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/l3.dtbo" "$work/l3.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/l3.dtb" "$work/l3.dtbo"
	mv "$work/l3.dtb" "$work/composed.dtb"
	l3p=$(fdtget "$work/composed.dtb" /soc@0/interconnect@18590000 phandle)
	for c in 0 100 200 300 400 500 600 700; do
		[ "$(fdtget "$work/composed.dtb" /cpus/cpu@$c interconnects)" = "$l3p 0 $l3p 1" ] &&
			[ -n "$(fdtget "$work/composed.dtb" /cpus/cpu@$c operating-points-v2)" ] ||
			{ echo "FAIL l3 composition cpu@$c" >&2; exit 1; }
	done
	[ "$(fdtget -l "$work/composed.dtb" /opp-table-cpu7 | wc -l)" = 19 ] ||
		{ echo 'FAIL l3 composition: prime OPPs' >&2; exit 1; }
fi
if [ "$skin" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/skin.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-skin-thermal.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/skin.dtbo" "$work/skin.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/skin.dtb" "$work/skin.dtbo"
	mv "$work/skin.dtb" "$work/composed.dtb"
	pk=/soc@0/spmi@c440000/pmic@0
	[ "$(fdtget "$work/composed.dtb" $pk/adc@3100 status)" = okay ] &&
		[ "$(fdtget "$work/composed.dtb" $pk/adc-tm@3400 status)" = okay ] &&
		[ "$(fdtget -l "$work/composed.dtb" $pk/adc-tm@3400 | wc -l)" = 6 ] &&
		[ "$(fdtget "$work/composed.dtb" /thermal-zones/skin-thermal/trips/skin-crit temperature)" = 65000 ] ||
		{ echo 'FAIL skin composition' >&2; exit 1; }
fi
if [ "$acd" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/acd.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-gpu-acd.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/acd.dtbo" "$work/acd.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/acd.dtb" "$work/acd.dtbo"
	mv "$work/acd.dtb" "$work/composed.dtb"
	[ "$(fdtget "$work/composed.dtb" /soc@0/gmu@3d6a000 qcom,qmp)" = \
		"$(fdtget "$work/composed.dtb" /soc@0/power-management@c300000 phandle)" ] ||
		{ echo 'FAIL acd composition: qmp' >&2; exit 1; }
	for opp in $(fdtget -l "$work/composed.dtb" /soc@0/gpu@3d00000/opp-table); do
		[ -n "$(fdtget "$work/composed.dtb" /soc@0/gpu@3d00000/opp-table/$opp qcom,opp-acd-level)" ] ||
			{ echo "FAIL acd composition: $opp" >&2; exit 1; }
	done
fi
if [ "$disprsc" = 1 ]; then
	grep -q 'rog5,disp-rsc-votes' "$source/drivers/soc/qcom/rog5-disp-rsc-votes.c" 2>/dev/null ||
		{ echo 'FAIL disprsc: kernel source lacks 0086' >&2; exit 1; }
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/disprsc.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-disp-rsc.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/disprsc.dtbo" "$work/disprsc.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/disprsc.dtb" "$work/disprsc.dtbo"
	mv "$work/disprsc.dtb" "$work/composed.dtb"
	[ "$(fdtget "$work/composed.dtb" /soc@0/rsc@af20000 qcom,tcs-offset)" = 7168 ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/rsc@af20000/disp-rsc-votes compatible)" = rog5,disp-rsc-votes ] ||
		{ echo 'FAIL disprsc composition' >&2; exit 1; }
fi
if [ "$cpucap" = 1 ]; then
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/cpucap.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-cpu-capacity.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/cpucap.dtbo" "$work/cpucap.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/cpucap.dtb" "$work/cpucap.dtbo"
	mv "$work/cpucap.dtb" "$work/composed.dtb"
	[ "$(fdtget "$work/composed.dtb" /cpus/cpu@700 capacity-dmips-mhz)" = 2048 ] &&
		[ "$(fdtget "$work/composed.dtb" /cpus/cpu@0 dynamic-power-coefficient)" = 100 ] ||
		{ echo 'FAIL cpucap composition' >&2; exit 1; }
fi
if [ "$usbbtm" = 1 ]; then
	grep -q asus,btm-otg-boost "$source/drivers/power/supply/qcom_battmgr.c" ||
		{ echo 'FAIL usbbtm: kernel source lacks 0089' >&2; exit 1; }
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/usbbtm.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-usb-bottom.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/usbbtm.dtbo" "$work/usbbtm.pp"
	fdtoverlay -i "$work/composed.dtb" -o "$work/usbbtm.dtb" "$work/usbbtm.dtbo"
	mv "$work/usbbtm.dtb" "$work/composed.dtb"
	# HS host only, and no QUP wrapper beyond the base (wrapper 2 never at boot).
	[ "$(fdtget "$work/composed.dtb" /soc@0/usb@a8f8800 status)" = okay ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/usb@a8f8800/usb@a800000 dr_mode)" = host ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/phy@88e4000 status)" = okay ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/phy@88eb000 status)" = disabled ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/geniqup@8c0000 status)" = disabled ] &&
		[ "$(fdtget "$work/composed.dtb" /soc@0/geniqup@ac0000 status)" = disabled ] &&
		[ "$(fdtget "$work/composed.dtb" /pmic-glink asus,btm-otg-boost)" = \
			"$(fdtget "$work/composed.dtb" /regulator-rog5-btm-vbus/btm-otg-boost phandle)" ] &&
		# ucsi_glink/pmic_glink_altmode need "reg" on every pmic-glink child.
		[ "$(fdtget -l "$work/composed.dtb" /pmic-glink)" = connector@0 ] ||
		{ echo 'FAIL usbbtm composition' >&2; exit 1; }
fi
rtc=/soc@0/spmi@c440000/pmic@0/rtc@6100
[ "$(fdtget "$work/composed.dtb" "$rtc" status)" = okay ] || { echo 'FAIL RTC not enabled' >&2; exit 1; }
# The base already enables the PON power key and RESIN volume-down (V9
# buttons-indicator); qcom_pon in the boot list binds them.
pon=/soc@0/spmi@c440000/pmic@0/pon@1300
[ "$(fdtget "$work/composed.dtb" "$pon/pwrkey" status)" = okay ] &&
	[ "$(fdtget "$work/composed.dtb" "$pon/resin" status)" = okay ] &&
	[ "$(fdtget "$work/composed.dtb" "$pon/resin" linux,code)" = 114 ] ||
	{ echo 'FAIL power key / volume-down not enabled' >&2; exit 1; }
[ "$(fdtget "$work/composed.dtb" "$node" compatible)" = ramoops ]
[ "$(fdtget -tx "$work/composed.dtb" "$node" reg)" = '0 9b800000 0 400000' ]
[ "$(fdtget -l "$work/composed.dtb" /reserved-memory | grep -c 9b8)" = 1 ]
[ "$(fdtget "$work/composed.dtb" /soc@0/spmi@c440000/pmic@5 status)" = disabled ]
cp "$work/composed.dtb" "$output"
sha256sum "$output"
