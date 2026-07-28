#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ ${ALLOW_PERSISTENT_ROOT_P2_LIVE_GATE:-} == 1 ]] ||
	fail 'set ALLOW_PERSISTENT_ROOT_P2_LIVE_GATE=1 for the one-shot P2 gate'
[[ ${ALLOW_TEMPORARY_BOOT:-} == 1 ]] ||
	fail 'set ALLOW_TEMPORARY_BOOT=1 for the non-flashing boot'
[[ ${ALLOW_ATTENDED_KEXEC:-} == 1 ]] ||
	fail 'set ALLOW_ATTENDED_KEXEC=1 for the one-shot kexec'

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
ssh_key=${SSH_KEY:-}
known_hosts=${KNOWN_HOSTS:-}
evidence_dir=${EVIDENCE_DIR:-}
target_timeout=${P2_TARGET_TIMEOUT:-480}
fallback_timeout=${P2_FALLBACK_TIMEOUT:-750}
[[ -n $ssh_key && -n $known_hosts && -n $evidence_dir ]] ||
	fail 'set SSH_KEY, KNOWN_HOSTS, and EVIDENCE_DIR'

case $target_timeout:$fallback_timeout in
	*[^0-9:]*|:*|*:) fail 'P2 timeouts must be integers' ;;
esac
(( target_timeout >= 120 && target_timeout <= 540 )) ||
	fail 'P2_TARGET_TIMEOUT must be between 120 and 540 seconds'
(( fallback_timeout >= 620 && fallback_timeout <= 900 )) ||
	fail 'P2_FALLBACK_TIMEOUT must be between 620 and 900 seconds'

for command in awk chmod cut date git grep mktemp realpath rm sha256sum \
	sleep ssh stat systemctl tee; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
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
case $ssh_key:$known_hosts:$evidence_dir in
	"$repo":*|"$repo"/*:*|*:"$repo":*|*:"$repo"/*:*|*:"$repo"|*:"$repo"/*)
		fail 'credentials and evidence must remain outside the repository'
		;;
esac

boot_image=$repo/artifacts/persistent-root-p2/boot-5.4.210-persistent-root.avb.img
recovery=$repo/scripts/host/recovery-linux.sh
acm=$repo/scripts/host/persistent-root-acm.py
fallback=$repo/scripts/host/reboot-fallback-to-fastboot.sh
for input in "$boot_image" "$recovery" "$acm" "$fallback"; do
	[[ -f $input && ! -L $input && -r $input ]] ||
		fail "P2 live input is absent or linked: $input"
done
[[ -x $recovery && -x $acm && -x $fallback ]] ||
	fail 'a P2 host control is not executable'

target_log=$evidence_dir/persistent-root-p2-target.log
fallback_log=$evidence_dir/persistent-root-p2-fallback.log
[[ ! -e $target_log && ! -e $fallback_log ]] ||
	fail 'a private P2 evidence log already exists'

umask 077
target_known_hosts=$(mktemp)
chmod 0600 "$target_known_hosts"
modem_manager_was_active=0
cleanup() {
	local status=$?
	[[ -z ${target_known_hosts:-} ]] ||
		rm -f -- "$target_known_hosts"
	if (( modem_manager_was_active )); then
		systemctl start ModemManager.service >/dev/null 2>&1 || true
	fi
	return "$status"
}
trap cleanup EXIT

BOOT_IMAGE=$boot_image "$recovery" preflight
if systemctl is-active --quiet ModemManager.service; then
	systemctl stop ModemManager.service
	modem_manager_was_active=1
fi
systemctl is-active --quiet ModemManager.service &&
	fail 'ModemManager remained active'

BOOT_IMAGE=$boot_image ALLOW_TEMPORARY_BOOT=1 "$recovery" boot
ALLOW_PERSISTENT_ROOT_ACM=1 "$acm" load
ALLOW_PERSISTENT_ROOT_ACM=1 "$acm" preflight
execute_epoch=$(date +%s)
ALLOW_PERSISTENT_ROOT_ACM=1 ALLOW_ATTENDED_KEXEC=1 "$acm" execute

target=root@169.254.77.2
target_accept_options=(
	-F /dev/null
	-i "$ssh_key"
	-o IdentitiesOnly=yes
	-o BatchMode=yes
	-o StrictHostKeyChecking=accept-new
	-o UserKnownHostsFile="$target_known_hosts"
	-o HostKeyAlias=rog5-persistent-root
	-o ConnectTimeout=5
	-o ConnectionAttempts=1
	-o ServerAliveInterval=5
	-o ServerAliveCountMax=2
	-o LogLevel=ERROR
)
target_strict_options=("${target_accept_options[@]}")
for index in "${!target_strict_options[@]}"; do
	if [[ ${target_strict_options[$index]} == \
		StrictHostKeyChecking=accept-new ]]; then
		target_strict_options[$index]=StrictHostKeyChecking=yes
	fi
done
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

target_deadline=$(( $(date +%s) + target_timeout ))
target_boot_id=
early_fallback_boot_id=
early_fallback_elapsed=
while (( $(date +%s) < target_deadline )); do
	set +e
	candidate=$(ssh -n "${target_accept_options[@]}" "$target" \
		'[ "$(uname -r)" = 7.1.4-gcfd385a1c754 ] &&
			cat /proc/sys/kernel/random/boot_id' 2>/dev/null)
	status=$?
	set -e
	if [[ $status == 0 &&
		$candidate =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
		target_boot_id=$candidate
		break
	fi
	: >"$target_known_hosts"
	set +e
	fallback_candidate=$(ssh -n "${fallback_options[@]}" "$target" \
		'[ "$(uname -r)" = 5.4.134-qgki-perf-00001-g6c308144c23e ] &&
			cat /proc/sys/kernel/random/boot_id' 2>/dev/null)
	fallback_status=$?
	set -e
	if [[ $fallback_status == 0 &&
		$fallback_candidate =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
		early_fallback_boot_id=$fallback_candidate
		early_fallback_elapsed=$(( $(date +%s) - execute_epoch ))
		printf \
			'REJECTED P2 target returned to exact fallback before acceptance elapsed_seconds=%s\n' \
			"$early_fallback_elapsed" |
			tee -a "$fallback_log" >/dev/null
		chmod 0600 "$fallback_log"
		break
	fi
	sleep 2
done
[[ -z $early_fallback_boot_id ]] ||
	fail "P2 target returned to exact fallback before acceptance after ${early_fallback_elapsed}s"
[[ -n $target_boot_id ]] || fail 'exact P2 target SSH did not appear'
[[ -s $target_known_hosts && ! -L $target_known_hosts &&
	$(stat -c '%u:%a' "$target_known_hosts") == "$EUID:600" ]] ||
	fail 'volatile target host key was not privately pinned'

while (( $(date +%s) < target_deadline )); do
	if ssh -n "${target_strict_options[@]}" "$target" \
		'test -r /run/rog5-p2-ready' 2>/dev/null; then
		break
	fi
	sleep 2
done
ssh -n "${target_strict_options[@]}" "$target" \
	'test -r /run/rog5-p2-ready' 2>/dev/null ||
	fail 'P2 target readiness marker did not appear'

remote_target='
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

ready=/run/rog5-p2-ready
lower=/.rog5/userdata-ro/rog5/roots/arch-a
expected_seal=e201955dead61a04ca0e70d67fcea18750940330421334c91cfe2c760e7fb3ff
expected_tree=b71eccbe5275f8d125a6d3251fff166b57f196c23984b845e31666ecaaea9a8c

[ "$(uname -r)" = 7.1.4-gcfd385a1c754 ] ||
	fail "unexpected target kernel"
[ "$(cat /proc/1/comm)" = systemd ] || fail "PID 1 is not systemd"
[ "$(systemctl is-system-running 2>/dev/null || true)" = running ] ||
	fail "systemd is not running"
systemctl is-active --quiet sshd.service ||
	fail "target SSH service is not active"
systemctl is-active --quiet rog5-p2-ready.service ||
	fail "target acceptance service is not active"
[ "$(stat -c "%u:%g:%a" "$ready")" = 0:0:444 ] ||
	fail "readiness marker metadata changed"
for line in \
	"status=PASS" \
	"kernel=7.1.4-gcfd385a1c754" \
	"physical_blocks=116" \
	"block_backed_mounts=1" \
	"userdata_mount=ro-noload" \
	"root=overlay-tmpfs" \
	"blocked_device_queries=0" \
	"blocked_scsi_commands=0" \
	"journal_recovery_events=0" \
	"ufs_error_events=0" \
	"ssh=strict-key-only"; do
	grep -Fxq "$line" "$ready" || fail "readiness marker omits $line"
done
grep -Eq "^backlights=[0-9]+$" "$ready" ||
	fail "readiness backlight count is invalid"
[ "$(wc -l <"$ready")" -eq 12 ] ||
	fail "readiness marker field count changed"

[ "$(sha256sum "$lower/.rog5-persistent-seal" | cut -d " " -f 1)" = \
	"$expected_seal" ] || fail "root seal changed"
grep -Fxq "tree_sha256=$expected_tree" \
	"$lower/.rog5-persistent-seal" || fail "tree identity changed"
grep -Fxq "promotion_state=UNBOOTED" \
	"$lower/.rog5-persistent-seal" || fail "root promotion state changed"
[ ! -e /.rog5/userdata-ro/rog5/state/good ] ||
	fail "root was promoted"
[ ! -e /.rog5/userdata-ro/rog5/state/next ] ||
	fail "root was selected"

awk "\$1 == \"overlay\" && \$2 == \"/\" && \$3 == \"overlay\" &&
	\$4 ~ /(^|,)rw(,|$)/ { found++ }
	END { exit found != 1 }" /proc/mounts ||
	fail "active root is not the volatile overlay"
awk "\$1 == \"/dev/sda23\" && \$2 == \"/.rog5/userdata-ro\" &&
	\$3 == \"ext4\" && \$4 ~ /(^|,)ro(,|$)/ { found++ }
	END { exit found != 1 }" /proc/mounts ||
	fail "userdata is not the exact read-only mount"

physical=0
for sys_disk in /sys/class/block/*; do
	[ -e "$sys_disk/device" ] || continue
	[ ! -e "$sys_disk/partition" ] || continue
	disk=$(basename "$sys_disk")
	for sys_block in "$sys_disk" "$sys_disk"/"$disk"*; do
		[ -e "$sys_block/dev" ] || continue
		[ "$sys_block" = "$sys_disk" ] ||
			[ -e "$sys_block/partition" ] || continue
		device=/dev/$(basename "$sys_block")
		[ "$(cat "$sys_block/ro")" = 1 ] &&
			[ "$(blockdev --getro "$device")" = 1 ] ||
			fail "writable physical block node"
		physical=$((physical + 1))
	done
done
[ "$physical" -eq 116 ] || fail "physical topology changed"

blocked_query=$(dmesg |
	grep -F -c "ROG5 UFS discovery: blocked device query" || true)
blocked_scsi=$(dmesg |
	grep -F -c "ROG5 UFS discovery: blocked SCSI opcode" || true)
journal=$(dmesg |
	grep -Eic "EXT4-fs.*(journal recovery|recovery complete|recovering journal)" ||
	true)
ufs_errors=$(dmesg |
	grep -Eic "(ufshcd|ufshcd-qcom|scsi|sd [0-9]).*(fatal|abort|reset|I/O error|timed out)" ||
	true)
[ "$blocked_query:$blocked_scsi:$journal:$ufs_errors" = 0:0:0:0 ] ||
	fail "storage health changed after readiness"

[ -s /run/rog5-p2-watchdog.pid ] ||
	fail "target watchdog PID is absent"
watchdog=$(cat /run/rog5-p2-watchdog.pid)
kill -0 "$watchdog" 2>/dev/null || fail "target watchdog is not alive"
[ ! -e /run/rog5-p2-watchdog.disarmed.pid ] ||
	fail "target watchdog was disarmed"

backlights=0
for brightness in /sys/class/backlight/*/brightness; do
	[ -e "$brightness" ] || continue
	backlights=$((backlights + 1))
	[ "$(cat "$brightness")" = 0 ] || fail "a backlight is on"
done
failed_units=$(systemctl --failed --no-legend --plain |
	awk "NF { count++ } END { print count + 0 }")
[ "$failed_units" -eq 0 ] || fail "systemd has failed units"
fatal="Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite"
[ "$(dmesg | grep -Eic "$fatal" || true)" -eq 0 ] ||
	fail "fatal target signature appeared"

printf "kernel=%s\n" "$(uname -r)"
printf "physical_blocks=%s\n" "$physical"
printf "backlights=%s\n" "$backlights"
printf "failed_units=%s\n" "$failed_units"
echo "watchdog=armed"
echo "PASS P2 target acceptance kernel=7.1.4-gcfd385a1c754 storage=ro overlay=tmpfs watchdog=armed"
'

set +e
ssh -n "${target_strict_options[@]}" "$target" "$remote_target" 2>&1 |
	tee "$target_log" >/dev/null
target_status=${PIPESTATUS[0]}
set -e
chmod 0600 "$target_log"
[[ $target_status == 0 ]] || fail 'P2 target acceptance SSH failed'
grep -Fxq \
	'PASS P2 target acceptance kernel=7.1.4-gcfd385a1c754 storage=ro overlay=tmpfs watchdog=armed' \
	"$target_log" || fail 'exact P2 target acceptance marker is absent'

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
[[ $fallback_boot_id != "$target_boot_id" ]] ||
	fail 'fallback retained the target boot identity'

set +e
SSH_KEY=$ssh_key KNOWN_HOSTS=$known_hosts \
	"$fallback" preflight 2>&1 | tee "$fallback_log" >/dev/null
fallback_status=${PIPESTATUS[0]}
set -e
chmod 0600 "$fallback_log"
[[ $fallback_status == 0 ]] || fail 'exact fallback preflight failed'

remote_fallback='
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

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

attempt=0
while [ "$attempt" -lt 30 ]; do
	on=0
	for brightness in /sys/class/backlight/*/brightness; do
		[ -e "$brightness" ] || continue
		[ "$(cat "$brightness")" = 0 ] || on=$((on + 1))
	done
	[ "$on" -eq 0 ] && break
	attempt=$((attempt + 1))
	sleep 1
done
[ "$on" -eq 0 ] || fail "fallback backlight remained on"

echo "root_state=UNBOOTED"
echo "selectors=absent"
echo "screen=off-or-absent"
echo "PASS P2 fallback acceptance kernel=5.4.134-qgki-perf-00001-g6c308144c23e root=UNBOOTED selectors=absent"
'

set +e
ssh -n "${fallback_options[@]}" "$target" "$remote_fallback" 2>&1 |
	tee -a "$fallback_log" >/dev/null
fallback_state_status=${PIPESTATUS[0]}
set -e
chmod 0600 "$fallback_log"
[[ $fallback_state_status == 0 ]] ||
	fail 'fallback persistent-root state check failed'
grep -Fxq \
	'PASS P2 fallback acceptance kernel=5.4.134-qgki-perf-00001-g6c308144c23e root=UNBOOTED selectors=absent' \
	"$fallback_log" || fail 'exact P2 fallback acceptance marker is absent'

if (( modem_manager_was_active )); then
	systemctl start ModemManager.service
	systemctl is-active --quiet ModemManager.service ||
		fail 'ModemManager was not restored'
	modem_manager_was_active=0
fi
rm -f -- "$target_known_hosts"
target_known_hosts=
trap - EXIT

echo 'PASS one-shot P2 live gate temporarily booted, attested read-only Arch, preserved the watchdog, returned to exact Alpine, and restored host state'
