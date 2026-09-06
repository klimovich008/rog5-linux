#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
runner=$repo/scripts/host/run-a660-gmu-resume-entry-v9-live-gate.sh

[[ -x $runner ]] || {
	echo 'FAIL missing host A660 GMU resume-entry v9 live-gate runner' >&2
	exit 1
}
bash -n "$runner"
ssh -G -T -F /dev/null -o ConnectionAttempts=1 localhost >/dev/null

for contract in \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_LIVE_GATE' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_REBOOT' \
	'SSH_KEY' \
	'KNOWN_HOSTS' \
	'EVIDENCE_DIR' \
	'/var/lib/rog5-network-root-a660-gmu-resume-entry-v9' \
	'verify-a660-gmu-resume-entry-v9-export.sh' \
	'pkexec --disable-internal-agent' \
	'artifacts/network-root-a660-registration/boot-5.4.210-network-root-stage.avb.img' \
	c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c \
	'disarm-network-root-a660-watchdog.sh' \
	'run-network-root-a660-gmu-resume-entry-v9-gate.sh' \
	733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc \
	3922fdb46b587e543940b6703382568a81601fb50189f6b66231d1b62de629d2 \
	a3f526c6aa5e2f75af49a5b72b89ee24958ce23898e410e43749b482dde3179c \
	'root@169.254.77.2' \
	'HostKeyAlias=rog5-network-root' \
	'StrictHostKeyChecking=yes' \
	'BatchMode=yes' \
	'ConnectionAttempts=1' \
	'ssh -n' \
	'scp -q' \
	'chmod 0500' \
	'a660-gmu-resume-entry-v9-export' \
	137eb101708a8f96c063ed068caf7f8265641c43c228501fc578d5076be02bd5 \
	'diagnostic_generation=v9' \
	'base_export=rog5-network-root-a660-gmu-resume-entry-v8' \
	'predecessor=v8_live_rejected_consumed' \
	'predecessor_consumption_commit=ff1250f' \
	'compiler_policy=PINNED_V8_MSM_RELOCATIONS' \
	'trace_policy=PID_FILTERED_SIGNED32_GPU_DEVICE_AND_LOGICAL_VMAP' \
	'trace_oracle_sha256=48325037a54fe737aa4c623a1be59f644952bd21d9f13f0bba6a6563fea6f223' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'gmu_entry_parameter_mode=0400' \
	'v7_reuse=FORBIDDEN' \
	'v8_reuse=FORBIDDEN' \
	b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861 \
	337535cda800963bc1887203d1f60d9340b8fc5e9956f652a75bf26ada5d4ecc \
	078bb4cb2e6e1edac0182a22023121f2f6fbef2ec02715b7f3f6a5fe9338f387 \
	'file_count" -eq 2' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_GATE=1' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_REBOOT=1' \
	'PASS A660 gmu-resume-entry-v9 open_invocations=1 open_errno=117 gmu_resume_entry_only=Y firmware_request_only=N ucode_allocation_only=N' \
	'gpu_runtime_pm=1 generic_runtime_pm=[1-9][0-9]* inner_runtime_pm=0' \
	'kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal' \
	'generic_runtime_pm=device-classified' \
	'transition_watchdog=armed reboot=requested' \
	'PIPESTATUS[0]' \
	'umask 077'
do
	grep -Fq "$contract" "$runner" || {
		echo "FAIL host GMU resume-entry v9 runner omits: $contract" >&2
		exit 1
	}
done

[[ $(grep -Fc \
	'exec env ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_GATE=1' "$runner") == 1 ]]

if grep -Eq \
	'fastboot|adb|serve-network-root|exportfs|rpc[.]nfsd|rmmod|modprobe[[:space:]].*(-r|--remove)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|StrictHostKeyChecking=(no|accept-new)|UserKnownHostsFile=/dev/null' \
	"$runner"
then
	echo 'FAIL host GMU resume-entry v9 runner bypasses identity, server, or storage safety' >&2
	exit 1
fi

set +e
"$runner" >/dev/null 2>&1
missing_guards=$?
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_LIVE_GATE=1 \
	ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_REBOOT=unsafe \
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
	*"exec env ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_GATE=1"*)
		printf '%s\n' gate >>"$MOCK_CALLS"
		echo 'PASS A660-gmu-resume-entry-v9 baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 firmware_releases=0 zap=absent render=0 drm_fds=0 maps=0 unmaps=0 closes=0 gem_frees=0 runtime_resume=0 gmu_resume=0 inner_runtime_pm=0 clocks=0 irq=0 hfi=0 hw_init=0 scm=0 failed_units=0 thermal_zones=29 thermal_max_mC=38500 module_files=7 helper=exact compiler=v8-relocations oracle=v9-s32-device watchdog=armed'
		echo 'PASS A660 gmu-resume-entry-v9 open_invocations=1 open_errno=117 gmu_resume_entry_only=Y firmware_request_only=N ucode_allocation_only=N firmware_requests=2 firmware_releases=2 entry_markers=1 rollback_markers=1 adreno_load_gpu=1 runtime_resume=1 gmu_pm_resume=1 gmu_resume=1 rollback=1 gpu_runtime_pm=1 generic_runtime_pm=21 inner_runtime_pm=0 clocks=0 irq=0 hfi=0 devfreq=0 llc=0 hw_init=0 scm=0 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal zap=absent drm_fds=0 storage=0 mounts=0 failed_units=0 iommu=2 render=1 thermal_zones=29 thermal_max_mC=38500 exact_reprobe=1 driver_override=unset-null-representation watchdog=disarmed'
		echo 'PASS compound A660 GMU resume-entry v9 gate open_errno=117 gmu_resume_entry_only=Y firmware_request_only=N ucode_allocation_only=N firmware_requests=2 firmware_releases=2 gmu_resume=1 rollback=1 gpu_runtime_pm=1 generic_runtime_pm=device-classified inner_runtime_pm=0 clocks=0 irq=0 hfi=0 devfreq=0 llc=0 hw_init=0 scm=0 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal transition_watchdog=armed reboot=requested'
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
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_LIVE_GATE=1 \
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_REBOOT=1 \
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
	"$stage/evidence/a660-gmu-resume-entry-v9-live-gate.log") == 600 ]]

echo 'PASS host A660 GMU resume-entry v9 gate stages two exact tmpfs inputs, invokes once, accepts device-classified generic PM, logs privately, and never retries'
