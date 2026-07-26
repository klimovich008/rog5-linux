#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ ${ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_LIVE_GATE:-} == 1 ]] ||
	fail 'set ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_LIVE_GATE=1 for the one-shot gate'
[[ ${ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_REBOOT:-} == 1 ]] ||
	fail 'set ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_REBOOT=1 for immediate fallback'

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
[[ $(stat -c '%u:%a' "$evidence_dir") == "$UID:700" ]] ||
	fail 'EVIDENCE_DIR must be owned by caller with mode 0700'

key_mode=$(stat -c %a "$ssh_key")
known_hosts_mode=$(stat -c %a "$known_hosts")
(( (8#$key_mode & 077) == 0 )) ||
	fail 'SSH_KEY must not be accessible to group or other users'
(( (8#$known_hosts_mode & 022) == 0 )) ||
	fail 'KNOWN_HOSTS must not be writable by group or other users'

boot_image=$repo/artifacts/network-root-a660-registration/boot-5.4.210-network-root-stage.avb.img
disarm=$repo/scripts/device/disarm-network-root-a660-watchdog.sh
gate=$repo/scripts/device/run-network-root-a660-ucode-allocation-v7-gate.sh
export_root=/var/lib/rog5-network-root-a660-ucode-allocation-v7

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
	f7f223b62521306007c9ac224f008c0a9e6f85fdbdcac1529bf7c8e3a9ea3d1e

pkexec --disable-internal-agent env PATH=/usr/sbin:/usr/bin:/sbin:/bin \
	"$repo/scripts/host/verify-a660-ucode-allocation-v7-export.sh" \
	"$export_root" \
	/var/lib/rog5-network-root-a660-ucode-allocation-v6 >/dev/null

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
directory=/run/rog5-a660-ucode-allocation-v7-control
[ ! -e "$directory" ] || {
	echo "FAIL live staging directory already exists" >&2
	exit 1
}
install -d -m 0700 "$directory"
'
ssh -n "${ssh_options[@]}" "$target" "$remote_prepare"

scp -q "${ssh_options[@]}" "$disarm" "$gate" \
	"$target:/run/rog5-a660-ucode-allocation-v7-control/"

remote_verify='
set -eu
directory=/run/rog5-a660-ucode-allocation-v7-control
chown root:root "$directory" "$directory"/*
chmod 0700 "$directory"
chmod 0500 \
	"$directory/disarm-network-root-a660-watchdog.sh" \
	"$directory/run-network-root-a660-ucode-allocation-v7-gate.sh"
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
check "$directory/run-network-root-a660-ucode-allocation-v7-gate.sh" \
	f7f223b62521306007c9ac224f008c0a9e6f85fdbdcac1529bf7c8e3a9ea3d1e
seal=/.rog5/root-ro/etc/rog5/a660-ucode-allocation-v7-export
[ "$(stat -c "%u:%g:%a" "$seal")" = 0:0:444 ]
[ "$(sha256sum "$seal" | cut -d " " -f 1)" = \
	c679ff6cbed6aefb28b7537cd30c561948e4d4672cd9320a8e70fd3d79b4f046 ]
grep -qx "diagnostic_generation=v7" "$seal"
grep -qx "base_export=rog5-network-root-a660-ucode-allocation-v6" "$seal"
grep -qx "predecessor=v6_live_rejected_consumed" "$seal"
grep -qx "predecessor_consumption_commit=664fd09" "$seal"
grep -qx \
	"predecessor_report_sha256=cfdd0837e6da7d06ba74e0557c6abeea396f12f02e345d9ab87ba1a47ade89e6" \
	"$seal"
grep -qx \
	"source_boundary_report_sha256=a17847d18c21d5b2c039df4353a899abce37159ec0009b5afaa0dda6067d146f" \
	"$seal"
grep -qx "compiler_policy=PINNED_MSM_RELOCATIONS" "$seal"
grep -qx "firmware_policy=SQE_GMU_ONLY_ZAP_ABSENT" "$seal"
grep -qx "open_policy=EXACTLY_ONE_EUCLEAN" "$seal"
grep -qx "size_policy=RAW_KERNEL_NEW_ENTRY_ARGUMENTS" "$seal"
grep -qx "raw_size_contract=4,4096,43288" "$seal"
grep -qx "object_size_policy=SOURCE_PINNED_PAGE_ALIGN" "$seal"
grep -qx "object_size_contract=4096,4096,45056" "$seal"
grep -qx "trace_policy=PID_FILTERED_LOGICAL_VMAP_BALANCE" "$seal"
grep -qx "state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL" "$seal"
grep -qx "v6_reuse=FORBIDDEN" "$seal"
grep -qx \
	"baseline_sha256=d8c2d697d20c213f3528d6a4cf99ca7d0243bf83222a34ff6f665ab22fc27386" \
	"$seal"
grep -qx \
	"probe_sha256=01a681bdf9fc17b3c676797cafadc43338eee49f2a5e3b7c6789edc1c7056cf0" \
	"$seal"
marker=/.rog5/root-ro/etc/rog5/a660-registration-v3-live.accepted
[ "$(stat -c "%u:%g:%a" "$marker")" = 0:0:444 ]
[ "$(sha256sum "$marker" | cut -d " " -f 1)" = \
	8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f ]
'
ssh -n "${ssh_options[@]}" "$target" "$remote_verify"

umask 077
log=$evidence_dir/a660-ucode-allocation-v7-live-gate.log
[[ ! -e $log ]] || fail 'private live-gate log already exists'
remote_gate='exec env ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_GATE=1 ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_REBOOT=1 /run/rog5-a660-ucode-allocation-v7-control/run-network-root-a660-ucode-allocation-v7-gate.sh'
set +e
ssh -n "${ssh_options[@]}" "$target" "$remote_gate" 2>&1 |
	tee "$log" >/dev/null
ssh_status=${PIPESTATUS[0]}
set -e
chmod 0600 "$log"

grep -Fq \
	'PASS A660-ucode-allocation-v7 baseline storage=0 mounts=0 firmware_files=2 firmware_requests=0 firmware_releases=0 zap=absent render=0 drm_fds=0 maps=0 unmaps=0 closes=0 gem_frees=0 failed_units=0' \
	"$log" || fail 'target ucode-allocation v7 baseline did not pass'
grep -Fq \
	'PASS A660 ucode-allocation-v7 open_invocations=1 open_errno=117 firmware_requests=2 firmware_releases=2 success_markers=1 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal zap=absent power=0 hfi=0 scm=0 drm_fds=0 storage=0 mounts=0 failed_units=0' \
	"$log" || fail 'target ucode-allocation v7 probe did not pass'
grep -Fq \
	'PASS compound A660 ucode-allocation v7 gate open_errno=117 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal transition_watchdog=armed reboot=requested' \
	"$log" || fail 'target did not request guarded fallback reboot'
[[ $ssh_status -ne 0 ]] ||
	fail 'target gate returned without expected reboot disconnect'

echo 'PASS one-shot A660 ucode-allocation v7 gate returned EUCLEAN with raw-size-pinned compiler/logical rollback evidence and requested fallback reboot; verify fallback and host cleanup separately'
