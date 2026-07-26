#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ ${ALLOW_MAINLINE_ADRENO_SMMU_LIVE_GATE:-} == 1 ]] ||
	fail 'set ALLOW_MAINLINE_ADRENO_SMMU_LIVE_GATE=1 for the one-shot gate'
[[ ${ALLOW_MAINLINE_ADRENO_SMMU_REBOOT:-} == 1 ]] ||
	fail 'set ALLOW_MAINLINE_ADRENO_SMMU_REBOOT=1 for immediate fallback'

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
ssh_key=${SSH_KEY:-}
known_hosts=${KNOWN_HOSTS:-}
evidence_dir=${EVIDENCE_DIR:-}
[[ -n $ssh_key && -n $known_hosts && -n $evidence_dir ]] ||
	fail 'set SSH_KEY, KNOWN_HOSTS, and EVIDENCE_DIR'

for command in chmod cut grep pkexec realpath scp sha256sum ssh stat tee; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done

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

module=$repo/artifacts/network-root-v18-adreno-smmu-diagnostic/gpucc-sm8350.ko
baseline=$repo/scripts/device/check-network-root-adreno-smmu-baseline.sh
disarm=$repo/scripts/device/disarm-network-root-watchdog.sh
probe=$repo/scripts/device/probe-network-root-adreno-smmu.sh
gate=$repo/scripts/device/run-network-root-adreno-smmu-gate.sh

verify_input() {
	local file=$1 expected=$2
	[[ -f $file && ! -L $file && -r $file ]] ||
		fail "live input is absent or linked: $file"
	[[ $(sha256sum "$file" | cut -d ' ' -f 1) == "$expected" ]] ||
		fail "live input hash mismatch: $file"
}
verify_input "$module" \
	9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a
verify_input "$baseline" \
	cf08ada160359b7f193b6d4d0d8eb721a95788195432a488d383c1db498771db
verify_input "$disarm" \
	b126182b615831e6f39784e4a2657cc60096ff906c26f1458be7d9a0d3ea065a
verify_input "$probe" \
	220b40676269cf36c5159a8c5fcda99512bc910c56fb2bbd28b24f745b7cb985
verify_input "$gate" \
	ba2d81c3e7f3d4ffc1a873e235f7e35dab5ce56a6c90c0de011ce06a0bae6cfe

pkexec --disable-internal-agent env PATH=/usr/sbin:/usr/bin:/sbin:/bin \
	"$repo/scripts/host/verify-adreno-smmu-export.sh" \
	/var/lib/rog5-network-root-adreno-smmu-v20 \
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
directory=/run/rog5-gpucc-diagnostic
[ ! -e "$directory" ] || {
	echo "FAIL live staging directory already exists" >&2
	exit 1
}
install -d -m 0700 "$directory"
'
ssh -n "${ssh_options[@]}" "$target" "$remote_prepare"

scp -q "${ssh_options[@]}" \
	"$module" "$baseline" "$disarm" "$probe" "$gate" \
	"$target:/run/rog5-gpucc-diagnostic/"

remote_verify='
set -eu
directory=/run/rog5-gpucc-diagnostic
chown root:root "$directory" "$directory"/*
chmod 0700 "$directory"
chmod 0400 "$directory/gpucc-sm8350.ko"
chmod 0500 \
	"$directory/check-network-root-adreno-smmu-baseline.sh" \
	"$directory/disarm-network-root-watchdog.sh" \
	"$directory/probe-network-root-adreno-smmu.sh" \
	"$directory/run-network-root-adreno-smmu-gate.sh"
file_count=$(find "$directory" -mindepth 1 -maxdepth 1 -type f | wc -l)
entry_count=$(find "$directory" -mindepth 1 -maxdepth 1 | wc -l)
[ "$file_count" -eq 5 ] && [ "$entry_count" -eq 5 ]
check() {
	file=$1
	mode=$2
	expected=$3
	[ -f "$file" ] && [ ! -L "$file" ]
	[ "$(stat -c "%u:%g:%a" "$file")" = "0:0:$mode" ]
	[ "$(sha256sum "$file" | cut -d " " -f 1)" = "$expected" ]
}
check "$directory/gpucc-sm8350.ko" 400 \
	9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a
check "$directory/check-network-root-adreno-smmu-baseline.sh" 500 \
	cf08ada160359b7f193b6d4d0d8eb721a95788195432a488d383c1db498771db
check "$directory/disarm-network-root-watchdog.sh" 500 \
	b126182b615831e6f39784e4a2657cc60096ff906c26f1458be7d9a0d3ea065a
check "$directory/probe-network-root-adreno-smmu.sh" 500 \
	220b40676269cf36c5159a8c5fcda99512bc910c56fb2bbd28b24f745b7cb985
check "$directory/run-network-root-adreno-smmu-gate.sh" 500 \
	ba2d81c3e7f3d4ffc1a873e235f7e35dab5ce56a6c90c0de011ce06a0bae6cfe
grep -qx "diagnostic_generation=v20" \
	/etc/rog5/adreno-smmu-v20-export
grep -qx "smmu_reprobe=EXACT_PLATFORM_DEVICE_ONCE" \
	/etc/rog5/adreno-smmu-v20-export
grep -qx "smmu_acceptance=NOT_ACCEPTED" \
	/etc/rog5/adreno-smmu-v20-export
'
ssh -n "${ssh_options[@]}" "$target" "$remote_verify"

umask 077
log=$evidence_dir/adreno-smmu-live-gate.log
[[ ! -e $log ]] || fail 'private live-gate log already exists'
remote_gate='exec env ALLOW_MAINLINE_ADRENO_SMMU_GATE=1 ALLOW_MAINLINE_ADRENO_SMMU_REBOOT=1 /run/rog5-gpucc-diagnostic/run-network-root-adreno-smmu-gate.sh'
set +e
ssh -n "${ssh_options[@]}" "$target" "$remote_gate" 2>&1 |
	tee "$log" >/dev/null
ssh_status=${PIPESTATUS[0]}
set -e
chmod 0600 "$log"

grep -Fq 'PASS Adreno-SMMU baseline' "$log" ||
	fail 'target baseline did not pass'
grep -Fq \
	'PASS Adreno-SMMU probe GPUCC=1 SMMU=1 runtime=suspended firmware=0 render=0 storage=0 mounts=0 failed_units=0' \
	"$log" || fail 'target Adreno-SMMU probe did not pass'
grep -Fq 'transition_watchdog=armed reboot=requested' "$log" ||
	fail 'target did not request guarded fallback reboot'
[[ $ssh_status -ne 0 ]] ||
	fail 'target gate returned without the expected reboot disconnect'

echo 'PASS one-shot Adreno-SMMU gate passed and requested fallback reboot; verify fallback and host cleanup separately'
