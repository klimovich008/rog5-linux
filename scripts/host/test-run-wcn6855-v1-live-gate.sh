#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
runner=$repo/scripts/host/run-wcn6855-v1-live-gate.sh
gate=$repo/scripts/device/run-network-root-wifi-gate.sh
disarm=$repo/scripts/device/disarm-network-root-watchdog.sh
verify=$repo/scripts/host/verify-wcn6855-v1-export.sh

for script in "$runner" "$gate" "$disarm" "$verify"; do
	[[ -x $script ]] || {
		echo "FAIL missing WCN6855 v1 live-gate control: $script" >&2
		exit 1
	}
	bash -n "$script"
done
ssh -G -T -F /dev/null -o ConnectionAttempts=1 localhost >/dev/null

gate_hash=$(sha256sum "$gate" | cut -d ' ' -f 1)
verify_hash=$(sha256sum "$verify" | cut -d ' ' -f 1)
for contract in \
	'ALLOW_WCN6855_V1_LIVE_GATE' \
	'ALLOW_WCN6855_V1_REBOOT' \
	'SSH_KEY' \
	'KNOWN_HOSTS' \
	'EVIDENCE_DIR' \
	'/var/lib/rog5-network-root-wcn6855-v1' \
	'verify-wcn6855-v1-export.sh' \
	'pkexec --disable-internal-agent' \
	'disarm-network-root-watchdog.sh' \
	'run-network-root-wifi-gate.sh' \
	"$gate_hash" \
	"$verify_hash" \
	'b126182b615831e6f39784e4a2657cc60096ff906c26f1458be7d9a0d3ea065a' \
	'root@169.254.77.2' \
	'HostKeyAlias=rog5-wcn6855-v1' \
	'StrictHostKeyChecking=yes' \
	'BatchMode=yes' \
	'ConnectionAttempts=1' \
	'ssh -n' \
	'scp -q' \
	'chmod 0500' \
	'wcn6855-v1-export' \
	'ALLOW_MAINLINE_WCN6855_GATE=1' \
	'ALLOW_MAINLINE_WCN6855_REBOOT=1' \
	'PASS WCN6855 enumeration-only probe' \
	'PASS compound WCN6855 enumeration-only gate' \
	'PIPESTATUS[0]' \
	'umask 077'
do
	grep -Fq "$contract" "$runner" || {
		echo "FAIL host WCN6855 v1 runner omits: $contract" >&2
		exit 1
	}
done

[[ $(grep -Fc 'exec env ALLOW_MAINLINE_WCN6855_GATE=1' "$runner") == 1 ]]
if grep -Eq \
	'fastboot|adb|serve-(network-root|wcn6855)|exportfs|rpc[.]nfsd|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|StrictHostKeyChecking=(no|accept-new)|UserKnownHostsFile=/dev/null' \
	"$runner"
then
	echo 'FAIL host WCN6855 v1 runner bypasses server, identity, or storage safety' >&2
	exit 1
fi

set +e
"$runner" >/dev/null 2>&1
missing_guards=$?
ALLOW_WCN6855_V1_LIVE_GATE=1 \
	ALLOW_WCN6855_V1_REBOOT=unsafe \
	"$runner" >/dev/null 2>&1
invalid_reboot_guard=$?
set -e
[[ $missing_guards -ne 0 ]]
[[ $invalid_reboot_guard -ne 0 ]]

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
install -d -m 0700 "$stage/evidence"
install -d -m 0755 "$stage/bin"
install -m 0600 /dev/null "$stage/ssh-key"
install -m 0600 /dev/null "$stage/known-hosts"
calls=$stage/calls

cat >"$stage/bin/pkexec" <<'MOCK'
#!/bin/sh
set -eu
printf '%s\n' pkexec >>"$MOCK_CALLS"
MOCK
cat >"$stage/bin/git" <<'MOCK'
#!/bin/sh
set -eu
case $* in
	*"status --porcelain"*) exit 0 ;;
	*"branch --show-current"*) echo agent/linux-recovery-host ;;
	*"rev-parse HEAD"*|*"rev-parse origin/agent/linux-recovery-host"*)
		echo mock-synchronized-checkpoint
		;;
	*) exit 1 ;;
esac
MOCK
cat >"$stage/bin/scp" <<'MOCK'
#!/bin/sh
set -eu
printf '%s\n' scp >>"$MOCK_CALLS"
MOCK
cat >"$stage/bin/ssh" <<'MOCK'
#!/bin/sh
set -eu
case $* in
	*"exec env ALLOW_MAINLINE_WCN6855_GATE=1"*)
		printf '%s\n' gate >>"$MOCK_CALLS"
		echo 'PASS WCN6855 enumeration-only probe pci=17cb:1103 subsystem=17cb:0108 driver=ath11k_pci wlan=wlan0 type=managed link=not-connected nm=unmanaged addresses=0 routes=0 hci=0 storage=0 mounts=0 failed_units=0 thermal_zones=33 thermal_max_mC=41000 pstore_records=0 watchdog=disarmed'
		echo 'PASS compound WCN6855 enumeration-only gate watchdog=armed probe=passed reboot=requested'
		exit 255
		;;
	*"file_count="*) printf '%s\n' verify >>"$MOCK_CALLS" ;;
	*) printf '%s\n' prepare >>"$MOCK_CALLS" ;;
esac
MOCK
chmod 0755 "$stage/bin/git" "$stage/bin/pkexec" "$stage/bin/scp" \
	"$stage/bin/ssh"

PATH="$stage/bin:$PATH" \
MOCK_CALLS=$calls \
ALLOW_WCN6855_V1_LIVE_GATE=1 \
ALLOW_WCN6855_V1_REBOOT=1 \
SSH_KEY=$stage/ssh-key \
KNOWN_HOSTS=$stage/known-hosts \
EVIDENCE_DIR=$stage/evidence \
	"$runner" >/dev/null

[[ $(grep -Fxc pkexec "$calls") == 1 ]]
[[ $(grep -Fxc prepare "$calls") == 1 ]]
[[ $(grep -Fxc scp "$calls") == 1 ]]
[[ $(grep -Fxc verify "$calls") == 1 ]]
[[ $(grep -Fxc gate "$calls") == 1 ]]
[[ $(stat -c %a "$stage/evidence/wcn6855-v1-live-gate.log") == 600 ]]

echo 'PASS host WCN6855 v1 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries'
