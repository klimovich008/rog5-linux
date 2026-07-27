#!/bin/bash
set -euo pipefail

stage=${STAGE_ROOT:-/stage}
[[ $stage == /* ]] || {
	echo "FAIL stage root is not absolute: $stage" >&2
	exit 1
}
ARCH_DEVICE_STAGE=scripts/device/stage-arch-rootfs-v3.sh \
	exec "$stage/workspace/repo/scripts/device/run-arch-rootfs-stage.sh"
