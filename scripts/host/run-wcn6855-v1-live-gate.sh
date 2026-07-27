#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ ${ALLOW_WCN6855_V1_LIVE_GATE:-} == 1 ]] ||
	fail 'set ALLOW_WCN6855_V1_LIVE_GATE=1 for the one-shot gate'
[[ ${ALLOW_WCN6855_V1_REBOOT:-} == 1 ]] ||
	fail 'set ALLOW_WCN6855_V1_REBOOT=1 for immediate fallback'

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

disarm=$repo/scripts/device/disarm-network-root-watchdog.sh
gate=$repo/scripts/device/run-network-root-wifi-gate.sh
export_verifier=$repo/scripts/host/verify-wcn6855-v1-export.sh
export_root=/var/lib/rog5-network-root-wcn6855-v1

verify_input() {
	local file=$1 expected=$2
	[[ -f $file && ! -L $file && -r $file ]] ||
		fail "live input is absent or linked: $file"
	[[ $(sha256sum "$file" | cut -d ' ' -f 1) == "$expected" ]] ||
		fail "live input hash mismatch: $file"
}
verify_input "$disarm" \
	b126182b615831e6f39784e4a2657cc60096ff906c26f1458be7d9a0d3ea065a
verify_input "$gate" \
	d6057b843355a17c1c4c9087c5f4e8a49b1fd0c3edf0ec7a839026ea2fe7dfbc
verify_input "$export_verifier" \
	5fcb8fb6773c9634e7a333960c1b8a354feb89ada21a1ddc558f1c74db9af078

pkexec --disable-internal-agent env PATH=/usr/sbin:/usr/bin:/sbin:/bin \
	"$export_verifier" "$export_root" >/dev/null

target=root@169.254.77.2
ssh_options=(
	-F /dev/null
	-i "$ssh_key"
	-o IdentitiesOnly=yes
	-o BatchMode=yes
	-o StrictHostKeyChecking=yes
	-o UserKnownHostsFile="$known_hosts"
	-o HostKeyAlias=rog5-wcn6855-v1
	-o ConnectTimeout=8
	-o ConnectionAttempts=1
	-o ServerAliveInterval=5
	-o ServerAliveCountMax=2
	-o LogLevel=ERROR
)

remote_prepare='
set -eu
directory=/run/rog5-wcn6855-v1-control
[ ! -e "$directory" ] || {
	echo "FAIL live staging directory already exists" >&2
	exit 1
}
install -d -m 0700 "$directory"
'
ssh -n "${ssh_options[@]}" "$target" "$remote_prepare"

scp -q "${ssh_options[@]}" "$disarm" "$gate" \
	"$target:/run/rog5-wcn6855-v1-control/"

remote_verify='
set -eu
directory=/run/rog5-wcn6855-v1-control
chown root:root "$directory" "$directory"/*
chmod 0700 "$directory"
chmod 0500 \
	"$directory/disarm-network-root-watchdog.sh" \
	"$directory/run-network-root-wifi-gate.sh"
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
check "$directory/disarm-network-root-watchdog.sh" \
	b126182b615831e6f39784e4a2657cc60096ff906c26f1458be7d9a0d3ea065a
check "$directory/run-network-root-wifi-gate.sh" \
	d6057b843355a17c1c4c9087c5f4e8a49b1fd0c3edf0ec7a839026ea2fe7dfbc
seal=/.rog5/root-ro/etc/rog5/wcn6855-v1-export
[ "$(stat -c "%u:%g:%a" "$seal")" = 0:0:444 ]
[ "$(sha256sum "$seal" | cut -d " " -f 1)" = \
	e7249141aea31d743d4d52abc14a0f870f5e57d5e379a7bfdf2963305355a310 ]
grep -qx "export_generation=wcn6855-enumeration-v1" "$seal"
grep -qx "root_overlay_sha256=4e2de54fad3476c950cfc1a97ad30d38a8d03810e66665747adc85762faa6025" \
	"$seal"
grep -qx "wifi_modules_sha256=e7a2eed91e20742012cc0a1fb893545fc61870ec94ca0ca4add3ee6c41e5300d" \
	"$seal"
grep -qx "probe_scope=ENUMERATION_ONLY_NO_SCAN_NO_ASSOCIATION_NO_AP" "$seal"
grep -qx "promotion_state=UNBOOTED_HOLD" "$seal"
inner=/.rog5/root-ro/etc/rog5/wifi-enumeration-v1
[ "$(sha256sum "$inner" | cut -d " " -f 1)" = \
	897608e6a4cf1725512ed22fc1332af680de103cf6947fd9f05dc64e20e8e9eb ]
'
ssh -n "${ssh_options[@]}" "$target" "$remote_verify"

umask 077
log=$evidence_dir/wcn6855-v1-live-gate.log
[[ ! -e $log ]] || fail 'private live-gate log already exists'
remote_gate='exec env ALLOW_MAINLINE_WCN6855_GATE=1 ALLOW_MAINLINE_WCN6855_REBOOT=1 /run/rog5-wcn6855-v1-control/run-network-root-wifi-gate.sh'
set +e
ssh -n "${ssh_options[@]}" "$target" "$remote_gate" 2>&1 |
	tee "$log" >/dev/null
ssh_status=${PIPESTATUS[0]}
set -e
chmod 0600 "$log"

grep -Eq \
	'^PASS WCN6855 enumeration-only probe pci=17cb:1103 subsystem=17cb:0108 driver=ath11k_pci wlan=wlan0 type=managed link=not-connected nm=unmanaged addresses=0 routes=0 hci=0 storage=0 mounts=0 failed_units=0 thermal_zones=[0-9]+ thermal_max_mC=-?[0-9]+ pstore_records=[0-9]+ watchdog=disarmed$' \
	"$log" || fail 'target WCN6855 enumeration-only probe did not pass'
grep -Fxq \
	'PASS compound WCN6855 enumeration-only gate watchdog=armed probe=passed reboot=requested' \
	"$log" || fail 'target WCN6855 compound gate did not pass'
[[ $ssh_status -ne 0 ]] ||
	fail 'target gate returned without expected reboot disconnect'

echo 'PASS one-shot WCN6855 v1 host gate returned exact enumeration-only evidence and requested fallback reboot; verify fallback and host cleanup separately'
