#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
base=$repo/artifacts/network-root-v3/sm8350-asus-rog-phone5-recovery.dtb
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-headless-display-isolation.dtso
builder=$repo/scripts/device/build-headless-display-isolation-candidate-dtb.sh
verifier=$repo/scripts/device/verify-headless-display-isolation-dtb-delta.py
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

for input in "$base" "$overlay" "$builder" "$verifier"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "missing readable ordinary test input: $input"
done
[ -x "$builder" ] || fail "builder is not executable: $builder"
[ -x "$verifier" ] || fail "verifier is not executable: $verifier"
for command in cmp dtc fdtget fdtoverlay fdtput python3 sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing DTB test command: $command"
done

"$builder" "$base" "$overlay" "$stage/one.dtb" >/dev/null
"$builder" "$base" "$overlay" "$stage/two.dtb" >/dev/null
cmp "$stage/one.dtb" "$stage/two.dtb"
"$verifier" "$base" "$stage/one.dtb" >/dev/null
[ "$(fdtget -t s "$stage/one.dtb" \
	/soc@0/clock-controller@af00000 status)" = disabled ] ||
	fail 'candidate display clock controller is not disabled'

reject_delta() {
	mutant=$1
	expected=$2
	if "$verifier" "$base" "$mutant" >"$mutant.log" 2>&1; then
		fail "verifier accepted $(basename "$mutant")"
	fi
	grep -Fq "$expected" "$mutant.log" || {
		echo "FAIL verifier rejected $(basename "$mutant") incorrectly" >&2
		cat "$mutant.log" >&2
		exit 1
	}
}

cp "$stage/one.dtb" "$stage/mdss-enabled.dtb"
fdtput -t s "$stage/mdss-enabled.dtb" \
	/soc@0/display-subsystem@ae00000 status okay
reject_delta "$stage/mdss-enabled.dtb" \
	'FAIL candidate headless display provider is not disabled: mdss'

cp "$stage/one.dtb" "$stage/dsi-enabled.dtb"
fdtput -t s "$stage/dsi-enabled.dtb" \
	/soc@0/display-subsystem@ae00000/dsi@ae94000 status okay
reject_delta "$stage/dsi-enabled.dtb" \
	'FAIL candidate headless display provider is not disabled: dsi0'

cp "$stage/one.dtb" "$stage/dispcc-status-removed.dtb"
fdtput -d "$stage/dispcc-status-removed.dtb" \
	/soc@0/clock-controller@af00000 status
reject_delta "$stage/dispcc-status-removed.dtb" \
	'FAIL candidate headless display provider is not disabled: dispcc'

cp "$stage/one.dtb" "$stage/unapproved-property.dtb"
fdtput -t s "$stage/unapproved-property.dtb" / model rog5-mutant
reject_delta "$stage/unapproved-property.dtb" \
	'FAIL candidate changed an unapproved property:'

cp "$stage/one.dtb" "$stage/extra-node.dtb"
fdtput -c "$stage/extra-node.dtb" /rog5-mutant
reject_delta "$stage/extra-node.dtb" \
	'FAIL candidate changed the DTB node set:'

cp "$base" "$stage/wrong-base.dtb"
fdtput -t s "$stage/wrong-base.dtb" / model rog5-mutant
if "$verifier" "$stage/wrong-base.dtb" "$stage/one.dtb" \
	>"$stage/wrong-base.log" 2>&1; then
	fail 'verifier accepted an unpinned base DTB'
fi
grep -Fq 'FAIL base DTB identity is not accepted:' "$stage/wrong-base.log"

dd if="$stage/one.dtb" of="$stage/truncated.dtb" \
	bs=1 count=128 status=none
reject_delta "$stage/truncated.dtb" \
	'FAIL DTB total size does not equal its file size:'

ln -s "$stage/one.dtb" "$stage/linked.dtb"
reject_delta "$stage/linked.dtb" \
	'FAIL DTB is not an ordinary file:'

cat >"$stage/wrong-overlay.dtso" <<'EOF'
/dts-v1/;
/plugin/;

&mdss {
	status = "okay";
};

&dispcc {
	status = "disabled";
};
EOF
if "$builder" "$base" "$stage/wrong-overlay.dtso" \
	"$stage/wrong-overlay.dtb" >"$stage/wrong-overlay.log" 2>&1; then
	fail 'builder accepted an overlay that enabled MDSS'
fi
grep -Fq 'FAIL candidate headless display provider is not disabled: mdss' \
	"$stage/wrong-overlay.log"
[ ! -e "$stage/wrong-overlay.dtb" ]

printf 'preserve\n' >"$stage/output-target"
ln -s "$stage/output-target" "$stage/linked-output"
if "$builder" "$base" "$overlay" "$stage/linked-output" \
	>"$stage/linked-output.log" 2>&1; then
	fail 'builder accepted a linked output'
fi
grep -Fq 'FAIL output is a link or directory:' "$stage/linked-output.log"
grep -Fxq preserve "$stage/output-target"

echo 'PASS hostile headless display-isolation DTB candidate contract'
