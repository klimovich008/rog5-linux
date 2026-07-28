#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
target=${TARGET:-$repo/scripts/device/load-mainline-persistent-root-entry.sh}
[ -x "$target" ] || {
	echo "FAIL missing P2 entry loader: $target" >&2
	exit 1
}
sh -n "$target"

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
mkdir -p "$stage/bin" "$stage/drivers/hh-watchdog" "$stage/drivers/other" \
	"$stage/payload" "$stage/sys/good/of_node" \
	"$stage/sys/wrong-driver/of_node" \
	"$stage/sys/wrong-compatible/of_node"

printf 'kernel\n' >"$stage/payload/Image"
printf 'dtb\n' >"$stage/payload/board.dtb"
printf 'initramfs\n' | gzip -n >"$stage/payload/initramfs.cpio.gz"
(cd "$stage/payload" &&
	sha256sum Image board.dtb initramfs.cpio.gz >SHA256SUMS)

ln -s "$stage/drivers/hh-watchdog" "$stage/sys/good/driver"
ln -s "$stage/drivers/other" "$stage/sys/wrong-driver/driver"
ln -s "$stage/drivers/hh-watchdog" \
	"$stage/sys/wrong-compatible/driver"
printf 'qcom,hh-watchdog\000' >"$stage/sys/good/of_node/compatible"
printf 'qcom,hh-watchdog\000' \
	>"$stage/sys/wrong-driver/of_node/compatible"
printf 'qcom,other-watchdog\000' \
	>"$stage/sys/wrong-compatible/of_node/compatible"
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

export KEXEC_RECORD=$stage/kexec.args
PATH=$stage/bin:$PATH \
	PAYLOAD=$stage/payload \
	SYS_DEVICES=$stage/sys \
	ROG5_RECOVERY_TIMEOUT=600 \
	"$target" >/dev/null

grep -qx 1 "$stage/sys/good/disable"
grep -qx 0 "$stage/sys/wrong-driver/disable"
grep -qx 0 "$stage/sys/wrong-compatible/disable"
grep -qx -- -c "$KEXEC_RECORD"
grep -qx -- -l "$KEXEC_RECORD"
for required in \
	rog5.persistent_ro=1 \
	rog5.ufs_discovery=1 \
	rog5.p2_entry_diag=1 \
	rog5.recovery_timeout=600 \
	ramoops.mem_address=0x9b800000 \
	ramoops.mem_size=0x400000 \
	ramoops.record_size=0x100000 \
	ramoops.console_size=0x300000 \
	ramoops.pmsg_size=0 \
	ramoops.ftrace_size=0 \
	ramoops.dump_oops=1; do
	[ "$(grep -Fo "$required" "$KEXEC_RECORD" | wc -l)" -eq 1 ]
done

for invalid in 299 901 not-a-number; do
	rm -f "$KEXEC_RECORD"
	set +e
	PATH=$stage/bin:$PATH \
		PAYLOAD=$stage/payload \
		SYS_DEVICES=$stage/sys \
		ROG5_RECOVERY_TIMEOUT=$invalid \
		"$target" >/dev/null 2>&1
	status=$?
	set -e
	[ "$status" -ne 0 ]
	[ ! -e "$KEXEC_RECORD" ]
done

if grep -Eq \
	'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*(ext[234]|f2fs|btrfs)|mkfs|fsck' \
	"$target"; then
	echo 'FAIL P2 entry loader contains a flash or filesystem-write path' >&2
	exit 1
fi

echo 'PASS P2 early-entry loader pins read-only UFS, exact diagnostic token, ramoops, and bounded staging timeout'
