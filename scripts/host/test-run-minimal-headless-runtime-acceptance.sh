#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
runner=$repo/scripts/host/run-minimal-headless-runtime-acceptance.sh
probe=$repo/scripts/device/collect-minimal-headless-runtime.sh
verifier=$repo/scripts/host/verify-minimal-headless-runtime.py

for input in "$runner" "$probe" "$verifier"; do
	[[ -f $input && ! -L $input && -x $input ]] || {
		echo "FAIL missing runtime-acceptance input: $input" >&2
		exit 1
	}
done
bash -n "$runner"
sh -n "$probe"

for token in \
	ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE \
	SSH_KEY \
	TARGET_KNOWN_HOSTS \
	EVIDENCE_DIR \
	'git -C "$repo" status --porcelain --untracked-files=all' \
	'origin/$branch' \
	'StrictHostKeyChecking=yes' \
	'HostKeyAlias=rog5-minimal-headless-v1' \
	'ConnectionAttempts=3' \
	'root@169.254.77.2' \
	'/run/rog5-minimal-headless-runtime-control' \
	'collect-minimal-headless-runtime.sh' \
	'verify-minimal-headless-runtime.py' \
	'historical-headless-network-root-v1' \
	'headless-ssh-deployment-v3' \
	'headless-ssh-network-root-v3' \
	'--deployment-profile' \
	'--candidate-record' \
	'--candidate-sha256' \
	"ROG5_RUNTIME_CANDIDATE='\$runtime_candidate'" \
	'exec env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin' \
	'remote_stage_verify_and_collect=' \
	'[ \"\$(uname -r)\" = 7.1.4-g7a5cef0db479 ]' \
	'ssh -T "${ssh_options[@]}" "$target"' \
	'"$remote_stage_verify_and_collect" <"$probe"' \
	'PIPESTATUS[0]' \
	'rollback watchdog remains armed' \
	'no reboot was requested'; do
	grep -Fq -- "$token" "$runner" || {
		echo "FAIL runtime-acceptance runner omits: $token" >&2
		exit 1
	}
done

if grep -Eq \
	'fastboot|adb|StrictHostKeyChecking=(no|accept-new)|UserKnownHostsFile=/dev/null|systemctl[[:space:]]+reboot|disarm-network-root-watchdog|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|ssh-keygen|openssl' \
	"$runner"; then
	echo 'FAIL runtime-acceptance runner expands transport, trust, or mutation authority' >&2
	exit 1
fi
[[ $(grep -Fc 'ssh -T "${ssh_options[@]}" "$target"' \
	"$runner") == 1 ]]
! grep -Eq '(^|[[:space:]])scp([[:space:]]|$)' "$runner"

set +e
"$runner" >/dev/null 2>&1
missing_guard=$?
ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE=unsafe \
	"$runner" >/dev/null 2>&1
invalid_guard=$?
set -e
[[ $missing_guard -ne 0 && $invalid_guard -ne 0 ]]

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
install -d -m 0700 "$stage/evidence"
install -d -m 0755 "$stage/bin"
install -m 0600 /dev/null "$stage/ssh-key"
install -m 0600 /dev/null "$stage/known-hosts"
calls=$stage/calls
probe_hash=$(sha256sum "$probe" | cut -d ' ' -f 1)
record=$stage/golden.record
cat >"$record" <<EOF
format=rog5-minimal-headless-runtime-v1
profile=minimal-headless-v1
execution_mode=live
probe_sha256=$probe_hash
active_capabilities=cpu-ram,init-key-only-ssh,read-only-network-root,thermal-readonly,usb-ncm-network,watchdog-rollback-reboot
candidate=headless-network-root-v1
boot_id=7d9a6f34-0e4a-4d4e-9d24-0b1f6c7215a8
kernel_release=7.1.4-g7a5cef0db479
machine=aarch64
pid1=systemd
system_state=running
default_target=multi-user.target
cpu_online_count=8
cpu_online_set=0-7
cpu_present_set=0-7
cpufreq_policy_count=3
cpufreq_policy_names=policy0;policy4;policy7
cpufreq_policy_cpu_sets=0 1 2 3;4 5 6;7
cpufreq_policy_drivers=qcom-cpufreq-hw;qcom-cpufreq-hw;qcom-cpufreq-hw
cpufreq_policy_governors=schedutil;schedutil;schedutil
memory_total_kib=11900000
memory_available_kib=10949632
overlay_mount_id=101
overlay_lower_mount_id=102
state_mount_id=103
overlay_lowerdir=/mnt/root-ro
overlay_upperdir=/mnt/state/upper
overlay_workdir=/mnt/state/work
root_fstype=overlay
lower_fstype=nfs4
lower_source=169.254.77.1:/
lower_nfs_version=4.2
lower_transport=tcp
lower_read_only=1
state_fstype=tmpfs
state_nodev=1
state_nosuid=1
block_device_count=0
physical_block_devices=0
scsi_host_count=0
rpmb_device_count=0
ufs_platform_device_count=0
block_backed_mounts=0
usb_gadget=rog5-network-root
usb_vid_pid=1d6b:0104
usb_product=ROG5 network root
usb_configuration=NFS root over NCM
usb_function=ncm.usb0
usb_udc_controller=a600000
usb_current_speed=high-speed
usb_interface=usb0
usb_carrier=1
usb_operstate=up
usb_mtu=1500
usb_ipv4_cidr=169.254.77.2/30
usb_route_cidr=169.254.77.0/30
usb_default_route_count=0
sshd_state=active
ssh_port=22
ssh_session_count=1
ssh_session_local=169.254.77.2:22
ssh_session_peer=169.254.77.1
ssh_authorized_key_type=ssh-ed25519
ssh_authorized_key_bits=256
ssh_host_key_type=ssh-ed25519
ssh_host_key_bits=256
ssh_host_key_pair_match=1
ssh_auth=key-only
server_inhibitor_state=active
failed_units=0
fatal_kernel_signatures=0
thermal_zone_count=33
thermal_min_millidegree_c=32000
thermal_max_millidegree_c=37000
watchdog_state=armed
watchdog_timeout_seconds=600
watchdog_remaining_seconds=300
network_root_identity_format=rog5-network-root-identity-v1
root_generation=arch-a
root_tree_sha256=7c35d2b75f09722afd4fa59135f4327a29c4d612441b1e165908f4777b458afb
root_seal_sha256=6cd986cae4918effc236d28ee50344032795853b546296a94e9431508fa32896
root_seal_file_sha256=6cd986cae4918effc236d28ee50344032795853b546296a94e9431508fa32896
root_tree_entries=37669
root_subtree=/
command_manifest_sha256=99f194b32171c9c9f09d28636e351bba4cb34751997e1aa174e3466bd758a1d2
command_manifest_format=rog5-headless-command-manifest-v1
workload=none
result=PASS
EOF

cat >"$stage/bin/git" <<'EOF'
#!/bin/sh
case $* in
	*"status --porcelain"*) exit 0 ;;
	*"branch --show-current"*) echo agent/linux-recovery-host ;;
	*"rev-parse --abbrev-ref --symbolic-full-name @{u}"*)
		echo origin/agent/linux-recovery-host
		;;
	*"rev-parse HEAD"*|*"rev-parse origin/agent/linux-recovery-host"*)
		echo synchronized-checkpoint
		;;
	*) exit 1 ;;
esac
EOF
cat >"$stage/bin/ssh" <<'EOF'
#!/bin/sh
received=$(sha256sum | cut -d ' ' -f 1)
[ "$received" = "$MOCK_PROBE_HASH" ] || exit 96
printf '%s\n' collect >>"$MOCK_CALLS"
cat "$MOCK_RECORD"
EOF
chmod 0755 "$stage/bin/git" "$stage/bin/ssh"

output=$(
	PATH="$stage/bin:$PATH" \
	MOCK_CALLS="$calls" \
	MOCK_RECORD="$record" \
	MOCK_PROBE_HASH="$probe_hash" \
	ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE=1 \
	SSH_KEY="$stage/ssh-key" \
	TARGET_KNOWN_HOSTS="$stage/known-hosts" \
	EVIDENCE_DIR="$stage/evidence" \
		"$runner"
)
grep -Fq 'PASS minimal headless runtime acceptance' <<<"$output"
grep -Fq 'rollback watchdog remains armed' <<<"$output"
[[ $(grep -Fxc collect "$calls") == 1 ]]
[[ $(wc -l <"$calls") == 1 ]]
[[ $(stat -c %a "$stage/evidence/minimal-headless-runtime.record") == 600 ]]
cmp "$record" "$stage/evidence/minimal-headless-runtime.record"

candidate=$stage/headless-ssh-network-root-v3.json
sed \
	-e 's/6f8a8f11bfb581bb52ca7d590141ce465b8d48d8f9f4577a076b7a37604a2fd5/4444444444444444444444444444444444444444444444444444444444444444/' \
	-e 's/f443a47c456b33d670e6efd4a2e20cff2bc72061e7661472694acfbba45c8d5a/5555555555555555555555555555555555555555555555555555555555555555/' \
	-e 's/"root_tree_entries": "37735"/"root_tree_entries": "37736"/' \
	"$repo/configs/recovery-candidates/headless-ssh-network-root-v3.json" \
	>"$candidate"
chmod 0400 "$candidate"
candidate_sha256=$(sha256sum "$candidate" | cut -d ' ' -f 1)

deployment_record=$stage/deployment-golden.record
sed \
	-e 's/candidate=headless-network-root-v1/candidate=headless-ssh-network-root-v3/' \
	-e 's/7c35d2b75f09722afd4fa59135f4327a29c4d612441b1e165908f4777b458afb/4444444444444444444444444444444444444444444444444444444444444444/' \
	-e 's/6cd986cae4918effc236d28ee50344032795853b546296a94e9431508fa32896/5555555555555555555555555555555555555555555555555555555555555555/g' \
	-e 's/root_tree_entries=37669/root_tree_entries=37736/' \
	"$record" >"$deployment_record"
install -d -m 0700 "$stage/evidence-v3"
: >"$calls"
deployment_output=$(
	PATH="$stage/bin:$PATH" \
	MOCK_CALLS="$calls" \
	MOCK_RECORD="$deployment_record" \
	MOCK_PROBE_HASH="$probe_hash" \
	ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE=1 \
	SSH_KEY="$stage/ssh-key" \
	TARGET_KNOWN_HOSTS="$stage/known-hosts" \
	EVIDENCE_DIR="$stage/evidence-v3" \
		"$runner" headless-ssh-deployment-v3 \
		"$candidate" "$candidate_sha256"
)
grep -Fq 'PASS minimal headless runtime acceptance' \
	<<<"$deployment_output"
grep -Fq 'rollback watchdog remains armed' <<<"$deployment_output"
[[ $(grep -Fxc collect "$calls") == 1 ]]
[[ $(wc -l <"$calls") == 1 ]]
cmp "$deployment_record" \
	"$stage/evidence-v3/minimal-headless-runtime.record"

install -d -m 0700 "$stage/evidence-transfer-failure"
: >"$calls"
set +e
PATH="$stage/bin:$PATH" \
MOCK_CALLS="$calls" \
MOCK_RECORD="$record" \
MOCK_PROBE_HASH=0000000000000000000000000000000000000000000000000000000000000000 \
ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE=1 \
SSH_KEY="$stage/ssh-key" \
TARGET_KNOWN_HOSTS="$stage/known-hosts" \
EVIDENCE_DIR="$stage/evidence-transfer-failure" \
	"$runner" >"$stage/transfer.out" 2>"$stage/transfer.err"
transfer_status=$?
set -e
[[ $transfer_status -ne 0 ]]
grep -Fq 'target runtime probe failed' "$stage/transfer.err"
[[ $(stat -c %a \
	"$stage/evidence-transfer-failure/minimal-headless-runtime.record") == \
	600 ]]

duplicate_record=$stage/duplicate-boot-id.record
cp "$record" "$duplicate_record"
printf '%s\n' \
	'boot_id=11111111-2222-3333-4444-555555555555' \
	>>"$duplicate_record"
install -d -m 0700 "$stage/evidence-duplicate"
: >"$calls"
set +e
PATH="$stage/bin:$PATH" \
MOCK_CALLS="$calls" \
MOCK_RECORD="$duplicate_record" \
MOCK_PROBE_HASH="$probe_hash" \
ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE=1 \
SSH_KEY="$stage/ssh-key" \
TARGET_KNOWN_HOSTS="$stage/known-hosts" \
EVIDENCE_DIR="$stage/evidence-duplicate" \
	"$runner" >"$stage/duplicate.out" 2>"$stage/duplicate.err"
duplicate_status=$?
set -e
[[ $duplicate_status -ne 0 ]]
grep -Fq 'target runtime record lacks one boot identity' \
	"$stage/duplicate.err"
[[ $(grep -Fxc collect "$calls") == 1 ]]
[[ $(wc -l <"$calls") == 1 ]]

echo 'PASS runtime-acceptance runner preserves the historical path, binds one admitted v3 candidate, uses strict SSH once, verifies privately, and leaves rollback armed'
