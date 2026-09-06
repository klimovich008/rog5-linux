#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
runner=$repo/scripts/host/run-a660-gmu-cx-runtime-pm-v10-live-gate.sh

[[ -x $runner ]] || {
	echo 'FAIL missing host A660 GMU/CX runtime-PM v10 live-gate runner' >&2
	exit 1
}
bash -n "$runner"
ssh -G -T -F /dev/null -o ConnectionAttempts=1 localhost >/dev/null

for contract in \
	'ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_LIVE_GATE' \
	'ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_REBOOT' \
	'SSH_KEY' \
	'KNOWN_HOSTS' \
	'EVIDENCE_DIR' \
	'/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10' \
	'verify-a660-gmu-cx-runtime-pm-v10-export.sh' \
	'pkexec --disable-internal-agent' \
	'artifacts/network-root-a660-registration/boot-5.4.210-network-root-stage.avb.img' \
	c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c \
	'disarm-network-root-a660-watchdog.sh' \
	'run-network-root-a660-gmu-cx-runtime-pm-v10-gate.sh' \
	'root@169.254.77.2' \
	'HostKeyAlias=rog5-network-root' \
	'StrictHostKeyChecking=yes' \
	'BatchMode=yes' \
	'ConnectionAttempts=1' \
	'ssh -n' \
	'scp -q' \
	'chmod 0500' \
	'a660-gmu-cx-runtime-pm-v10-export' \
	'diagnostic_generation=v10' \
	'base_export=rog5-network-root-a660-gmu-resume-entry-v9' \
	'predecessor=v9_live_accepted_consumed' \
	'predecessor_consumption_commit=3d708cd' \
	'kernel/module delta=v10-msm-only' \
	'gmu_cx_runtime_pm_parameter_mode=0400' \
	c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d \
	a68960aa1ac84dbc6f3b469d8369d1c66dcd343f9adfc0a9f4e9909e9ee4245d \
	f28b1c28ec43da21747ce7e17247d33074bfa01f7c9c6171e80806a98eb70b36 \
	'file_count" -eq 2' \
	'ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_GATE=1' \
	'ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_REBOOT=1' \
	'PASS A660 gmu-cx-runtime-pm-v10 open_invocations=1 open_errno=117' \
	'gmu_runtime_pm=1/1 cx_runtime_pm=1/1' \
	'gx_runtime_pm=0' \
	'clocks=0 secure=0 mmio=0 irq=0 firmware_start=0 hfi=0' \
	'transition_watchdog=armed reboot=requested' \
	'PIPESTATUS[0]' \
	'umask 077'
do
	grep -Fq "$contract" "$runner" || {
		echo "FAIL host GMU/CX v10 runner omits: $contract" >&2
		exit 1
	}
done

[[ $(grep -Fc \
	'exec env ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_GATE=1' \
	"$runner") == 1 ]]
if grep -Eq \
	'fastboot|adb|serve-network-root|exportfs|rpc[.]nfsd|rmmod|modprobe[[:space:]].*(-r|--remove)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|StrictHostKeyChecking=(no|accept-new)|UserKnownHostsFile=/dev/null' \
	"$runner"
then
	echo 'FAIL host GMU/CX v10 runner bypasses identity, server, or storage safety' >&2
	exit 1
fi

set +e
"$runner" >/dev/null 2>&1
missing_guards=$?
ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_LIVE_GATE=1 \
	ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_REBOOT=unsafe \
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
	*"exec env ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_GATE=1"*)
		printf '%s\n' gate >>"$MOCK_CALLS"
		echo 'PASS A660-gmu-cx-runtime-pm-v10 baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 firmware_releases=0 zap=absent render=0 drm_fds=0 gmu_runtime_pm=0 cx_runtime_pm=0 gx_runtime_pm=0 clocks=0 secure=0 mmio=0 irq=0 firmware_start=0 hfi=0 failed_units=0'
		echo 'PASS A660 gmu-cx-runtime-pm-v10 open_invocations=1 open_errno=117 gmu_cx_runtime_pm_only=Y gmu_resume_entry_only=N firmware_request_only=N ucode_allocation_only=N firmware_requests=2 firmware_releases=2 gmu_runtime_pm=1/1 cx_runtime_pm=1/1 cx_suspend_ret=0 generic_resume=4 generic_suspend=2 gx_runtime_pm=0 clocks=0 secure=0 mmio=0 irq=0 firmware_start=0 hfi=0 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal storage=0 mounts=0 failed_units=0 watchdog=disarmed'
		echo 'PASS compound A660 GMU/CX runtime-PM v10 gate open_errno=117 gmu_cx_runtime_pm_only=Y gmu_resume_entry_only=N firmware_request_only=N ucode_allocation_only=N firmware_requests=2 firmware_releases=2 gmu_resume=1 rollback=1 gpu_runtime_pm=1 gmu_runtime_pm=1/1 cx_runtime_pm=1/1 gx_runtime_pm=0 clocks=0 secure=0 mmio=0 irq=0 firmware_start=0 hfi=0 devfreq=0 llc=0 hw_init=0 scm=0 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal transition_watchdog=armed reboot=requested'
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
ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_LIVE_GATE=1 \
ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_REBOOT=1 \
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
	"$stage/evidence/a660-gmu-cx-runtime-pm-v10-live-gate.log") == 600 ]]

echo 'PASS host A660 GMU/CX runtime-PM v10 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries'
