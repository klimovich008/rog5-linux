#!/bin/bash
set -euo pipefail

ARCH_DEVICE_STAGE=scripts/device/stage-arch-rootfs-v3.sh \
	exec /workspace/repo/scripts/device/run-arch-rootfs-stage.sh
