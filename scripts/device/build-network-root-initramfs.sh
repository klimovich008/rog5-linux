#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "$#" -eq 2 ] ||
	fail 'usage: build-network-root-initramfs.sh BASE OUTPUT'
base=$1
output=$2
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
init=$repo/initramfs/network-root-init
shutdown=$repo/initramfs/network-root-shutdown
charging_probe=$repo/scripts/device/probe-network-root-battery-telemetry.sh
power_usb_profile=$repo/initramfs/generated-power-usb-active.sh
xattr_projection=$repo/configs/network-roots/rog5-nfs4-xattr-projection-v1
verifier_builder=$repo/scripts/device/build-persistent-root-verifier-static.sh
reviewed_verifier=${NETWORK_ROOT_VERIFIER:-}
reviewed_verifier_hash=2bcead5ca06751d2744cdf0199802ba7ea089257ff383301d1c371f1ef60e28f
reviewed_reporter=${NETWORK_ROOT_DIAGNOSTIC_REPORTER:-}
reviewed_reporter_size=67288
reviewed_reporter_hash=437747043b5d606d82e00c37b8a3e45f54a96cdb9c5c22780bb285ab10650a9d
accepted_base=4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
epoch=1681862400
export LC_ALL=C

for command in cpio cut dirname find grep gzip install ln mktemp readelf rm \
	sha256sum sort stat touch; do
	command -v "$command" >/dev/null ||
		fail "missing network-root initramfs build command: $command"
done
for path in "$init" "$shutdown" "$charging_probe"; do
	[ -x "$path" ] && [ -f "$path" ] && [ ! -L "$path" ] ||
		fail "missing initramfs source: $path"
done
[ -r "$power_usb_profile" ] && [ -f "$power_usb_profile" ] &&
	[ ! -L "$power_usb_profile" ] ||
	fail 'generated power/USB identity is absent or linked'
sh -n "$power_usb_profile"
[ -r "$xattr_projection" ] && [ -f "$xattr_projection" ] &&
	[ ! -L "$xattr_projection" ] ||
	fail "missing xattr projection: $xattr_projection"
if [ -z "$reviewed_verifier" ]; then
	[ -x "$verifier_builder" ] && [ -f "$verifier_builder" ] &&
		[ ! -L "$verifier_builder" ] ||
		fail 'reviewed static verifier builder is absent or linked'
else
	case $reviewed_verifier in
		/*) ;;
		*) fail 'NETWORK_ROOT_VERIFIER must be an absolute path' ;;
	esac
	[ -x "$reviewed_verifier" ] && [ -f "$reviewed_verifier" ] &&
		[ ! -L "$reviewed_verifier" ] ||
		fail 'reviewed static verifier artifact is absent or linked'
	[ "$(sha256sum "$reviewed_verifier" | cut -d ' ' -f 1)" = \
		"$reviewed_verifier_hash" ] ||
		fail 'reviewed static verifier artifact hash changed'
fi
if [ -n "$reviewed_reporter" ]; then
	case $reviewed_reporter in
		/*) ;;
		*) fail 'NETWORK_ROOT_DIAGNOSTIC_REPORTER must be an absolute path' ;;
	esac
	[ -x "$reviewed_reporter" ] && [ -f "$reviewed_reporter" ] &&
		[ ! -L "$reviewed_reporter" ] ||
		fail 'reviewed diagnostic reporter artifact is absent or linked'
	[ "$(stat -c %s "$reviewed_reporter")" -eq "$reviewed_reporter_size" ] ||
		fail 'reviewed diagnostic reporter artifact size changed'
	[ "$(sha256sum "$reviewed_reporter" | cut -d ' ' -f 1)" = \
		"$reviewed_reporter_hash" ] ||
		fail 'reviewed diagnostic reporter artifact hash changed'
	readelf -h "$reviewed_reporter" | grep -q 'Machine:.*AArch64' ||
		fail 'diagnostic reporter is not AArch64'
	if readelf -l "$reviewed_reporter" |
		grep -q 'Requesting program interpreter'; then
		fail 'diagnostic reporter is dynamically linked'
	fi
	if readelf -d "$reviewed_reporter" 2>/dev/null |
		grep -q 'Shared library:'; then
		fail 'diagnostic reporter has a shared-library dependency'
	fi
fi
[ -f "$base" ] && [ ! -L "$base" ] ||
	fail 'accepted network-root base is absent or linked'
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$accepted_base" ] ||
	fail 'accepted network-root base hash changed'
case $output in
	/*) ;;
	*) fail 'output path must be absolute' ;;
esac
output_parent=$(dirname -- "$output")
[ -d "$output_parent" ] && [ ! -L "$output_parent" ] ||
	fail 'output parent is absent or linked'
[ ! -e "$output" ] && [ ! -L "$output" ] ||
	fail 'output already exists'

stage=$(mktemp -d)
output_stage=
cleanup() {
	[ -z "$output_stage" ] || rm -f -- "$output_stage"
	rm -rf -- "$stage"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
verifier=$stage/.reviewed-persistent-root-verify
if [ -z "$reviewed_verifier" ]; then
	"$verifier_builder" "$verifier" >"$stage/.verifier-build-record" ||
		fail 'reviewed static verifier build failed'
else
	install -m 0755 "$reviewed_verifier" "$verifier"
	{
		printf 'format=rog5-reviewed-verifier-artifact-v1\n'
		printf 'sha256=%s\n' "$reviewed_verifier_hash"
	} >"$stage/.verifier-build-record"
fi
[ "$(sha256sum "$verifier" | cut -d ' ' -f 1)" = \
	"$reviewed_verifier_hash" ] ||
	fail 'selected static verifier hash changed'
readelf -h "$verifier" | grep -q 'Machine:.*AArch64' ||
	fail 'persistent-root verifier is not AArch64'
if readelf -l "$verifier" | grep -q 'Requesting program interpreter'; then
	fail 'persistent-root verifier is dynamically linked'
fi
if readelf -d "$verifier" 2>/dev/null | grep -q 'Shared library:'; then
	fail 'persistent-root verifier has a shared-library dependency'
fi
gzip -dc "$base" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
install -m 0755 "$init" "$stage/init"
install -m 0755 "$shutdown" "$stage/shutdown"
install -D -m 0755 "$charging_probe" \
	"$stage/sbin/rog5-early-charging-probe"
install -D -m 0444 "$power_usb_profile" \
	"$stage/etc/rog5/power-usb-active.sh"
install -D -m 0755 "$verifier" "$stage/sbin/persistent-root-verify"
install -D -m 0444 "$xattr_projection" \
	"$stage/etc/rog5/nfs4-xattr-projection"
rm -f "$stage/sbin/rog5-early-target-diag"
if [ -n "$reviewed_reporter" ]; then
	install -D -m 0755 "$reviewed_reporter" \
		"$stage/sbin/rog5-early-target-diag"
fi
rm -f "$verifier" "$stage/.verifier-build-record"
rm -f "$stage"/etc/ssh/ssh_host_* "$stage/etc/machine-id" \
	"$stage/var/lib/dbus/machine-id" "$stage/root/.ssh/authorized_keys"
[ ! -e "$stage/root/.ssh/authorized_keys" ]
[ -z "$(find "$stage/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit 2>/dev/null)" ]
private_key_scan=$stage/.private-key-scan
if grep -rIl 'BEGIN .*PRIVATE KEY' "$stage" >"$private_key_scan"; then
	rm -f "$private_key_scan"
	fail 'network-root initramfs contains private key material'
else
	scan_status=$?
	rm -f "$private_key_scan"
	[ "$scan_status" -eq 1 ] ||
		fail 'network-root private-key scan failed'
fi

find "$stage" -exec touch -h -d "@$epoch" {} +
output_stage=$(mktemp "$output_parent/.network-root-initramfs.XXXXXX")
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output_stage"
NETWORK_ROOT_DIAGNOSTIC_REPORTER="$reviewed_reporter" \
	"$repo/scripts/device/verify-network-root-initramfs.sh" "$output_stage"
ln "$output_stage" "$output" 2>/dev/null ||
	fail 'output appeared during build'
rm -f -- "$output_stage"
output_stage=
printf 'format=rog5-network-root-initramfs-build-v1\n'
printf 'size=%s\n' "$(stat -c %s "$output")"
printf 'sha256=%s\n' "$(sha256sum "$output" | cut -d ' ' -f 1)"
