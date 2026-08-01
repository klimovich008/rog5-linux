#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
tier=${1:-quick}
case $tier in
	ci|quick|rootfs) ;;
	*) fail 'usage: test-repository-linux.sh [ci|quick|rootfs]' ;;
esac

for command in bash dtc gcc git head nm openssl pkg-config python3 sh \
	ssh-keygen strings; do
	command -v "$command" >/dev/null ||
		fail "missing repository-test command: $command"
done
if [[ $tier != ci ]]; then
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

if git -C "$repo" grep -nE \
	'BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|OPENROUTER_API_KEY[[:space:]]*=[[:space:]]*['"'"'"]?[A-Za-z0-9_-]{20}' \
	-- \
	':!scripts/host/test-repository-linux.sh' \
	':!scripts/host/Test-Repository.ps1'
then
	fail 'repository contains a private-key header or literal OpenRouter key'
fi

if [[ $tier == ci ]]; then
	tests=(
		scripts/host/test-qemu-system-smoke-contract.sh
		scripts/host/test-qemu-systemd-runtime.sh
		scripts/host/test-kernel-builder-bootstrap-contract.sh
		scripts/host/test-import-asus-source-volume-contract.sh
		scripts/host/test-steam-deck-builder-contract.sh
		scripts/host/test-network-root-kernel-rebuild-contract.sh
		scripts/host/test-reconstruct-recovery-base-v18r-contract.sh
		scripts/host/test-reconstruct-network-root-v3-contract.sh
		scripts/host/test-rebuild-headless-network-root-initramfs-contract.sh
		scripts/host/test-rebuild-early-target-diagnostic-initramfs-contract.sh
		scripts/host/test-early-target-diagnostic-candidate-offline-contract.sh
		scripts/host/test-restore-stable-recovery-inputs-contract.sh
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
		scripts/host/test-stage-recovery-deployment-signing-inputs.py
		scripts/host/test-preflight-headless-ssh-successor-candidate.py
		scripts/device/test-recovery-candidate-dtb-contract.sh
			scripts/device/test-buttons-indicator-candidate-dtb.sh
			scripts/host/test-buttons-indicator-source-contract.py
			scripts/host/test-core-compatibility-oracle.py
			scripts/host/test-core-source-dtb-contract.py
			scripts/device/test-collect-minimal-headless-runtime.sh
			scripts/host/test-verify-minimal-headless-runtime.py
			scripts/host/test-pin-minimal-headless-host-key.py
			scripts/host/test-run-minimal-headless-runtime-acceptance.sh
			scripts/host/test-verify-headless-ssh-v2-key-admission.py
			scripts/host/test-prepare-headless-ssh-deployment-root-contract.sh
		scripts/host/test-prepare-headless-ssh-deployment-candidate.py
		scripts/host/test-prepare-early-target-diagnostic-deployment-candidate.py
			scripts/host/test-install-headless-ssh-deployment-export.py
			scripts/host/test-run-headless-ssh-deployment-export-install.py
			scripts/host/test-headless-battery-series.py
			scripts/host/test-fallback-acm-control.py
			scripts/host/test-run-minimal-headless-live-cycle.py
			scripts/host/test-early-target-diagnostics.py
			scripts/host/test-collect-early-target-diagnostics.py
			scripts/device/test-build-early-target-diag.sh
			scripts/host/test-recovery-linux.sh
		scripts/host/test-recovery-control-reference.py
		scripts/host/test-recovery-control-native.py
		scripts/host/test-stable-recovery-control.py
		scripts/host/test-verified-fastboot-boot.py
		scripts/host/test-run-stable-recovery-live-gate.sh
		scripts/host/test-recovery-bundle-native.py
		scripts/host/test-prepare-recovery-runtime-bundle.py
		scripts/host/test-prepare-recovery-candidate.py
		scripts/host/test-recovery-candidate-integration.py
		scripts/host/test-headless-network-root.py
		scripts/host/test-compare-root-archives.py
		scripts/host/test-normalize-headless-core-archive-contract.sh
		scripts/host/test-kernel-source-seal.py
		scripts/host/test-stable-recovery-wrapper-cache.py
		scripts/host/test-stable-recovery-wrapper-cache-contract.sh
		scripts/host/test-stable-wrapper-slim-config.py
		scripts/host/test-stable-wrapper-slim-config-contract.sh
		scripts/host/test-arch-headless-rootfs-contract.sh
		scripts/host/test-key-indicatord.sh
		scripts/host/test-arch-headless-core-rootfs-contract.sh
		scripts/host/test-claude-readonly-review.sh
		scripts/device/test-network-root-init.sh
		scripts/device/test-kernel-build-contract.sh
		scripts/device/test-asus-kexec-stage-slim-build-contract.sh
		scripts/host/test-generate-artifact-prune-plan.py
		scripts/host/test-generate-host-storage-cleanup-plan.py
		scripts/host/test-cleanup-podman-volumes.py
		scripts/host/test-recovery-fetch-native.py
		scripts/host/test-recovery-bundle-server.py
		scripts/host/test-recovery-host-controller.py
		scripts/host/test-recovery-init-policy.py
		scripts/host/test-reboot-fallback-to-fastboot.sh
	)
else
	tests=(
		scripts/host/test-qemu-system-smoke-contract.sh
		scripts/host/test-qemu-systemd-runtime.sh
		scripts/host/test-kernel-builder-bootstrap-contract.sh
		scripts/host/test-import-asus-source-volume-contract.sh
		scripts/host/test-steam-deck-builder-contract.sh
		scripts/host/test-network-root-kernel-rebuild-contract.sh
		scripts/host/test-reconstruct-recovery-base-v18r-contract.sh
		scripts/host/test-reconstruct-network-root-v3-contract.sh
		scripts/host/test-rebuild-headless-network-root-initramfs-contract.sh
		scripts/host/test-rebuild-early-target-diagnostic-initramfs-contract.sh
		scripts/host/test-early-target-diagnostic-candidate-offline-contract.sh
		scripts/host/test-restore-stable-recovery-inputs-contract.sh
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
		scripts/host/test-stage-recovery-deployment-signing-inputs.py
		scripts/host/test-preflight-headless-ssh-successor-candidate.py
			scripts/device/test-recovery-candidate-dtb-contract.sh
			scripts/device/test-buttons-indicator-candidate-dtb.sh
			scripts/host/test-buttons-indicator-source-contract.py
			scripts/host/test-core-compatibility-oracle.py
			scripts/host/test-core-source-dtb-contract.py
			scripts/device/test-collect-minimal-headless-runtime.sh
			scripts/host/test-verify-minimal-headless-runtime.py
			scripts/host/test-pin-minimal-headless-host-key.py
			scripts/host/test-run-minimal-headless-runtime-acceptance.sh
			scripts/host/test-verify-headless-ssh-v2-key-admission.py
			scripts/host/test-prepare-headless-ssh-deployment-root-contract.sh
			scripts/host/test-prepare-headless-ssh-deployment-candidate.py
			scripts/host/test-prepare-early-target-diagnostic-deployment-candidate.py
			scripts/host/test-install-headless-ssh-deployment-export.py
			scripts/host/test-run-headless-ssh-deployment-export-install.py
			scripts/host/test-headless-battery-series.py
			scripts/host/test-fallback-acm-control.py
			scripts/host/test-run-minimal-headless-live-cycle.py
			scripts/host/test-early-target-diagnostics.py
			scripts/host/test-collect-early-target-diagnostics.py
			scripts/host/test-recovery-linux.sh
		scripts/host/test-recovery-control-reference.py
		scripts/host/test-recovery-control-native.py
		scripts/host/test-stable-recovery-control.py
		scripts/host/test-verified-fastboot-boot.py
		scripts/host/test-run-stable-recovery-live-gate.sh
		scripts/host/test-recovery-bundle-native.py
		scripts/host/test-prepare-recovery-runtime-bundle.py
		scripts/host/test-prepare-recovery-candidate.py
		scripts/host/test-recovery-candidate-integration.py
		scripts/host/test-headless-network-root.py
		scripts/host/test-compare-root-archives.py
		scripts/host/test-normalize-headless-core-archive-contract.sh
		scripts/host/test-kernel-source-seal.py
		scripts/host/test-stable-recovery-wrapper-cache.py
		scripts/host/test-stable-recovery-wrapper-cache-contract.sh
		scripts/host/test-stable-wrapper-slim-config.py
		scripts/host/test-stable-wrapper-slim-config-contract.sh
		scripts/host/test-arch-headless-rootfs-contract.sh
		scripts/host/test-key-indicatord.sh
		scripts/host/test-arch-headless-core-rootfs-contract.sh
		scripts/host/test-claude-readonly-review.sh
		scripts/host/test-generate-artifact-prune-plan.py
		scripts/host/test-generate-host-storage-cleanup-plan.py
		scripts/host/test-cleanup-podman-volumes.py
		scripts/device/test-kernel-build-contract.sh
		scripts/device/test-asus-kexec-stage-slim-build-contract.sh
		scripts/device/test-a660-acceptance.py
		scripts/host/test-a660-runtime-root.py
		scripts/device/test-network-root-init.sh
		scripts/device/test-persistent-root-verifier.sh
		scripts/host/test-recovery-fetch-native.py
		scripts/host/test-recovery-bundle-server.py
		scripts/host/test-recovery-host-controller.py
		scripts/host/test-recovery-init-policy.py
		scripts/host/test-reboot-fallback-to-fastboot.sh
		scripts/host/test-network-root-acm.py
		scripts/host/test-persistent-root-acm.py
		scripts/host/test-persistent-root-entry-acm.py
		scripts/host/test-network-root-gpucc-atomic-confirmation.sh
		scripts/host/test-network-root-host.sh
		scripts/host/test-capture-vendor-kernel-log.sh
		scripts/host/test-sync-network-root-time.sh
		scripts/host/test-rog5-remote-tunnel-service.sh
	)
fi

for test_path in "${tests[@]}"; do
	test_file=$repo/$test_path
	[[ -f $test_file && ! -L $test_file ]] ||
		fail "missing core offline test: $test_path"
	case $test_file in
		*.py) python3 "$test_file" ;;
		*) [[ -x $test_file ]] || fail "offline test is not executable: $test_path"
			"$test_file"
			;;
	esac
done

if [[ $tier == rootfs ]]; then
	rootfs_test=$repo/scripts/host/test-linux-rootfs-tools.sh
	[[ -f $rootfs_test && ! -L $rootfs_test && -x $rootfs_test ]] ||
		fail 'missing executable rootfs offline suite'
	"$rootfs_test"
fi

echo "PASS repository Linux $tier tier"
