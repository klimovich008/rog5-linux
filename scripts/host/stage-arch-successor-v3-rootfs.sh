#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
authorized_key=${1:?usage: stage-arch-successor-v3-rootfs.sh AUTHORIZED_KEY [OUTPUT]}
output=${2:-$repo/artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor-v3.tar.gz}

ARCH_ROOTFS_GENERATION=v3 \
	exec "$repo/scripts/host/stage-arch-rootfs.sh" "$authorized_key" "$output"
