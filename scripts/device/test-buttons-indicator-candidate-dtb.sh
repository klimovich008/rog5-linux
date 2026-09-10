#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
base_relative=artifacts/network-root-v3/sm8350-asus-rog-phone5-recovery.dtb
base=$repo/$base_relative
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-buttons-indicator.dtso
builder=$repo/scripts/device/build-buttons-indicator-candidate-dtb.sh
verifier=$repo/scripts/device/verify-buttons-indicator-dtb-delta.py
artifact=$repo/artifacts/buttons-indicator-v1/sm8350-asus-rog-phone5-buttons-indicator.dtb
manifest=$repo/manifests/artifacts.tsv
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

for input in "$base" "$overlay" "$builder" "$verifier" "$artifact" \
	"$manifest"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "missing readable ordinary test input: $input"
done
for command in awk cmp cut dtc fdtget fdtoverlay fdtput git python3 \
	sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing DTB test command: $command"
done

[ "$(stat -c %s "$base")" = 102870 ] ||
	fail 'accepted base DTB size changed'
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = \
	86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46 ] ||
	fail 'accepted base DTB hash changed'
# Both repository tiers run from Git checkouts. Requiring a tracked base here
# prevents an ignored local artifact cache from making local-only CI pass.
git -C "$repo" ls-files --error-unmatch -- "$base_relative" >/dev/null ||
	fail 'accepted base DTB is not tracked for clean-checkout CI'

base_manifest_is_exact() {
	awk -F '\t' -v name="$base_relative" '
		$1 == name {
			count++
			if ($2 != 102870 ||
			    $3 != "86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46" ||
			    $5 != "yes")
				bad = 1
		}
		END { exit (bad || count != 1) }
	' "$1"
}

base_manifest_is_exact "$manifest" ||
	fail 'accepted base DTB manifest entry is not exact and tracked'
awk -F '\t' -v OFS='\t' -v name="$base_relative" '
	$1 == name { $5 = "no" }
	{ print }
' "$manifest" >"$stage/untracked-manifest.tsv"
if base_manifest_is_exact "$stage/untracked-manifest.tsv"; then
	fail 'accepted base DTB manifest verifier accepted tracked=no'
fi

"$builder" "$base" "$overlay" "$stage/one.dtb" >/dev/null
"$builder" "$base" "$overlay" "$stage/two.dtb" >/dev/null
cmp "$stage/one.dtb" "$stage/two.dtb"
cmp "$stage/one.dtb" "$artifact"
"$verifier" "$base" "$stage/one.dtb" >/dev/null
"$verifier" "$base" "$artifact" >/dev/null

reject_delta() {
	mutant=$1
	expected=$2
	log=$mutant.log
	if "$verifier" "$base" "$mutant" >"$log" 2>&1; then
		echo "FAIL verifier accepted $(basename "$mutant")" >&2
		exit 1
	fi
	grep -Fq "$expected" "$log" || {
		echo "FAIL verifier rejected $(basename "$mutant") incorrectly" >&2
		cat "$log" >&2
		exit 1
	}
}

cp "$stage/one.dtb" "$stage/unapproved-property.dtb"
fdtput -t s "$stage/unapproved-property.dtb" / model rog5-mutant
reject_delta "$stage/unapproved-property.dtb" \
	'FAIL candidate changed an unapproved property set:'

cp "$stage/one.dtb" "$stage/extra-node.dtb"
fdtput -c "$stage/extra-node.dtb" /rog5-mutant
reject_delta "$stage/extra-node.dtb" \
	'FAIL candidate changed an unapproved node set:'

cp "$stage/one.dtb" "$stage/missing-volume-up.dtb"
fdtput -r "$stage/missing-volume-up.dtb" /gpio-keys/key-volume-up
reject_delta "$stage/missing-volume-up.dtb" \
	'FAIL candidate changed an unapproved node set:'

cp "$stage/one.dtb" "$stage/wrong-pwrkey-status.dtb"
fdtput -t s "$stage/wrong-pwrkey-status.dtb" \
	/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey status disabled
reject_delta "$stage/wrong-pwrkey-status.dtb" \
	'FAIL candidate changed an unapproved property set:'

for parent in \
	/soc@0/spmi@c440000 \
	/soc@0/spmi@c440000/pmic@0 \
	/soc@0/spmi@c440000/pmic@0/pon@1300 \
	/soc@0/spmi@c440000/pmic@1 \
	/soc@0/spmi@c440000/pmic@1/gpio@8800 \
	/soc@0/spmi@c440000/pmic@2
do
	name=$(printf '%s' "$parent" | tr '/@' '__')
	cp "$stage/one.dtb" "$stage/disabled-parent-$name.dtb"
	fdtput -t s "$stage/disabled-parent-$name.dtb" "$parent" status disabled
	reject_delta "$stage/disabled-parent-$name.dtb" \
		'FAIL candidate approved parent is disabled:'
done

cp "$stage/one.dtb" "$stage/not-gpio-controller.dtb"
fdtput -d "$stage/not-gpio-controller.dtb" \
	/soc@0/spmi@c440000/pmic@1/gpio@8800 gpio-controller
reject_delta "$stage/not-gpio-controller.dtb" \
	'FAIL candidate PM8350 GPIO provider is wrong: gpio-controller'

cp "$stage/one.dtb" "$stage/wrong-gpio-cells.dtb"
fdtput -t x "$stage/wrong-gpio-cells.dtb" \
	/soc@0/spmi@c440000/pmic@1/gpio@8800 '#gpio-cells' 1
reject_delta "$stage/wrong-gpio-cells.dtb" \
	'FAIL candidate PM8350 GPIO provider is wrong: #gpio-cells'

cp "$stage/one.dtb" "$stage/wrong-resin-code.dtb"
fdtput -t x "$stage/wrong-resin-code.dtb" \
	/soc@0/spmi@c440000/pmic@0/pon@1300/resin linux,code 73
reject_delta "$stage/wrong-resin-code.dtb" \
	'FAIL candidate approved property is wrong:'

cp "$stage/one.dtb" "$stage/resin-wakeup.dtb"
fdtput "$stage/resin-wakeup.dtb" \
	/soc@0/spmi@c440000/pmic@0/pon@1300/resin wakeup-source
reject_delta "$stage/resin-wakeup.dtb" \
	'FAIL candidate changed an unapproved property set:'

cp "$stage/one.dtb" "$stage/wrong-volume-gpio.dtb"
gpio_phandle=$(fdtget -t x "$stage/one.dtb" \
	/soc@0/spmi@c440000/pmic@1/gpio@8800 phandle)
fdtput -t x "$stage/wrong-volume-gpio.dtb" \
	/gpio-keys/key-volume-up gpios "0x$gpio_phandle" 7 1
reject_delta "$stage/wrong-volume-gpio.dtb" \
	'FAIL candidate node properties are wrong: /gpio-keys/key-volume-up'

cp "$stage/one.dtb" "$stage/no-volume-wakeup.dtb"
fdtput -d "$stage/no-volume-wakeup.dtb" \
	/gpio-keys/key-volume-up wakeup-source
reject_delta "$stage/no-volume-wakeup.dtb" \
	'FAIL candidate node properties are wrong: /gpio-keys/key-volume-up'

cp "$stage/one.dtb" "$stage/no-pull-up.dtb"
fdtput -d "$stage/no-pull-up.dtb" \
	/soc@0/spmi@c440000/pmic@1/gpio@8800/volume-up-default-state \
	bias-pull-up
reject_delta "$stage/no-pull-up.dtb" \
	'FAIL candidate node properties are wrong:'

cp "$stage/one.dtb" "$stage/wrong-led-channel.dtb"
fdtput -t x "$stage/wrong-led-channel.dtb" \
	/soc@0/spmi@c440000/pmic@2/pwm/led@2 reg 1
reject_delta "$stage/wrong-led-channel.dtb" \
	'FAIL candidate node properties are wrong:'

cp "$stage/one.dtb" "$stage/idle-heartbeat.dtb"
fdtput -t s "$stage/idle-heartbeat.dtb" \
	/soc@0/spmi@c440000/pmic@2/pwm/led@2 \
	linux,default-trigger heartbeat
reject_delta "$stage/idle-heartbeat.dtb" \
	'FAIL candidate node properties are wrong:'

cp "$stage/one.dtb" "$stage/duplicate-phandle.dtb"
gpio_phandle=$(fdtget -t x "$stage/one.dtb" \
	/soc@0/spmi@c440000/pmic@1/gpio@8800 phandle)
fdtput -t x "$stage/duplicate-phandle.dtb" \
	/soc@0/spmi@c440000/pmic@1/gpio@8800/volume-up-default-state \
	phandle "0x$gpio_phandle"
fdtput -t x "$stage/duplicate-phandle.dtb" /gpio-keys \
	pinctrl-0 "0x$gpio_phandle"
reject_delta "$stage/duplicate-phandle.dtb" \
	'FAIL candidate has a duplicate phandle:'

cp "$base" "$stage/wrong-base.dtb"
fdtput -t s "$stage/wrong-base.dtb" / model rog5-mutant
if "$verifier" "$stage/wrong-base.dtb" "$stage/one.dtb" \
	>"$stage/wrong-base.log" 2>&1; then
	echo 'FAIL verifier accepted an unpinned base DTB' >&2
	exit 1
fi
grep -Fq 'FAIL base DTB ' "$stage/wrong-base.log"

dd if="$stage/one.dtb" of="$stage/truncated.dtb" \
	bs=1 count=128 status=none
reject_delta "$stage/truncated.dtb" \
	'FAIL DTB total size does not equal its file size:'

ln -s "$stage/one.dtb" "$stage/linked.dtb"
reject_delta "$stage/linked.dtb" \
	'FAIL DTB is not an ordinary file:'

printf 'preserve\n' >"$stage/output-target"
ln -s "$stage/output-target" "$stage/linked-output"
if "$builder" "$base" "$overlay" "$stage/linked-output" \
	>"$stage/linked-output.log" 2>&1; then
	echo 'FAIL builder accepted a linked output' >&2
	exit 1
fi
grep -Fq 'FAIL output is a link or directory:' "$stage/linked-output.log"
grep -Fxq preserve "$stage/output-target"

mkdir "$stage/output-directory"
if "$builder" "$base" "$overlay" "$stage/output-directory" \
	>"$stage/output-directory.log" 2>&1; then
	echo 'FAIL builder accepted a directory output' >&2
	exit 1
fi
grep -Fq 'FAIL output is a link or directory:' "$stage/output-directory.log"

echo 'PASS hostile buttons and green-indicator DTB contract'
