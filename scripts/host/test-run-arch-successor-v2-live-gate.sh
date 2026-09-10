#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
runner=$repo/scripts/host/run-arch-successor-v2-live-gate.sh
gate=$repo/scripts/device/run-network-root-arch-successor-v2-gate.sh
disarm=$repo/scripts/device/disarm-network-root-watchdog.sh
verify=$repo/scripts/host/verify-arch-successor-v2-export.sh

for script in "$runner" "$gate" "$disarm" "$verify"; do
	[[ -x $script ]] || {
		echo "FAIL missing Arch successor v2 live-gate control: $script" >&2
		exit 1
	}
	bash -n "$script"
done
ssh -G -T -F /dev/null -o ConnectionAttempts=1 localhost >/dev/null

gate_hash=$(sha256sum "$gate" | cut -d ' ' -f 1)
for contract in \
	'ALLOW_ARCH_SUCCESSOR_V2_LIVE_GATE' \
	'ALLOW_ARCH_SUCCESSOR_V2_REBOOT' \
	'SSH_KEY' \
	'KNOWN_HOSTS' \
	'EVIDENCE_DIR' \
	'/var/lib/rog5-network-root-arch-successor-v2' \
	'verify-arch-successor-v2-export.sh' \
	'pkexec --disable-internal-agent' \
	'disarm-network-root-watchdog.sh' \
	'run-network-root-arch-successor-v2-gate.sh' \
	"$gate_hash" \
	'b126182b615831e6f39784e4a2657cc60096ff906c26f1458be7d9a0d3ea065a' \
	'root@169.254.77.2' \
	'HostKeyAlias=rog5-arch-successor-v2' \
	'StrictHostKeyChecking=yes' \
	'BatchMode=yes' \
	'ConnectionAttempts=1' \
	'ssh -n' \
	'scp -q' \
	'chmod 0500' \
	'arch-successor-v2-export' \
	'f7c39890f2777d9d95f963bf802a09fe3cbfdb863ac9f80392a61d01867796c4' \
	'ALLOW_ARCH_SUCCESSOR_V2_GATE=1' \
	'ALLOW_ARCH_SUCCESSOR_V2_REBOOT=1' \
	'PASS Arch successor v2 headless gate' \
	'transition_watchdog=armed reboot=requested' \
	'PIPESTATUS[0]' \
	'umask 077'
do
	grep -Fq "$contract" "$runner" || {
		echo "FAIL host Arch successor v2 runner omits: $contract" >&2
		exit 1
	}
done

[[ $(grep -Fc 'exec env ALLOW_ARCH_SUCCESSOR_V2_GATE=1' "$runner") == 1 ]]
if grep -Fq 'arch-successor-v1' "$runner"; then
	echo 'FAIL host Arch successor v2 runner references v1' >&2
	exit 1
fi
if grep -Eq \
	'fastboot|adb|serve-(network-root|arch-successor)|exportfs|rpc[.]nfsd|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|StrictHostKeyChecking=(no|accept-new)|UserKnownHostsFile=/dev/null' \
	"$runner"
then
	echo 'FAIL host Arch successor v2 runner bypasses server, identity, or storage safety' >&2
	exit 1
fi

set +e
"$runner" >/dev/null 2>&1
missing_guards=$?
ALLOW_ARCH_SUCCESSOR_V2_LIVE_GATE=1 \
	ALLOW_ARCH_SUCCESSOR_V2_REBOOT=unsafe \
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
	*"exec env ALLOW_ARCH_SUCCESSOR_V2_GATE=1"*)
		printf '%s\n' gate >>"$MOCK_CALLS"
		echo 'kernel=7.1.4-g7a5cef0db479'
		echo 'default_target=multi-user.target'
		echo 'server_inhibitor_state=active'
		echo 'agent_active_state=inactive'
		echo 'PASS Arch successor v2 headless gate kernel=7.1.4-g7a5cef0db479 packages=655 systemd=running coldplug=success tmpfiles=success sysusers=success agent=isolated hotspot=fail-closed-v2 headless=1 screen=absent machine_id=volatile lower=sealed storage=0 mounts=0 failed_units=0 transition_watchdog=armed reboot=requested'
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
ALLOW_ARCH_SUCCESSOR_V2_LIVE_GATE=1 \
ALLOW_ARCH_SUCCESSOR_V2_REBOOT=1 \
SSH_KEY=$stage/ssh-key \
KNOWN_HOSTS=$stage/known-hosts \
EVIDENCE_DIR=$stage/evidence \
	"$runner" >/dev/null

[[ $(grep -Fxc pkexec "$calls") == 1 ]]
[[ $(grep -Fxc prepare "$calls") == 1 ]]
[[ $(grep -Fxc scp "$calls") == 1 ]]
[[ $(grep -Fxc verify "$calls") == 1 ]]
[[ $(grep -Fxc gate "$calls") == 1 ]]
[[ $(stat -c %a \
	"$stage/evidence/arch-successor-v2-live-gate.log") == 600 ]]

echo 'PASS host Arch successor v2 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries'
