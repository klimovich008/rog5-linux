#!/bin/sh
set -eu

[ "$#" -eq 2 ] || {
	echo 'usage: build-qcom-wdt-candidate-dtb.sh BASE_DTB OUTPUT_DTB' >&2
	exit 1
}
base=$1
output=$2
expected_base=4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8

fail() { echo "FAIL $*" >&2; exit 1; }
for command in dtc fdtoverlay fdtget sha256sum; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
[ -f "$base" ] && [ ! -L "$base" ] || fail 'unsafe base DTB'
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] ||
	fail 'base DTB identity changed'
[ ! -e "$output" ] && [ ! -L "$output" ] || fail 'output already exists'

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
cat >"$stage/qcom-wdt.dtso" <<'EOF'
/dts-v1/;
/plugin/;

/ {
	fragment@0 {
		target-path = "/soc@0";

		__overlay__ {
			watchdog@17c10000 {
				compatible = "qcom,kpss-wdt";
				reg = <0x0 0x17c10000 0x0 0x1000>;
				clocks = <&sleep_clk>;
				timeout-sec = <30>;
			};
		};
	};
};
EOF
dtc -q -@ -I dts -O dtb -o "$stage/qcom-wdt.dtbo" "$stage/qcom-wdt.dtso"
mkdir -p "$(dirname "$output")"
fdtoverlay -i "$base" -o "$output.tmp" "$stage/qcom-wdt.dtbo"
mv -T "$output.tmp" "$output"

[ "$(fdtget "$output" /soc@0/watchdog@17c10000 compatible)" = qcom,kpss-wdt ]
[ "$(fdtget -tx "$output" /soc@0/watchdog@17c10000 reg)" = \
	'0 17c10000 0 1000' ]
[ "$(fdtget "$output" /soc@0/watchdog@17c10000 timeout-sec)" = 30 ]
sha256sum "$output"
echo 'PASS exact stock-grounded SM8350 APSS watchdog node added'
