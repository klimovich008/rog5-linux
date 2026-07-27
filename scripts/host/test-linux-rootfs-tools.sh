#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
fetch=$repo/scripts/host/get-arch-rootfs.sh
stage=$repo/scripts/host/stage-arch-rootfs.sh
agent_test=$repo/scripts/device/test-agent-isolation.sh
metrics_test=$repo/scripts/device/test-collect-baseline.sh
component_metrics_test=$repo/scripts/device/test-collect-component-pss.sh
persistent_layout_test=$repo/scripts/device/test-inspect-persistent-layout.sh
persistent_stage=$repo/scripts/device/stage-persistent-arch-root.sh
persistent_stage_test=$repo/scripts/device/test-stage-persistent-arch-root.sh
persistent_root_tool=$repo/scripts/device/persistent-root-tool.py
vendor_log_capture=$repo/scripts/host/capture-vendor-kernel-log.sh
vendor_log_capture_test=$repo/scripts/host/test-capture-vendor-kernel-log.sh
wifi_contract=$repo/scripts/device/collect-vendor-wifi-contract.py
wifi_contract_test=$repo/scripts/device/test-collect-vendor-wifi-contract.py
wifi_candidate_test=$repo/scripts/device/test-wifi-candidate-dtb.sh
wifi_schema_test=$repo/scripts/host/test-validate-wifi-candidate-dtb.sh
wifi_kernel_test=$repo/scripts/device/test-mainline-wifi-build-contract.sh
wifi_probe_test=$repo/scripts/device/test-probe-network-root-wifi.sh
wifi_overlay_test=$repo/scripts/device/test-wifi-root-overlay-contract.sh
wifi_bundle_contract_test=$repo/scripts/device/test-wifi-network-root-bundle-contract.sh
wifi_bundle_test=$repo/scripts/device/test-network-root-wifi-bundle.sh
wifi_gate_test=$repo/scripts/device/test-run-network-root-wifi-gate.sh
wifi_export_test=$repo/scripts/host/test-wcn6855-v1-export.sh
wifi_nfs_test=$repo/scripts/host/test-serve-wcn6855-v1-live-window.sh
wifi_runner_test=$repo/scripts/host/test-run-wcn6855-v1-live-gate.sh
hotspot_wireguard_contract=$repo/scripts/device/test-vpn-hotspot-wireguard-contract.sh
successor_export_test=$repo/scripts/host/test-arch-successor-export.sh
successor_target_test=$repo/scripts/device/test-run-network-root-arch-successor-v1-gate.sh
successor_runner_test=$repo/scripts/host/test-run-arch-successor-v1-live-gate.sh
successor_v2_test=$repo/scripts/device/test-arch-successor-v2-packaging-contract.sh
successor_v2_export_test=$repo/scripts/host/test-arch-successor-v2-export.sh
successor_v2_nfs_test=$repo/scripts/host/test-serve-arch-successor-v2-live-window.sh
successor_v2_target_test=$repo/scripts/device/test-run-network-root-arch-successor-v2-gate.sh
successor_v2_runner_test=$repo/scripts/host/test-run-arch-successor-v2-live-gate.sh
successor_v3_test=$repo/scripts/device/test-arch-successor-v3-power-button-contract.sh
successor_v3_archive_test=$repo/scripts/host/test-arch-successor-v3-archive-contract.sh
successor_v3_export_test=$repo/scripts/host/test-arch-successor-v3-export.sh
successor_v3_nfs_test=$repo/scripts/host/test-serve-arch-successor-v3-live-window.sh
successor_v3_target_test=$repo/scripts/device/test-run-network-root-arch-successor-v3-gate.sh
successor_v3_runner_test=$repo/scripts/host/test-run-arch-successor-v3-live-gate.sh

for script in "$fetch" "$stage" "$agent_test" "$metrics_test" \
	"$component_metrics_test" "$persistent_layout_test" \
	"$persistent_stage" "$persistent_stage_test" \
	"$vendor_log_capture" "$vendor_log_capture_test" \
	"$wifi_candidate_test" "$wifi_schema_test" "$wifi_kernel_test" \
	"$wifi_probe_test" "$wifi_overlay_test" \
	"$wifi_bundle_contract_test" "$wifi_bundle_test" "$wifi_gate_test" \
	"$wifi_export_test" "$wifi_nfs_test" "$wifi_runner_test" \
	"$hotspot_wireguard_contract" \
	"$successor_export_test" "$successor_target_test" \
	"$successor_runner_test" "$successor_v2_test" \
	"$successor_v2_export_test" "$successor_v2_nfs_test" \
	"$successor_v2_target_test" "$successor_v2_runner_test" \
	"$successor_v3_test" "$successor_v3_archive_test" \
	"$successor_v3_export_test" "$successor_v3_nfs_test" \
	"$successor_v3_target_test" "$successor_v3_runner_test"; do
	[ -x "$script" ] || {
		echo "FAIL missing executable Linux host tool: $script" >&2
		exit 1
	}
	bash -n "$script"
done
[ -x "$persistent_root_tool" ] || {
	echo "FAIL missing executable Linux device tool: $persistent_root_tool" >&2
	exit 1
}
python3 -m py_compile "$persistent_root_tool"
for script in "$wifi_contract" "$wifi_contract_test"; do
	[ -x "$script" ] || {
		echo "FAIL missing executable Linux device tool: $script" >&2
		exit 1
	}
done
"$agent_test" >/dev/null
"$metrics_test" >/dev/null
"$component_metrics_test" >/dev/null
"$persistent_layout_test" >/dev/null
"$persistent_stage_test" >/dev/null
"$vendor_log_capture_test" >/dev/null
"$wifi_contract_test" >/dev/null
"$wifi_candidate_test" >/dev/null
"$wifi_schema_test" >/dev/null
"$wifi_kernel_test" >/dev/null
"$wifi_probe_test" >/dev/null
"$wifi_overlay_test" >/dev/null
"$wifi_bundle_contract_test" >/dev/null
"$wifi_bundle_test" >/dev/null
"$wifi_gate_test" >/dev/null
"$wifi_export_test" >/dev/null
"$wifi_nfs_test" >/dev/null
"$wifi_runner_test" >/dev/null
"$hotspot_wireguard_contract" >/dev/null
"$successor_export_test" >/dev/null
"$successor_target_test" >/dev/null
"$successor_runner_test" >/dev/null
"$successor_v2_test" >/dev/null
"$successor_v2_export_test" >/dev/null
"$successor_v2_nfs_test" >/dev/null
"$successor_v2_target_test" >/dev/null
"$successor_v2_runner_test" >/dev/null
"$successor_v3_test" >/dev/null
"$successor_v3_archive_test" >/dev/null
"$successor_v3_export_test" >/dev/null
"$successor_v3_nfs_test" >/dev/null
"$successor_v3_target_test" >/dev/null
"$successor_v3_runner_test" >/dev/null

grep -Fq 'verify-arch-rootfs.sh' "$fetch"
grep -Fq '91e6b11698f8df66042d56aaa56fbe9c9263847d' "$fetch"
grep -Fq '68B3537F39A313B3E574D06777193F152BDBE6A6' \
	"$repo/scripts/device/verify-arch-rootfs.sh"

grep -Fq 'verify-staged-arch-rootfs-v2.sh' "$stage"
grep -Fq 'modules-7.1.4-network-root.tar.gz' "$stage"
grep -Fq 'bsdtar --acls --xattrs --fflags' "$stage"
grep -Fq 'libarchive-tools-3.8.7-r0.apk' \
	"$repo/scripts/host/Get-RecoveryPackages.ps1"
grep -Fq \
	'033049f6d53ff0d267341087adfe142d3e4abe8d3fcec6853e2ed7c95ce2d41e' \
	"$repo/scripts/host/Get-RecoveryPackages.ps1"
grep -Fq '10-rog5-sshd.conf' "$repo/scripts/device/stage-arch-rootfs.sh"
grep -Fqx 'HostKey /etc/ssh/ssh_host_ed25519_key' \
	"$repo/packaging/arch/10-rog5-sshd.conf"
grep -Fq 'unmanaged-devices=interface-name:usb0' \
	"$repo/packaging/arch/10-rog5-usb-unmanaged.conf"

if grep -Eq -- '--privileged|--network[= ]host' "$fetch" "$stage"; then
	echo 'FAIL Linux rootfs tools request broad container privileges' >&2
	exit 1
fi
if grep -Eq '(^|[[:space:]])fastboot[[:space:]]+flash|(^|[[:space:]])dd[[:space:]].*of=/dev/' \
	"$fetch" "$stage"; then
	echo 'FAIL Linux rootfs tools contain a phone-storage write command' >&2
	exit 1
fi

echo 'PASS Linux rootfs tools pin signed input, preserve metadata, and avoid phone writes'
