#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
runner=$repo/scripts/host/run-a660-registration-live-gate.sh

[[ -x $runner ]] || {
	echo 'FAIL missing host A660 registration live-gate runner' >&2
	exit 1
}
bash -n "$runner"
ssh -G -T -F /dev/null -o ConnectionAttempts=1 localhost >/dev/null

for contract in \
	'ALLOW_MAINLINE_A660_REGISTRATION_LIVE_GATE' \
	'ALLOW_MAINLINE_A660_REGISTRATION_REBOOT' \
	'SSH_KEY' \
	'KNOWN_HOSTS' \
	'EVIDENCE_DIR' \
	'/var/lib/rog5-network-root-a660-registration-v3' \
	'verify-a660-registration-export.sh' \
	'pkexec --disable-internal-agent' \
	'artifacts/network-root-a660-registration/boot-5.4.210-network-root-stage.avb.img' \
	c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c \
	'disarm-network-root-a660-watchdog.sh' \
	'run-network-root-a660-registration-gate.sh' \
	733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc \
	13224d8ac0a6eafddac6554a77d08d381312ead2730268859b3a375b778b3364 \
	'root@169.254.77.2' \
	'HostKeyAlias=rog5-network-root' \
	'StrictHostKeyChecking=yes' \
	'BatchMode=yes' \
	'ConnectionAttempts=1' \
	'ssh -n' \
	'scp -q' \
	'chmod 0500' \
	'registration_generation=v3' \
	'smmu_acceptance=ACCEPTED_IDLE_V21' \
	'smmu_reprobe=EXACT_PLATFORM_DEVICE_AT_MOST_ONCE' \
	'file_count" -eq 2' \
	'ALLOW_MAINLINE_A660_REGISTRATION_GATE=1' \
	'ALLOW_MAINLINE_A660_REGISTRATION_REBOOT=1' \
	'PASS A660 registration GPUCC=1 SMMU=1 GPU=1 GMU=1 iommu=2 render=1 drm_fds=0 firmware=0 storage=0 mounts=0 failed_units=0' \
	'exact_reprobe=' \
	'transition_watchdog=armed reboot=requested' \
	'PIPESTATUS[0]' \
	'umask 077'
do
	grep -Fq "$contract" "$runner" || {
		echo "FAIL host A660 registration runner omits: $contract" >&2
		exit 1
	}
done

for rejected in \
	/var/lib/rog5-network-root-a660-registration \
	/var/lib/rog5-network-root-a660-registration-v2
do
	if grep -Fq "$rejected " "$runner"; then
		echo "FAIL host A660 registration runner accepts old root: $rejected" >&2
		exit 1
	fi
done

[[ $(grep -Fc \
	'exec env ALLOW_MAINLINE_A660_REGISTRATION_GATE=1' "$runner") == 1 ]]

if grep -Eq \
	'fastboot|adb|rmmod|modprobe[[:space:]].*(-r|--remove)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|StrictHostKeyChecking=(no|accept-new)|UserKnownHostsFile=/dev/null' \
	"$runner"
then
	echo 'FAIL host A660 registration runner bypasses identity or storage safety' >&2
	exit 1
fi

set +e
"$runner" >/dev/null 2>&1
missing_guards=$?
ALLOW_MAINLINE_A660_REGISTRATION_LIVE_GATE=1 \
	ALLOW_MAINLINE_A660_REGISTRATION_REBOOT=unsafe \
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
	*"exec env ALLOW_MAINLINE_A660_REGISTRATION_GATE=1"*)
		printf '%s\n' gate >>"$MOCK_CALLS"
		echo 'PASS A660-registration baseline storage=0'
		echo 'PASS A660 registration GPUCC=1 SMMU=1 GPU=1 GMU=1 iommu=2 render=1 drm_fds=0 firmware=0 storage=0 mounts=0 failed_units=0 exact_reprobe=1'
		echo 'PASS compound A660 registration gate transition_watchdog=armed reboot=requested'
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
chmod 0755 "$stage/bin/git" "$stage/bin/pkexec" "$stage/bin/scp" \
	"$stage/bin/ssh"

PATH="$stage/bin:$PATH" \
MOCK_CALLS=$calls \
ALLOW_MAINLINE_A660_REGISTRATION_LIVE_GATE=1 \
ALLOW_MAINLINE_A660_REGISTRATION_REBOOT=1 \
SSH_KEY=$stage/ssh-key \
KNOWN_HOSTS=$stage/known-hosts \
EVIDENCE_DIR=$stage/evidence \
	"$runner" >/dev/null

[[ $(grep -Fxc pkexec "$calls") == 1 ]]
[[ $(grep -Fxc prepare "$calls") == 1 ]]
[[ $(grep -Fxc scp "$calls") == 1 ]]
[[ $(grep -Fxc verify "$calls") == 1 ]]
[[ $(grep -Fxc gate "$calls") == 1 ]]
[[ $(stat -c %a "$stage/evidence/a660-registration-live-gate.log") == 600 ]]

echo 'PASS host A660 registration gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries'
