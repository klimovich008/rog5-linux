#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ ${ALLOW_PERSISTENT_ROOT_ENTRY_LIVE_GATE:-} == 1 ]] ||
	fail 'set ALLOW_PERSISTENT_ROOT_ENTRY_LIVE_GATE=1 for the one-shot entry gate'
[[ ${ALLOW_TEMPORARY_BOOT:-} == 1 ]] ||
	fail 'set ALLOW_TEMPORARY_BOOT=1 for the non-flashing boot'
[[ ${ALLOW_ATTENDED_KEXEC:-} == 1 ]] ||
	fail 'set ALLOW_ATTENDED_KEXEC=1 for the one-shot kexec'

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
ssh_key=${SSH_KEY:-}
known_hosts=${KNOWN_HOSTS:-}
evidence_dir=${EVIDENCE_DIR:-}
fallback_timeout=${ENTRY_FALLBACK_TIMEOUT:-360}
[[ -n $ssh_key && -n $known_hosts && -n $evidence_dir ]] ||
	fail 'set SSH_KEY, KNOWN_HOSTS, and EVIDENCE_DIR'
case $fallback_timeout in
	''|*[!0-9]*) fail 'ENTRY_FALLBACK_TIMEOUT must be an integer' ;;
esac
(( fallback_timeout >= 180 && fallback_timeout <= 600 )) ||
	fail 'ENTRY_FALLBACK_TIMEOUT must be between 180 and 600 seconds'

for command in awk cat chmod cut date fastboot git grep realpath rm \
	sha256sum sleep ssh stat systemctl tee; do
	command -v "$command" >/dev/null ||
		fail "missing host command: $command"
done
[[ -z $(git -C "$repo" status --porcelain --untracked-files=all) ]] ||
	fail 'repository must be clean before the one-shot gate'
[[ $(git -C "$repo" branch --show-current) == agent/linux-recovery-host ]] ||
	fail 'unexpected repository branch'
[[ $(git -C "$repo" rev-parse HEAD) == \
	$(git -C "$repo" rev-parse origin/agent/linux-recovery-host) ]] ||
	fail 'local and remote-tracking checkpoints differ'

ssh_key=$(realpath -e "$ssh_key")
known_hosts=$(realpath -e "$known_hosts")
evidence_dir=$(realpath -e "$evidence_dir")
[[ -f $ssh_key && ! -L $ssh_key && -r $ssh_key ]] ||
	fail 'SSH_KEY is not a readable regular file'
[[ -f $known_hosts && ! -L $known_hosts && -r $known_hosts ]] ||
	fail 'KNOWN_HOSTS is not a readable regular file'
[[ -d $evidence_dir && ! -L $evidence_dir && $evidence_dir != / ]] ||
	fail 'EVIDENCE_DIR is not a safe existing directory'
[[ $(stat -c %u "$ssh_key") == "$EUID" &&
	$(stat -c %u "$known_hosts") == "$EUID" &&
	$(stat -c %u "$evidence_dir") == "$EUID" ]] ||
	fail 'credential and evidence paths must be caller-owned'
key_mode=$(stat -c %a "$ssh_key")
known_hosts_mode=$(stat -c %a "$known_hosts")
evidence_mode=$(stat -c %a "$evidence_dir")
[[ $key_mode =~ ^[0-7]{3,4}$ &&
	$known_hosts_mode =~ ^[0-7]{3,4}$ &&
	$evidence_mode =~ ^[0-7]{3,4}$ ]] ||
	fail 'credential or evidence mode is invalid'
(( (8#$key_mode & 077) == 0 )) ||
	fail 'SSH_KEY must not be accessible by group or other users'
(( (8#$known_hosts_mode & 022) == 0 )) ||
	fail 'KNOWN_HOSTS must not be writable by group or other users'
(( (8#$evidence_mode & 077) == 0 )) ||
	fail 'EVIDENCE_DIR must not be accessible by group or other users'
for private_path in "$ssh_key" "$known_hosts" "$evidence_dir"; do
	case $private_path in
		"$repo"|"$repo"/*)
			fail 'credentials and evidence must remain outside the repository'
			;;
	esac
done

artifact_dir=$repo/artifacts/persistent-root-entry-v1
boot_image=$artifact_dir/boot-5.4.210-persistent-root-entry.avb.img
recovery=$repo/scripts/host/recovery-linux.sh
staging_acm=$repo/scripts/host/persistent-root-acm.py
entry_acm=$repo/scripts/host/persistent-root-entry-acm.py
fallback=$repo/scripts/host/reboot-fallback-to-fastboot.sh
screen_toggle=$repo/scripts/device/screen-toggle.sh
screen_daemon=$repo/scripts/device/alpine-screen-button-daemon.sh
screen_starter=$repo/scripts/device/alpine-screen-button-openrc-start.sh
phone_wrapper=$repo/scripts/device/alpine-phone-start-wrapper.sh
screen_service=$repo/packaging/alpine/rog5-screen-button
for input in \
	"$boot_image" "$recovery" "$staging_acm" "$entry_acm" "$fallback" \
	"$screen_toggle" "$screen_daemon" "$screen_starter" \
	"$phone_wrapper" "$screen_service"; do
	[[ -f $input && ! -L $input && -r $input ]] ||
		fail "entry live input is absent or linked: $input"
done
for control in "$recovery" "$staging_acm" "$entry_acm" "$fallback"; do
	[[ -x $control ]] || fail "entry host control is not executable: $control"
done

toggle_hash=$(sha256sum "$screen_toggle" | cut -d ' ' -f 1)
daemon_hash=$(sha256sum "$screen_daemon" | cut -d ' ' -f 1)
starter_hash=$(sha256sum "$screen_starter" | cut -d ' ' -f 1)
wrapper_hash=$(sha256sum "$phone_wrapper" | cut -d ' ' -f 1)
service_hash=$(sha256sum "$screen_service" | cut -d ' ' -f 1)
for hash in \
	"$toggle_hash" "$daemon_hash" "$starter_hash" "$wrapper_hash" \
	"$service_hash"; do
	[[ $hash =~ ^[0-9a-f]{64}$ ]] || fail 'invalid local screen-service hash'
done

target_log=$evidence_dir/persistent-root-entry-target.log
fallback_log=$evidence_dir/persistent-root-entry-fallback.log
[[ ! -e $target_log && ! -e $fallback_log ]] ||
	fail 'a private entry evidence log already exists'
umask 077
: >"$target_log"
: >"$fallback_log"
chmod 0600 "$target_log" "$fallback_log"

modem_manager_was_active=0
cleanup() {
	local status=$?
	if (( modem_manager_was_active )); then
		systemctl start ModemManager.service >/dev/null 2>&1 || true
	fi
	return "$status"
}
trap cleanup EXIT

devices=$(fastboot devices 2>/dev/null) || fail 'fastboot devices failed'
device_count=$(awk '$2 == "fastboot" { count++ }
	END { print count + 0 }' <<<"$devices")
[[ $device_count == 1 ]] ||
	fail "expected exactly one fastboot device, found $device_count"

BOOT_IMAGE=$boot_image "$recovery" preflight
if systemctl is-active --quiet ModemManager.service; then
	systemctl stop ModemManager.service
	modem_manager_was_active=1
fi
systemctl is-active --quiet ModemManager.service &&
	fail 'ModemManager remained active'

BOOT_IMAGE=$boot_image ALLOW_TEMPORARY_BOOT=1 "$recovery" boot
ALLOW_PERSISTENT_ROOT_ACM=1 "$staging_acm" load
ALLOW_PERSISTENT_ROOT_ACM=1 "$staging_acm" preflight
ALLOW_PERSISTENT_ROOT_ACM=1 ALLOW_ATTENDED_KEXEC=1 \
	"$staging_acm" execute

set +e
ALLOW_PERSISTENT_ROOT_ENTRY_ACM=1 "$entry_acm" read 2>&1 |
	tee -a "$target_log" >/dev/null
entry_status=${PIPESTATUS[0]}
set -e
chmod 0600 "$target_log"
entry_accepted=0
if (( entry_status == 0 )) &&
	grep -Fxq 'kernel_release=7.1.4-gcfd385a1c754' "$target_log" &&
	grep -Fxq \
		'PASS P2 early-entry oracle init=entered storage=untouched watchdog=armed' \
		"$target_log" &&
	grep -Fxq 'PASS receive-only P2 early-entry ACM marker' "$target_log"; then
	entry_accepted=1
fi

target=root@169.254.77.2
fallback_options=(
	-F /dev/null
	-i "$ssh_key"
	-o IdentitiesOnly=yes
	-o BatchMode=yes
	-o StrictHostKeyChecking=yes
	-o UserKnownHostsFile="$known_hosts"
	-o HostKeyAlias=rog5-fallback
	-o ConnectTimeout=5
	-o ConnectionAttempts=1
	-o ServerAliveInterval=5
	-o ServerAliveCountMax=2
	-o LogLevel=ERROR
)

fallback_deadline=$(( $(date +%s) + fallback_timeout ))
fallback_boot_id=
while (( $(date +%s) < fallback_deadline )); do
	set +e
	candidate=$(ssh -n "${fallback_options[@]}" "$target" \
		'[ "$(uname -r)" = 5.4.134-qgki-perf-00001-g6c308144c23e ] &&
			cat /proc/sys/kernel/random/boot_id' 2>/dev/null)
	status=$?
	set -e
	if [[ $status == 0 &&
		$candidate =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
		fallback_boot_id=$candidate
		break
	fi
	sleep 2
done
[[ -n $fallback_boot_id ]] || fail 'exact Alpine fallback did not return'

set +e
SSH_KEY=$ssh_key KNOWN_HOSTS=$known_hosts \
	"$fallback" preflight 2>&1 |
	tee -a "$fallback_log" >/dev/null
fallback_preflight_status=${PIPESTATUS[0]}
set -e
[[ $fallback_preflight_status == 0 ]] ||
	fail 'exact fallback preflight failed'

remote_fallback=$(cat <<'REMOTE'
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

expected_toggle=__TOGGLE_HASH__
expected_daemon=__DAEMON_HASH__
expected_starter=__STARTER_HASH__
expected_wrapper=__WRAPPER_HASH__
expected_service=__SERVICE_HASH__
expected_phone_base=d42215d6a619d21b41e890b4c7f622284bd33cb360c122c71aca5c5ffc5435a6
root=/rog5/roots/arch-a
seal=$root/.rog5-persistent-seal

[ "$(uname -r)" = 5.4.134-qgki-perf-00001-g6c308144c23e ] ||
	fail "unexpected fallback kernel"
[ -d "$root" ] && [ ! -L "$root" ] || fail "staged root is absent"
[ "$(stat -c "%u:%g:%a" "$seal")" = 0:0:444 ] ||
	fail "fallback root seal metadata changed"
[ "$(sha256sum "$seal" | cut -d " " -f 1)" = \
	e201955dead61a04ca0e70d67fcea18750940330421334c91cfe2c760e7fb3ff ] ||
	fail "fallback root seal changed"
grep -Fxq \
	"tree_sha256=b71eccbe5275f8d125a6d3251fff166b57f196c23984b845e31666ecaaea9a8c" \
	"$seal" || fail "fallback tree identity changed"
grep -Fxq "promotion_state=UNBOOTED" "$seal" ||
	fail "fallback promotion state changed"
[ ! -e /rog5/state/good ] || fail "root was promoted"
[ ! -e /rog5/state/next ] || fail "root was selected"
[ ! -e /rog5/roots/arch-a.partial ] || fail "partial root appeared"

check_hash() {
	path=$1
	expected=$2
	[ -f "$path" ] && [ ! -L "$path" ] && [ -x "$path" ] ||
		fail "screen service file is absent, linked, or not executable: $path"
	[ "$(stat -c "%u:%g:%a" "$path")" = 0:0:755 ] ||
		fail "screen service file metadata changed: $path"
	[ "$(sha256sum "$path" | cut -d " " -f 1)" = "$expected" ] ||
		fail "screen service file hash changed: $path"
}

check_hash /usr/local/bin/rog5-screen-toggle.sh "$expected_toggle"
check_hash /usr/local/sbin/rog5-screen-button-daemon.sh "$expected_daemon"
check_hash /usr/local/sbin/rog5-screen-button-openrc-start.sh \
	"$expected_starter"
check_hash /usr/local/sbin/rog5-phone-start "$expected_wrapper"
check_hash /etc/init.d/rog5-screen-button "$expected_service"
check_hash /usr/local/libexec/rog5-phone-start-base "$expected_phone_base"
[ -f /run/openrc/softlevel ] && [ ! -L /run/openrc/softlevel ] ||
	fail "OpenRC softlevel was not initialized after rollback"
rc-update show default |
	awk '$1 == "rog5-screen-button" { found=1 } END { exit !found }' ||
	fail "screen service is not enabled"
rc-service rog5-screen-button status >/dev/null 2>&1 ||
	fail "screen service is not active"

[ "$(cat /run/rog5-screen-state)" = off ] ||
	fail "fallback screen state is not off"
backlights=0
for brightness in /sys/class/backlight/*/brightness; do
	[ -e "$brightness" ] || continue
	backlights=$((backlights + 1))
	[ "$(cat "$brightness")" = 0 ] ||
		fail "a fallback backlight is on"
done
[ "$backlights" -gt 0 ] || fail "fallback backlight telemetry is absent"

power_event=
power_events=0
for name in /sys/class/input/event*/device/name; do
	[ -r "$name" ] || continue
	[ "$(cat "$name" 2>/dev/null)" = qpnp_pon ] || continue
	event_path=${name%/device/name}
	event_name=${event_path##*/}
	candidate=/dev/input/$event_name
	[ -c "$candidate" ] || continue
	power_event=$candidate
	power_events=$((power_events + 1))
done
[ "$power_events" -eq 1 ] ||
	fail "expected one qpnp_pon power input"

daemons=0
evtests=0
unexpected_evtests=0
for process in /proc/[0-9]*; do
	[ -r "$process/cmdline" ] || continue
	cmdline=$(tr "\000" " " <"$process/cmdline" 2>/dev/null || true)
	case $cmdline in
		"/bin/sh /usr/local/sbin/rog5-screen-button-daemon.sh ")
			daemons=$((daemons + 1))
			;;
		"evtest --grab $power_event ")
			evtests=$((evtests + 1))
			;;
		"evtest --grab /dev/input/event"*" ")
			unexpected_evtests=$((unexpected_evtests + 1))
			;;
	esac
done
[ "$daemons" -eq 1 ] || fail "expected one screen daemon"
[ "$evtests" -eq 1 ] || fail "expected one screen event reader"
[ "$unexpected_evtests" -eq 0 ] ||
	fail "an unexpected screen event reader remained"
fifos=0
for fifo in /run/rog5-screen-button.*.events; do
	[ -p "$fifo" ] || continue
	fifos=$((fifos + 1))
done
[ "$fifos" -eq 1 ] || fail "expected one screen event FIFO"

echo "root_state=UNBOOTED"
echo "selectors=absent"
echo "screen=off"
echo "screen_service=active"
echo "PASS P2 early-entry fallback acceptance kernel=5.4.134-qgki-perf-00001-g6c308144c23e root=UNBOOTED screen=off"
REMOTE
)
remote_fallback=${remote_fallback//__TOGGLE_HASH__/$toggle_hash}
remote_fallback=${remote_fallback//__DAEMON_HASH__/$daemon_hash}
remote_fallback=${remote_fallback//__STARTER_HASH__/$starter_hash}
remote_fallback=${remote_fallback//__WRAPPER_HASH__/$wrapper_hash}
remote_fallback=${remote_fallback//__SERVICE_HASH__/$service_hash}

set +e
ssh -n "${fallback_options[@]}" "$target" "$remote_fallback" 2>&1 |
	tee -a "$fallback_log" >/dev/null
fallback_attest_status=${PIPESTATUS[0]}
set -e
chmod 0600 "$fallback_log"
[[ $fallback_attest_status == 0 ]] ||
	fail 'exact fallback state attestation failed'
grep -Fxq \
	'PASS P2 early-entry fallback acceptance kernel=5.4.134-qgki-perf-00001-g6c308144c23e root=UNBOOTED screen=off' \
	"$fallback_log" ||
	fail 'exact fallback acceptance marker is absent'

(( entry_accepted )) ||
	fail 'P2 early-entry oracle was rejected; exact fallback and screen service were verified'

echo 'PASS P2 early-entry live gate accepted RAM-only entry and exact fallback rollback'
