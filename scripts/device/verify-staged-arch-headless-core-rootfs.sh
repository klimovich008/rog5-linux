#!/bin/bash
set -euo pipefail
trap 'echo "FAIL headless-core verify line=$LINENO command=$BASH_COMMAND" >&2' ERR

repo=/workspace/repo
binary=/usr/local/libexec/rog5-key-indicatord
: "${TARGET_KERNEL_RELEASE:?missing TARGET_KERNEL_RELEASE}"
: "${INDICATOR_SHA256:?missing INDICATOR_SHA256}"

fail() {
	echo "FAIL $*" >&2
	exit 1
}

core_profile=${EXPECTED_HEADLESS_PROFILE:-headless-core-v2}
case $core_profile in
	headless-core-v2|headless-core-v3) ;;
	*) fail "unsupported headless-core profile: $core_profile" ;;
esac

EXPECTED_HEADLESS_PROFILE=$core_profile \
TARGET_KERNEL_RELEASE=$TARGET_KERNEL_RELEASE \
	/bin/bash "$repo/scripts/device/verify-staged-arch-headless-rootfs.sh"

[[ -f $binary && ! -L $binary && -x $binary ]]
[[ $(stat -c %U:%G:%a "$binary") == root:root:755 ]]
[[ $(stat -c %s "$binary") == 67520 ]]
[[ $(sha256sum "$binary" | cut -d' ' -f1) == "$INDICATOR_SHA256" ]]
grep -Fqx "indicator_sha256=$INDICATOR_SHA256" /etc/rog5/build
grep -Fqx 'indicator_policy=power-key-green-status-pulse-v1' \
	/etc/rog5/build

cmp /etc/systemd/system/rog5-key-indicator.service \
	"$repo/packaging/arch/rog5-key-indicator.service"
cmp /etc/modules-load.d/rog5-status-led.conf \
	"$repo/packaging/arch/rog5-status-led.modules.conf"
[[ $(systemctl is-enabled rog5-key-indicator.service) == enabled ]]
systemd-analyze verify \
	/etc/systemd/system/rog5-key-indicator.service >/dev/null

mapfile -t lpg_modules < <(
	find "/lib/modules/$TARGET_KERNEL_RELEASE" -type f \
		-name 'leds-qcom-lpg.ko' -print
)
[[ ${#lpg_modules[@]} == 1 ]] ||
	fail "expected one Qualcomm LPG module, found ${#lpg_modules[@]}"
grep -Fqx 'leds-qcom-lpg' \
	<(sed -e 's/[[:space:]]*#.*$//' -e '/^[[:space:]]*$/d' \
		/etc/modules-load.d/rog5-status-led.conf)

for command in chromium greetd krdpserver kwin_wayland node npm \
	python python3 startplasma-wayland ttyd vulkaninfo; do
	if command -v "$command" >/dev/null; then
		fail "headless-core root retained deferred command: $command"
	fi
done

echo "PASS staged native headless-core Arch rootfs kernel=$TARGET_KERNEL_RELEASE"
