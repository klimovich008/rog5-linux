#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
runner=$repo/scripts/host/run-arch-successor-v3-live-gate.sh
gate=$repo/scripts/device/run-network-root-arch-successor-v3-gate.sh
disarm=$repo/scripts/device/disarm-network-root-watchdog.sh
verify=$repo/scripts/host/verify-arch-successor-v3-export.sh

for script in "$runner" "$gate" "$disarm" "$verify"; do
	[[ -x $script ]] || {
		echo "FAIL missing Arch successor v3 live-gate control: $script" >&2
		exit 1
	}
	bash -n "$script"
done
ssh -G -T -F /dev/null -o ConnectionAttempts=1 localhost >/dev/null

gate_hash=$(sha256sum "$gate" | cut -d ' ' -f 1)
verify_hash=$(sha256sum "$verify" | cut -d ' ' -f 1)
for contract in \
	'ALLOW_ARCH_SUCCESSOR_V3_LIVE_GATE' \
	'ALLOW_ARCH_SUCCESSOR_V3_REBOOT' \
	'SSH_KEY' \
	'KNOWN_HOSTS' \
	'EVIDENCE_DIR' \
	'/var/lib/rog5-network-root-arch-successor-v3' \
	'verify-arch-successor-v3-export.sh' \
	'pkexec --disable-internal-agent' \
	'disarm-network-root-watchdog.sh' \
	'run-network-root-arch-successor-v3-gate.sh' \
	"$gate_hash" \
	"$verify_hash" \
	'b126182b615831e6f39784e4a2657cc60096ff906c26f1458be7d9a0d3ea065a' \
	'root@169.254.77.2' \
	'HostKeyAlias=rog5-arch-successor-v3' \
	'StrictHostKeyChecking=yes' \
	'BatchMode=yes' \
	'ConnectionAttempts=1' \
	'ssh -n' \
	'scp -q' \
	'chmod 0500' \
	'arch-successor-v3-export' \
	'26b4fcd8f21c5974d281d4b39386f82965265a31728c3a54877ab6717e98f2a7' \
	'a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7' \
	'ALLOW_ARCH_SUCCESSOR_V3_GATE=1' \
	'ALLOW_ARCH_SUCCESSOR_V3_REBOOT=1' \
	'PASS Arch successor v3 headless gate' \
	'power-button=active-input-present' \
	'transition_watchdog=armed reboot=requested' \
	'PIPESTATUS[0]' \
	'umask 077'
do
	grep -Fq "$contract" "$runner" || {
		echo "FAIL host Arch successor v3 runner omits: $contract" >&2
		exit 1
	}
done

[[ $(grep -Fc 'exec env ALLOW_ARCH_SUCCESSOR_V3_GATE=1' "$runner") == 1 ]]
if grep -Eq 'arch-successor-v[12]([^0-9]|$)' "$runner"; then
	echo 'FAIL host Arch successor v3 runner references a predecessor' >&2
	exit 1
fi
if grep -Eq \
	'fastboot|adb|serve-(network-root|arch-successor)|exportfs|rpc[.]nfsd|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|StrictHostKeyChecking=(no|accept-new)|UserKnownHostsFile=/dev/null' \
	"$runner"
then
	echo 'FAIL host Arch successor v3 runner bypasses server, identity, or storage safety' >&2
	exit 1
fi

set +e
"$runner" >/dev/null 2>&1
missing_guards=$?
ALLOW_ARCH_SUCCESSOR_V3_LIVE_GATE=1 \
	ALLOW_ARCH_SUCCESSOR_V3_REBOOT=unsafe \
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
	*"exec env ALLOW_ARCH_SUCCESSOR_V3_GATE=1"*)
		printf '%s\n' gate >>"$MOCK_CALLS"
		echo 'kernel=7.1.4-g7a5cef0db479'
		echo 'default_target=multi-user.target'
		echo 'server_inhibitor_state=active'
		echo 'agent_active_state=inactive'
		echo 'PASS Arch successor v3 headless gate kernel=7.1.4-g7a5cef0db479 packages=655 systemd=running coldplug=success tmpfiles=success sysusers=success agent=isolated hotspot=fail-closed-v2 power-button=active-input-present headless=1 screen=absent machine_id=volatile lower=sealed storage=0 mounts=0 failed_units=0 transition_watchdog=armed reboot=requested'
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
ALLOW_ARCH_SUCCESSOR_V3_LIVE_GATE=1 \
ALLOW_ARCH_SUCCESSOR_V3_REBOOT=1 \
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
	"$stage/evidence/arch-successor-v3-live-gate.log") == 600 ]]

echo 'PASS host Arch successor v3 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries'
