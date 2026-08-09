#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
gate=$repo/scripts/device/run-network-root-physical-keys.sh
closure=$repo/packaging/arch/headless-package-closure.txt
work=$(mktemp -d)
trap 'rm -rf -- "$work"' 0 HUP INT TERM

fail() {
	echo "FAIL $*" >&2
	exit 1
}

write_field() {
	root=$1
	name=$2
	value=$3
	mkdir -p -- "$root/$(dirname "$name")"
	printf '%s\n' "$value" >"$root/$name"
}

make_fixture() {
	root=$1
	mkdir -m 0700 -- "$root"

	write_field "$root" pre/kernel_release 7.1.4-g7a5cef0db479
	write_field "$root" pre/pid1 systemd
	write_field "$root" pre/cmdline 'console=ttyMSM0,115200n8 root=overlay'
	write_field "$root" pre/system_state running
	write_field "$root" pre/server_inhibitor active
	write_field "$root" pre/failed_units 0
	write_field "$root" pre/root_fstype overlay
	write_field "$root" pre/run_fstype tmpfs
	write_field "$root" pre/nfs_source 169.254.77.1:/
	write_field "$root" pre/nfs_options ro,vers=4.2,proto=tcp
	write_field "$root" pre/physical_blocks 0
	write_field "$root" pre/block_mounts 0
	write_field "$root" pre/watchdog_pid 0
	write_field "$root" pre/watchdog_disarmed 1
	write_field "$root" pre/udcs a600000.dwc3
	write_field "$root" pre/bound_udc a600000.dwc3
	write_field "$root" pre/usb0_present 1
	write_field "$root" pre/carrier 1
	write_field "$root" pre/addresses 169.254.77.2/30
	write_field "$root" pre/route \
		'169.254.77.1 dev usb0 src 169.254.77.2 uid 0'
	write_field "$root" pre/fatal_count 0
	write_field "$root" pre/warning_digest clean

	write_field "$root" keys/power/count 1
	write_field "$root" keys/power/name pmic_pwrkey
	write_field "$root" keys/power/driver pm8941-pwrkey
	write_field "$root" keys/power/of_node \
		'/sys/firmware/devicetree/base/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey'
	write_field "$root" keys/power/compatible qcom,pmk8350-pwrkey
	write_field "$root" keys/power/wakeup enabled
	write_field "$root" keys/power/key_bitmap '10000000000000 0'
	write_field "$root" keys/power/irq_before 100
	write_field "$root" keys/power/irq_after 102
	write_field "$root" events/power '1 116 1
1 116 0'

	write_field "$root" keys/volume-down/count 1
	write_field "$root" keys/volume-down/name pmic_resin
	write_field "$root" keys/volume-down/driver pm8941-pwrkey
	write_field "$root" keys/volume-down/of_node \
		'/sys/firmware/devicetree/base/soc@0/spmi@c440000/pmic@0/pon@1300/resin'
	write_field "$root" keys/volume-down/compatible qcom,pmk8350-resin
	write_field "$root" keys/volume-down/wakeup absent
	write_field "$root" keys/volume-down/key_bitmap '4000000000000 0'
	write_field "$root" keys/volume-down/irq_before 200
	write_field "$root" keys/volume-down/irq_after 202
	write_field "$root" events/volume-down '1 114 1
1 114 0'

	write_field "$root" keys/volume-up/count 1
	write_field "$root" keys/volume-up/name gpio-keys
	write_field "$root" keys/volume-up/driver gpio-keys
	write_field "$root" keys/volume-up/of_node \
		'/sys/firmware/devicetree/base/gpio-keys'
	write_field "$root" keys/volume-up/compatible gpio-keys
	write_field "$root" keys/volume-up/wakeup enabled
	write_field "$root" keys/volume-up/key_bitmap '8000000000000 0'
	write_field "$root" keys/volume-up/irq_before 300
	write_field "$root" keys/volume-up/irq_after 302
	write_field "$root" events/volume-up '1 115 1
1 115 0'
}

run_gate() {
	fixture=$1
	shift
	ALLOW_ROG5_PHYSICAL_KEYS=rog5-physical-keys-v1 \
		ROG5_PHYSICAL_KEYS_TESTING=1 \
		ROG5_PHYSICAL_KEYS_FIXTURE_ROOT=$fixture \
		"$gate" "$@"
}

expect_failure() {
	fixture=$1
	expected=$2
	shift 2
	if run_gate "$fixture" "$@" >"$work/failure.log" 2>&1; then
		fail "hostile fixture passed: $expected"
	fi
	grep -Fq "FAIL $expected" "$work/failure.log" || {
		cat "$work/failure.log" >&2
		fail "wrong classification: $expected"
	}
}

[ -x "$gate" ] || fail 'missing executable physical-key gate'
sh -n "$gate"
grep -Fq 'exec 7<"$current_event"' "$gate" ||
	fail 'target reader does not keep one evdev descriptor across press/release'
grep -Fq '<&7' "$gate" ||
	fail 'target reader does not consume the retained evdev descriptor'
if grep -Fq 'if="$current_event"' "$gate"; then
	fail 'target reader reopens evdev between press and release'
fi
python3 - "$gate" <<'PY' ||
import sys

text = open(sys.argv[1], encoding="utf-8").read()
body = text.split("capture_key() {", 1)[1].split("\n}", 1)[0]
assert body.index('exec 7<"$current_event"') < body.index('echo "READY key=')
PY
	fail 'target reader announces readiness before retaining evdev'

descriptor_fifo=$work/descriptor.fifo
mkfifo -- "$descriptor_fifo"
python3 - "$descriptor_fifo" <<'PY' &
import struct
import sys

record = struct.Struct("@llHHi")
with open(sys.argv[1], "wb", buffering=0) as stream:
    stream.write(record.pack(0, 0, 1, 116, 1))
    stream.write(record.pack(0, 0, 1, 116, 0))
PY
writer_pid=$!
exec 8<"$descriptor_fifo"
dd of="$work/descriptor-press" bs=24 count=1 status=none <&8
wait "$writer_pid"
dd of="$work/descriptor-release" bs=24 count=1 status=none <&8
exec 8<&-
[ "$(od -An -j 16 -N 8 -t u2 "$work/descriptor-press" |
	awk '{$1=$1; print}')" = '1 116 1 0' ] ||
	fail 'retained descriptor lost or corrupted the press record'
[ "$(od -An -j 16 -N 8 -t u2 "$work/descriptor-release" |
	awk '{$1=$1; print}')" = '1 116 0 0' ] ||
	fail 'retained descriptor lost or corrupted the release record'

[ -f "$closure" ] && [ ! -L "$closure" ] ||
	fail 'minimal package closure is unavailable'
for package in bash coreutils findutils gawk grep iproute2 systemd util-linux; do
	grep -Eq "^${package} [^[:space:]]+$" "$closure" ||
		fail "minimal package closure omits physical-key dependency: $package"
done
if grep -Eq '^python([[:space:]]|$)' "$closure"; then
	fail 'physical-key gate silently depends on Python in the minimal root'
fi

baseline=$work/baseline
make_fixture "$baseline"
run_gate "$baseline" 180 >"$work/pass.log"
grep -Fqx \
	'PASS physical keys events=power:1/1,volume-down:1/1,volume-up:1/1 irq_deltas=2,2,2 wake_sources=power,volume-up resin_wake=off writes=0 suspend=0 backend=fixture' \
	"$work/pass.log"

if ROG5_PHYSICAL_KEYS_TESTING=1 \
	ROG5_PHYSICAL_KEYS_FIXTURE_ROOT=$baseline \
	"$gate" 180 >"$work/no-guard.log" 2>&1; then
	fail 'missing execution guard passed'
fi
grep -Fq 'FAIL set the exact physical-key execution guard' \
	"$work/no-guard.log"
expect_failure "$baseline" 'timeout must be between 30 and 300 seconds' 29

for case_record in \
	'wrong-kernel|pre/kernel_release|7.1.5|unexpected kernel' \
	'rw-nfs|pre/nfs_options|rw,vers=4.2|NFS lower is not read-only' \
	'block-device|pre/physical_blocks|1|physical block device is present' \
	'wrong-udc|pre/udcs|renamed.dwc3|expected exactly one expected UDC' \
	'inactive-inhibitor|pre/server_inhibitor|inactive|server inhibitor is not active'
do
	name=${case_record%%|*}
	rest=${case_record#*|}
	field=${rest%%|*}
	rest=${rest#*|}
	value=${rest%%|*}
	expected=${rest#*|}
	fixture=$work/pre-$name
	cp -a -- "$baseline" "$fixture"
	write_field "$fixture" "$field" "$value"
	expect_failure "$fixture" "$expected" 180
done

for case_record in \
	'power-driver|keys/power/driver|gpio-keys|power driver changed' \
	'resin-wakeup|keys/volume-down/wakeup|enabled|volume-down wake policy changed' \
	'volume-compatible|keys/volume-up/compatible|vendor,gpio-keys|volume-up compatible changed' \
	'duplicate-power|keys/power/count|2|expected exactly one power input' \
	'wrong-key-bitmap|keys/volume-down/key_bitmap|0 0|volume-down key capability changed'
do
	name=${case_record%%|*}
	rest=${case_record#*|}
	field=${rest%%|*}
	rest=${rest#*|}
	value=${rest%%|*}
	expected=${rest#*|}
	fixture=$work/identity-$name
	cp -a -- "$baseline" "$fixture"
	write_field "$fixture" "$field" "$value"
	expect_failure "$fixture" "$expected" 180
done

fixture=$work/release-before-press
cp -a -- "$baseline" "$fixture"
write_field "$fixture" events/power '1 116 0'
expect_failure "$fixture" 'power release arrived before its press' 180

fixture=$work/autorepeat
cp -a -- "$baseline" "$fixture"
write_field "$fixture" events/volume-down '1 114 1
1 114 2'
expect_failure "$fixture" 'volume-down autorepeat is forbidden' 180

fixture=$work/wrong-code
cp -a -- "$baseline" "$fixture"
write_field "$fixture" events/volume-up '1 116 1'
expect_failure "$fixture" 'volume-up emitted an unexpected key code' 180

fixture=$work/missing-release
cp -a -- "$baseline" "$fixture"
write_field "$fixture" events/power '1 116 1'
expect_failure "$fixture" 'power event stream ended before press and release' 180

fixture=$work/linked-key-directory
cp -a -- "$baseline" "$fixture"
mv -- "$fixture/keys/power" "$fixture/keys/power-real"
ln -s power-real "$fixture/keys/power"
expect_failure "$fixture" 'fixture field contains a linked component: keys/power/count' 180

fixture=$work/no-irq
cp -a -- "$baseline" "$fixture"
write_field "$fixture" keys/power/irq_after 100
expect_failure "$fixture" 'power IRQ did not advance twice' 180

fixture=$work/irq-storm
cp -a -- "$baseline" "$fixture"
write_field "$fixture" keys/volume-up/irq_after 333
expect_failure "$fixture" 'volume-up IRQ delta exceeds the bounce bound' 180

for case_record in \
	'udc|post/udcs||post-return UDC loss' \
	'interface|post/usb0_present|0|post-return interface loss' \
	'carrier|post/carrier|0|post-return carrier loss' \
	'address|post/addresses|169.254.77.2/24|post-return address loss' \
	'route|post/route|169.254.77.1 via 10.0.0.1 dev usb0|post-return route loss' \
	'late-via|post/route|169.254.77.1 dev usb0 src 169.254.77.2 via 10.0.0.1|post-return route loss' \
	'nfs|post/nfs_source|169.254.77.9:/|NFS lower source changed during the key test' \
	'warning|post/warning_digest|changed|kernel warning state changed during the key test' \
	'fatal|post/fatal_count|1|fatal kernel signature appeared during the key test'
do
	name=${case_record%%|*}
	rest=${case_record#*|}
	field=${rest%%|*}
	rest=${rest#*|}
	value=${rest%%|*}
	expected=${rest#*|}
	fixture=$work/post-$name
	cp -a -- "$baseline" "$fixture"
	write_field "$fixture" "$field" "$value"
	expect_failure "$fixture" "$expected" 180
done

if grep -Eq \
	'(python|modprobe|/sys/class/leds/.*/brightness|/sys/power/state|fastboot|adb|reboot|poweroff|shutdown|/dev/(block|disk)|dd[[:space:]].*of=/dev/)' \
	"$gate"
then
	fail 'physical-key gate contains a device-state, boot, or storage write path'
fi

echo 'PASS physical-key gate is dependency-free, exact, bounded, hostile-tested, and hardware-free'
