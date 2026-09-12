#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
base=$repo/artifacts/display-60hz-v1/sm8350-asus-rog-phone5-wifi-base.dtb
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-display-60hz-reviewed.dtso
builder=$repo/scripts/device/build-display-60hz-candidate-dtb.sh
verifier=$repo/scripts/device/verify-display-60hz-dtb-delta.py
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

# Real cpp/dtc/overlay/delta checks; schema executables below are explicit
# fixtures. This suite does not claim execution of the unavailable DT schema.
mkdir -p "$work/tools" "$work/linux/include/dt-bindings/gpio" \
 "$work/linux/include/dt-bindings/regulator" \
 "$work/linux/Documentation/devicetree/bindings/display/panel"
cp "$repo/scripts/device/fixtures/display60/gpio.h" "$work/linux/include/dt-bindings/gpio/"
cp "$repo/scripts/device/fixtures/display60/qcom,rpmh-regulator.h" "$work/linux/include/dt-bindings/regulator/"
python3 - "$repo" "$work/linux" <<'PYCODE'
from pathlib import Path
import sys
root, source = map(Path, sys.argv[1:])
p = root / 'patches/linux-7.1.4/0037-drm-panel-add-ASUS-ROG-Phone-5-AMS678-ER2.patch'
s = p.read_text().split('+++ b/Documentation/devicetree/bindings/display/panel/asus,rog5-ams678.yaml\n', 1)[1].split('diff --git', 1)[0]
(source / 'Documentation/devicetree/bindings/display/panel/asus,rog5-ams678.yaml').write_text('\n'.join(line[1:] for line in s.splitlines() if line.startswith('+')) + '\n')
PYCODE
printf '#!/bin/sh\nexit 0\n' > "$work/tools/dt-validate"
cp "$work/tools/dt-validate" "$work/tools/dt-doc-validate"
chmod +x "$work/tools/"*
export PATH="$work/tools:$PATH" ROG5_LINUX_SOURCE="$work/linux"

"$builder" "$base" "$overlay" "$work/first" >"$work/build.log" 2>&1 || { cat "$work/build.log"; exit 1; }
"$builder" "$base" "$overlay" "$work/second" >>"$work/build.log" 2>&1 || { cat "$work/build.log"; exit 1; }
cmp "$work/first/candidate.dtb" "$work/second/candidate.dtb"
"$verifier" --input-direction output-disable "$base" "$work/first/candidate.dtb" >/dev/null

cp "$work/first/candidate.dtb" "$work/old-direction.dtb"
for pin in te-pins iris-ready-pins; do
 node=/soc@0/pinctrl@f100000/rog5-panel-default-state/$pin
 fdtput -d "$work/old-direction.dtb" "$node" output-disable
 fdtput "$work/old-direction.dtb" "$node" input-enable
done
if "$verifier" --input-direction output-disable "$base" "$work/old-direction.dtb" >/dev/null 2>&1; then
 echo 'FAIL current contract accepted old input-enable properties' >&2; exit 1
fi
"$verifier" "$base" "$work/old-direction.dtb" >/dev/null

cp "$work/first/candidate.dtb" "$work/usb-mutant.dtb"
fdtput -t s "$work/usb-mutant.dtb" /soc@0/usb@a8f8800 status okay
if "$verifier" --input-direction output-disable "$base" "$work/usb-mutant.dtb" >/dev/null 2>&1; then
	echo 'FAIL display verifier accepted unrelated USB enablement' >&2
	exit 1
fi

cp "$work/first/candidate.dtb" "$work/gpio-mutant.dtb"
panel=/soc@0/display-subsystem@ae00000/dsi@ae94000/panel@0
set -- $(fdtget -t x "$work/gpio-mutant.dtb" "$panel" iris-wakeup-gpios)
fdtput -t x "$work/gpio-mutant.dtb" "$panel" iris-wakeup-gpios "$1" 5d 0
if "$verifier" --input-direction output-disable "$base" "$work/gpio-mutant.dtb" >/dev/null 2>&1; then
	echo 'FAIL display verifier accepted wrong Iris wakeup GPIO' >&2
	exit 1
fi

cp "$work/first/candidate.dtb" "$work/mode-mutant.dtb"
fdtput -t s "$work/mode-mutant.dtb" "$panel" compatible asus,other-panel
if "$verifier" --input-direction output-disable "$base" "$work/mode-mutant.dtb" >/dev/null 2>&1; then
	echo 'FAIL display verifier accepted wrong panel identity' >&2
	exit 1
fi

cp "$work/first/candidate.dtb" "$work/supply-mutant.dtb"
dsi=/soc@0/display-subsystem@ae00000/dsi@ae94000
set -- $(fdtget -t x "$work/supply-mutant.dtb" "$panel" vddio-supply)
fdtput -t x "$work/supply-mutant.dtb" "$dsi" vdda-supply "$1"
if "$verifier" --input-direction output-disable "$base" "$work/supply-mutant.dtb" >/dev/null 2>&1; then
	echo 'FAIL display verifier accepted wrong DSI analog supply' >&2
	exit 1
fi

if "$builder" "$base" "$overlay" "$work/first" >>"$work/build.log" 2>&1; then
 echo 'FAIL replaced output without explicit request' >&2; exit 1
fi
"$builder" "$base" "$overlay" "$work/first" --replace >>"$work/build.log" 2>&1
cmp "$work/first/candidate.dtb" "$work/second/candidate.dtb"
printf '#!/bin/sh\necho "fixture schema error" >&2\nexit 0\n' > "$work/tools/dt-validate"
if "$builder" "$base" "$overlay" "$work/invalid" >>"$work/build.log" 2>&1; then
 echo 'FAIL accepted schema diagnostics with exit zero' >&2; exit 1
fi
[ ! -e "$work/invalid" ]
python3 "$repo/scripts/device/test-display-60hz-publication.py"
echo 'PASS real DT compile/delta, schema-refusal fixtures and atomic bundle publication'
echo 'NOT RUN actual DT schema validation (fixture validators); physical validation'
