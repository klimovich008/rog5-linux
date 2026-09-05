#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ ${ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_LIVE_GATE:-} == 1 ]] ||
	fail 'set ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_LIVE_GATE=1 for the one-shot gate'
[[ ${ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_REBOOT:-} == 1 ]] ||
	fail 'set ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_REBOOT=1 for immediate fallback'

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
ssh_key=${SSH_KEY:-}
known_hosts=${KNOWN_HOSTS:-}
evidence_dir=${EVIDENCE_DIR:-}
[[ -n $ssh_key && -n $known_hosts && -n $evidence_dir ]] ||
	fail 'set SSH_KEY, KNOWN_HOSTS, and EVIDENCE_DIR'

for command in chmod cut git grep pkexec realpath scp sha256sum ssh stat tee; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[[ -z $(git -C "$repo" status --porcelain --untracked-files=all) ]] ||
	fail 'repository must be clean before the one-shot gate'
[[ $(git -C "$repo" branch --show-current) == agent/linux-recovery-host ]] ||
	fail 'unexpected repository branch'
[[ $(git -C "$repo" rev-parse HEAD) == \
	$(git -C "$repo" rev-parse origin/agent/linux-recovery-host) ]] ||
	fail 'local and remote-tracking checkpoints differ'

ssh_key=$(realpath -e "$ssh_key")
known_hosts=$(realpath -e "$known_hosts")
evidence_dir=$(realpath -e "$evidence_dir")
[[ -f $ssh_key && ! -L $ssh_key && -r $ssh_key ]] ||
	fail 'SSH_KEY is not a readable regular file'
[[ -f $known_hosts && ! -L $known_hosts && -r $known_hosts ]] ||
	fail 'KNOWN_HOSTS is not a readable regular file'
[[ -d $evidence_dir && ! -L $evidence_dir && $evidence_dir != / ]] ||
	fail 'EVIDENCE_DIR is not a safe existing directory'
[[ $(stat -c '%u:%a' "$ssh_key") == "$UID:600" ]] ||
	fail 'SSH_KEY must be caller-owned mode 0600'
[[ $(stat -c '%u:%a' "$known_hosts") == "$UID:600" ]] ||
	fail 'KNOWN_HOSTS must be caller-owned mode 0600'
[[ $(stat -c '%u:%a' "$evidence_dir") == "$UID:700" ]] ||
	fail 'EVIDENCE_DIR must be caller-owned mode 0700'
case $ssh_key:$known_hosts:$evidence_dir in
	"$repo":*|"$repo"/*:*|*:"$repo":*|*:"$repo"/*:*|*:"$repo"|*:"$repo"/*)
		fail 'credentials and evidence must remain outside the repository'
		;;
esac

boot_image=$repo/artifacts/network-root-a660-registration/boot-5.4.210-network-root-stage.avb.img
disarm=$repo/scripts/device/disarm-network-root-a660-watchdog.sh
gate=$repo/scripts/device/run-network-root-a660-gmu-cx-runtime-pm-v10-gate.sh
export_verifier=$repo/scripts/host/verify-a660-gmu-cx-runtime-pm-v10-export.sh
export_root=/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10

verify_input() {
	local file=$1 expected=$2
	[[ -f $file && ! -L $file && -r $file ]] ||
		fail "live input is absent or linked: $file"
	[[ $(sha256sum "$file" | cut -d ' ' -f 1) == "$expected" ]] ||
		fail "live input hash mismatch: $file"
}
verify_input "$boot_image" \
	c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c
verify_input "$disarm" \
	733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc
verify_input "$gate" \
	785827f58cfde18130b4e36d5b201b93ed1232f5f4d9a41e8441cbcdcde937f4
verify_input "$export_verifier" \
	f26d67a3267f34153fb672b30bcc9cede8bc4b5bef4f011fa2a3028473601743

pkexec --disable-internal-agent env PATH=/usr/sbin:/usr/bin:/sbin:/bin \
	"$export_verifier" "$export_root" \
	/var/lib/rog5-network-root-a660-gmu-resume-entry-v9 >/dev/null

target=root@169.254.77.2
ssh_options=(
	-F /dev/null
	-i "$ssh_key"
	-o IdentitiesOnly=yes
	-o BatchMode=yes
	-o StrictHostKeyChecking=yes
	-o UserKnownHostsFile="$known_hosts"
	-o HostKeyAlias=rog5-network-root
	-o ConnectTimeout=8
	-o ConnectionAttempts=1
	-o ServerAliveInterval=5
	-o ServerAliveCountMax=2
	-o LogLevel=ERROR
)

remote_prepare='
set -eu
directory=/run/rog5-a660-gmu-cx-runtime-pm-v10-control
[ ! -e "$directory" ] || {
	echo "FAIL live staging directory already exists" >&2
	exit 1
}
install -d -m 0700 "$directory"
'
ssh -n "${ssh_options[@]}" "$target" "$remote_prepare"

scp -q "${ssh_options[@]}" "$disarm" "$gate" \
	"$target:/run/rog5-a660-gmu-cx-runtime-pm-v10-control/"

remote_verify='
set -eu
directory=/run/rog5-a660-gmu-cx-runtime-pm-v10-control
chown root:root "$directory" "$directory"/*
chmod 0700 "$directory"
chmod 0500 \
	"$directory/disarm-network-root-a660-watchdog.sh" \
	"$directory/run-network-root-a660-gmu-cx-runtime-pm-v10-gate.sh"
file_count=$(find "$directory" -mindepth 1 -maxdepth 1 -type f | wc -l)
entry_count=$(find "$directory" -mindepth 1 -maxdepth 1 | wc -l)
[ "$file_count" -eq 2 ] && [ "$entry_count" -eq 2 ]
check() {
	file=$1
	expected=$2
	[ -f "$file" ] && [ ! -L "$file" ]
	[ "$(stat -c "%u:%g:%a" "$file")" = 0:0:500 ]
	[ "$(sha256sum "$file" | cut -d " " -f 1)" = "$expected" ]
}
check "$directory/disarm-network-root-a660-watchdog.sh" \
	733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc
check "$directory/run-network-root-a660-gmu-cx-runtime-pm-v10-gate.sh" \
	785827f58cfde18130b4e36d5b201b93ed1232f5f4d9a41e8441cbcdcde937f4
seal=/.rog5/root-ro/etc/rog5/a660-gmu-cx-runtime-pm-v10-export
[ "$(stat -c "%u:%g:%a" "$seal")" = 0:0:444 ]
[ "$(sha256sum "$seal" | cut -d " " -f 1)" = \
	eaa44f2a7cef85e14d1b9dd0359b47d3cf10a5d5b05dafee77c085ce12a45cb4 ]
grep -qx "diagnostic_generation=v10" "$seal"
grep -qx "base_export=rog5-network-root-a660-gmu-resume-entry-v9" "$seal"
grep -qx "predecessor=v9_live_accepted_consumed" "$seal"
grep -qx "predecessor_consumption_commit=3d708cd" "$seal"
grep -qx \
	"module_archive_sha256=87e5c3bae7d5034b64aea7212be8372506bf8b28cbdca7fb1b79bb20db50b9d0" \
	"$seal"
grep -qx \
	"msm_module_sha256=c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d" \
	"$seal"
grep -qx \
	"trace_oracle_sha256=33ccadc6ae1e5f6f12ed83de0ddc192d30d204e229ec1b97aa813e1d0ac9c7e6" \
	"$seal"
grep -qx \
	"baseline_sha256=a68960aa1ac84dbc6f3b469d8369d1c66dcd343f9adfc0a9f4e9909e9ee4245d" \
	"$seal"
grep -qx \
	"probe_sha256=f28b1c28ec43da21747ce7e17247d33074bfa01f7c9c6171e80806a98eb70b36" \
	"$seal"
grep -qx \
	"trace_policy=PID_FILTERED_S32_EXACT_GMU_LINKED_CX_RPM_AND_LOGICAL_VMAP" \
	"$seal"
grep -qx "gmu_cx_runtime_pm_parameter_mode=0400" "$seal"
grep -qx "v9_reuse=FORBIDDEN" "$seal"
grep -qx "kernel/module delta=v10-msm-only" "$seal"
marker=/.rog5/root-ro/etc/rog5/a660-registration-v3-live.accepted
[ "$(stat -c "%u:%g:%a" "$marker")" = 0:0:444 ]
[ "$(sha256sum "$marker" | cut -d " " -f 1)" = \
	8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f ]
'
ssh -n "${ssh_options[@]}" "$target" "$remote_verify"

umask 077
log=$evidence_dir/a660-gmu-cx-runtime-pm-v10-live-gate.log
[[ ! -e $log ]] || fail 'private live-gate log already exists'
remote_gate='exec env ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_GATE=1 ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_REBOOT=1 /run/rog5-a660-gmu-cx-runtime-pm-v10-control/run-network-root-a660-gmu-cx-runtime-pm-v10-gate.sh'
set +e
ssh -n "${ssh_options[@]}" "$target" "$remote_gate" 2>&1 |
	tee "$log" >/dev/null
ssh_status=${PIPESTATUS[0]}
set -e
chmod 0600 "$log"

grep -Fq \
	'PASS A660-gmu-cx-runtime-pm-v10 baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 firmware_releases=0 zap=absent render=0 drm_fds=0' \
	"$log" || fail 'target GMU/CX runtime-PM v10 baseline did not pass'
grep -Eq \
	'^PASS A660 gmu-cx-runtime-pm-v10 open_invocations=1 open_errno=117 gmu_cx_runtime_pm_only=Y gmu_resume_entry_only=N firmware_request_only=N ucode_allocation_only=N firmware_requests=2 firmware_releases=2 .*gmu_runtime_pm=1/1 cx_runtime_pm=1/1 cx_suspend_ret=[01] generic_resume=[1-9][0-9]* generic_suspend=[1-9][0-9]* gx_runtime_pm=0 .*clocks=0 secure=0 mmio=0 irq=0 firmware_start=0 hfi=0 .*kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal .*storage=0 mounts=0 failed_units=0 .*watchdog=disarmed$' \
	"$log" || fail 'target GMU/CX runtime-PM v10 probe did not pass'
grep -Fq \
	'PASS compound A660 GMU/CX runtime-PM v10 gate open_errno=117 gmu_cx_runtime_pm_only=Y gmu_resume_entry_only=N firmware_request_only=N ucode_allocation_only=N firmware_requests=2 firmware_releases=2 gmu_resume=1 rollback=1 gpu_runtime_pm=1 gmu_runtime_pm=1/1 cx_runtime_pm=1/1 gx_runtime_pm=0 clocks=0 secure=0 mmio=0 irq=0 firmware_start=0 hfi=0 devfreq=0 llc=0 hw_init=0 scm=0 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal transition_watchdog=armed reboot=requested' \
	"$log" || fail 'target did not request guarded fallback reboot'
[[ $ssh_status -ne 0 ]] ||
	fail 'target gate returned without expected reboot disconnect'

echo 'PASS one-shot A660 GMU/CX runtime-PM v10 gate returned exact GMU/CX suspended-state evidence and requested fallback reboot; verify fallback and host cleanup separately'
