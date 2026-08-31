#!/bin/sh
set -eu
PATH=/usr/sbin:/usr/bin:/sbin:/bin
LC_ALL=C
export PATH LC_ALL
root=/run/rog5-native-wifi
radio_manifest=${1:?expected radio-files.sha256 digest required}
expected_bundle=${2:?verified target bundle required}
modules_manifest=${3:?verified module archive digest required}
expected_release=${4:?kernel release from the verified execution plan required}
fail() { printf 'WIFI_PROBE_ABORT %s\n' "$*"; exit 1; }
read_optional() {
 if [ -r "$1" ]; then
  printf 'OBS present %s\n' "$1"
  cat "$1" || printf 'OBS error %s\n' "$1"
 else printf 'OBS absent %s\n' "$1"; fi
}
guard() {
 [ ! -e /run/rog5-persistent-state.runtime ] || fail 'persistent-state-active'
 count=0
 for node in /sys/class/block/sd*; do
  [ "$(cat "$node/ro")" = 1 ] || fail 'writable-UFS'
  count=$((count + 1))
 done
 [ "$count" = 117 ] || fail 'UFS-inventory'
 [ "$(cat /sys/class/power_supply/qcom-battmgr-bat/health)" = Good ] || fail 'battery-health'
 temperature=$(cat /sys/class/power_supply/qcom-battmgr-bat/temp)
 [ "$temperature" -ge 0 ] && [ "$temperature" -lt 400 ] || fail 'battery-temperature'
 [ "$(cat /sys/class/power_supply/qcom-battmgr-bat/voltage_now)" -ge 8400000 ] || fail 'battery-voltage'
 if [ -e "$root/automatic" ] || [ -L "$root/automatic" ]; then
  [ -f "$root/automatic" ] && [ ! -L "$root/automatic" ] &&
   [ "$(stat -c '%u:%g:%a:%s:%h' "$root/automatic")" = 0:0:444:25:1 ] &&
   [ "$(cat "$root/automatic")" = rog5-native-wifi-boot-v1 ] || fail 'automatic-mode'
 else
  [ "$(cat /sys/class/net/usb0/carrier)" = 1 ] || fail 'NCM-carrier'
 fi
}
collect() {
 for path in /sys/class/power_supply/*/uevent /sys/class/thermal/thermal_zone*/temp \
  /sys/bus/pci/devices/*/uevent /sys/kernel/debug/regulator/regulator_summary \
  /sys/kernel/debug/clk/clk_summary /sys/kernel/debug/devices_deferred; do
  read_optional "$path"
 done
 ip -details link show || true
 "$root/wifi-userspace/lib/ld-musl-aarch64.so.1" --library-path "$root/wifi-userspace/lib" \
  "$root/wifi-userspace/usr/sbin/iw" dev || true
 "$root/wifi-userspace/lib/ld-musl-aarch64.so.1" --library-path "$root/wifi-userspace/lib" \
  "$root/wifi-userspace/usr/sbin/iw" reg get || true
 dmesg | tail -n 700 || true
}
[ "$(id -u)" = 0 ] || fail 'root-required'
[ "$(uname -r)" = "$expected_release" ] || fail 'kernel-identity'
grep -Fqw "rog5.bundle=$expected_bundle" /proc/cmdline || fail 'target-identity'
[ "$(tr -d '\000' </sys/firmware/devicetree/base/model)" = 'ASUS ROG Phone 5' ] || fail 'model'
[ "$(sha256sum "$root/module-root-complete.tar.gz" | cut -d ' ' -f1)" = "$modules_manifest" ] || fail 'module-package'
[ "$(sha256sum "$root/load-roots.txt" | cut -d ' ' -f1)" = 43fe54dcb0f182e5f8a69049e9f3b858c1fd06ef160c343ceff27a28ce12ae44 ] || fail 'root-list'
[ "$(sha256sum "$root/radio-files.sha256" | cut -d ' ' -f1)" = "$radio_manifest" ] || fail 'radio-manifest'
(cd "$root" && sha256sum -c radio-files.sha256) || fail 'radio-file-integrity'
[ ! -d /sys/module/ath11k_pci ] || fail 'radio-already-active'
[ "$(cat /sys/kernel/tracing/instances/rog5_native_wifi/events/rog5_native_wifi/enable)" = 1 ] || fail 'pcie-trace-not-armed'
[ "$(cat /run/rog5-native-wifi-trace-owner/boot-id)" = "$(cat /proc/sys/kernel/random/boot_id)" ] || fail 'trace-boot-mismatch'
guard
umask 077
mkdir "$root/probe-entered" || fail 'probe-already-entered'
# 17*(20+2)s loads +30s activation +30s PCI +60s PHY +90s cleanup
# =584s, within 600s. The caller must budget the preceding S12 qualification.
systemd-run --unit=rog5-wifi-probe-rollback --on-active=600s --timer-property=AccuracySec=1s \
 --property=DefaultDependencies=no --property=Before=shutdown.target --property=Conflicts=shutdown.target \
 --timer-property=DefaultDependencies=no --timer-property=Before=shutdown.target --timer-property=Conflicts=shutdown.target \
 /usr/bin/systemctl reboot
systemctl is-active --quiet rog5-wifi-probe-rollback.timer || fail 'rollback-not-armed'
trap collect EXIT
printf '%s' "$root/firmware" >/sys/module/firmware_class/parameters/path
load_one() {
 module=$1
 guard
 printf 'WIFI_MODULE_ENTER %s uptime=' "$module"
 cat /proc/uptime
 if [ "$module" = ath11k_pci ]; then
  timeout -k 2 20 "$root/module-once" "$root/module-root/lib/modules/$expected_release/kernel/drivers/net/wireless/ath/ath11k/ath11k_pci.ko" || fail "module-$module"
 elif [ "$module" = pwrseq-qcom-wcn ]; then
  timeout -k 2 20 modprobe -d "$root/module-root" -S "$(uname -r)" "$module" serial_observation_ms=250 || fail "module-$module"
 elif [ "$module" = pci-pwrctrl-pwrseq ]; then
  timeout -k 2 20 modprobe -d "$root/module-root" -S "$(uname -r)" "$module" observation_ms=250 || fail "module-$module"
 else
  timeout -k 2 20 modprobe -d "$root/module-root" -S "$(uname -r)" "$module" || fail "module-$module"
 fi
 printf 'WIFI_MODULE_RETURN %s\n' "$module"
}
# Load software before starting the controller; do not bind ath11k until the
# exact PCI endpoint is visible. This avoids the prior MHI-init overlap.
[ -z "$(ls -A /sys/bus/pci/devices)" ] || fail 'unexpected-initial-PCI-device'
while IFS= read -r module; do
 case $module in phy-qcom-qmp-pcie|ath11k_pci) continue ;; esac
 load_one "$module"
done <"$root/load-roots.txt"
load_one phy-qcom-qmp-pcie
# Only this fixed activator changes the staged PMU/PHY/PCIe statuses. Its
# module dependency revalidates the held/cache-coherent S12 vote first.
guard
timeout -k 2 30 "$root/module-once" "$root/rog5-wifi-activate.ko" || fail 'radio-activation'
[ "$(cat /sys/module/rog5_wifi_activate/parameters/result)" = 0 ] || fail 'radio-activation-result'
pci=/sys/bus/pci/devices/0000:01:00.0
for attempt in $(seq 1 30); do
 guard
 if [ -r "$pci/vendor" ] && [ -r "$pci/device" ] &&
  [ -r "$pci/subsystem_vendor" ] && [ -r "$pci/subsystem_device" ]; then
  break
 fi
 sleep 1
done
[ -r "$pci/vendor" ] || fail 'PCI-endpoint-not-enumerated'
[ "$(cat "$pci/vendor")" = 0x17cb ] && [ "$(cat "$pci/device")" = 0x1103 ] &&
 [ "$(cat "$pci/subsystem_vendor")" = 0x17cb ] && [ "$(cat "$pci/subsystem_device")" = 0x0108 ] || fail 'PCI-endpoint-identity'
printf 'WIFI_PCI_IDENTITY_PASS\n'
load_one ath11k_pci
for attempt in $(seq 1 60); do
 guard
 if [ -d /sys/class/ieee80211/phy0 ]; then
  printf 'WIFI_PHY_READY uptime='
  cat /proc/uptime
  exit 0
 fi
 sleep 1
done
fail 'phy-not-ready-after-60s'
