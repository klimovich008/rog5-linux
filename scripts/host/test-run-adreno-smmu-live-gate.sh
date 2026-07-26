#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
runner=$repo/scripts/host/run-adreno-smmu-live-gate.sh

[[ -x $runner ]] || {
	echo 'FAIL missing host Adreno-SMMU live-gate runner' >&2
	exit 1
}
bash -n "$runner"

for contract in \
	'ALLOW_MAINLINE_ADRENO_SMMU_LIVE_GATE' \
	'ALLOW_MAINLINE_ADRENO_SMMU_REBOOT' \
	'SSH_KEY' \
	'KNOWN_HOSTS' \
	'EVIDENCE_DIR' \
	'/var/lib/rog5-network-root-adreno-smmu-v18' \
	'verify-adreno-smmu-export.sh' \
	'pkexec --disable-internal-agent' \
	'artifacts/network-root-v18-adreno-smmu-diagnostic/gpucc-sm8350.ko' \
	'check-network-root-adreno-smmu-baseline.sh' \
	'disarm-network-root-watchdog.sh' \
	'probe-network-root-adreno-smmu.sh' \
	'run-network-root-adreno-smmu-gate.sh' \
	9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a \
	2385fbed96a59362cfb7d34cf1970362fcf2937eb7a238aa6628158141b4a592 \
	b126182b615831e6f39784e4a2657cc60096ff906c26f1458be7d9a0d3ea065a \
	14ef5916fdecc6ac412f8f5f7deb8121eb7c668614e4bd5b7b91ac6df96597bb \
	57aea7d0996c901deaea898d64dbd5ac5beae57518392bd0f7c5028a46469e09 \
	'root@169.254.77.2' \
	'HostKeyAlias=rog5-network-root' \
	'StrictHostKeyChecking=yes' \
	'BatchMode=yes' \
	'ConnectAttempts=1' \
	'ssh -n' \
	'scp -q' \
	'chmod 0400 "$directory/gpucc-sm8350.ko"' \
	'chmod 0500' \
	'file_count" -eq 5' \
	'ALLOW_MAINLINE_ADRENO_SMMU_GATE=1' \
	'ALLOW_MAINLINE_ADRENO_SMMU_REBOOT=1' \
	'transition_watchdog=armed reboot=requested' \
	'PIPESTATUS[0]' \
	'umask 077'
do
	grep -Fq "$contract" "$runner" || {
		echo "FAIL host Adreno-SMMU runner omits: $contract" >&2
		exit 1
	}
done

[[ $(grep -Fc 'exec env ALLOW_MAINLINE_ADRENO_SMMU_GATE=1' \
	"$runner") == 1 ]]

if grep -Eq \
	'fastboot|adb|rmmod|modprobe[[:space:]].*(-r|--remove)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|StrictHostKeyChecking=(no|accept-new)|UserKnownHostsFile=/dev/null' \
	"$runner"
then
	echo 'FAIL host Adreno-SMMU runner bypasses identity or storage safety' >&2
	exit 1
fi

set +e
"$runner" >/dev/null 2>&1
missing_guards=$?
ALLOW_MAINLINE_ADRENO_SMMU_LIVE_GATE=1 \
	ALLOW_MAINLINE_ADRENO_SMMU_REBOOT=unsafe \
	"$runner" >/dev/null 2>&1
invalid_reboot_guard=$?
set -e
[[ $missing_guards -ne 0 ]]
[[ $invalid_reboot_guard -ne 0 ]]

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
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
cat >"$stage/bin/scp" <<'MOCK'
#!/bin/sh
set -eu
printf '%s\n' scp >>"$MOCK_CALLS"
MOCK
cat >"$stage/bin/ssh" <<'MOCK'
#!/bin/sh
set -eu
case $* in
	*"exec env ALLOW_MAINLINE_ADRENO_SMMU_GATE=1"*)
		printf '%s\n' gate >>"$MOCK_CALLS"
		echo 'PASS Adreno-SMMU baseline firmware=0'
		echo 'PASS Adreno-SMMU probe GPUCC=1 SMMU=1 runtime=suspended firmware=0 render=0 storage=0 mounts=0 failed_units=0'
		echo 'PASS compound Adreno-SMMU gate transition_watchdog=armed reboot=requested'
		exit 255
		;;
	*"file_count="*)
		printf '%s\n' verify >>"$MOCK_CALLS"
		;;
	*)
		printf '%s\n' prepare >>"$MOCK_CALLS"
		;;
esac
MOCK
chmod 0755 "$stage/bin/pkexec" "$stage/bin/scp" "$stage/bin/ssh"

PATH="$stage/bin:$PATH" \
MOCK_CALLS=$calls \
ALLOW_MAINLINE_ADRENO_SMMU_LIVE_GATE=1 \
ALLOW_MAINLINE_ADRENO_SMMU_REBOOT=1 \
SSH_KEY=$stage/ssh-key \
KNOWN_HOSTS=$stage/known-hosts \
EVIDENCE_DIR=$stage/evidence \
	"$runner" >/dev/null

[[ $(grep -Fxc pkexec "$calls") == 1 ]]
[[ $(grep -Fxc prepare "$calls") == 1 ]]
[[ $(grep -Fxc scp "$calls") == 1 ]]
[[ $(grep -Fxc verify "$calls") == 1 ]]
[[ $(grep -Fxc gate "$calls") == 1 ]]
[[ $(stat -c %a "$stage/evidence/adreno-smmu-live-gate.log") == 600 ]]

echo 'PASS host live gate stages five exact tmpfs inputs, invokes once, logs privately, and never retries'
