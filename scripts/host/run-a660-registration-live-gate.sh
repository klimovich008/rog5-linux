#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ ${ALLOW_MAINLINE_A660_REGISTRATION_LIVE_GATE:-} == 1 ]] ||
	fail 'set ALLOW_MAINLINE_A660_REGISTRATION_LIVE_GATE=1 for the one-shot gate'
[[ ${ALLOW_MAINLINE_A660_REGISTRATION_REBOOT:-} == 1 ]] ||
	fail 'set ALLOW_MAINLINE_A660_REGISTRATION_REBOOT=1 for immediate fallback'

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
	fail 'EVIDENCE_DIR must be owned by the caller with mode 0700'

key_mode=$(stat -c %a "$ssh_key")
known_hosts_mode=$(stat -c %a "$known_hosts")
[[ $key_mode =~ ^[0-7]{3,4}$ && $known_hosts_mode =~ ^[0-7]{3,4}$ ]] ||
	fail 'credential file mode is invalid'
(( (8#$key_mode & 077) == 0 )) ||
	fail 'SSH_KEY must not be accessible to group or other users'
(( (8#$known_hosts_mode & 022) == 0 )) ||
	fail 'KNOWN_HOSTS must not be writable by group or other users'

boot_image=$repo/artifacts/network-root-a660-registration/boot-5.4.210-network-root-stage.avb.img
disarm=$repo/scripts/device/disarm-network-root-a660-watchdog.sh
gate=$repo/scripts/device/run-network-root-a660-registration-gate.sh

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
	13224d8ac0a6eafddac6554a77d08d381312ead2730268859b3a375b778b3364

pkexec --disable-internal-agent env PATH=/usr/sbin:/usr/bin:/sbin:/bin \
	"$repo/scripts/host/verify-a660-registration-export.sh" \
	/var/lib/rog5-network-root-a660-registration-v3 \
	/var/lib/rog5-network-root-v1 >/dev/null

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
directory=/run/rog5-a660-registration-control
[ ! -e "$directory" ] || {
	echo "FAIL live staging directory already exists" >&2
	exit 1
}
install -d -m 0700 "$directory"
'
ssh -n "${ssh_options[@]}" "$target" "$remote_prepare"

scp -q "${ssh_options[@]}" "$disarm" "$gate" \
	"$target:/run/rog5-a660-registration-control/"

remote_verify='
set -eu
directory=/run/rog5-a660-registration-control
chown root:root "$directory" "$directory"/*
chmod 0700 "$directory"
chmod 0500 \
	"$directory/disarm-network-root-a660-watchdog.sh" \
	"$directory/run-network-root-a660-registration-gate.sh"
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
check "$directory/run-network-root-a660-registration-gate.sh" \
	13224d8ac0a6eafddac6554a77d08d381312ead2730268859b3a375b778b3364
seal=/.rog5/root-ro/etc/rog5/a660-registration-export
[ "$(stat -c "%u:%g:%a" "$seal")" = 0:0:444 ]
grep -qx "registration_generation=v3" "$seal"
grep -qx "smmu_acceptance=ACCEPTED_IDLE_V21" "$seal"
grep -qx "smmu_reprobe=EXACT_PLATFORM_DEVICE_AT_MOST_ONCE" "$seal"
marker=/.rog5/root-ro/etc/rog5/adreno-smmu-v21-live.accepted
[ "$(stat -c "%u:%g:%a" "$marker")" = 0:0:444 ]
[ "$(sha256sum "$marker" | cut -d " " -f 1)" = \
	c5c97d92266088cb0ced1eda556faecc5c27c1e241ce3bc1ba6020431c7e9875 ]
'
ssh -n "${ssh_options[@]}" "$target" "$remote_verify"

umask 077
log=$evidence_dir/a660-registration-live-gate.log
[[ ! -e $log ]] || fail 'private live-gate log already exists'
remote_gate='exec env ALLOW_MAINLINE_A660_REGISTRATION_GATE=1 ALLOW_MAINLINE_A660_REGISTRATION_REBOOT=1 /run/rog5-a660-registration-control/run-network-root-a660-registration-gate.sh'
set +e
ssh -n "${ssh_options[@]}" "$target" "$remote_gate" 2>&1 |
	tee "$log" >/dev/null
ssh_status=${PIPESTATUS[0]}
set -e
chmod 0600 "$log"

grep -Fq 'PASS A660-registration baseline storage=0' "$log" ||
	fail 'target A660 registration baseline did not pass'
grep -Fq \
	'PASS A660 registration GPUCC=1 SMMU=1 GPU=1 GMU=1 iommu=2 render=1 drm_fds=0 firmware=0 storage=0 mounts=0 failed_units=0' \
	"$log" || fail 'target A660 registration probe did not pass'
grep -Fq 'exact_reprobe=1' "$log" ||
	fail 'target did not use the expected exact SMMU reprobe'
grep -Fq 'transition_watchdog=armed reboot=requested' "$log" ||
	fail 'target did not request guarded fallback reboot'
[[ $ssh_status -ne 0 ]] ||
	fail 'target gate returned without the expected reboot disconnect'

echo 'PASS one-shot A660 registration gate passed and requested fallback reboot; verify fallback and host cleanup separately'
