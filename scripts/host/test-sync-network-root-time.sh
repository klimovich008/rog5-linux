#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
target=$repo/scripts/host/sync-network-root-time.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/bin"

[[ -x $target ]]
bash -n "$target"

for contract in \
	'ALLOW_NETWORK_ROOT_TIME_SYNC' \
	'SSH_KEY and KNOWN_HOSTS' \
	'host clock is not NTP-synchronized' \
	'1735689600' \
	'StrictHostKeyChecking=yes' \
	'HostKeyAlias=rog5-network-root' \
	'root@169.254.77.2' \
	'7.1.4-g7a5cef0db479' \
	'time bootstrap requires normal unmasked mode' \
	'findmnt -n -o SOURCE /.rog5/root-ro' \
	'physical block device is present' \
	'block-backed mount is present' \
	'169.254.77.2/30' \
	'systemd has failed units' \
	'/run/rog5-network-root-watchdog.pid' \
	'/soc@0/spmi@c440000/pmic@0/rtc@6100' \
	'/sys/module/rtc_pm8xxx' \
	'date --utc --set="@$host_epoch"' \
	'target clock did not converge on host time' \
	'RTC module loaded during sync' \
	'physical storage appeared during sync' \
	'rollback watchdog disappeared during sync' \
	'USB carrier dropped during sync' \
	'fatal kernel signature appeared during sync'; do
	grep -Fq "$contract" "$target" || {
		echo "FAIL time-sync contract missing: $contract" >&2
		exit 1
	}
done

if grep -Eq 'hwclock|/dev/rtc|timedatectl[[:space:]]+set-time|fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/' \
	"$target"; then
	echo 'FAIL time-sync tool can write RTC or phone storage' >&2
	exit 1
fi

cat >"$stage/bin/timedatectl" <<'EOF'
#!/bin/sh
set -eu
[ "$*" = 'show -p NTPSynchronized --value' ]
printf '%s\n' "${FAKE_NTP_SYNC:-yes}"
EOF
cat >"$stage/bin/ssh" <<'EOF'
#!/bin/sh
set -eu
: "${FAKE_SSH_ARGS:?}"
: "${FAKE_REMOTE_SCRIPT:?}"
printf '%s\n' "$@" >"$FAKE_SSH_ARGS"
cat >"$FAKE_REMOTE_SCRIPT"
echo 'PASS fake volatile Linux time sync'
EOF
chmod 0755 "$stage/bin/timedatectl" "$stage/bin/ssh"
printf 'not-a-private-key\n' >"$stage/client-key"
printf 'rog5-network-root ssh-ed25519 test-only\n' >"$stage/known-hosts"
chmod 0600 "$stage/client-key" "$stage/known-hosts"

set +e
PATH="$stage/bin:/usr/bin:/bin" "$target" >/dev/null 2>&1
missing_guard=$?
set -e
[[ $missing_guard -ne 0 ]]

FAKE_NTP_SYNC=no \
PATH="$stage/bin:/usr/bin:/bin" \
ALLOW_NETWORK_ROOT_TIME_SYNC=1 \
SSH_KEY="$stage/client-key" \
KNOWN_HOSTS="$stage/known-hosts" \
FAKE_SSH_ARGS="$stage/ssh-args" \
FAKE_REMOTE_SCRIPT="$stage/remote-script" \
	"$target" >/dev/null 2>&1 && {
	echo 'FAIL unsynchronized host clock was accepted' >&2
	exit 1
}
[[ ! -e $stage/ssh-args ]]

PATH="$stage/bin:/usr/bin:/bin" \
ALLOW_NETWORK_ROOT_TIME_SYNC=1 \
SSH_KEY="$stage/client-key" \
KNOWN_HOSTS="$stage/known-hosts" \
FAKE_SSH_ARGS="$stage/ssh-args" \
FAKE_REMOTE_SCRIPT="$stage/remote-script" \
	"$target" | grep -qx 'PASS fake volatile Linux time sync'

grep -Fxq -- '-F' "$stage/ssh-args"
grep -Fxq -- '/dev/null' "$stage/ssh-args"
grep -Fxq -- '-o' "$stage/ssh-args"
grep -Fxq -- 'StrictHostKeyChecking=yes' "$stage/ssh-args"
grep -Fxq -- 'HostKeyAlias=rog5-network-root' "$stage/ssh-args"
grep -Fxq -- 'root@169.254.77.2' "$stage/ssh-args"
grep -Fq 'date --utc --set="@$host_epoch"' "$stage/remote-script"
! grep -Eq 'hwclock|/dev/rtc|fastboot[[:space:]]+flash' "$stage/remote-script"

chmod 0644 "$stage/client-key"
set +e
PATH="$stage/bin:/usr/bin:/bin" \
ALLOW_NETWORK_ROOT_TIME_SYNC=1 \
SSH_KEY="$stage/client-key" \
KNOWN_HOSTS="$stage/known-hosts" \
FAKE_SSH_ARGS="$stage/ssh-args-weak-key" \
FAKE_REMOTE_SCRIPT="$stage/remote-script-weak-key" \
	"$target" >/dev/null 2>&1
weak_key=$?
set -e
[[ $weak_key -ne 0 ]]
[[ ! -e $stage/ssh-args-weak-key ]]

echo 'PASS host time bootstrap requires synchronized time, strict SSH, armed rollback, zero storage, and disabled RTC'
