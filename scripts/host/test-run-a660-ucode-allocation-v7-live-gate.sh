#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
runner=$repo/scripts/host/run-a660-ucode-allocation-v7-live-gate.sh

[[ -x $runner ]] || {
	echo 'FAIL missing host A660 ucode-allocation v7 live-gate runner' >&2
	exit 1
}
bash -n "$runner"
ssh -G -T -F /dev/null -o ConnectionAttempts=1 localhost >/dev/null

for contract in \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_LIVE_GATE' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_REBOOT' \
	'SSH_KEY' \
	'KNOWN_HOSTS' \
	'EVIDENCE_DIR' \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v7' \
	'verify-a660-ucode-allocation-v7-export.sh' \
	'pkexec --disable-internal-agent' \
	'artifacts/network-root-a660-registration/boot-5.4.210-network-root-stage.avb.img' \
	c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c \
	'disarm-network-root-a660-watchdog.sh' \
	'run-network-root-a660-ucode-allocation-v7-gate.sh' \
	733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc \
	f7f223b62521306007c9ac224f008c0a9e6f85fdbdcac1529bf7c8e3a9ea3d1e \
	'root@169.254.77.2' \
	'HostKeyAlias=rog5-network-root' \
	'StrictHostKeyChecking=yes' \
	'BatchMode=yes' \
	'ConnectionAttempts=1' \
	'ssh -n' \
	'scp -q' \
	'chmod 0500' \
	'a660-ucode-allocation-v7-export' \
	c679ff6cbed6aefb28b7537cd30c561948e4d4672cd9320a8e70fd3d79b4f046 \
	'diagnostic_generation=v7' \
	'predecessor=v6_live_rejected_consumed' \
	'predecessor_consumption_commit=664fd09' \
	'size_policy=RAW_KERNEL_NEW_ENTRY_ARGUMENTS' \
	'raw_size_contract=4,4096,43288' \
	'object_size_policy=SOURCE_PINNED_PAGE_ALIGN' \
	'object_size_contract=4096,4096,45056' \
	'compiler_policy=PINNED_MSM_RELOCATIONS' \
	'trace_policy=PID_FILTERED_LOGICAL_VMAP_BALANCE' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'v6_reuse=FORBIDDEN' \
	d8c2d697d20c213f3528d6a4cf99ca7d0243bf83222a34ff6f665ab22fc27386 \
	01a681bdf9fc17b3c676797cafadc43338eee49f2a5e3b7c6789edc1c7056cf0 \
	'file_count" -eq 2' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_GATE=1' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_REBOOT=1' \
	'PASS A660 ucode-allocation-v7 open_invocations=1 open_errno=117 firmware_requests=2 firmware_releases=2 success_markers=1 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal zap=absent power=0 hfi=0 scm=0 drm_fds=0 storage=0 mounts=0 failed_units=0' \
	'kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal transition_watchdog=armed reboot=requested' \
	'PIPESTATUS[0]' \
	'umask 077'
do
	grep -Fq "$contract" "$runner" || {
		echo "FAIL host ucode-allocation v7 runner omits: $contract" >&2
		exit 1
	}
done

[[ $(grep -Fc \
	'exec env ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_GATE=1' "$runner") == 1 ]]

if grep -Eq \
	'fastboot|adb|serve-network-root|exportfs|rpc[.]nfsd|rmmod|modprobe[[:space:]].*(-r|--remove)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|StrictHostKeyChecking=(no|accept-new)|UserKnownHostsFile=/dev/null' \
	"$runner"
then
	echo 'FAIL host ucode-allocation v7 runner bypasses identity, server, or storage safety' >&2
	exit 1
fi

set +e
"$runner" >/dev/null 2>&1
missing_guards=$?
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_LIVE_GATE=1 \
	ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_REBOOT=unsafe \
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
	*"exec env ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_GATE=1"*)
		printf '%s\n' gate >>"$MOCK_CALLS"
		echo 'PASS A660-ucode-allocation-v7 baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 firmware_releases=0 zap=absent render=0 drm_fds=0 maps=0 unmaps=0 closes=0 gem_frees=0 failed_units=0 thermal_zones=29 thermal_max_mC=38500 module_files=7 helper=exact compiler=relocations watchdog=armed'
		echo 'PASS A660 ucode-allocation-v7 open_invocations=1 open_errno=117 firmware_requests=2 firmware_releases=2 success_markers=1 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal zap=absent power=0 hfi=0 scm=0 drm_fds=0 storage=0 mounts=0 failed_units=0 iommu=2 render=1 thermal_zones=29 thermal_max_mC=38500 exact_reprobe=1 driver_override=unset-null-representation watchdog=disarmed'
		echo 'PASS compound A660 ucode-allocation v7 gate open_errno=117 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal transition_watchdog=armed reboot=requested'
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
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_LIVE_GATE=1 \
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_REBOOT=1 \
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
	"$stage/evidence/a660-ucode-allocation-v7-live-gate.log") == 600 ]]

echo 'PASS host A660 ucode-allocation v7 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries'
