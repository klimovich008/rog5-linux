#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=generated-power-usb-active.sh
source "$script_dir/generated-power-usb-active.sh"

deployment_profile=historical-headless-network-root-v1
candidate_record=
candidate_sha256=
runtime_candidate=headless-network-root-v1
diagnostic_profile=0
power_usb_profile=0
case $# in
	0) ;;
	3)
		deployment_profile=$1
		candidate_record=$2
		candidate_sha256=$3
		case $deployment_profile in
			headless-ssh-deployment-v3)
				runtime_candidate=headless-ssh-network-root-v3
				;;
			diagnostic-initramfs-v1)
				runtime_candidate=headless-netroot-early-diag-v2
				diagnostic_profile=1
				;;
			headless-core-deployment-v1)
				runtime_candidate=headless-core-network-root-v2
				;;
			"$POWER_USB_RUNTIME_PROFILE")
				runtime_candidate=$POWER_USB_CANDIDATE
				power_usb_profile=1
				;;
			*) fail 'unsupported runtime deployment profile' ;;
		esac
		[[ $candidate_sha256 =~ ^[0-9a-f]{64}$ &&
			$candidate_sha256 != \
			0000000000000000000000000000000000000000000000000000000000000000 ]] ||
			fail 'deployment candidate identity is invalid'
		;;
	*) fail "usage: run-minimal-headless-runtime-acceptance.sh [headless-ssh-deployment-v3|headless-core-deployment-v1|diagnostic-initramfs-v1|$POWER_USB_RUNTIME_PROFILE CANDIDATE_RECORD CANDIDATE_SHA256]" ;;
esac

[[ ${ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE:-} == 1 ]] ||
	fail 'set ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE=1 for one observation'

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
for command in awk chmod cut git grep realpath sha256sum ssh stat tee timeout; do
	command -v "$command" >/dev/null ||
		fail "missing runtime-acceptance host command: $command"
done
[[ -z $(git -C "$repo" status --porcelain --untracked-files=all) ]] ||
	fail 'repository must be clean before runtime acceptance'
branch=$(git -C "$repo" branch --show-current)
[[ -n $branch ]] || fail 'repository is not on a branch'
upstream=$(git -C "$repo" rev-parse --abbrev-ref --symbolic-full-name '@{u}')
[[ $upstream == "origin/$branch" ]] ||
	fail 'runtime-acceptance branch does not track its origin peer'
git -C "$repo" fetch --no-tags --prune origin \
	"refs/heads/$branch:refs/remotes/origin/$branch"
[[ $(git -C "$repo" rev-parse HEAD) == \
	$(git -C "$repo" rev-parse "$upstream") ]] ||
	fail 'local and remote-tracking checkpoints differ'

if [[ $deployment_profile != historical-headless-network-root-v1 ]]; then
	[[ $candidate_record == /* && ! -L $candidate_record ]] ||
		fail 'deployment candidate path must be absolute and canonical'
	candidate_lexical=$candidate_record
	candidate_record=$(realpath -e "$candidate_record")
	[[ $candidate_record == "$candidate_lexical" ]] ||
		fail 'deployment candidate path must be absolute and canonical'
	[[ -f $candidate_record && ! -L $candidate_record &&
		-r $candidate_record ]] ||
		fail 'deployment candidate is not a readable regular file'
	case $(stat -c '%u:%a:%h' "$candidate_record") in
		"$UID":400:1|"$UID":444:1) ;;
		*) fail 'deployment candidate must be caller-owned, singly linked, and mode 0400 or 0444' ;;
	esac
	case $candidate_record in
		"$repo"|"$repo"/*)
			fail 'deployment candidate must remain outside the repository'
			;;
	esac
	[[ $(sha256sum "$candidate_record" | cut -d ' ' -f 1) == \
		"$candidate_sha256" ]] ||
		fail 'deployment candidate identity changed'
fi

ssh_key=${SSH_KEY:-}
known_hosts=${TARGET_KNOWN_HOSTS:-}
evidence_dir=${EVIDENCE_DIR:-}
[[ -n $ssh_key && -n $known_hosts && -n $evidence_dir ]] ||
	fail 'set SSH_KEY, TARGET_KNOWN_HOSTS, and EVIDENCE_DIR'

ssh_key=$(realpath -e "$ssh_key")
known_hosts=$(realpath -e "$known_hosts")
evidence_dir=$(realpath -e "$evidence_dir")
[[ -f $ssh_key && ! -L $ssh_key && -r $ssh_key ]] ||
	fail 'SSH_KEY is not a readable regular file'
[[ -f $known_hosts && ! -L $known_hosts && -r $known_hosts ]] ||
	fail 'TARGET_KNOWN_HOSTS is not a readable regular file'
[[ -d $evidence_dir && ! -L $evidence_dir && $evidence_dir != / ]] ||
	fail 'EVIDENCE_DIR is not a safe existing directory'
[[ $(stat -c '%u:%a' "$ssh_key") == "$UID:600" ]] ||
	fail 'SSH_KEY must be caller-owned mode 0600'
[[ $(stat -c '%u:%a' "$known_hosts") == "$UID:600" ]] ||
	fail 'TARGET_KNOWN_HOSTS must be caller-owned mode 0600'
[[ $(stat -c '%u:%a' "$evidence_dir") == "$UID:700" ]] ||
	fail 'EVIDENCE_DIR must be caller-owned mode 0700'
case $ssh_key:$known_hosts:$evidence_dir in
	"$repo":*|"$repo"/*:*|*:"$repo":*|*:"$repo"/*:*|*:"$repo"|*:"$repo"/*)
		fail 'credentials and evidence must remain outside the repository'
		;;
esac

probe=$repo/scripts/device/collect-minimal-headless-runtime.sh
verifier=$repo/scripts/host/verify-minimal-headless-runtime.py
for input in "$probe" "$verifier"; do
	[[ -f $input && ! -L $input && -x $input ]] ||
		fail "runtime-acceptance input is unsafe: ${input#"$repo"/}"
done
probe_hash=$(sha256sum "$probe" | cut -d ' ' -f 1)
[[ $probe_hash =~ ^[0-9a-f]{64}$ ]] ||
	fail 'runtime probe hash is invalid'

target=root@169.254.77.2
ssh_options=(
	-F /dev/null
	-i "$ssh_key"
	-o IdentitiesOnly=yes
	-o BatchMode=yes
	-o StrictHostKeyChecking=yes
	-o UserKnownHostsFile="$known_hosts"
	-o HostKeyAlias=rog5-minimal-headless-v1
	-o ConnectTimeout=8
	# OpenSSH retries only before the remote command starts. An established
	# session is never replayed, and the fresh /run directory rejects residue.
	-o ConnectionAttempts=3
	-o ServerAliveInterval=5
	-o ServerAliveCountMax=2
	-o LogLevel=ERROR
)
remote_directory=/run/rog5-minimal-headless-runtime-control
remote_probe=$remote_directory/collect-minimal-headless-runtime.sh
remote_exec=exec
diagnostic_completion=
if [[ $diagnostic_profile == 1 ]]; then
	remote_exec=
	diagnostic_completion='/run/initramfs/sbin/rog5-early-target-diag emit 150'
fi

remote_stage_verify_and_collect="
set -eu
directory=$remote_directory
file=$remote_probe
[ \"\$(uname -r)\" = 7.1.4-g7a5cef0db479 ] || {
	echo 'FAIL unexpected target kernel' >&2
	exit 1
}
test ! -e \"\$directory\" || {
	echo 'FAIL runtime probe staging directory already exists' >&2
	exit 1
}
install -d -m 0700 \"\$directory\"
umask 077
cat >\"\$file\"
chown root:root \"\$file\"
chmod 0500 \"\$file\"
[ -f \"\$file\" ] && [ ! -L \"\$file\" ]
[ \"\$(stat -c '%u:%g:%a' \"\$file\")\" = 0:0:500 ]
[ \"\$(sha256sum \"\$file\" | cut -d ' ' -f 1)\" = $probe_hash ]
$remote_exec env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin \
	ROG5_RUNTIME_CANDIDATE='$runtime_candidate' \
	ROG5_RUNTIME_ALLOWED_CANDIDATE='$runtime_candidate' \
	ROG5_RUNTIME_USB_PROFILE='$diagnostic_profile' \"\$file\"
$diagnostic_completion
"

umask 077
record=$evidence_dir/minimal-headless-runtime.record
[[ ! -e $record ]] || fail 'private runtime record already exists'
set +e
ssh -T "${ssh_options[@]}" "$target" \
	"$remote_stage_verify_and_collect" <"$probe" |
	tee "$record" >/dev/null
ssh_status=${PIPESTATUS[0]}
set -e
chmod 0600 "$record"
[[ $ssh_status == 0 ]] || fail 'target runtime probe failed'
boot_id=$(
	awk '
		/^boot_id=/ {
			count++
			value = substr($0, 9)
		}
		END {
			if (count != 1)
				exit 1
			print value
		}
	' "$record"
) || fail 'target runtime record lacks one boot identity'
[[ $boot_id =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] ||
	fail 'exact minimal-headless target boot identity did not appear'

verifier_arguments=(
	--repo "$repo"
	--record "$record"
	--expected-boot-id "$boot_id"
)
if [[ $deployment_profile != historical-headless-network-root-v1 ]]; then
	verifier_arguments+=(
		--deployment-profile "$deployment_profile"
		--candidate-record "$candidate_record"
		--candidate-sha256 "$candidate_sha256"
	)
fi
"$verifier" "${verifier_arguments[@]}"

if [[ $power_usb_profile == 1 ]]; then
	power_record=$evidence_dir/power-usb-observation.log
	[[ ! -e $power_record ]] || fail 'private power/USB observation already exists'
	remote_power_probe='
set -eu
probe=/run/initramfs/sbin/rog5-early-charging-probe
[ -f "$probe" ] && [ ! -L "$probe" ] && [ -x "$probe" ]
[ "$(stat -c "%u:%g:%a" "$probe")" = 0:0:755 ]
exec env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin \
	ALLOW_NETWORK_ROOT_BATTERY_PROBE=1 \
	ALLOW_NETWORK_ROOT_CHARGING_PROBE=1 \
	ROG5_BATTERY_INPUT_DIR=/run/initramfs/rog5-charge-inputs \
	ROG5_PROBE_TIMEOUT=150 ROG5_PROBE_SETTLE=20 \
	ROG5_TELEMETRY_WAIT=30 "$probe" charging
'
	set +e
	timeout --signal=TERM 180 ssh -T "${ssh_options[@]}" "$target" \
		"$remote_power_probe" </dev/null | tee "$power_record" >/dev/null
	power_status=${PIPESTATUS[0]}
	set -e
	chmod 0600 "$power_record"
	[[ $power_status == 0 ]] || fail 'target power/USB probe failed'
	[[ $(grep -Fxc 'PASS battery-telemetry mode=charging stayed RAM-only, storage-isolated, full-UCSI, explicit-write-free, and rollback-guarded' "$power_record") == 1 ]] ||
		fail 'target power/USB probe lacks its exact success marker'
	[[ $(grep -c '^EVIDENCE typec_port_count=' "$power_record") == 1 &&
		$(grep -c '^EVIDENCE capacity_percent=' "$power_record") == 1 &&
		$(grep -c '^EVIDENCE final_voltage_uV=' "$power_record") == 1 ]] ||
		fail 'target power/USB evidence is incomplete'
fi

echo 'PASS one exact minimal-headless runtime observation was verified privately; rollback watchdog remains armed and no reboot was requested'
