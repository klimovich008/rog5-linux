#!/bin/bash
set -euo pipefail
trap 'echo "FAIL headless-core stage line=$LINENO command=$BASH_COMMAND" >&2' ERR

repo=${REPO:-/workspace/repo}
indicator=${INDICATOR_BINARY:-/input/rog5-key-indicatord}
: "${INDICATOR_SHA256:?missing INDICATOR_SHA256}"
: "${TARGET_KERNEL_RELEASE:?missing TARGET_KERNEL_RELEASE}"

[[ -f $indicator && ! -L $indicator && -x $indicator ]]
[[ $(stat -c %s "$indicator") == 67520 ]]
[[ $(sha256sum "$indicator" | cut -d' ' -f1) == "$INDICATOR_SHA256" ]]

HEADLESS_BUILD_PROFILE=headless-ssh-v1 \
	/bin/bash "$repo/scripts/device/stage-arch-headless-rootfs.sh"

install -Dm0755 "$indicator" \
	/usr/local/libexec/rog5-key-indicatord
install -Dm0644 "$repo/packaging/arch/rog5-key-indicator.service" \
	/etc/systemd/system/rog5-key-indicator.service
install -Dm0644 "$repo/packaging/arch/rog5-status-led.modules.conf" \
	/etc/modules-load.d/rog5-status-led.conf
systemctl enable rog5-key-indicator.service

sed -i 's/^profile=headless-ssh-v1$/profile=headless-core-v2/' \
	/etc/rog5/build
grep -Fqx 'profile=headless-core-v2' /etc/rog5/build
cat >>/etc/rog5/build <<EOF
indicator_sha256=$INDICATOR_SHA256
indicator_policy=power-key-green-status-pulse-v1
EOF

EXPECTED_HEADLESS_PROFILE=headless-core-v2 \
INDICATOR_SHA256=$INDICATOR_SHA256 \
TARGET_KERNEL_RELEASE=$TARGET_KERNEL_RELEASE \
	/bin/bash "$repo/scripts/device/verify-staged-arch-headless-core-rootfs.sh"
