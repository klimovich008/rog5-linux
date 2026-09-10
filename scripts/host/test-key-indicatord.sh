#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
source_file=$repo/tools/key-indicator/rog5-key-indicatord.c
build_script=$repo/scripts/device/build-key-indicatord.sh
aarch64_test=$repo/scripts/host/test-key-indicatord-aarch64.sh
unit=$repo/packaging/arch/rog5-key-indicator.service
modules_conf=$repo/packaging/arch/rog5-status-led.modules.conf
expected_source_size=20530
expected_source_sha256=3d597f919d71a76f2aef0ae2aa269e219ffe7c0bdca0e9b73481d52dff686939

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in file python3 readelf sha256sum stat strings systemd-analyze; do
	command -v "$command" >/dev/null ||
		fail "missing key-indicator test command: $command"
done
if [[ -z ${ROG5_INDICATOR_PRODUCTION_BINARY:-} &&
	-z ${ROG5_INDICATOR_FIXTURE_BINARY:-} ]]; then
	command -v gcc >/dev/null ||
		fail 'missing key-indicator test command: gcc'
fi
for path in "$source_file" "$build_script" "$aarch64_test" "$unit" \
	"$modules_conf"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing regular key-indicator contract file: $path"
done
[[ $(stat -c %s "$source_file") == "$expected_source_size" ]] ||
	fail 'key-indicator source size drifted from the sealed contract'
[[ $(sha256sum "$source_file" | cut -d' ' -f1) == \
	"$expected_source_sha256" ]] ||
	fail 'key-indicator source hash drifted from the sealed contract'
for pin_file in "$build_script" "$aarch64_test"; do
	grep -Fqx "expected_source_size=$expected_source_size" "$pin_file" ||
		fail "source-size pin diverged in $pin_file"
	grep -Fqx "expected_source_sha256=$expected_source_sha256" \
		"$pin_file" ||
		fail "source-hash pin diverged in $pin_file"
done
[[ $(sed -e 's/[[:space:]]*#.*$//' -e '/^[[:space:]]*$/d' \
	"$modules_conf") == leds-qcom-lpg ]] ||
	fail 'status-LED module-load contract changed'
[[ -x $build_script ]] ||
	fail 'key-indicator build script is not executable'
bash -n "$build_script"

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
production=${ROG5_INDICATOR_PRODUCTION_BINARY:-$work/rog5-key-indicatord}
fixture_binary=${ROG5_INDICATOR_FIXTURE_BINARY:-$work/rog5-key-indicatord-fixture}
runner=()
if [[ -n ${ROG5_INDICATOR_TEST_RUNNER:-} ]]; then
	[[ -x $ROG5_INDICATOR_TEST_RUNNER ]] ||
		fail 'key-indicator test runner is not executable'
	runner=("$ROG5_INDICATOR_TEST_RUNNER")
fi

common_flags=(
	-std=c11 -O2 -fPIE -pie -fstack-protector-strong
	-Wall -Wextra -Werror
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none
)
if [[ -z ${ROG5_INDICATOR_PRODUCTION_BINARY:-} &&
	-z ${ROG5_INDICATOR_FIXTURE_BINARY:-} ]]; then
	gcc "${common_flags[@]}" "$source_file" -o "$production"
	gcc "${common_flags[@]}" -DROG5_INDICATOR_TESTING=1 \
		"$source_file" -o "$fixture_binary"
elif [[ -z ${ROG5_INDICATOR_PRODUCTION_BINARY:-} ||
	-z ${ROG5_INDICATOR_FIXTURE_BINARY:-} ]]; then
	fail 'both external key-indicator binaries must be provided together'
fi
[[ -f $production && ! -L $production && -x $production ]]
[[ -f $fixture_binary && ! -L $fixture_binary && -x $fixture_binary ]]

for marker in \
	'INPUT_DEVICE_NAME "pmic_pwrkey"' \
	'LED_DEVICE_NAME "green:status"' \
	'LED_DRIVER_NAME "qcom-spmi-lpg"' \
	'"/soc@0/spmi@c440000/pmic@2/pwm/led@2"' \
	'LED_MAX_BRIGHTNESS 511U' \
	'LED_PULSE_MILLISECONDS 180U' \
	'event->type != EV_KEY' \
	'event->code != KEY_POWER' \
	'event->value != 1' \
	'timerfd_create(CLOCK_BOOTTIME' \
	'signalfd(-1, &stop_signals' \
	'force_led_off(brightness_descriptor)'
do
	grep -Fq "$marker" "$source_file" ||
		fail "key-indicator source omits: $marker"
done
if grep -q '^ConditionPathExists=' "$unit"; then
	fail 'key-indicator service can silently skip before LPG probe'
fi
for marker in \
	'ExecStart=/usr/local/libexec/rog5-key-indicatord' \
	'ExecStopPost=/usr/local/libexec/rog5-key-indicatord --off' \
	'DevicePolicy=closed' \
	'DeviceAllow=char-input r' \
	'ReadWritePaths=/sys/class/leds/green:status/brightness' \
	'NoNewPrivileges=yes' \
	'ProtectSystem=strict' \
	'ProtectKernelTunables=yes' \
	'CapabilityBoundingSet=' \
	'RestrictAddressFamilies=AF_UNIX' \
	'SystemCallFilter=@system-service' \
	'WantedBy=multi-user.target'
do
	grep -Fqx "$marker" "$unit" ||
		fail "key-indicator service omits: $marker"
done
if grep -Eq \
	'system[(]|popen[(]|execl|execv|/bin/(ba)?sh|/dev/(block|disk)|(^|[^[:alnum:]_])(fastboot|adb|reboot|poweroff)([^[:alnum:]_]|$)' \
	"$source_file" "$unit"
then
	fail 'key-indicator path contains a shell, storage, or boot action'
fi
if strings "$production" | grep -q -- '--fixture'; then
	fail 'production key indicator exposes the fixture interface'
fi

mkdir "$work/systemd"
sed \
	-e "s|^ExecStart=/usr/local/libexec/rog5-key-indicatord$|ExecStart=$production|" \
	-e "s|^ExecStopPost=/usr/local/libexec/rog5-key-indicatord --off$|ExecStopPost=$production --off|" \
	"$unit" >"$work/systemd/rog5-key-indicator.service"
systemd-analyze verify "$work/systemd/rog5-key-indicator.service"

make_led_fixture() {
	local root=$1
	local led=$root/led
	local of_node=$root/device-tree/soc@0/spmi@c440000/pmic@2/pwm/led@2
	local driver=$root/drivers/qcom-spmi-lpg

	mkdir -p "$led/device" "$of_node" "$driver"
	ln -s "$of_node" "$led/of_node"
	ln -s "$driver" "$led/device/driver"
	printf '511\n' >"$led/max_brightness"
	printf '0000000000\n' >"$led/brightness"
	printf '[none] timer heartbeat\n' >"$led/trigger"
	printf '%s\n' "$led"
}

python3 - "$work/events" "$work/ignored" "$work/truncated" <<'PY'
import struct
import sys

event = struct.Struct("@llHHi")
records = (
    (0, 0, 0, 0, 0),
    (0, 0, 1, 116, 0),
    (0, 0, 1, 116, 2),
    (0, 0, 1, 114, 1),
    (0, 0, 1, 116, 1),
    (0, 0, 1, 116, 1),
    (0, 0, 1, 116, 0),
)
with open(sys.argv[1], "wb") as output:
    for record in records:
        output.write(event.pack(*record))
with open(sys.argv[2], "wb") as output:
    for record in records[:4]:
        output.write(event.pack(*record))
with open(sys.argv[3], "wb") as output:
    output.write(event.pack(*records[0]))
    output.write(b"short")
PY

led=$(make_led_fixture "$work/valid")
"${runner[@]}" "$fixture_binary" --fixture "$work/events" "$led" 1 20 \
	>"$work/valid.log"
[[ $(grep -c '^state=on brightness=31 pulse=1$' "$work/valid.log") == 1 ]]
[[ $(grep -c '^state=off brightness=0 pulse=1$' "$work/valid.log") == 1 ]]
[[ $(cat "$led/brightness") == 0000000000 ]] ||
	fail 'completed pulse did not leave fixture LED off'

ignored_led=$(make_led_fixture "$work/ignored-led")
"${runner[@]}" "$fixture_binary" --fixture "$work/ignored" \
	"$ignored_led" 0 20 \
	>"$work/ignored.log"
[[ ! -s $work/ignored.log ]] ||
	fail 'release, repeat, or non-power event changed the LED'
[[ $(cat "$ignored_led/brightness") == 0000000000 ]]

truncated_led=$(make_led_fixture "$work/truncated-led")
if "${runner[@]}" "$fixture_binary" --fixture "$work/truncated" \
	"$truncated_led" 0 20 \
	>"$work/truncated.log" 2>&1
then
	fail 'truncated input_event stream was accepted'
fi
grep -Fq 'contract_error=input.event_alignment' "$work/truncated.log" ||
	fail 'truncated event rejection was not explicit'
[[ $(cat "$truncated_led/brightness") == 0000000000 ]]

timer_failure_led=$(make_led_fixture "$work/timer-failure-led")
if "${runner[@]}" "$fixture_binary" --fixture "$work/events" \
	"$timer_failure_led" 0 20 timer-failure \
	>"$work/timer-failure.log" 2>&1
then
	fail 'injected timer-arm failure was accepted'
fi
grep -Fq 'state=off brightness=0 pulse=0' \
	"$work/timer-failure.log" ||
	fail 'timer-arm failure did not synchronously turn the LED off'
[[ $(cat "$timer_failure_led/brightness") == 0000000000 ]] ||
	fail 'timer-arm failure left fixture LED active'

explicit_off_led=$(make_led_fixture "$work/explicit-off-led")
printf '0000000031\n' >"$explicit_off_led/brightness"
"${runner[@]}" "$fixture_binary" --fixture-off "$explicit_off_led" \
	>"$work/explicit-off.log"
grep -Fqx 'state=off brightness=0 reason=explicit' \
	"$work/explicit-off.log" ||
	fail 'explicit stop fallback did not report LED-off'
[[ $(cat "$explicit_off_led/brightness") == 0000000000 ]] ||
	fail 'explicit stop fallback left fixture LED active'

signal_led=$(make_led_fixture "$work/signal-led")
"${runner[@]}" "$fixture_binary" --fixture "$work/events" \
	"$signal_led" 1 5000 \
	>"$work/signal.log" &
indicator_pid=$!
for _ in $(seq 1 100); do
	grep -q '^state=on ' "$work/signal.log" 2>/dev/null && break
	sleep 0.01
done
grep -q '^state=on ' "$work/signal.log" ||
	fail 'signal-cleanup fixture did not start its pulse'
kill -TERM "$indicator_pid"
wait "$indicator_pid"
[[ $(tail -n 1 "$work/signal.log") == \
	'state=off brightness=0 pulse=1' ]] ||
	fail 'SIGTERM did not synchronously turn the LED off'
[[ $(cat "$signal_led/brightness") == 0000000000 ]]

bad_max_led=$(make_led_fixture "$work/bad-max")
printf '255\n' >"$bad_max_led/max_brightness"
if "${runner[@]}" "$fixture_binary" --fixture "$work/ignored" \
	"$bad_max_led" 0 20 \
	>"$work/bad-max.log" 2>&1
then
	fail 'wrong LPG maximum brightness was accepted'
fi
grep -Fq 'contract_error=led.max_brightness' "$work/bad-max.log"

active_led=$(make_led_fixture "$work/active")
printf '1\n' >"$active_led/brightness"
if "${runner[@]}" "$fixture_binary" --fixture "$work/ignored" \
	"$active_led" 0 20 \
	>"$work/active.log" 2>&1
then
	fail 'initially active LED was accepted'
fi
grep -Fq 'contract_error=led.initial_brightness' "$work/active.log"

triggered_led=$(make_led_fixture "$work/triggered")
printf 'none [heartbeat]\n' >"$triggered_led/trigger"
if "${runner[@]}" "$fixture_binary" --fixture "$work/ignored" \
	"$triggered_led" 0 20 \
	>"$work/triggered.log" 2>&1
then
	fail 'selected automatic LED trigger was accepted'
fi
grep -Fq 'contract_error=led.trigger' "$work/triggered.log"

wrong_node_led=$(make_led_fixture "$work/wrong-node")
unlink "$wrong_node_led/of_node"
mkdir -p "$work/wrong-node/device-tree/led@1"
ln -s "$work/wrong-node/device-tree/led@1" "$wrong_node_led/of_node"
if "${runner[@]}" "$fixture_binary" --fixture "$work/ignored" \
	"$wrong_node_led" 0 20 \
	>"$work/wrong-node.log" 2>&1
then
	fail 'wrong LED OF node was accepted'
fi
grep -Fq 'contract_error=led.of_node' "$work/wrong-node.log"

wrong_driver_led=$(make_led_fixture "$work/wrong-driver")
unlink "$wrong_driver_led/device/driver"
mkdir -p "$work/wrong-driver/drivers/other"
ln -s "$work/wrong-driver/drivers/other" \
	"$wrong_driver_led/device/driver"
if "${runner[@]}" "$fixture_binary" --fixture "$work/ignored" \
	"$wrong_driver_led" 0 20 \
	>"$work/wrong-driver.log" 2>&1
then
	fail 'wrong LED driver was accepted'
fi
grep -Fq 'contract_error=led.driver' "$work/wrong-driver.log"

linked_brightness_led=$(make_led_fixture "$work/linked-brightness")
mv "$linked_brightness_led/brightness" \
	"$linked_brightness_led/real-brightness"
ln -s "$linked_brightness_led/real-brightness" \
	"$linked_brightness_led/brightness"
if "${runner[@]}" "$fixture_binary" --fixture "$work/ignored" \
	"$linked_brightness_led" 0 20 >"$work/linked.log" 2>&1
then
	fail 'linked brightness endpoint was accepted'
fi
grep -Fq 'contract_error=led.brightness_type' "$work/linked.log"

missing_node_led=$(make_led_fixture "$work/missing-node")
unlink "$missing_node_led/of_node"
if "${runner[@]}" "$fixture_binary" --fixture "$work/ignored" \
	"$missing_node_led" 0 20 >"$work/missing-node.log" 2>&1
then
	fail 'missing LED OF node was accepted'
fi
grep -Fq 'contract_error=led.of_node_resolve' "$work/missing-node.log"

missing_driver_led=$(make_led_fixture "$work/missing-driver")
unlink "$missing_driver_led/device/driver"
if "${runner[@]}" "$fixture_binary" --fixture "$work/ignored" \
	"$missing_driver_led" 0 20 >"$work/missing-driver.log" 2>&1
then
	fail 'missing LED driver link was accepted'
fi
grep -Fq 'contract_error=led.driver_resolve' "$work/missing-driver.log"

echo 'PASS native key indicator is identity-bound, press-only, bounded, default-off, signal-safe, and fixture-tested'
