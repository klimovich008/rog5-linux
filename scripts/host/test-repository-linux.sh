#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
tier=${1:-quick}
case $tier in
	active|ci|nightly|probe|quick|rootfs) ;;
	*) fail 'usage: test-repository-linux.sh [active|ci|nightly|probe|quick|rootfs]' ;;
esac

for command in bash date dirname dtc gcc git head nm openssl pkg-config python3 sh \
	ssh-keygen strings; do
	command -v "$command" >/dev/null ||
		fail "missing repository-test command: $command"
done
if [[ $tier == quick || $tier == rootfs ]]; then
	pkg-config --exists vulkan ||
		fail 'quick tier requires Vulkan headers and loader metadata'
	cgroup_relative=$(sed -n 's/^0:://p' /proc/self/cgroup)
	[[ -n $cgroup_relative && $cgroup_relative != / ]] ||
		fail 'quick tier requires a non-root delegated cgroup v2'
	cgroup_parent=/sys/fs/cgroup$cgroup_relative
	for control in cgroup.procs cgroup.events cgroup.kill; do
		[[ -f $cgroup_parent/$control ]] ||
			fail "quick tier delegated cgroup lacks $control"
	done
	[[ -w $cgroup_parent ]] ||
		fail 'quick tier cgroup is not delegated writable'
fi

if [[ $tier != active && $tier != probe ]]; then
python3 - "$repo" <<'PY'
from pathlib import Path
import subprocess
import sys

repo = Path(sys.argv[1])
shell_interpreters = {
    b"#!/bin/bash": "bash",
    b"#!/usr/bin/bash": "bash",
    b"#!/usr/bin/env bash": "bash",
    b"#!/bin/sh": "sh",
}
isolated_python_shebang = b"#!/usr/bin/env -S -i /usr/bin/python3 -I -S"
tracked = subprocess.run(
    ["git", "-C", str(repo), "ls-files", "-z", "*.py", "*.sh"],
    check=True,
    stdout=subprocess.PIPE,
).stdout
shell_count = 0
for raw in tracked.split(b"\0"):
    if not raw:
        continue
    path = repo / raw.decode()
    source = path.read_bytes()
    first_line = source.partition(b"\n")[0]
    if path.suffix == ".py" or first_line == isolated_python_shebang:
        compile(source, str(path), "exec")
        continue
    shell_count += 1
    interpreter = shell_interpreters.get(first_line)
    if interpreter is None:
        raise SystemExit(f"unsupported tracked shell shebang: {path}: {first_line!r}")
    subprocess.run([interpreter, "-n", str(path)], check=True)
if shell_count == 0:
    raise SystemExit("git returned no tracked shell scripts")
PY
fi

python3 - "$repo" <<'PY'
from pathlib import Path
import re
import sys

repo = Path(sys.argv[1])
documents = [
    repo / "README.md",
    repo / "ROADMAP.md",
    *sorted((repo / "docs").glob("*.md")),
]
for entry in ("docs/current-state.md", "docs/active-context.md", "docs/development.md"):
    if not (repo / entry).is_file():
        raise SystemExit(f"missing context entry point: {entry}")
link = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
broken = []
for document in documents:
    fenced = False
    for number, line in enumerate(document.read_text().splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if fenced:
            continue
        for match in link.finditer(line):
            target = match.group(1).strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            target = target.split("#", 1)[0].split("?", 1)[0]
            if (
                not target
                or "://" in target
                or target.startswith(("mailto:", "#"))
            ):
                continue
            candidate = (document.parent / target).resolve()
            try:
                candidate.relative_to(repo)
            except ValueError:
                broken.append((document, number, match.group(1)))
                continue
            if not candidate.exists():
                broken.append((document, number, match.group(1)))

if broken:
    for document, number, target in broken:
        print(
            f"{document.relative_to(repo)}:{number}: "
            f"missing local link target {target}",
            file=sys.stderr,
        )
    raise SystemExit(1)
print(
    f"PASS {len(documents)} source Markdown files have valid local targets"
)
PY

if [[ $tier != active && $tier != probe ]] && git -C "$repo" grep -nE \
	'BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|OPENROUTER_API_KEY[[:space:]]*=[[:space:]]*['"'"'"]?[A-Za-z0-9_-]{20}' \
	-- \
	':!scripts/host/test-repository-linux.sh' \
	':!scripts/host/Test-Repository.ps1'
then
	fail 'repository contains a private-key header or literal OpenRouter key'
fi

native_wifi_probe_tests=(
	scripts/device/test-rpmh-readback.py
	scripts/device/test-rpmh-state-reader.py
	scripts/device/test-pmic-rail-reader.py
	scripts/device/test-persistent-power-readiness.py
	scripts/device/test-s12-ufs-vote.py
	scripts/device/test-asus-s12-oem-point.py
	scripts/device/test-native-ath11k-hw11.py
	scripts/device/test-native-wifi-pcie-trace.py
	scripts/device/test-native-wifi-activation.py
	scripts/device/test-native-wifi-wpa-start.py
	scripts/device/test-native-wifi-boot.py
	scripts/device/test-native-wifi-healthy.py
	scripts/host/test-quiesce-native-usb-data.py
	scripts/host/test-native-wifi-discovery.py
	scripts/host/test-controller-bindings.py
	scripts/device/test-wifi-pwrctrl-probe.py
	scripts/device/test-pmic-pon-reader.py
)
active_tests=(
	scripts/host/test-release-acceptance.py
	scripts/device/test-standalone-rescue-composition.py
	scripts/host/test-qemu-watchdog-artifact.py
	scripts/device/test-persistent-root-watchdog.py
	scripts/host/test-persistent-trial-state.py
	scripts/host/test-build-persistent-wifi-selector.py
	"${native_wifi_probe_tests[@]}"
	scripts/device/test-rog5-healthd.py
	scripts/host/test-select-repository-test-tier.py
	scripts/host/test-run-sealed-busybox.py
)

probe_tests=(
	"${native_wifi_probe_tests[@]}"
	scripts/host/test-select-repository-test-tier.py
	scripts/device/test-observe-early-mainline-power.sh
	scripts/device/test-probe-network-root-battery-telemetry.sh
	scripts/device/test-build-early-target-diag.sh
	scripts/host/test-early-target-diagnostics.py
	scripts/host/test-collect-early-target-diagnostics.py
	scripts/device/test-network-root-init.sh
	scripts/host/test-generate-power-usb-active.py
)

shared_tests=(
	scripts/host/test-repository-linux-runner-contract.sh
	scripts/device/test-probe-network-root-battery-telemetry.sh
	scripts/device/test-inspect-local-image-partial.sh
	scripts/device/test-benchmark-local-image-write.sh
	scripts/device/test-stage-local-image-direct.sh
	scripts/device/test-inspect-native-clone-progress.sh
	scripts/device/test-power-usb-active-dtb.sh
	scripts/device/test-persistent-root-power-usb-dtb.sh
	scripts/device/test-persistent-root-power-usb-composition.sh
	scripts/device/test-network-root-pdr-override.sh
	scripts/device/test-persistent-slotb-loader.sh
	scripts/device/test-persistent-slotb-recovery-loader.sh
	scripts/device/test-stage-persistent-service-state.sh
	scripts/device/test-persistent-root-overlay-runtime.sh
	scripts/device/test-persistent-service-state-runtime.sh
	scripts/device/test-persistent-tailscale-runtime.sh
	scripts/device/test-tailscale-netfilter-kernel.sh
	scripts/device/test-standalone-module-refresh.sh
	scripts/device/test-native-wifi-module-kit.sh
	scripts/device/test-native-wifi-dtb.py
	scripts/device/test-ams678-panel-patch.sh
	scripts/device/test-display-60hz-candidate-dtb.sh
	scripts/device/test-screen-toggle.sh
	scripts/device/test-power-buttond.sh
	scripts/device/test-status-screen.sh
	scripts/device/test-display-post-switch-report.sh
	scripts/host/test-display-post-switch-report.py
	scripts/device/test-load-native-ram-bundle.sh
	scripts/device/test-native-kexec-shutdown.py
	scripts/host/test-retention-cycle-runtime-closure.py
	scripts/device/test-persistent-ufs-module-profile.sh
	scripts/device/test-observe-persistent-usb-liveness.sh
	scripts/host/test-generate-power-usb-active.py
	scripts/host/check-power-usb-active-closure.py
	scripts/host/test-rog5-host-doctor.py
	scripts/host/test-power-usb-deployment-receipt.py
	scripts/host/test-power-usb-real-output-replay.py
	scripts/host/test-persistent-trial-state-aarch64.sh
	scripts/host/test-reusable-recovery-claim-design.sh
	scripts/device/test-collect-minimal-headless-runtime.sh
	scripts/host/test-wait-stock-android-fallback.py
	scripts/host/test-verify-headless-ssh-v2-key-admission.py
	scripts/host/test-verify-minimal-headless-runtime.py
	scripts/host/test-qemu-system-smoke-contract.sh
	scripts/host/test-qemu-network-root-nfs-hostile.sh
	scripts/host/test-qemu-systemd-runtime.sh
	scripts/host/test-kernel-builder-bootstrap-contract.sh
	scripts/host/test-import-asus-source-volume-contract.sh
	scripts/host/test-steam-deck-builder-contract.sh
	scripts/host/test-network-root-kernel-rebuild-contract.sh
	scripts/host/test-network-root-kernel-builder-acceleration.sh
	scripts/host/test-network-root-thermal-pmic-candidate.sh
	scripts/host/test-network-root-dual-cell-readonly-candidate.sh
	scripts/host/test-suspend-pm-test-source-contract.py
	scripts/host/test-network-root-suspend-pm-test-candidate.sh
	scripts/device/test-run-network-root-suspend-pm-test-devices.py
	scripts/host/test-reconstruct-recovery-base-v18r-contract.sh
	scripts/host/test-reconstruct-network-root-v3-contract.sh
	scripts/host/test-rebuild-headless-network-root-initramfs-contract.sh
	scripts/host/test-rebuild-early-target-diagnostic-initramfs-contract.sh
	scripts/host/test-early-target-diagnostic-candidate-offline-contract.sh
	scripts/host/test-restore-stable-recovery-inputs-contract.sh
	scripts/host/test-post-wipe-restoration-bundle-contract.sh
	scripts/host/test-stable-recovery-retained-preflight-dedup.sh
	scripts/host/test-fetch-android-boot-tools-contract.sh
	scripts/host/test-canonical-boot-v3-template-contract.sh
	scripts/host/test-asus-kexec-stage-successor-contract.sh
	scripts/host/test-private-arm64-binfmt-contract.sh
	scripts/host/test-steam-deck-recovery-builders-contract.sh
	scripts/host/test-verify-asus-source-tree.py
	scripts/host/test-corrected-headless-candidate-offline-contract.sh
	scripts/host/test-corrected-successor-live-gate-offline.sh
	scripts/host/test-headless-core-candidate-offline-contract.sh
	scripts/host/test-headless-ssh-v2-candidate-offline-contract.sh
	scripts/host/test-build-headless-ssh-deployment-candidate-contract.sh
	scripts/host/test-deployment-checkpoint-inputs.py
	scripts/host/test-stage-recovery-deployment-signing-inputs.py
	scripts/host/test-preflight-headless-ssh-successor-candidate.py
	scripts/device/test-recovery-candidate-dtb-contract.sh
	scripts/device/test-ufs-rmtfs-reserved-candidate-dtb.sh
	scripts/device/test-ufs-phy-disabled-control-dtb.sh
	scripts/device/test-buttons-indicator-candidate-dtb.sh
	scripts/device/test-headless-display-isolation-candidate-dtb.sh
	scripts/device/test-headless-display-isolation-runtime.sh
	scripts/host/test-buttons-indicator-source-contract.py
	scripts/host/test-vcnl36866-port-contract.py
	scripts/device/test-run-network-root-physical-keys.sh
	scripts/host/test-core-compatibility-oracle.py
	scripts/host/test-core-source-dtb-contract.py
	scripts/host/test-pin-minimal-headless-host-key.py
	scripts/host/test-run-minimal-headless-runtime-acceptance.sh
	scripts/host/test-prepare-headless-ssh-deployment-root-contract.sh
	scripts/host/test-prepare-headless-ssh-deployment-candidate.py
	scripts/host/test-prepare-early-target-diagnostic-deployment-candidate.py
	scripts/host/test-install-headless-ssh-deployment-export.py
	scripts/host/test-run-headless-ssh-deployment-export-install.py
	scripts/host/test-headless-battery-series.py
	scripts/host/test-dual-cell-readonly-snapshot.py
	scripts/device/test-qcom-battmgr-asus-cell-voltage-patch.sh
	scripts/device/test-dual-cell-readonly-candidate-dtb.sh
	scripts/host/test-fallback-acm-control.py
	scripts/host/test-retired-legacy-acm-entrypoints.py
	scripts/host/test-run-minimal-headless-live-cycle.py
	scripts/host/test-run-persistent-root-storage-live-cycle.py
	scripts/host/test-early-target-diagnostics.py
	scripts/host/test-collect-early-target-diagnostics.py
	scripts/host/test-consume-generation11-boot-claim.py
	scripts/host/test-consume-generation12-boot-claim.py
	scripts/host/test-consume-exact-boot-claim.py
	scripts/host/test-retention-cycle-sequence-reference.py
	scripts/host/test-retention-cycle-transaction.py
	scripts/host/test-retention-cycle-adapter.py
	scripts/host/test-run-retention-cycle-live.py
	scripts/host/test-retention-cycle-executor-contract.py
	scripts/host/test-retention-cycle-executor-boundary.py
	scripts/host/test-retention-cycle-descriptor-execution.py
	scripts/host/test-recovery-control-reference.py
	scripts/host/test-recovery-control-native.py
	scripts/host/test-recovery-progress-collector.py
	scripts/host/test-recovery-progress-runtime.py
	scripts/host/test-stable-recovery-control.py
	scripts/host/test-verified-fastboot-boot.py
	scripts/host/test-run-stable-recovery-live-gate.sh
	scripts/host/test-current-production-recovery-profile.sh
	scripts/host/test-current-core-recovery-profile.sh
	scripts/host/test-current-persistent-root-storage-profile.sh
	scripts/host/test-current-observation-recovery-profile.sh
	scripts/host/test-recovery-bundle-native.py
	scripts/host/test-prepare-recovery-runtime-bundle.py
	scripts/host/test-prepare-recovery-candidate.py
	scripts/host/test-recovery-candidate-integration.py
	scripts/host/test-headless-network-root.py
	scripts/host/test-compare-root-archives.py
	scripts/host/test-normalize-headless-core-archive-contract.sh
	scripts/host/test-kernel-source-seal.py
	scripts/host/test-observation-recovery-wrapper.py
	scripts/host/test-recovery-control-build-record.py
	scripts/host/test-verify-retention-cycle-admission.py
	scripts/host/test-stable-recovery-wrapper-cache.py
	scripts/host/test-stable-recovery-wrapper-cache-contract.sh
	scripts/host/test-issue-stable-recovery-avb-generation.sh
	scripts/host/test-stable-wrapper-slim-config.py
	scripts/host/test-stable-wrapper-slim-config-contract.sh
	scripts/host/test-arch-headless-rootfs-contract.sh
	scripts/host/test-headless-package-closure.py
	scripts/host/test-key-indicatord.sh
	scripts/host/test-arch-headless-core-rootfs-contract.sh
	scripts/host/test-claude-readonly-review.sh
	scripts/host/test-github-exact-head-workflow.sh
	scripts/device/test-collect-readonly-storage-inventory.py
	scripts/device/test-persistent-root-storage-resolution.py
	scripts/device/test-persistent-root-handoff.sh
	scripts/device/test-persistent-root-initramfs.sh
	scripts/device/test-stage-local-arch-image.sh
	scripts/device/test-local-image-stage-initramfs.sh
	scripts/device/test-clone-local-image-to-arch-root.sh
	scripts/device/test-inspect-native-arch-root.sh
	scripts/device/test-repair-native-arch-root-ssh.sh
	scripts/device/test-qcom-wdt-candidate-dtb.sh
	scripts/device/test-build-qcom-wdt-module.sh
	scripts/device/test-qcom-wdt-observer.sh
	scripts/device/test-local-image-stage-preusb-diagnostic.sh
	scripts/device/test-local-image-stage-configfs-beacon.sh
	scripts/device/test-local-image-stage-udc-inventory.sh
	scripts/device/test-local-image-stage-timing.sh
	scripts/device/test-local-image-stage-address.sh
	scripts/device/test-local-image-stage-configfs-udc.sh
	scripts/device/test-local-image-stage-bind-error.sh
	scripts/device/test-local-image-stage-ufs-baseline.sh
	scripts/device/test-persistent-root-power-usb-v9.sh
	scripts/device/test-persistent-root-power-usb-v10.sh
	scripts/device/test-persistent-root-local-image-probe-writer-v11.sh
	scripts/device/test-persistent-root-local-image-any-prior-v12.sh
	scripts/device/test-persistent-root-local-image-any-prior-v13.sh
	scripts/device/test-persistent-root-local-image-any-prior-v14.sh
	scripts/device/test-persistent-root-local-image-restart2-v15.sh
	scripts/device/test-persistent-root-local-image-reboot-mode-v16.sh
	scripts/device/test-persistent-root-sparse-diagnostic-v17.sh
	scripts/device/test-mainline-persistent-root-build.sh
	scripts/device/test-mainline-local-image-stage-power-usb.sh
	scripts/host/test-backup-readonly-storage-inventory.py
	scripts/host/test-verify-dedicated-linux-layout.py
	scripts/host/test-storage-preflight-initramfs-contract.py
	scripts/host/test-build-storage-layout-gpt-regions.py
	scripts/host/test-storage-layout-stage1-contract.py
	scripts/device/test-userdata-ext4-reset-runtime.sh
	scripts/device/test-disarm-recovery-layout-watchdog.sh
	scripts/host/test-collect-storage-layout-stage1.py
	scripts/host/test-observe-storage-layout-stage1-prewrite.py
	scripts/host/test-storage-layout-stage2-contract.py
	scripts/host/test-collect-storage-layout-stage2.py
	scripts/device/test-storage-layout-stage2-runtime.sh
	scripts/host/test-rog5-charging-firmware-resolution.sh
	scripts/host/test-alpine-charging-rescue-contract.sh
	scripts/host/test-build-direct-charging-rescue.sh
	scripts/host/test-build-stock-charging-successor-initramfs.sh
	scripts/device/test-load-stock-charging-recovery.sh
	scripts/host/test-collect-storage-preflight-report.py
	scripts/host/test-storage-preflight-candidate.py
	scripts/device/test-network-root-init.sh
	scripts/device/test-kernel-build-contract.sh
	scripts/device/test-asus-kexec-stage-slim-build-contract.sh
	scripts/host/test-generate-artifact-prune-plan.py
	scripts/host/test-generate-host-storage-cleanup-plan.py
	scripts/host/test-cleanup-podman-volumes.py
	scripts/host/test-recovery-fetch-native.py
	scripts/host/test-recovery-timeout-lattice.py
	scripts/host/test-recovery-bundle-server.py
	scripts/host/test-recovery-host-controller.py
	scripts/host/test-recovery-host-socket.py
	scripts/host/test-recovery-init-policy.py
	scripts/host/test-reboot-fallback-to-fastboot.sh
)

nightly_tests=(
	scripts/device/test-qmp-ufs-probe-regulator-stage-patch.sh
	scripts/device/test-qmp-ufs-probe-mmio-stage-patch.sh
	scripts/device/test-qmp-ufs-probe-clock-provider-stage-patch.sh
	scripts/device/test-qmp-ufs-probe-fixed-clocks-stage-patch.sh
	scripts/device/test-qmp-ufs-probe-first-fixed-clock-stage-patch.sh
	scripts/device/test-qmp-ufs-probe-allocation-stage-patch.sh
	scripts/device/test-qmp-ufs-probe-first-clock-name-stage-patch.sh
	scripts/device/test-clk-orphan-runtime-pm-current-source-patch.sh
	scripts/device/test-clk-orphan-runtime-pm-lock-model.py
	scripts/device/test-qmp-ufs-probe-first-clock-runtime-pm-stage-patch.sh
	scripts/device/test-qmp-ufs-probe-second-clock-runtime-pm-stage-patch.sh
	scripts/device/test-qmp-ufs-probe-third-clock-runtime-pm-stage-patch.sh
	scripts/device/test-qmp-ufs-clock-provider-cleanup-stage-patch.sh
	scripts/device/test-qmp-ufs-phy-creation-stage-patch.sh
	scripts/device/test-qmp-ufs-phy-provider-stage-patch.sh
	scripts/host/test-recovery-linux.sh
)

tier_tests=()
case $tier in
	nightly)
		tier_tests+=("${nightly_tests[@]}" scripts/device/test-build-early-target-diag.sh)
		;;
	ci)
		tier_tests+=(scripts/device/test-build-early-target-diag.sh)
		;;
	quick|rootfs)
		tier_tests+=(
			scripts/device/test-a660-acceptance.py
			scripts/host/test-a660-runtime-root.py
			scripts/device/test-persistent-root-verifier.sh
			scripts/host/test-network-root-acm.py
			scripts/host/test-persistent-root-acm.py
			scripts/host/test-persistent-root-entry-acm.py
			scripts/host/test-network-root-gpucc-atomic-confirmation.sh
			scripts/host/test-network-root-host.sh
			scripts/host/test-capture-vendor-kernel-log.sh
			scripts/host/test-sync-network-root-time.sh
			scripts/host/test-rog5-remote-tunnel-service.sh
		)
		[[ $tier != rootfs ]] ||
			tier_tests+=(scripts/host/test-linux-rootfs-tools.sh)
		;;
esac
if [[ $tier == active ]]; then
	tests=("${active_tests[@]}")
elif [[ $tier == probe ]]; then
	tests=("${probe_tests[@]}")
else
	tests=("${active_tests[@]}" "${shared_tests[@]}" "${tier_tests[@]}")
fi

for test_path in "${tests[@]}"; do
	test_file=$repo/$test_path
	[[ -f $test_file && ! -L $test_file ]] ||
		fail "missing core offline test: $test_path"
	case $test_file in
		*.py) ;;
		*) [[ -x $test_file ]] ||
			fail "offline test is not executable: $test_path" ;;
	esac
done

run_test() {
	test_path=$1
	test_file=$repo/$test_path
	started=$(date +%s%N)
	set +e
	case $test_file in
		*.py) python3 "$test_file" ;;
		*) "$test_file" ;;
	esac
	status=$?
	set -e
	finished=$(date +%s%N)
	elapsed_ms=$(((finished - started) / 1000000))
	printf 'DURATION %s %dms\n' "$test_path" "$elapsed_ms"
	return "$status"
}

isolated_tests=(
	"${native_wifi_probe_tests[@]}"
	# Private temporary files and loopback port 0; no shared service/listener.
	scripts/device/test-rog5-healthd.py
	scripts/host/test-persistent-trial-state.py
	scripts/host/test-build-persistent-wifi-selector.py
	scripts/host/test-select-repository-test-tier.py
	scripts/host/test-qemu-system-smoke-contract.sh
	scripts/host/test-qemu-network-root-nfs-hostile.sh
	scripts/host/test-kernel-builder-bootstrap-contract.sh
	scripts/host/test-import-asus-source-volume-contract.sh
	scripts/host/test-steam-deck-builder-contract.sh
)
selected_test() {
	local candidate=$1
	local selected
	for selected in "${tests[@]}"; do
		[[ $selected != "$candidate" ]] || return 0
	done
	return 1
}
# An unset override preserves HOME; an explicitly empty override is invalid.
test_tmp_parent=${ROG5_TEST_TMP_PARENT-${HOME:-}}
[[ $test_tmp_parent == /* && -d $test_tmp_parent &&
	! -L $test_tmp_parent && -w $test_tmp_parent ]] ||
	fail 'repository test temporary parent is unavailable'
test_tmp_root=$(mktemp -d "$test_tmp_parent/.rog5-tests.XXXXXXXX")
chmod 0700 "$test_tmp_root"
# Prove the actual longest host-broker fixture path before costly suites.
# AF_UNIX has a byte limit even when the containing directory is writable.
if ! python3 - "$test_tmp_root" <<'PY'
from pathlib import Path
import socket
import sys
import tempfile

try:
    with tempfile.TemporaryDirectory(prefix="rog5-host-socket-test-", dir=sys.argv[1]) as fixture:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(Path(fixture) / "broker-peer.sock"))
except OSError:
    raise SystemExit("test scratch cannot host the broker Unix socket; choose a shorter parent")
PY
then
	rmdir -- "$test_tmp_root"
	test_tmp_root=
	fail 'repository test temporary parent cannot host Unix sockets'
fi
export TMPDIR=$test_tmp_root
parallel_root=$(mktemp -d)
parallel_pids=()
parallel_paths=()
parallel_status_files=()
parallel_group_has_other_members() {
	local group_pid=$1
	local member_pid member_pgid
	while read -r member_pid member_pgid; do
		if [[ $member_pgid == "$group_pid" && $member_pid != "$group_pid" ]]; then
			return 0
		fi
	done < <(ps -e -o pid= -o pgid=)
	return 1
}
terminate_parallel_group() {
	local group_pid=$1
	local attempt=0
	/bin/kill -0 "$group_pid" 2>/dev/null || return 1
	/bin/kill -TERM -- "-$group_pid" 2>/dev/null || return 1
	while [[ $attempt -lt 100 ]]; do
		/bin/kill -0 "$group_pid" 2>/dev/null || return 1
		if ! parallel_group_has_other_members "$group_pid"; then
			/bin/kill -KILL "$group_pid" 2>/dev/null || return 1
			return 0
		fi
		sleep 0.01
		attempt=$((attempt + 1))
	done
	/bin/kill -0 "$group_pid" 2>/dev/null || return 1
	/bin/kill -KILL -- "-$group_pid" 2>/dev/null
}
cleanup_parallel_tests() {
	cleanup_status=$?
	trap - EXIT HUP INT TERM
	for pid in "${parallel_pids[@]}"; do
		[[ -z $pid ]] || terminate_parallel_group "$pid" || true
	done
	for pid in "${parallel_pids[@]}"; do
		[[ -z $pid ]] || wait "$pid" 2>/dev/null || true
	done
	rm -rf -- "$parallel_root"
	[[ -z ${test_tmp_root:-} ]] || rm -rf -- "$test_tmp_root"
	exit "$cleanup_status"
}
trap cleanup_parallel_tests EXIT HUP INT TERM
set -m
for test_path in "${isolated_tests[@]}"; do
	selected_test "$test_path" || continue
	parallel_paths+=("$test_path")
	status_file=$parallel_root/${#parallel_paths[@]}.status
	hold_fifo=$parallel_root/${#parallel_paths[@]}.hold
	mkfifo -- "$hold_fifo"
	parallel_status_files+=("$status_file")
	(
		trap : TERM
		if run_test "$test_path"; then
			test_status=0
		else
			test_status=$?
		fi
		printf '%s\n' "$test_status" >"$status_file"
		while :; do
			read -r _ <"$hold_fifo" || true
		done
	) >"$parallel_root/${#parallel_paths[@]}.log" 2>&1 &
	parallel_pids+=("$!")
done
set +m
for index in "${!parallel_pids[@]}"; do
	log=$parallel_root/$((index + 1)).log
	pid=${parallel_pids[$index]}
	status_file=${parallel_status_files[$index]}
	while [[ ! -s $status_file ]]; do
		/bin/kill -0 "$pid" 2>/dev/null || {
			wait "$pid" 2>/dev/null || true
			parallel_pids[$index]=
			fail "isolated offline test supervisor exited early: ${parallel_paths[$index]}"
		}
		sleep 0.01
	done
	read -r wait_status <"$status_file"
	[[ $wait_status =~ ^[0-9]+$ ]] ||
		fail "isolated offline test returned an invalid status: ${parallel_paths[$index]}"
	had_descendants=false
	parallel_group_has_other_members "$pid" && had_descendants=true
	terminate_parallel_group "$pid" ||
		fail "isolated offline test supervisor identity was lost: ${parallel_paths[$index]}"
	wait "$pid" 2>/dev/null || true
	parallel_pids[$index]=
	if [[ $wait_status == 0 ]]; then
		if $had_descendants; then
			fail "isolated offline test left background descendants: ${parallel_paths[$index]}"
		fi
		cat "$log"
	else
		cat "$log" >&2
		fail "isolated offline test failed: ${parallel_paths[$index]}"
	fi
done

for test_path in "${tests[@]}"; do
	case " ${isolated_tests[*]} " in
		*" $test_path "*) continue ;;
	esac
	if ! run_test "$test_path"; then
		fail "sequential offline test failed: $test_path"
	fi
done

echo "PASS repository Linux $tier tier"
