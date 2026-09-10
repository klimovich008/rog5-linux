#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ ${ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_LIVE_GATE:-} == 1 ]] ||
	fail 'set ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_LIVE_GATE=1 for the one-shot gate'
[[ ${ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_REBOOT:-} == 1 ]] ||
	fail 'set ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_REBOOT=1 for immediate fallback'

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
gate=$repo/scripts/device/run-network-root-a660-gmu-resume-entry-v9-gate.sh
export_verifier=$repo/scripts/host/verify-a660-gmu-resume-entry-v9-export.sh
export_root=/var/lib/rog5-network-root-a660-gmu-resume-entry-v9

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
	3922fdb46b587e543940b6703382568a81601fb50189f6b66231d1b62de629d2
verify_input "$export_verifier" \
	a3f526c6aa5e2f75af49a5b72b89ee24958ce23898e410e43749b482dde3179c

pkexec --disable-internal-agent env PATH=/usr/sbin:/usr/bin:/sbin:/bin \
	"$export_verifier" \
	"$export_root" \
	/var/lib/rog5-network-root-a660-gmu-resume-entry-v8 >/dev/null

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
directory=/run/rog5-a660-gmu-resume-entry-v9-control
[ ! -e "$directory" ] || {
	echo "FAIL live staging directory already exists" >&2
	exit 1
}
install -d -m 0700 "$directory"
'
ssh -n "${ssh_options[@]}" "$target" "$remote_prepare"

scp -q "${ssh_options[@]}" "$disarm" "$gate" \
	"$target:/run/rog5-a660-gmu-resume-entry-v9-control/"

remote_verify='
set -eu
directory=/run/rog5-a660-gmu-resume-entry-v9-control
chown root:root "$directory" "$directory"/*
chmod 0700 "$directory"
chmod 0500 \
	"$directory/disarm-network-root-a660-watchdog.sh" \
	"$directory/run-network-root-a660-gmu-resume-entry-v9-gate.sh"
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
check "$directory/run-network-root-a660-gmu-resume-entry-v9-gate.sh" \
	3922fdb46b587e543940b6703382568a81601fb50189f6b66231d1b62de629d2
seal=/.rog5/root-ro/etc/rog5/a660-gmu-resume-entry-v9-export
[ "$(stat -c "%u:%g:%a" "$seal")" = 0:0:444 ]
[ "$(sha256sum "$seal" | cut -d " " -f 1)" = \
	137eb101708a8f96c063ed068caf7f8265641c43c228501fc578d5076be02bd5 ]
grep -qx "diagnostic_generation=v9" "$seal"
grep -qx "base_export=rog5-network-root-a660-gmu-resume-entry-v8" "$seal"
grep -qx \
	"module_archive_sha256=38045b4c68d85d32dadf7d8db28f6ce1665fa2718ded3a9777dc0429035da6e7" \
	"$seal"
grep -qx \
	"msm_module_sha256=b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861" \
	"$seal"
grep -qx \
	"sqe_firmware_sha256=d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76" \
	"$seal"
grep -qx \
	"gmu_firmware_sha256=8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7" \
	"$seal"
grep -qx "zap=absent" "$seal"
grep -qx \
	"helper_sha256=d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae" \
	"$seal"
grep -qx \
	"trace_oracle_sha256=48325037a54fe737aa4c623a1be59f644952bd21d9f13f0bba6a6563fea6f223" \
	"$seal"
grep -qx \
	"baseline_sha256=337535cda800963bc1887203d1f60d9340b8fc5e9956f652a75bf26ada5d4ecc" \
	"$seal"
grep -qx \
	"probe_sha256=078bb4cb2e6e1edac0182a22023121f2f6fbef2ec02715b7f3f6a5fe9338f387" \
	"$seal"
grep -qx "predecessor=v8_live_rejected_consumed" "$seal"
grep -qx "predecessor_consumption_commit=ff1250f" "$seal"
grep -qx \
	"predecessor_report_sha256=fe5a6130cce3063ef6a0b1093d492d2a35763781f23af029c2959548cb092a9c" \
	"$seal"
grep -qx \
	"predecessor_seal_sha256=a6c14600ed17a52641f8700393d095e7cd86f2aa0d01c1f1f6bf649e283f2923" \
	"$seal"
grep -qx \
	"predecessor_export_verifier_sha256=fe45a420b7241bea6dc3f37fc4beba5397221a8e27d747bd64baab0971181972" \
	"$seal"
grep -qx \
	"predecessor_consumption_test_sha256=efbea8d09ecf81be8df32a0aaaffc55ecdd65209ef7fc1e1d71945a7d38180ec" \
	"$seal"
grep -qx \
	"source_boundary_report_sha256=41c06dcd895fcc873638ddf40dce0b0d5dd5bbf9e148f5d3abd5521b072c320d" \
	"$seal"
grep -qx \
	"kernel_build_report_sha256=6c50a822d30368bba4564daa77633b6e22ae1e167cd3486670b786e430153b7c" \
	"$seal"
grep -qx \
	"runtime_report_sha256=a9b99930799902cabf6c65bd877a21588b63ccb6b617d1ac526b9e0d159bf60d" \
	"$seal"
grep -qx \
	"gmu_entry_patch_sha256=a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051" \
	"$seal"
grep -qx "compiler_policy=PINNED_V8_MSM_RELOCATIONS" "$seal"
grep -qx \
	"compiler_verifier_sha256=e602f61702093050f5faba7a28c8efe54f50bf74a68369aa6096c94427389bf1" \
	"$seal"
grep -qx \
	"runtime_builder_sha256=da8b18e6c995bbc2b7402b7be6d38577911c2258c2b131304865ab55ada0cafb" \
	"$seal"
grep -qx \
	"runtime_verifier_sha256=9e3f39e60d5edb06ea50ff2673bd818029274960af0e95c84f3e438a3d1c5ef1" \
	"$seal"
grep -qx "firmware_policy=SQE_GMU_ONLY_ZAP_ABSENT" "$seal"
grep -qx "open_policy=EXACTLY_ONE_EUCLEAN" "$seal"
grep -qx "size_policy=RAW_KERNEL_NEW_ENTRY_ARGUMENTS" "$seal"
grep -qx "raw_size_contract=4,4096,43288" "$seal"
grep -qx "object_size_policy=SOURCE_PINNED_PAGE_ALIGN" "$seal"
grep -qx "object_size_contract=4096,4096,45056" "$seal"
grep -qx \
	"trace_policy=PID_FILTERED_SIGNED32_GPU_DEVICE_AND_LOGICAL_VMAP" \
	"$seal"
grep -qx "state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL" "$seal"
grep -qx "gmu_entry_parameter_mode=0400" "$seal"
grep -qx "v7_reuse=FORBIDDEN" "$seal"
grep -qx "v8_reuse=FORBIDDEN" "$seal"
marker=/.rog5/root-ro/etc/rog5/a660-registration-v3-live.accepted
[ "$(stat -c "%u:%g:%a" "$marker")" = 0:0:444 ]
[ "$(sha256sum "$marker" | cut -d " " -f 1)" = \
	8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f ]
'
ssh -n "${ssh_options[@]}" "$target" "$remote_verify"

umask 077
log=$evidence_dir/a660-gmu-resume-entry-v9-live-gate.log
[[ ! -e $log ]] || fail 'private live-gate log already exists'
remote_gate='exec env ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_GATE=1 ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9_REBOOT=1 /run/rog5-a660-gmu-resume-entry-v9-control/run-network-root-a660-gmu-resume-entry-v9-gate.sh'
set +e
ssh -n "${ssh_options[@]}" "$target" "$remote_gate" 2>&1 |
	tee "$log" >/dev/null
ssh_status=${PIPESTATUS[0]}
set -e
chmod 0600 "$log"

grep -Fq \
	'PASS A660-gmu-resume-entry-v9 baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 firmware_releases=0 zap=absent render=0 drm_fds=0 maps=0 unmaps=0 closes=0 gem_frees=0 runtime_resume=0 gmu_resume=0 inner_runtime_pm=0 clocks=0 irq=0 hfi=0 hw_init=0 scm=0 failed_units=0' \
	"$log" || fail 'target GMU resume-entry v9 baseline did not pass'
grep -Eq \
	'^PASS A660 gmu-resume-entry-v9 open_invocations=1 open_errno=117 gmu_resume_entry_only=Y firmware_request_only=N ucode_allocation_only=N firmware_requests=2 firmware_releases=2 entry_markers=1 rollback_markers=1 adreno_load_gpu=1 runtime_resume=1 gmu_pm_resume=1 gmu_resume=1 rollback=1 gpu_runtime_pm=1 generic_runtime_pm=[1-9][0-9]* inner_runtime_pm=0 clocks=0 irq=0 hfi=0 devfreq=0 llc=0 hw_init=0 scm=0 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal zap=absent drm_fds=0 storage=0 mounts=0 failed_units=0' \
	"$log" || fail 'target GMU resume-entry v9 probe did not pass'
grep -Fq \
	'PASS compound A660 GMU resume-entry v9 gate open_errno=117 gmu_resume_entry_only=Y firmware_request_only=N ucode_allocation_only=N firmware_requests=2 firmware_releases=2 gmu_resume=1 rollback=1 gpu_runtime_pm=1 generic_runtime_pm=device-classified inner_runtime_pm=0 clocks=0 irq=0 hfi=0 devfreq=0 llc=0 hw_init=0 scm=0 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal transition_watchdog=armed reboot=requested' \
	"$log" || fail 'target did not request guarded fallback reboot'
[[ $ssh_status -ne 0 ]] ||
	fail 'target gate returned without expected reboot disconnect'

echo 'PASS one-shot A660 GMU resume-entry v9 gate returned device-scoped EUCLEAN evidence with accepted compiler/logical rollback and requested fallback reboot; verify fallback and host cleanup separately'
