#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ ${ALLOW_ARCH_SUCCESSOR_V3_LIVE_GATE:-} == 1 ]] ||
	fail 'set ALLOW_ARCH_SUCCESSOR_V3_LIVE_GATE=1 for the one-shot gate'
[[ ${ALLOW_ARCH_SUCCESSOR_V3_REBOOT:-} == 1 ]] ||
	fail 'set ALLOW_ARCH_SUCCESSOR_V3_REBOOT=1 for immediate fallback'

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
gate=$repo/scripts/device/run-network-root-arch-successor-v3-gate.sh
export_verifier=$repo/scripts/host/verify-arch-successor-v3-export.sh
export_root=/var/lib/rog5-network-root-arch-successor-v3

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
	7b7b291d7972730f7914b6d23dcd41295e03e0931d51c37ba6ef7c8e0da9ba79
verify_input "$export_verifier" \
	ee301696a22565bb338781b455e5510dbb7102b1e11e1653baba9538a3282e1e

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
	-o HostKeyAlias=rog5-arch-successor-v3
	-o ConnectTimeout=8
	-o ConnectionAttempts=1
	-o ServerAliveInterval=5
	-o ServerAliveCountMax=2
	-o LogLevel=ERROR
)

remote_prepare='
set -eu
directory=/run/rog5-arch-successor-v3-control
[ ! -e "$directory" ] || {
	echo "FAIL live staging directory already exists" >&2
	exit 1
}
install -d -m 0700 "$directory"
'
ssh -n "${ssh_options[@]}" "$target" "$remote_prepare"

scp -q "${ssh_options[@]}" "$disarm" "$gate" \
	"$target:/run/rog5-arch-successor-v3-control/"

remote_verify='
set -eu
directory=/run/rog5-arch-successor-v3-control
chown root:root "$directory" "$directory"/*
chmod 0700 "$directory"
chmod 0500 \
	"$directory/disarm-network-root-watchdog.sh" \
	"$directory/run-network-root-arch-successor-v3-gate.sh"
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
check "$directory/run-network-root-arch-successor-v3-gate.sh" \
	7b7b291d7972730f7914b6d23dcd41295e03e0931d51c37ba6ef7c8e0da9ba79
seal=/.rog5/root-ro/etc/rog5/arch-successor-v3-export
[ "$(stat -c "%u:%g:%a" "$seal")" = 0:0:444 ]
[ "$(sha256sum "$seal" | cut -d " " -f 1)" = \
	26b4fcd8f21c5974d281d4b39386f82965265a31728c3a54877ab6717e98f2a7 ]
grep -qx "export_generation=arch-successor-v3" "$seal"
grep -qx "archive_sha256=a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7" \
	"$seal"
grep -qx "project_commit=b8b80013d0acd912530ce42af7bc0adf7f9fd6ea" "$seal"
grep -qx "package_count=655" "$seal"
grep -qx "power_handler_sha256=66b3a8bfc32434e450d10ea707e21481b991e6fc728cd7afa618664331b4298a" \
	"$seal"
grep -qx "power_service_sha256=c617188753e17482328f69abc55c3d2b6da62dd543ecb3a14f551c4f17fb72c7" \
	"$seal"
grep -qx "promotion_state=UNBOOTED_HOLD" "$seal"
'
ssh -n "${ssh_options[@]}" "$target" "$remote_verify"

umask 077
log=$evidence_dir/arch-successor-v3-live-gate.log
[[ ! -e $log ]] || fail 'private live-gate log already exists'
remote_gate='exec env ALLOW_ARCH_SUCCESSOR_V3_GATE=1 ALLOW_ARCH_SUCCESSOR_V3_REBOOT=1 /run/rog5-arch-successor-v3-control/run-network-root-arch-successor-v3-gate.sh'
set +e
ssh -n "${ssh_options[@]}" "$target" "$remote_gate" 2>&1 |
	tee "$log" >/dev/null
ssh_status=${PIPESTATUS[0]}
set -e
chmod 0600 "$log"

grep -Fxq 'kernel=7.1.4-g7a5cef0db479' "$log" ||
	fail 'redacted runtime collector did not report the exact kernel'
grep -Fxq 'default_target=multi-user.target' "$log" ||
	fail 'redacted runtime collector did not report headless default'
grep -Fxq 'server_inhibitor_state=active' "$log" ||
	fail 'redacted runtime collector did not report active sleep inhibitor'
grep -Fxq 'agent_active_state=inactive' "$log" ||
	fail 'redacted runtime collector did not report an on-demand agent'
grep -Eq \
	'^PASS Arch successor v3 headless gate kernel=7[.]1[.]4-g7a5cef0db479 packages=655 systemd=running coldplug=success tmpfiles=success sysusers=success agent=isolated hotspot=fail-closed-v2 power-button=active-input-present headless=1 screen=(off|absent) machine_id=volatile lower=sealed storage=0 mounts=0 failed_units=0 transition_watchdog=armed reboot=requested$' \
	"$log" || fail 'target Arch successor v3 acceptance did not pass'
[[ $ssh_status -ne 0 ]] ||
	fail 'target gate returned without expected reboot disconnect'

echo 'PASS one-shot Arch successor v3 gate returned exact headless/power-input first-boot evidence and requested fallback reboot; verify fallback and host cleanup separately'
