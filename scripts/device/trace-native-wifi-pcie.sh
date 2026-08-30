#!/bin/sh
# A private trace instance; never enables PCIe, loads a driver or accesses storage.
set -eu
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
action=${1:?usage: trace-native-wifi-pcie.sh plan|check|start|read|stop [BOOT_ID]}
trace=/sys/kernel/tracing
group=rog5_native_wifi
instance=$trace/instances/$group
owner=/run/rog5-native-wifi-trace-owner
symbols='qcom_pcie_host_init qcom_pcie_init_2_7_0 clk_bulk_prepare clk_bulk_enable
reset_control_assert reset_control_deassert phy_power_on
pci_pwrctrl_create_devices pci_pwrctrl_power_on_devices dw_pcie_version_detect'

fail() { printf 'FAIL native PCIe trace: %s\n' "$*" >&2; exit 1; }
plan() {
 for symbol in $symbols; do
  printf 'p:%s/enter_%s %s\n' "$group" "$symbol" "$symbol"
  if [ "$symbol" = dw_pcie_version_detect ]; then
   printf 'r64:%s/return_%s %s\n' "$group" "$symbol" "$symbol"
  else
   printf 'r64:%s/return_%s %s result=$retval:s32\n' "$group" "$symbol" "$symbol"
  fi
 done
}
if [ "$action" = plan ]; then plan; exit 0; fi
case $action in check|start|read|stop) ;; *) fail 'unknown action' ;; esac
boot=${2:?source boot ID required}
[ "$(id -u)" = 0 ] || fail 'root required'
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$boot" ] || fail 'boot changed'
[ "$(uname -r)" = 7.1.4-g359318de534f ] || fail 'kernel changed'
[ "$(tr -d '\000' </sys/firmware/devicetree/base/model)" = 'ASUS ROG Phone 5' ] || fail 'model changed'
[ "$(stat -f -c %T "$trace")" = tracefs ] || fail 'tracefs unavailable'
[ -w "$trace/kprobe_events" ] || fail 'kprobe events unavailable'

owns_instance() {
 [ -d "$owner" ] && [ ! -L "$owner" ] &&
  [ "$(stat -c '%u:%g:%a' "$owner")" = 0:0:700 ] &&
  [ -f "$owner/boot-id" ] && [ ! -L "$owner/boot-id" ] &&
  [ "$(cat "$owner/boot-id")" = "$boot" ]
}
cleanup() {
 owns_instance || return 1
 result=0
 if [ -d "$instance" ]; then
  printf '0\n' >"$instance/tracing_on" || result=1
  if [ -e "$instance/events/$group/enable" ]; then
   printf '0\n' >"$instance/events/$group/enable" || result=1
  fi
 fi
 for symbol in $symbols; do
  for direction in enter return; do
   if [ -d "$trace/events/$group/${direction}_$symbol" ]; then
    printf '%s\n' "-:$group/${direction}_$symbol" >>"$trace/kprobe_events" || result=1
   fi
  done
 done
 if [ -d "$instance" ]; then rmdir "$instance" || result=1; fi
 [ "$result" = 0 ] || return 1
 rm -- "$owner/boot-id"
 rmdir "$owner"
}
case $action in
 stop) cleanup; echo 'PASS native PCIe trace removed'; exit 0 ;;
 read)
  owns_instance || fail 'instance is not owned by this boot'
  # Outlive the 600s radio rollback plus setup/fallback margin.
  exec timeout 900 cat "$instance/trace_pipe"
  ;;
esac
[ ! -e "$instance" ] && [ ! -e "$owner" ] &&
 [ ! -e "$trace/events/$group" ] || fail 'trace namespace already exists'
for symbol in $symbols; do
 awk -v wanted="$symbol" '$3 == wanted { count++ } END { exit count != 1 }' \
  /proc/kallsyms || fail "missing or ambiguous symbol: $symbol"
done
if [ "$action" = check ]; then echo 'PASS native PCIe trace capability'; exit 0; fi
umask 077
mkdir "$owner"
printf '%s\n' "$boot" >"$owner/boot-id"
trap 'cleanup || true' EXIT
mkdir "$instance"
printf '0\n' >"$instance/tracing_on"
printf '64\n' >"$instance/buffer_size_kb"
plan | while IFS= read -r definition; do
 printf '%s\n' "$definition" >>"$trace/kprobe_events" || exit 1
done
printf '1\n' >"$instance/events/$group/enable"
printf '1\n' >"$instance/tracing_on"
printf 'ROG5_NATIVE_WIFI_TRACE_READY boot=%s\n' "$boot" >"$instance/trace_marker"
trap - EXIT
echo 'PASS native PCIe trace armed; hardware unchanged'
