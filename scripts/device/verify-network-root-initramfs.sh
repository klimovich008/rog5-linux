#!/bin/sh
set -eu

archive=${1:?usage: verify-network-root-initramfs.sh INITRAMFS}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier_builder=$repo/scripts/device/build-persistent-root-verifier-static.sh
reviewed_verifier=${NETWORK_ROOT_VERIFIER:-}
reviewed_verifier_hash=bc7d5c9e5a7a0ff4d46f9fc9dc1680f0d9a960bcd9b01d11fb327d407fa4ba58
reviewed_reporter=${NETWORK_ROOT_DIAGNOSTIC_REPORTER:-}
reviewed_reporter_size=67288
reviewed_reporter_hash=0b5d318e129e4d19c8bf2be8647fc4c3df64535c46347d4ae64e5a7cdb727bc1
for command in cmp cpio cut find grep gzip install mkdir mktemp readelf rm \
	sha256sum sh stat; do
	command -v "$command" >/dev/null || {
		echo "FAIL missing initramfs verifier command: $command" >&2
		exit 1
	}
done
if [ -z "$reviewed_verifier" ]; then
	[ -x "$verifier_builder" ] && [ -f "$verifier_builder" ] &&
		[ ! -L "$verifier_builder" ] || {
		echo 'FAIL reviewed static verifier builder is absent or linked' >&2
		exit 1
	}
else
	case $reviewed_verifier in
		/*) ;;
		*)
			echo 'FAIL NETWORK_ROOT_VERIFIER must be absolute' >&2
			exit 1
			;;
	esac
	[ -x "$reviewed_verifier" ] && [ -f "$reviewed_verifier" ] &&
		[ ! -L "$reviewed_verifier" ] || {
		echo 'FAIL reviewed static verifier artifact is absent or linked' >&2
		exit 1
	}
	[ "$(sha256sum "$reviewed_verifier" | cut -d ' ' -f 1)" = \
		"$reviewed_verifier_hash" ] || {
		echo 'FAIL reviewed static verifier artifact hash changed' >&2
		exit 1
	}
fi
if [ -n "$reviewed_reporter" ]; then
	case $reviewed_reporter in
		/*) ;;
		*)
			echo 'FAIL NETWORK_ROOT_DIAGNOSTIC_REPORTER must be absolute' >&2
			exit 1
			;;
	esac
	[ -x "$reviewed_reporter" ] && [ -f "$reviewed_reporter" ] &&
		[ ! -L "$reviewed_reporter" ] || {
		echo 'FAIL reviewed diagnostic reporter artifact is absent or linked' >&2
		exit 1
	}
	[ "$(stat -c %s "$reviewed_reporter")" -eq "$reviewed_reporter_size" ] || {
		echo 'FAIL reviewed diagnostic reporter artifact size changed' >&2
		exit 1
	}
	[ "$(sha256sum "$reviewed_reporter" | cut -d ' ' -f 1)" = \
		"$reviewed_reporter_hash" ] || {
		echo 'FAIL reviewed diagnostic reporter artifact hash changed' >&2
		exit 1
	}
fi
[ -s "$archive" ] || { echo 'FAIL missing network-root initramfs' >&2; exit 1; }
gzip -t "$archive"

work=$(mktemp -d)
stage=$work/archive
trusted=$work/trusted
mkdir "$stage" "$trusted"
trap 'rm -rf "$work"' EXIT INT TERM
gzip -dc "$archive" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)

[ -x "$stage/init" ] && [ -x "$stage/shutdown" ]
cmp "$stage/init" "$repo/initramfs/network-root-init"
cmp "$stage/shutdown" "$repo/initramfs/network-root-shutdown"
sh -n "$stage/init"
sh -n "$stage/shutdown"

for path in \
	bin/sh \
	bin/mount \
	bin/mountpoint \
	bin/sleep \
	sbin/ip \
	sbin/mdev \
	sbin/reboot \
	sbin/switch_root \
	usr/bin/awk \
	usr/bin/find \
	usr/bin/nc \
	usr/bin/readlink \
	usr/bin/sha256sum \
	usr/bin/setsid \
	usr/sbin/chroot; do
	[ -e "$stage/$path" ] || [ -L "$stage/$path" ] || {
		echo "FAIL initramfs command missing: /$path" >&2
		exit 1
	}
done

root_verifier=$stage/sbin/persistent-root-verify
[ -x "$root_verifier" ] && [ -f "$root_verifier" ] &&
	[ ! -L "$root_verifier" ] || {
	echo 'FAIL network-root initramfs lacks persistent-root verifier' >&2
	exit 1
}
readelf -h "$root_verifier" | grep -q 'Machine:.*AArch64' || {
	echo 'FAIL persistent-root verifier is not AArch64' >&2
	exit 1
}
if readelf -l "$root_verifier" |
	grep -q 'Requesting program interpreter'; then
	echo 'FAIL persistent-root verifier is dynamically linked' >&2
	exit 1
fi
if readelf -d "$root_verifier" 2>/dev/null |
	grep -q 'Shared library:'; then
	echo 'FAIL persistent-root verifier has a shared-library dependency' >&2
	exit 1
fi
[ "$(sha256sum "$root_verifier" | cut -d ' ' -f 1)" = \
	"$reviewed_verifier_hash" ] || {
	echo 'FAIL embedded persistent-root verifier hash changed' >&2
	exit 1
}
if [ -z "$reviewed_verifier" ]; then
	"$verifier_builder" "$trusted/persistent-root-verify" \
		>"$trusted/build-record" || {
		echo 'FAIL reviewed static verifier rebuild failed' >&2
		exit 1
	}
else
	install -m 0755 "$reviewed_verifier" \
		"$trusted/persistent-root-verify"
fi
cmp "$root_verifier" "$trusted/persistent-root-verify" || {
	echo 'FAIL persistent-root verifier differs from reviewed build' >&2
	exit 1
}

reporter=$stage/sbin/rog5-early-target-diag
if [ -z "$reviewed_reporter" ]; then
	[ ! -e "$reporter" ] && [ ! -L "$reporter" ] || {
		echo 'FAIL normal network-root initramfs carries diagnostic reporter' >&2
		exit 1
	}
else
	[ -x "$reporter" ] && [ -f "$reporter" ] && [ ! -L "$reporter" ] || {
		echo 'FAIL diagnostic initramfs lacks early-target reporter' >&2
		exit 1
	}
	[ "$(stat -c %s "$reporter")" -eq "$reviewed_reporter_size" ] || {
		echo 'FAIL embedded diagnostic reporter size changed' >&2
		exit 1
	}
	[ "$(sha256sum "$reporter" | cut -d ' ' -f 1)" = \
		"$reviewed_reporter_hash" ] || {
		echo 'FAIL embedded diagnostic reporter hash changed' >&2
		exit 1
	}
	readelf -h "$reporter" | grep -q 'Machine:.*AArch64' || {
		echo 'FAIL diagnostic reporter is not AArch64' >&2
		exit 1
	}
	if readelf -l "$reporter" |
		grep -q 'Requesting program interpreter'; then
		echo 'FAIL diagnostic reporter is dynamically linked' >&2
		exit 1
	fi
	if readelf -d "$reporter" 2>/dev/null |
		grep -q 'Shared library:'; then
		echo 'FAIL diagnostic reporter has a shared-library dependency' >&2
		exit 1
	fi
	cmp "$reporter" "$reviewed_reporter" || {
		echo 'FAIL diagnostic reporter differs from reviewed artifact' >&2
		exit 1
	}
fi

[ ! -e "$stage/root/.ssh/authorized_keys" ]
[ -z "$(find "$stage/etc/ssh" -maxdepth 1 -type f -name 'ssh_host_*' \
	-print -quit 2>/dev/null)" ]
[ ! -s "$stage/etc/machine-id" ]
[ ! -s "$stage/var/lib/dbus/machine-id" ]
private_key_scan=$work/private-key-scan
if grep -rIl 'BEGIN .*PRIVATE KEY' "$stage" >"$private_key_scan"; then
	echo 'FAIL network-root initramfs contains private key material' >&2
	exit 1
else
	scan_status=$?
	[ "$scan_status" -eq 1 ] || {
		echo 'FAIL network-root private-key scan failed' >&2
		exit 1
	}
fi

echo 'PASS credential-free network-root initramfs, static AArch64 root verifier, retained exitrd source, and required BusyBox applets'
