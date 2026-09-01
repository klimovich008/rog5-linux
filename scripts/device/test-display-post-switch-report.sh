#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
target=$repo/initramfs/native-wifi/display-post-switch-report
unit=$repo/initramfs/native-wifi/units/rog5-display-post-switch.service

[[ -x $target ]] || fail 'display post-switch reporter is absent'
[[ -f $unit && ! -L $unit ]] || fail 'display post-switch unit is absent'
sh -n "$target"

for required in \
	'format=rog5-display-post-switch-v1' \
	'refgen_status=' \
	'dsi_status=' \
	'drm_status=' \
	'fb_status=' \
	'backlight_status=' \
	'status_screen_status=' \
	'dmesg_tail_hex=' \
	'169.254.77.1 8077'; do
	grep -Fq "$required" "$target" || fail "reporter lacks $required"
done

for forbidden in 'mount ' 'umount ' 'blockdev ' 'mkfs' 'sgdisk' \
	'dd of=' '>/sys/class/backlight' 'systemctl reboot'; do
	! grep -Fq "$forbidden" "$target" ||
		fail "reporter contains forbidden write path: $forbidden"
done

grep -Fqx 'ExecStart=/run/rog5-native-wifi/display-post-switch-report send' "$unit" ||
	fail 'unit does not invoke the sealed reporter'
grep -Fqx 'TimeoutStartSec=90s' "$unit" || fail 'unit timeout changed'
grep -Fqx 'Before=basic.target shutdown.target' "$unit" ||
	fail 'observer is not ordered before basic target'
grep -Fqx 'WantedBy=sysinit.target' "$unit" ||
	fail 'observer is not attached to sysinit target'
! grep -Fq 'multi-user.target' "$unit" ||
	fail 'observer still depends on multi-user target'
! grep -Eq '^OnFailure=|reboot|poweroff' "$unit" ||
	fail 'optional display observer can trigger rollback'

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
sys=$work/sys
proc=$work/proc
dev=$work/dev
run=$work/run
bin=$work/bin
mkdir -p \
	"$sys/bus/platform/devices/88e7000.regulator" \
	"$sys/bus/platform/devices/ae94000.dsi" \
	"$sys/bus/platform/drivers/qcom-refgen-regulator" \
	"$sys/bus/platform/drivers/msm_dsi" \
	"$sys/class/regulator/regulator.12" \
	"$sys/class/drm/card0" "$sys/class/drm/card0-DSI-1" \
	"$sys/class/backlight/panel0-backlight" \
	"$proc/sys/kernel/random" "$dev" "$run" "$bin" \
	"$work/root/usr/local/bin" "$work/root/usr/local/libexec" \
	"$work/root/run/systemd/system"
ln -s ../../drivers/qcom-refgen-regulator \
	"$sys/bus/platform/devices/88e7000.regulator/driver"
ln -s ../../drivers/msm_dsi \
	"$sys/bus/platform/devices/ae94000.dsi/driver"
printf 'refgen\n' >"$sys/class/regulator/regulator.12/name"
printf 'connected\n' >"$sys/class/drm/card0-DSI-1/status"
printf '1080x2448\n' >"$sys/class/drm/card0-DSI-1/modes"
printf '1023\n' >"$sys/class/backlight/panel0-backlight/max_brightness"
printf '0\n' >"$sys/class/backlight/panel0-backlight/brightness"
ln -s /dev/null "$dev/fb0"
printf '7.1.4-rog5-display60-v1\n' >"$proc/sys/kernel/osrelease"
printf '11111111-2222-3333-4444-555555555555\n' >"$proc/sys/kernel/random/boot_id"
printf 'rog5.bundle=persistent-native-root-display60-v6\n' >"$proc/cmdline"
for path in \
	"$work/root/usr/local/bin/rog5-screen-toggle.sh" \
	"$work/root/usr/local/libexec/rog5-status-screen" \
	"$work/root/usr/local/libexec/rog5-power-buttond"; do
	printf '#!/bin/sh\nexit 0\n' >"$path"
	chmod 0755 "$path"
done
for service in rog5-status-screen rog5-power-button; do
	printf '[Service]\n' >"$work/root/run/systemd/system/$service.service"
done
cat >"$bin/dmesg" <<'EOF'
#!/bin/sh
printf '%s\n' 'qcom-refgen-regulator 88e7000.regulator: ready' \
	'msm_dsi ae94000.dsi: bound' 'drm: fb0 registered'
EOF
chmod 0755 "$bin/dmesg"
cat >"$bin/busybox" <<'EOF'
#!/bin/sh
applet=$1
shift
exec "$applet" "$@"
EOF
chmod 0755 "$bin/busybox"

record=$work/record
PATH="$bin:/usr/bin:/bin" \
	ROG5_OBSERVER_SYS_ROOT=$sys \
	ROG5_OBSERVER_PROC_ROOT=$proc \
	ROG5_OBSERVER_DEV_ROOT=$dev \
	ROG5_OBSERVER_RUN_ROOT=$run \
	ROG5_OBSERVER_TARGET_ROOT=$work/root \
	ROG5_OBSERVER_BUSYBOX=$bin/busybox \
	ROG5_OBSERVER_DMESG=$bin/dmesg \
	ROG5_OBSERVER_SETTLE_SECONDS=0 \
	"$target" record >"$record"

for exact in \
	'format=rog5-display-post-switch-v1' \
	'candidate=persistent-native-root-display60-v6' \
	'target_release=7.1.4-rog5-display60-v1' \
	'boot_id=11111111-2222-3333-4444-555555555555' \
	'refgen_status=present' \
	'dsi_status=present' \
	'drm_status=present' \
	'fb_status=present' \
	'backlight_status=present' \
	'status_screen_status=present' \
	'result=PASS'; do
	grep -Fqx "$exact" "$record" || fail "present fixture lacks $exact"
done
grep -Eq '^dmesg_tail_hex=[0-9a-f]+$' "$record" ||
	fail 'dmesg evidence is not bounded hex'

rm -f "$sys/bus/platform/devices/ae94000.dsi/driver" "$dev/fb0"
rm -rf -- "$sys/class/drm/card0" "$sys/class/drm/card0-DSI-1" \
	"$sys/class/backlight/panel0-backlight"
PATH="$bin:/usr/bin:/bin" \
	ROG5_OBSERVER_SYS_ROOT=$sys \
	ROG5_OBSERVER_PROC_ROOT=$proc \
	ROG5_OBSERVER_DEV_ROOT=$dev \
	ROG5_OBSERVER_RUN_ROOT=$run \
	ROG5_OBSERVER_TARGET_ROOT=$work/root \
	ROG5_OBSERVER_BUSYBOX=$bin/busybox \
	ROG5_OBSERVER_DMESG=$bin/dmesg \
	ROG5_OBSERVER_SETTLE_SECONDS=0 \
	"$target" record >"$work/absent"
for exact in 'dsi_status=absent' 'drm_status=absent' 'fb_status=absent' \
	'backlight_status=absent' 'result=PASS'; do
	grep -Fqx "$exact" "$work/absent" || fail "absent fixture lacks $exact"
done

echo 'PASS display post-switch observer is read-only, bounded, and non-fatal'
