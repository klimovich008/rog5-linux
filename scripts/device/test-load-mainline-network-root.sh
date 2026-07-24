#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
target=${TARGET:-$repo/scripts/device/load-mainline-network-root.sh}
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/bin" "$stage/drivers/hh-watchdog" "$stage/drivers/other" \
	"$stage/payload" "$stage/sys/good/of_node" "$stage/sys/wrong-driver/of_node" \
	"$stage/sys/wrong-compatible/of_node"

printf 'kernel\n' >"$stage/payload/Image"
printf 'dtb\n' >"$stage/payload/board.dtb"
printf 'initramfs\n' | gzip -n >"$stage/payload/initramfs.cpio.gz"
(cd "$stage/payload" && sha256sum Image board.dtb initramfs.cpio.gz >SHA256SUMS)

ln -s "$stage/drivers/hh-watchdog" "$stage/sys/good/driver"
ln -s "$stage/drivers/other" "$stage/sys/wrong-driver/driver"
ln -s "$stage/drivers/hh-watchdog" "$stage/sys/wrong-compatible/driver"
printf 'qcom,hh-watchdog\000' >"$stage/sys/good/of_node/compatible"
printf 'qcom,hh-watchdog\000' >"$stage/sys/wrong-driver/of_node/compatible"
printf 'qcom,other-watchdog\000' >"$stage/sys/wrong-compatible/of_node/compatible"
for node in good wrong-driver wrong-compatible; do
	printf '0\n' >"$stage/sys/$node/disable"
done

cat >"$stage/bin/dmesg" <<'EOF'
#!/bin/sh
exit 0
EOF
cat >"$stage/bin/kexec" <<'EOF'
#!/bin/sh
printf '%s\n' "$@" >"$KEXEC_RECORD"
EOF
chmod +x "$stage/bin/dmesg" "$stage/bin/kexec"

cat >"$stage/cmdline" <<'EOF'
rog5.netroot=0 rog5.recovery_timeout=180 ramoops.mem_address=0x1000000 ramoops.mem_size=0x400000 ramoops.record_size=0x100000 ramoops.console_size=0x100000 ramoops.pmsg_size=0x100000 ramoops.ftrace_size=0 ramoops.dump_oops=1
EOF

export KEXEC_RECORD=$stage/kexec.args
PATH=$stage/bin:$PATH \
	PAYLOAD=$stage/payload \
	SYS_DEVICES=$stage/sys \
	PROC_CMDLINE=$stage/cmdline \
	ROG5_RECOVERY_TIMEOUT=600 \
	"$target" >/dev/null

grep -qx 1 "$stage/sys/good/disable"
grep -qx 0 "$stage/sys/wrong-driver/disable"
grep -qx 0 "$stage/sys/wrong-compatible/disable"
grep -qx -- -c "$KEXEC_RECORD"
grep -qx -- -l "$KEXEC_RECORD"
[ "$(grep -o 'rog5\.netroot=1' "$KEXEC_RECORD" | wc -l)" -eq 1 ]
! grep -q 'rog5\.netroot=0' "$KEXEC_RECORD"
[ "$(grep -c 'rog5.recovery_timeout=600' "$KEXEC_RECORD")" -eq 1 ]
! grep -q 'rog5.recovery_timeout=180' "$KEXEC_RECORD"
! grep -q 'systemd.mask=' "$KEXEC_RECORD"

rm -f "$KEXEC_RECORD"
PATH=$stage/bin:$PATH \
	PAYLOAD=$stage/payload \
	SYS_DEVICES=$stage/sys \
	PROC_CMDLINE=$stage/cmdline \
	ROG5_RECOVERY_TIMEOUT=600 \
	ROG5_SYSTEMD_DIAGNOSTIC=1 \
	"$target" >/dev/null
[ "$(grep -c 'systemd.mask=systemd-udev-trigger.service' "$KEXEC_RECORD")" -eq 1 ]
[ "$(grep -c 'systemd.mask=systemd-modules-load.service' "$KEXEC_RECORD")" -eq 1 ]

rm -f "$KEXEC_RECORD"
set +e
PATH=$stage/bin:$PATH \
	PAYLOAD=$stage/payload \
	SYS_DEVICES=$stage/sys \
	PROC_CMDLINE=$stage/cmdline \
	ROG5_SYSTEMD_DIAGNOSTIC=invalid \
	"$target" >/dev/null 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
[ ! -e "$KEXEC_RECORD" ]

for invalid in 59 901 not-a-number; do
	rm -f "$KEXEC_RECORD"
	set +e
	PATH=$stage/bin:$PATH \
		PAYLOAD=$stage/payload \
		SYS_DEVICES=$stage/sys \
		PROC_CMDLINE=$stage/cmdline \
		ROG5_RECOVERY_TIMEOUT=$invalid \
		"$target" >/dev/null 2>&1
	status=$?
	set -e
	[ "$status" -ne 0 ]
	[ ! -e "$KEXEC_RECORD" ]
done

echo 'PASS network-root loader pins mode, diagnostic masks, watchdog allowlist, and timeout'
