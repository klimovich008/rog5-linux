#!/bin/sh
set -eu

archive=${1:?usage: verify-network-root-initramfs.sh INITRAMFS}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier_builder=$repo/scripts/device/build-persistent-root-verifier-static.sh
reviewed_verifier=${NETWORK_ROOT_VERIFIER:-}
reviewed_verifier_hash=2bcead5ca06751d2744cdf0199802ba7ea089257ff383301d1c371f1ef60e28f
reviewed_reporter=${NETWORK_ROOT_DIAGNOSTIC_REPORTER:-}
reviewed_reporter_size=67288
reviewed_reporter_hash=fbbeaf880ea595d9f00b0a19b582dc11911a3a8c025e6aae1ee469d6886da604
for command in cmp cpio cut find grep gzip install mkdir mktemp modinfo modprobe readelf rm \
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
cmp "$stage/etc/rog5/nfs4-xattr-projection" \
	"$repo/configs/network-roots/rog5-nfs4-xattr-projection-v1"
[ "$(stat -c %a "$stage/etc/rog5/nfs4-xattr-projection")" = 444 ]
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

charging_probe=$stage/sbin/rog5-early-charging-probe
reviewed_charging_probe=$repo/scripts/device/probe-network-root-battery-telemetry.sh
[ -x "$charging_probe" ] && [ -f "$charging_probe" ] &&
	[ ! -L "$charging_probe" ] || {
	echo 'FAIL network-root initramfs lacks reviewed charging probe' >&2
	exit 1
}
cmp "$charging_probe" "$reviewed_charging_probe" || {
	echo 'FAIL network-root charging probe differs from reviewed source' >&2
	exit 1
}
sh -n "$charging_probe"

power_observer=$stage/sbin/rog5-early-power-observer
reviewed_power_observer=$repo/scripts/device/observe-early-mainline-power.sh
[ -x "$power_observer" ] && [ -f "$power_observer" ] &&
	[ ! -L "$power_observer" ] || {
	echo 'FAIL network-root initramfs lacks early power observer' >&2
	exit 1
}
cmp "$power_observer" "$reviewed_power_observer" || {
	echo 'FAIL embedded early power observer differs from reviewed source' >&2
	exit 1
}
sh -n "$power_observer"

power_usb_profile=$stage/etc/rog5/power-usb-active.sh
reviewed_power_usb_profile=$repo/initramfs/generated-power-usb-active.sh
[ -f "$power_usb_profile" ] && [ ! -L "$power_usb_profile" ] || {
	echo 'FAIL network-root initramfs lacks generated power/USB identity' >&2
	exit 1
}
cmp "$power_usb_profile" "$reviewed_power_usb_profile" || {
	echo 'FAIL embedded power/USB identity differs from canonical generation' >&2
	exit 1
}
sh -n "$power_usb_profile"

charge_firmware=$stage/opt/rog5-charge-firmware
case ${NETWORK_ROOT_EXPECT_CHARGE_FIRMWARE:-0} in
	0)
		[ ! -e "$charge_firmware" ] && [ ! -L "$charge_firmware" ] || {
			echo 'FAIL unexpected private charge firmware in network-root initramfs' >&2
			exit 1
		}
		;;
	1)
		expected_firmware='adsp.b00
adsp.b01
adsp.b02
adsp.b03
adsp.b04
adsp.b05
adsp.b06
adsp.b07
adsp.b08
adsp.b09
adsp.b10
adsp.b11
adsp.b12
adsp.b13
adsp.b14
adsp.b15
adsp.b16
adsp.b17
adsp.b18
adsp.b19
adsp.b20
adsp.b21
adsp.b22
adsp.b23
adsp.b24
adsp.b25
adsp.b26
adsp.mbn
adsp.mdt'
		[ -d "$charge_firmware" ] && [ ! -L "$charge_firmware" ] || {
			echo 'FAIL required private charge firmware is absent' >&2
			exit 1
		}
		actual_firmware=$(find "$charge_firmware" -mindepth 1 -maxdepth 1 \
			-type f -printf '%f\n' | sort)
		[ "$actual_firmware" = "$expected_firmware" ] || {
			echo 'FAIL private charge firmware inventory changed' >&2
			exit 1
		}
		[ "$(find "$charge_firmware" -mindepth 1 -maxdepth 1 -type f \
			-printf '%s\n' | awk '{ total += $1 } END { print total + 0 }')" \
			= 30900841 ] || {
			echo 'FAIL private charge firmware byte count changed' >&2
			exit 1
		}
		[ "$(find "$charge_firmware" -mindepth 1 -maxdepth 1 ! -type f | wc -l)" \
			-eq 0 ] || {
			echo 'FAIL private charge firmware contains a non-file entry' >&2
			exit 1
		}
		;;
	*) echo 'FAIL invalid charge firmware verification mode' >&2; exit 1 ;;
esac

pdr_module=$stage/opt/rog5-charge-modules/pdr_interface.ko
case ${NETWORK_ROOT_EXPECT_PDR_MODULE:-0} in
	0)
		[ ! -e "$pdr_module" ] && [ ! -L "$pdr_module" ] || {
			echo 'FAIL unexpected PDR override in network-root initramfs' >&2
			exit 1
		}
		;;
	1)
		[ -f "$pdr_module" ] && [ ! -L "$pdr_module" ] || {
			echo 'FAIL required PDR override is absent or linked' >&2
			exit 1
		}
		[ "$(sha256sum "$pdr_module" | cut -d ' ' -f 1)" = \
			0b7df05e9fa0bfe224fc74ac93997bb1ee74ab5371bde172c3b0a2fcfe19601b ] || {
			echo 'FAIL PDR override hash changed' >&2
			exit 1
		}
		[ "$(modinfo -F name "$pdr_module")" = pdr_interface ] &&
			[ "$(modinfo -F depends "$pdr_module")" = qcom_pdr_msg ] &&
			[ "$(modinfo -F vermagic "$pdr_module")" = \
			'7.1.4-g7a5cef0db479 SMP preempt mod_unload aarch64' ] || {
			echo 'FAIL PDR override ABI changed' >&2
			exit 1
		}
		readelf -h "$pdr_module" | grep -q 'Machine:.*AArch64'
		! readelf -S "$pdr_module" | grep -q '[.]BTF' || {
			echo 'FAIL PDR override retains rejected BTF' >&2
			exit 1
		}
		;;
	*) echo 'FAIL invalid PDR override verification mode' >&2; exit 1 ;;
esac

module_root=$stage/lib/modules/7.1.4-g7a5cef0db479
case ${NETWORK_ROOT_EXPECT_CHARGE_MODULES:-0} in
	0)
		[ ! -e "$module_root" ] && [ ! -L "$module_root" ] || {
			echo 'FAIL unexpected early charge module tree' >&2
			exit 1
		}
		;;
	1)
		[ -d "$module_root" ] && [ ! -L "$module_root" ] || {
			echo 'FAIL early charge module tree is absent or linked' >&2
			exit 1
		}
		for module in qcom_q6v5_pas qrtr_smd qcom_pd_mapper qcom_pdr_msg \
			pmic_glink qcom_battmgr typec typec_ucsi ucsi_glink
		do
			modprobe -d "$stage" -S 7.1.4-g7a5cef0db479 \
				--show-depends "$module" >/dev/null || {
				echo "FAIL early charge module cannot resolve: $module" >&2
				exit 1
			}
		done
		pdr=$(find "$module_root" -type f -name pdr_interface.ko -print)
		[ "$(printf '%s\n' "$pdr" | awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] &&
			cmp "$pdr" "$stage/opt/rog5-charge-modules/pdr_interface.ko" || {
			echo 'FAIL early charge module closure does not use reviewed PDR' >&2
			exit 1
		}
		;;
	*) echo 'FAIL invalid charge module verification mode' >&2; exit 1 ;;
esac

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
