#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
prepare=$repo/scripts/host/prepare-network-root-export.sh
verify=$repo/scripts/host/verify-network-root-export.sh
serve=$repo/scripts/host/serve-network-root.sh
ucode_v5_consumed_test=$repo/scripts/host/test-consume-a660-ucode-allocation-v5.sh
ucode_v6_consumed_test=$repo/scripts/host/test-consume-a660-ucode-allocation-v6.sh
ucode_v7_consumed_test=$repo/scripts/host/test-consume-a660-ucode-allocation-v7.sh
gmu_v8_consumed_test=$repo/scripts/host/test-consume-a660-gmu-resume-entry-v8.sh
gmu_v9_consumed_test=$repo/scripts/host/test-consume-a660-gmu-resume-entry-v9.sh

for script in "$prepare" "$verify" "$serve" "$ucode_v5_consumed_test" \
	"$ucode_v6_consumed_test" "$ucode_v7_consumed_test" \
	"$gmu_v8_consumed_test" "$gmu_v9_consumed_test"; do
	[ -x "$script" ] || {
		echo "FAIL missing executable network-root host tool: $script" >&2
		exit 1
	}
	bash -n "$script"
done

grep -Fq 'rog5-arch-plasma-network-root-7.1.4.tar.gz' "$prepare"
grep -Fq 'bsdtar --acls --xattrs --fflags -xpf' "$prepare"
grep -Fq 'refusing existing export root' "$prepare"
grep -Fq 'verify-network-root-export.sh' "$prepare"

grep -Fq '7.1.4-g7a5cef0db479' "$verify"
grep -Fq 'modules-7.1.4-network-root.tar.gz' "$verify"
grep -Fq 'unmanaged-devices=interface-name:usb0' "$verify"
grep -Fq 'nfs_export_all_ro' "$verify"
grep -Fq 'ssh_host_ed25519_key' "$verify"
grep -Fq 'ssh-keygen -y' "$verify"
grep -Fq '10-rog5-sshd.conf' "$verify"
grep -Fq 'PASS prepared network-root export' "$verify"
grep -Fq "ssh-keygen -q -t ed25519 -N ''" "$prepare"
grep -Fq '10-rog5-sshd.conf' "$prepare"
grep -Fqx 'HostKey /etc/ssh/ssh_host_ed25519_key' \
	"$repo/packaging/arch/10-rog5-sshd.conf"

for contract in \
	'169.254.77.1' \
	'169.254.77.2' \
	'ROG5_network_root' \
	'ID_NET_DRIVER=cdc_ncm' \
	'--host "$host_ip"' \
	'--no-nfs-version 3' \
	'--nfs-version 4.2' \
	'--grace-time "$grace_time"' \
	'--lease-time "$lease_time"' \
	'ROG5_NFS_TIMEOUT:-900' \
	'serve_timeout > 86400' \
	'ROG5_NFS_HANDOFF_TOKEN' \
	'/run/rog5-network-root-nfs-ready' \
	'format=rog5-nfs-handoff-v1' \
	'format=rog5-nfs-handoff-v2' \
	'profile=headless-ssh-deployment-v3' \
	'package_sha256=$expected_package_sha256' \
	'versions=4.2-only' \
	'verify-export-ancestry' \
	'verify-root "$export_mount"' \
	'/var/lib/rog5-network-root-v1)' \
	'/home/rog5-linux/exports/headless-ssh-network-root-v3' \
	'only the deployment headless root accepts a package identity' \
	'deployment package changed before NFS handoff' \
	'/proc/fs/nfsd/v4_end_grace' \
	'ro,fsid=0,sync,no_subtree_check,no_root_squash' \
	'mount --bind "$root" "$export_mount"' \
	'remount,bind,ro,nodev,nosuid' \
	'etab=/var/lib/nfs/etab' \
	'0:0:600|0:0:644)' \
	'mkdir -p /proc/fs/nfsd' \
	'trap cleanup EXIT' \
	'firewall_zone=drop' \
	'$1 == "target:"' \
	'--add-rich-rule="$nfs_allow_rule"' \
	'--remove-rich-rule="$nfs_allow_rule"' \
	'export_listing=$(exportfs -v)' \
	'grep -Fc "$export_mount"' \
	'grep -Fc "$phone_ip"'; do
	grep -Fq -- "$contract" "$serve" || {
		echo "FAIL network-root host contract missing: $contract" >&2
		exit 1
	}
done

for transition in \
	gadget-interface-discovered \
	networkmanager-unmanaged \
	link-up \
	host-address-present \
	firewall-zone-confirmed \
	tcp-2049-listening \
	exact-network-root-link-ready; do
	grep -Fq "log_network_transition $transition" "$serve" || {
		echo "FAIL network-root host transition is not timestamped: $transition" >&2
		exit 1
	}
done
grep -Fq 'GENERAL.NM-MANAGED' "$serve"
grep -Fq 'network_root_poll_interval=1' "$serve"
grep -Fq 'sleep "$network_root_poll_interval"' "$serve"

transition_work=$(mktemp -d)
transition_functions=$transition_work/functions.sh
transition_output=$transition_work/transitions.log
awk '
	/^network_transition_time_ms\(\) \{/ { copy=1 }
	/^echo "PASS restricted NFSv4\.2 export ready; waiting for exact USB gadget"$/ { copy=0 }
	copy { print }
' "$serve" >"$transition_functions"
grep -Fq 'configure_target_interface() {' "$transition_functions"
grep -Fq 'verify_exact_nfs_listener() {' "$transition_functions"

(
	# shellcheck disable=SC1090
	. "$transition_functions"
	interface=fixture0
	touched_interfaces=()
	network_root_poll_interval=1
	host_ip=169.254.77.1
	host_cidr=169.254.77.1/30
	firewall_zone=drop
	nm_managed=yes
	address_present=0
	fixture_zone=public
	nmcli() {
		case "$*" in
			'device set fixture0 managed no')
				sleep 0.04
				nm_managed=no
				;;
			'-g GENERAL.NM-MANAGED device show fixture0')
				printf '%s\n' "$nm_managed"
				;;
			*) return 1 ;;
		esac
	}
	ip() {
		case "$*" in
			'link set fixture0 up') sleep 0.03 ;;
			'-4 -o address show dev fixture0')
				[ "$address_present" -eq 0 ] ||
					printf '%s\n' \
						'2: fixture0 inet 169.254.77.1/30 scope global fixture0'
				;;
			'address add 169.254.77.1/30 dev fixture0')
				sleep 0.03
				address_present=1
				;;
			'address del 169.254.77.1/30 dev fixture0')
				address_present=0
				;;
			*) return 1 ;;
		esac
	}
	firewall-cmd() {
		case "$*" in
			'--get-zone-of-interface=fixture0') printf '%s\n' "$fixture_zone" ;;
			'--zone=drop --change-interface=fixture0')
				sleep 0.04
				fixture_zone=drop
				;;
			*) return 1 ;;
		esac
	}
	ss() {
		[ "$*" = '-H -lnt4 sport = :2049' ] || return 1
		sleep 0.02
		printf '%s\n' \
			'LISTEN 0 64 169.254.77.1:2049 0.0.0.0:*'
	}
	start_ms=$(network_transition_time_ms)
	printf 'MEASURE modeled_transition=poll-start monotonic_ms=%s\n' \
		"$start_ms"
	sleep "$network_root_poll_interval"
	log_network_transition gadget-interface-discovered "$interface"
	configure_target_interface "$interface"
	end_ms=$(network_transition_time_ms)
	printf 'MEASURE modeled_host_readiness_total_ms=%s\n' \
		"$((end_ms - start_ms))"
) >"$transition_output"

expected_transitions='gadget-interface-discovered networkmanager-unmanaged link-up host-address-present firewall-zone-confirmed tcp-2049-listening exact-network-root-link-ready'
actual_transitions=$(awk '
	$1 == "STATE" && $2 == "network-root-usb" {
		for (i = 1; i <= NF; i++)
			if ($i ~ /^transition=/) {
				sub(/^transition=/, "", $i)
				printf "%s%s", separator, $i
				separator=" "
			}
	}
	END { print "" }
' "$transition_output")
[ "$actual_transitions" = "$expected_transitions" ] || {
	echo "FAIL measured network-root transitions were: $actual_transitions" >&2
	exit 1
}
awk '
	$1 == "MEASURE" && $2 == "modeled_transition=poll-start" {
		split($3, value, "=")
		previous=value[2]
		initialized=1
		next
	}
	$1 == "STATE" && $2 == "network-root-usb" {
		transition=""
		for (i = 1; i <= NF; i++)
			if ($i ~ /^transition=/) {
				split($i, name, "=")
				transition=name[2]
			} else if ($i ~ /^monotonic_ms=/) {
				split($i, value, "=")
				if (!initialized || value[2] < previous) exit 1
				printf "MEASURE modeled_transition=%s delta_ms=%d\n", \
					transition, value[2] - previous
				previous=value[2]
				seen=1
			}
	}
	END { exit !seen }
' "$transition_output"
cat "$transition_output"
find "$transition_work" -depth -delete

verify_ancestry_line=$(grep -n '^verify_deployment_export$' "$serve" |
	tail -n1 | cut -d: -f1)
bind_line=$(grep -n '^mount --bind "\$root" "\$export_mount"$' "$serve" |
	cut -d: -f1)
mounted_verify_line=$(grep -n \
	'verify-root "\$export_mount"' "$serve" |
	cut -d: -f1)
[ "$verify_ancestry_line" -lt "$bind_line" ]
[ "$bind_line" -lt "$mounted_verify_line" ]

for consumed in \
	/var/lib/rog5-network-root-adreno-smmu-v20 \
	/var/lib/rog5-network-root-adreno-smmu-v21 \
	/var/lib/rog5-network-root-a660-registration \
	/var/lib/rog5-network-root-a660-registration-v2 \
	/var/lib/rog5-network-root-a660-registration-v3 \
	/var/lib/rog5-network-root-a660-firmware-request-only-v4 \
	/var/lib/rog5-network-root-a660-ucode-allocation-v5 \
	/var/lib/rog5-network-root-a660-ucode-allocation-v6 \
	/var/lib/rog5-network-root-a660-ucode-allocation-v7 \
	/var/lib/rog5-network-root-a660-gmu-resume-entry-v8 \
	/var/lib/rog5-network-root-a660-gmu-resume-entry-v9
do
	if grep -Fq "$consumed)" "$serve"; then
		echo "FAIL network-root host still allowlists consumed root: $consumed" >&2
		exit 1
	fi
done

export_flag_line=$(grep -n '^export_active=1$' "$serve" |
	cut -d: -f1)
export_line=$(grep -n '^exportfs -i -o ' "$serve" |
	cut -d: -f1)
[ "$export_flag_line" -lt "$export_line" ]
grep -Fq 'exportfs -u "$phone_ip:$export_mount"' "$serve"
target_seen_line=$(grep -n 'if \[\[ \$target_seen == 0 \]\]; then' "$serve" |
	tail -n1 | cut -d: -f1)
configure_line=$(grep -n 'configure_target_interface "$target_interface"' "$serve" |
	tail -n1 | cut -d: -f1)
target_mark_line=$(grep -n 'target_seen=1' "$serve" | tail -n1 | cut -d: -f1)
[ "$target_seen_line" -lt "$configure_line" ]
[ "$configure_line" -lt "$target_mark_line" ]

cleanup_guard_line=$(grep -n \
	'if \[\[ -e /sys/class/net/\$interface \]\]; then' "$serve" |
	head -n1 | cut -d: -f1)
cleanup_guard_end_line=$(awk -v start="$cleanup_guard_line" \
	'NR > start && /^[[:space:]]*fi$/ { print NR; exit }' "$serve")
cleanup_remove_line=$(grep -n -- '--remove-interface="$interface"' "$serve" |
	head -n1 | cut -d: -f1)
[ "$cleanup_guard_line" -lt "$cleanup_guard_end_line" ]
[ "$cleanup_guard_end_line" -lt "$cleanup_remove_line" ]

if grep -Eq -- '--permanent|--new-zone|/etc/exports|(^|[[:space:]])\*\(|no_root_squash.*\*' \
	"$prepare" "$verify" "$serve"; then
	echo 'FAIL network-root host tools contain a persistent or broad export' >&2
	exit 1
fi
if grep -Eq '(^|[[:space:]])fastboot[[:space:]]+flash|(^|[[:space:]])dd[[:space:]].*of=/dev/' \
	"$prepare" "$verify" "$serve"; then
	echo 'FAIL network-root host tools contain a phone-storage write command' >&2
	exit 1
fi

"$ucode_v5_consumed_test" >/dev/null
"$ucode_v6_consumed_test" >/dev/null
"$ucode_v7_consumed_test" >/dev/null
"$gmu_v8_consumed_test" >/dev/null
"$gmu_v9_consumed_test" >/dev/null

echo 'PASS host gate is exact-peer, runtime-only, read-only, and fail-closed'
