#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
runner=$repo/scripts/host/run-a660-gmu-resume-entry-v8-live-gate.sh

[[ -x $runner ]] || {
	echo 'FAIL missing host A660 GMU resume-entry v8 live-gate runner' >&2
	exit 1
}
bash -n "$runner"
ssh -G -T -F /dev/null -o ConnectionAttempts=1 localhost >/dev/null

for contract in \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_LIVE_GATE' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_REBOOT' \
	'SSH_KEY' \
	'KNOWN_HOSTS' \
	'EVIDENCE_DIR' \
	'/var/lib/rog5-network-root-a660-gmu-resume-entry-v8' \
	'verify-a660-gmu-resume-entry-v8-export.sh' \
	'pkexec --disable-internal-agent' \
	'artifacts/network-root-a660-registration/boot-5.4.210-network-root-stage.avb.img' \
	c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c \
	'disarm-network-root-a660-watchdog.sh' \
	'run-network-root-a660-gmu-resume-entry-v8-gate.sh' \
	733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc \
	62050d15c16cc3a6e4bc11bd7ad3eeee4eb5026de51c4a51d6c61762764182d8 \
	fe45a420b7241bea6dc3f37fc4beba5397221a8e27d747bd64baab0971181972 \
	'root@169.254.77.2' \
	'HostKeyAlias=rog5-network-root' \
	'StrictHostKeyChecking=yes' \
	'BatchMode=yes' \
	'ConnectionAttempts=1' \
	'ssh -n' \
	'scp -q' \
	'chmod 0500' \
	'a660-gmu-resume-entry-v8-export' \
	a6c14600ed17a52641f8700393d095e7cd86f2aa0d01c1f1f6bf649e283f2923 \
	'diagnostic_generation=v8' \
	'base_export=rog5-network-root-a660-ucode-allocation-v7' \
	'predecessor=v7_live_accepted_consumed' \
	'predecessor_consumption_commit=12ad39c' \
	'compiler_policy=PINNED_V8_MSM_RELOCATIONS' \
	'trace_policy=PID_FILTERED_GMU_ENTRY_AND_LOGICAL_VMAP' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'gmu_entry_parameter_mode=0400' \
	'v7_reuse=FORBIDDEN' \
	b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861 \
	3a4bcdcd9a96b896f22fda3be3f73c68a3b16e5d154558da9ad299c969faaf23 \
	832a96db228a9f0771c0ff364ed943100f243fbbce51ec4c0e2532e211a9e255 \
	'file_count" -eq 2' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_GATE=1' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_REBOOT=1' \
	'PASS A660 gmu-resume-entry-v8 open_invocations=1 open_errno=117 gmu_resume_entry_only=Y firmware_request_only=N ucode_allocation_only=N' \
	'adreno_load_gpu=1 runtime_resume=1 gmu_pm_resume=1 gmu_resume=1 rollback=1 outer_runtime_pm=1 inner_runtime_pm=0 clocks=0 irq=0 hfi=0 devfreq=0 llc=0 hw_init=0 scm=0' \
	'kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal' \
	'transition_watchdog=armed reboot=requested' \
	'PIPESTATUS[0]' \
	'umask 077'
do
	grep -Fq "$contract" "$runner" || {
		echo "FAIL host GMU resume-entry v8 runner omits: $contract" >&2
		exit 1
	}
done

[[ $(grep -Fc \
	'exec env ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_GATE=1' "$runner") == 1 ]]

if grep -Eq \
	'fastboot|adb|serve-network-root|exportfs|rpc[.]nfsd|rmmod|modprobe[[:space:]].*(-r|--remove)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|StrictHostKeyChecking=(no|accept-new)|UserKnownHostsFile=/dev/null' \
	"$runner"
then
	echo 'FAIL host GMU resume-entry v8 runner bypasses identity, server, or storage safety' >&2
	exit 1
fi

set +e
"$runner" >/dev/null 2>&1
missing_guards=$?
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_LIVE_GATE=1 \
	ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_REBOOT=unsafe \
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
	*"exec env ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_GATE=1"*)
		printf '%s\n' gate >>"$MOCK_CALLS"
		echo 'PASS A660-gmu-resume-entry-v8 baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 firmware_releases=0 zap=absent render=0 drm_fds=0 maps=0 unmaps=0 closes=0 gem_frees=0 runtime_resume=0 gmu_resume=0 inner_runtime_pm=0 clocks=0 irq=0 hfi=0 hw_init=0 scm=0 failed_units=0 thermal_zones=29 thermal_max_mC=38500 module_files=7 helper=exact compiler=v8-relocations watchdog=armed'
		echo 'PASS A660 gmu-resume-entry-v8 open_invocations=1 open_errno=117 gmu_resume_entry_only=Y firmware_request_only=N ucode_allocation_only=N firmware_requests=2 firmware_releases=2 entry_markers=1 rollback_markers=1 adreno_load_gpu=1 runtime_resume=1 gmu_pm_resume=1 gmu_resume=1 rollback=1 outer_runtime_pm=1 inner_runtime_pm=0 clocks=0 irq=0 hfi=0 devfreq=0 llc=0 hw_init=0 scm=0 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal zap=absent drm_fds=0 storage=0 mounts=0 failed_units=0 iommu=2 render=1 thermal_zones=29 thermal_max_mC=38500 exact_reprobe=1 driver_override=unset-null-representation watchdog=disarmed'
		echo 'PASS compound A660 GMU resume-entry v8 gate open_errno=117 gmu_resume_entry_only=Y firmware_request_only=N ucode_allocation_only=N firmware_requests=2 firmware_releases=2 gmu_resume=1 rollback=1 outer_runtime_pm=1 inner_runtime_pm=0 clocks=0 irq=0 hfi=0 devfreq=0 llc=0 hw_init=0 scm=0 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal transition_watchdog=armed reboot=requested'
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
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_LIVE_GATE=1 \
ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_REBOOT=1 \
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
	"$stage/evidence/a660-gmu-resume-entry-v8-live-gate.log") == 600 ]]

echo 'PASS host A660 GMU resume-entry v8 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries'
