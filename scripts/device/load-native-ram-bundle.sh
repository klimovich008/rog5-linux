#!/bin/sh
set -eu
PATH=/usr/sbin:/usr/bin:/sbin:/bin
LC_ALL=C
export PATH LC_ALL
# Run only after host-side admission and durable one-use claim consumption.
# This path never writes a partition or changes the persistent bundle selector.
action=${1:?usage: load-native-ram-bundle.sh check|execute BUNDLE MANIFEST_SHA BOOT_ID TOOL_MANIFEST_SHA}
bundle=${2:?missing bundle}
manifest=${3:?missing manifest hash}
boot_id=${4:?missing source boot ID}
tool_manifest=${5:?missing tool manifest hash}
[ "$#" = 5 ]
case $action in check|execute) ;; *) exit 1 ;; esac
root=/run/rog5-native-kexec
tools=$root/tools
loader=$tools/lib/ld-musl-aarch64.so.1
kexec=$tools/usr/sbin/kexec
verifier=$tools/usr/libexec/rog5-bundle-verify
trust=/etc/rog5/recovery-bundle-ed25519.pub
plan=$root/verified-plan

fail() { printf 'FAIL native RAM trial: %s\n' "$*" >&2; exit 1; }
exact() {
	[ -f "$1" ] && [ ! -L "$1" ] || return 1
	[ "$(stat -c %u "$1")" = 0 ] || return 1
	[ "$(sha256sum "$1" | cut -d ' ' -f 1)" = "$2" ]
}

[ "$(id -u)" = 0 ] || fail 'root required'
for directory in "$root" "$tools"; do
	[ -d "$directory" ] && [ ! -L "$directory" ] &&
		[ "$(stat -c '%u:%g:%a' "$directory")" = 0:0:700 ] || fail 'unsafe runtime directory'
done
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$boot_id" ] || fail 'source boot changed'
[ "$(tr -d '\000' </sys/firmware/devicetree/base/model)" = 'ASUS ROG Phone 5' ] || fail 'wrong model'
grep -Fqw 'rog5.bundle=persistent-native-root-v11' /proc/cmdline || fail 'source is not V11'
[ "$(uname -r)" = 7.1.4-g359318de534f ] || fail 'source kernel changed'
[ "$(cat /proc/sys/kernel/kexec_load_disabled)" = 0 ] || fail 'kexec is disabled'
[ "$(cat /sys/kernel/kexec_loaded)" = 0 ] || fail 'another kexec image is loaded'
[ "$(cat /sys/class/power_supply/qcom-battmgr-bat/health)" = Good ] || fail 'battery health'
[ "$(cat /sys/class/power_supply/qcom-battmgr-bat/voltage_now)" -ge 8400000 ] || fail 'battery voltage'
[ "$(cat /sys/class/power_supply/qcom-battmgr-bat/temp)" -lt 400 ] || fail 'battery temperature'
[ "$(cat /sys/class/power_supply/qcom-battmgr-bat/temp)" -ge 0 ] || fail 'battery below freezing'
exact "$kexec" 5e5d0a78b3f0bcf3921ff060f4dce5011cbac24b5e12fedeb8ca03ea5b40d015 || fail 'kexec identity'
exact "$verifier" c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb || fail 'verifier identity'
exact "$trust" cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 || fail 'trust key identity'
exact "$root/tool-files.sha256" "$tool_manifest" || fail 'runtime manifest identity'
[ -z "$(find "$tools" -type l -print -quit)" ] || fail 'runtime contains symlinks'
[ "$(find "$tools" -type f | wc -l)" = "$(wc -l <"$root/tool-files.sha256")" ] || fail 'runtime inventory'
(cd "$tools" && sha256sum -c "$root/tool-files.sha256") || fail 'runtime library identity'
[ -x "$loader" ] && [ ! -L "$loader" ] || fail 'matching runtime loader unavailable'
"$loader" --library-path "$tools/lib:$tools/usr/lib" "$kexec" --version
"$verifier" "$bundle" "$manifest" >"$plan"
[ "$(grep -c '^cmdline=' "$plan")" = 1 ] || fail 'invalid verified plan'
grep -qx 'profile=persistent-root-ro-v1' "$plan" || fail 'wrong target profile'
cmdline=$(sed -n 's/^cmdline=//p' "$plan")
# The trial changes only the RAM exitrd. Never replace the persistent selector.
exact /run/initramfs/shutdown ec3c7fd28aa099a147a6f3c693c3eb4142be92f2dfd62c94efa5d06a2eec8ec2 || fail 'source shutdown changed'
[ ! -e /run/initramfs/rog5-kexec-exec ] || fail 'exitrd trial already staged'
[ -x "$tools/usr/libexec/rog5-kexec-exec" ] || fail 'static executor missing'
if [ -e "$tools/usr/libexec/rog5-exitrd-log" ]; then
	[ -f "$tools/usr/libexec/rog5-exitrd-log" ] &&
		[ ! -L "$tools/usr/libexec/rog5-exitrd-log" ] &&
		[ -x "$tools/usr/libexec/rog5-exitrd-log" ] || fail 'invalid optional serial logger'
fi
[ ! -e /run/initramfs/rog5-exitrd-log ] && [ ! -L /run/initramfs/rog5-exitrd-log ] ||
	fail 'exitrd logger already staged'
sh -n "$tools/shutdown" || fail 'shutdown syntax'
[ "$action" = execute ] || { echo 'PASS native RAM trial preflight'; exit 0; }

# The local transaction helper performs this quiesce after the host dispatches
# it and before SSH can disappear. Exitrd remains an independent fallback.
[ ! -e /run/rog5-persistent-state.runtime ] || fail 'persistent state remains mounted'
count=0
for node in /sys/class/block/sd*; do
	[ -e "$node/dev" ] || continue
	[ "$(cat "$node/ro")" = 1 ] || fail 'storage is not read-only'
	count=$((count + 1))
done
[ "$count" = 117 ] || fail 'storage inventory changed'
umask 077
mkdir "$root/entered" || fail 'trial already entered; do not retry'
payload=/run/rog5-bundles/$bundle
printf 'ROG5_NATIVE_KEXEC_LOAD bundle=%s manifest=%s\n' "$bundle" "$manifest"
"$loader" --library-path "$tools/lib:$tools/usr/lib" "$kexec" -c -l "$payload/Image" \
	--dtb="$payload/board.dtb" --initrd="$payload/initramfs.cpio.gz" \
	--command-line="$cmdline"
[ "$(cat /sys/kernel/kexec_loaded)" = 1 ] || fail 'kernel did not confirm load'
cp "$tools/usr/libexec/rog5-kexec-exec" /run/initramfs/rog5-kexec-exec
chmod 500 /run/initramfs/rog5-kexec-exec
cp "$tools/shutdown" /run/initramfs/shutdown.native
chmod 500 /run/initramfs/shutdown.native
cmp "$tools/shutdown" /run/initramfs/shutdown.native || fail 'shutdown staging'
cmp "$tools/usr/libexec/rog5-kexec-exec" /run/initramfs/rog5-kexec-exec || fail 'executor staging'
if [ -x "$tools/usr/libexec/rog5-exitrd-log" ]; then
	cp "$tools/usr/libexec/rog5-exitrd-log" /run/initramfs/rog5-exitrd-log
	chmod 500 /run/initramfs/rog5-exitrd-log
	cmp "$tools/usr/libexec/rog5-exitrd-log" /run/initramfs/rog5-exitrd-log || fail 'logger staging'
fi
(cd /run/initramfs && sha256sum rog5-kexec-exec >rog5-kexec-exec.sha256)
mv /run/initramfs/shutdown.native /run/initramfs/shutdown
printf 'ROG5_NATIVE_KEXEC_EXECUTE bundle=%s\n' "$bundle"
sync
systemctl kexec --no-block || fail 'shutdown request failed; candidate remains consumed'
