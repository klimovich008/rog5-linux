#!/bin/sh
set -eu

base=${1:?usage: build-persistent-root-initramfs.sh BASE VERIFIER OUTPUT [UFS_MODULES]}
verifier=${2:?missing persistent-root verifier}
output=${3:?missing output}
ufs_modules=${4:-}
require_deferred_ufs_modules=${REQUIRE_DEFERRED_UFS_MODULES:-0}
power_modules_root=${PERSISTENT_ROOT_POWER_MODULES_ROOT:-}
charge_firmware_dir=${PERSISTENT_ROOT_CHARGE_FIRMWARE_DIR:-}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/persistent-root-init
attest=$repo/initramfs/persistent-root-attest
shutdown=$repo/initramfs/persistent-root-shutdown
power_loader=$repo/scripts/device/load-persistent-root-power-usb.sh
expected_base=819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5
expected_current_base=908f18f752962fae798249060aa8ee4c45673d8795571fbb8883ac4ed8d9e19e
expected_stage_base=2f8fb42078cc9c827953cd0ad5a67042aae8a8989f60b4056319c25f3dccc280
expected_fast_base=e6836d2173341a200b2d728d4ade97a09233de1936621073ad32ae32402f9883
expected_verifier=bc7d5c9e5a7a0ff4d46f9fc9dc1680f0d9a960bcd9b01d11fb327d407fa4ba58
expected_release=${EXPECTED_RELEASE:-7.1.4-gcdf38b1ddebb}
storage_mode=${UFS_STORAGE_MODE:-read-only}
writer_boot_id=7c3afb64-8e84-4f4b-87f4-88d19c2646de
probe_boot_id=${EXPECTED_PROBE_BOOT_ID:-$writer_boot_id}
epoch=1681862400

case $storage_mode in
	read-only)
		printf '%s\n' "$probe_boot_id" |
			grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' || {
			echo 'FAIL EXPECTED_PROBE_BOOT_ID must pin a writer UUID for read-only' >&2
			exit 1
		}
		;;
	local-write)
		[ "${EXPECTED_PROBE_BOOT_ID:-current}" = current ] || {
			echo 'FAIL EXPECTED_PROBE_BOOT_ID must be current for local-write' >&2
			exit 1
		}
		probe_boot_id=current
		;;
	*)
		echo 'FAIL UFS_STORAGE_MODE must be read-only or local-write' >&2
		exit 1
		;;
esac

case $require_deferred_ufs_modules in
	0) ;;
	1)
		[ -n "$ufs_modules" ] || {
			echo 'FAIL deferred UFS modules are required for this kernel' >&2
			exit 1
		}
		;;
	*)
		echo 'FAIL REQUIRE_DEFERRED_UFS_MODULES must be 0 or 1' >&2
		exit 1
		;;
esac

case "$power_modules_root:$charge_firmware_dir" in
	:) ;;
	:*|*:) echo 'FAIL power modules and charging firmware must be supplied together' >&2; exit 1 ;;
	*) ;;
esac

printf '%s\n' "$expected_release" |
	grep -Eq '^7[.]1[.]4-g[0-9a-f]{12}$' || {
	echo 'FAIL invalid expected persistent-root kernel release' >&2
	exit 1
}

for path in "$init" "$attest" "$shutdown"; do
	[ -x "$path" ] || {
		echo "FAIL missing executable P2 initramfs source: $path" >&2
		exit 1
	}
done
if [ -n "$power_modules_root" ]; then
	[ -x "$power_loader" ] && [ -d "$power_modules_root" ] &&
		[ ! -L "$power_modules_root" ] && [ -d "$charge_firmware_dir" ] &&
		[ ! -L "$charge_firmware_dir" ] || {
		echo 'FAIL unsafe persistent-root power/USB inputs' >&2
		exit 1
	}
	firmware_tree_sha=$(
		cd "$charge_firmware_dir"
		find . -mindepth 1 -maxdepth 1 -type f -printf '%f\n' | sort |
			while IFS= read -r name; do
				case $name in ''|*[!A-Za-z0-9._-]*) exit 1 ;; esac
				sha256sum "$name"
			done |
			sha256sum | cut -d ' ' -f 1
	) || {
		echo 'FAIL charging firmware inventory is unsafe' >&2
		exit 1
	}
	[ "$firmware_tree_sha" = \
		52442f69be8a91347499bc7a5c45060ad2458bb711cf51f8a7fdd64c5d2d412b ] || {
		echo 'FAIL charging firmware identity changed' >&2
		exit 1
	}
fi
[ -r "$base" ] && [ -x "$verifier" ] || {
	echo 'FAIL missing P2 initramfs binary input' >&2
	exit 1
}
base_sha256=$(sha256sum "$base" | cut -d ' ' -f 1)
case $base_sha256 in
	"$expected_base"|"$expected_current_base"|"$expected_stage_base"|\
	"$expected_fast_base") ;;
	*)
		echo 'FAIL accepted persistent-root initramfs base hash changed' >&2
		exit 1
		;;
esac
[ "$(sha256sum "$verifier" | cut -d ' ' -f 1)" = \
	"$expected_verifier" ] || {
	echo 'FAIL persistent-root verifier hash changed' >&2
	exit 1
}

readelf -h "$verifier" | grep -q 'Machine:.*AArch64'
! readelf -d "$verifier" | grep -q '(NEEDED)'
! readelf -l "$verifier" | grep -q 'Requesting program interpreter'

if [ -n "$ufs_modules" ]; then
	[ -d "$ufs_modules" ] && [ ! -L "$ufs_modules" ] || {
		echo 'FAIL unsafe deferred UFS module directory' >&2
		exit 1
	}
	module_inventory=$(find "$ufs_modules" -mindepth 1 -maxdepth 1 \
		-printf '%f\n' | sort | tr '\n' ' ')
	[ "$module_inventory" = \
		'phy-qcom-qmp-ufs.ko ufs-qcom.ko ufshcd-core.ko ufshcd-pltfrm.ko ' ] || {
		echo 'FAIL deferred UFS module inventory changed' >&2
		exit 1
	}
	for module in phy-qcom-qmp-ufs.ko ufshcd-core.ko ufshcd-pltfrm.ko \
		ufs-qcom.ko; do
		path=$ufs_modules/$module
		[ -f "$path" ] && [ ! -L "$path" ] || {
			echo "FAIL unsafe deferred UFS module: $module" >&2
			exit 1
		}
		readelf -h "$path" | grep -q 'Type:.*REL (Relocatable file)'
		readelf -h "$path" | grep -q 'Machine:.*AArch64'
		[ "$(modinfo -F vermagic "$path" | awk '{ print $1 }')" = \
			"$expected_release" ] || {
			echo "FAIL deferred UFS module release changed: $module" >&2
			exit 1
		}
	done
fi

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
gzip -dc "$base" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
[ -f "$stage/bin/busybox" ] && [ ! -L "$stage/bin/busybox" ] &&
	[ -x "$stage/bin/busybox" ] &&
	[ -f "$stage/lib/ld-musl-aarch64.so.1" ] &&
	[ ! -L "$stage/lib/ld-musl-aarch64.so.1" ] &&
	[ -x "$stage/lib/ld-musl-aarch64.so.1" ] || {
	echo 'FAIL retained post-handoff runtime toolchain is absent' >&2
	exit 1
}
readelf -l "$stage/bin/busybox" |
	grep -Fq '[Requesting program interpreter: /lib/ld-musl-aarch64.so.1]' || {
	echo 'FAIL retained BusyBox interpreter identity changed' >&2
	exit 1
}
readelf -d "$stage/bin/busybox" |
	grep -Fq 'Shared library: [libc.musl-aarch64.so.1]' || {
	echo 'FAIL retained BusyBox libc identity changed' >&2
	exit 1
}
[ -x "$stage/sbin/persistent-root-verify" ] &&
	[ "$(sha256sum "$stage/sbin/persistent-root-verify" | cut -d ' ' -f 1)" = \
		"$expected_verifier" ] &&
	cmp "$stage/sbin/persistent-root-verify" "$verifier" || {
	echo 'FAIL base and selected persistent-root verifier differ' >&2
	exit 1
}
install -m 0755 "$init" "$stage/init"
[ "$(grep -Fc '@EXPECTED_KERNEL_RELEASE@' "$stage/init")" -eq 1 ] || {
	echo 'FAIL persistent-root init has no unique release placeholder' >&2
	exit 1
}
sed -i "s/@EXPECTED_KERNEL_RELEASE@/$expected_release/" "$stage/init"
grep -Fqx "expected_kernel_release=$expected_release" "$stage/init"
! grep -Fq '@EXPECTED_KERNEL_RELEASE@' "$stage/init"
[ "$(grep -Fc '@EXPECTED_UFS_STORAGE_MODE@' "$stage/init")" -eq 1 ] || {
	echo 'FAIL persistent-root init has no unique UFS storage-mode placeholder' >&2
	exit 1
}
sed -i "s/@EXPECTED_UFS_STORAGE_MODE@/$storage_mode/" "$stage/init"
grep -Fqx "expected_ufs_storage_mode=$storage_mode" "$stage/init"
! grep -Fq '@EXPECTED_UFS_STORAGE_MODE@' "$stage/init"
[ "$(grep -Fc '@EXPECTED_PROBE_BOOT_ID@' "$stage/init")" -eq 1 ] || {
	echo 'FAIL persistent-root init has no unique write-probe producer placeholder' >&2
	exit 1
}
sed -i "s/@EXPECTED_PROBE_BOOT_ID@/$probe_boot_id/" "$stage/init"
grep -Fqx "expected_probe_boot_id=$probe_boot_id" "$stage/init"
! grep -Fq '@EXPECTED_PROBE_BOOT_ID@' "$stage/init"
install -m 0755 "$shutdown" "$stage/shutdown"
rm -rf -- "$stage/rog5-power-usb-modules" "$stage/opt/rog5-charge-firmware"
if [ -n "$power_modules_root" ]; then
	install -D -m 0755 "$power_loader" \
		"$stage/sbin/rog5-load-persistent-power-usb"
	install -d -m 0755 "$stage/rog5-power-usb-modules" \
		"$stage/opt/rog5-charge-firmware"
	find "$charge_firmware_dir" -mindepth 1 -maxdepth 1 -type f -print |
		while IFS= read -r path; do
			install -m 0644 "$path" \
				"$stage/opt/rog5-charge-firmware/${path##*/}"
		done
	module_dir=$power_modules_root/lib/modules/$expected_release/kernel
	[ "$(find "$module_dir" -type f -name '*.ko' | wc -l)" -eq 15 ] || {
		echo 'FAIL persistent-root power module closure is not exactly 15 modules' >&2
		exit 1
	}
	for relative in \
		drivers/power/supply/qcom_battmgr.ko \
		drivers/remoteproc/qcom_common.ko \
		drivers/remoteproc/qcom_pil_info.ko \
		drivers/remoteproc/qcom_q6v5.ko \
		drivers/remoteproc/qcom_q6v5_pas.ko \
		drivers/rpmsg/qcom_glink_smem.ko \
		drivers/soc/qcom/pdr_interface.ko \
		drivers/soc/qcom/pmic_glink.ko \
		drivers/soc/qcom/qcom_pd_mapper.ko \
		drivers/soc/qcom/qcom_pdr_msg.ko \
		drivers/usb/typec/typec.ko \
		drivers/usb/typec/ucsi/typec_ucsi.ko \
		drivers/usb/typec/ucsi/ucsi_glink.ko \
		net/qrtr/qrtr-smd.ko net/qrtr/qrtr.ko; do
		path=$module_dir/$relative
		[ -f "$path" ] && [ ! -L "$path" ] &&
			[ "$(modinfo -F vermagic "$path" | awk '{print $1}')" = \
				"$expected_release" ] || {
			echo "FAIL invalid persistent-root power module: $relative" >&2
			exit 1
		}
		install -m 0644 "$path" \
			"$stage/rog5-power-usb-modules/${path##*/}"
	done
fi
attest_stage=$stage/usr/local/sbin/rog5-p2-attest
install -D -m 0755 "$attest" "$attest_stage"
[ "$(grep -Fc '@EXPECTED_UFS_STORAGE_MODE@' "$attest_stage")" -eq 1 ] || {
	echo 'FAIL persistent-root attestation has no unique UFS storage-mode placeholder' >&2
	exit 1
}
[ "$(grep -Fc '@EXPECTED_PROBE_BOOT_ID@' "$attest_stage")" -eq 1 ] || {
	echo 'FAIL persistent-root attestation has no unique write-probe producer placeholder' >&2
	exit 1
}
sed -i "s/@EXPECTED_UFS_STORAGE_MODE@/$storage_mode/" "$attest_stage"
sed -i "s/@EXPECTED_PROBE_BOOT_ID@/$probe_boot_id/" "$attest_stage"
grep -Fqx "expected_ufs_storage_mode=$storage_mode" "$attest_stage"
grep -Fqx "expected_probe_boot_id=$probe_boot_id" "$attest_stage"
! grep -Fq '@EXPECTED_' "$attest_stage"
install -m 0755 "$verifier" \
	"$stage/usr/local/sbin/persistent-root-verify"
rm -rf -- "$stage/rog5-ufs-modules"
if [ -n "$ufs_modules" ]; then
	mkdir -m 0755 "$stage/rog5-ufs-modules"
	for module in phy-qcom-qmp-ufs.ko ufshcd-core.ko ufshcd-pltfrm.ko \
		ufs-qcom.ko; do
		install -m 0644 "$ufs_modules/$module" \
			"$stage/rog5-ufs-modules/$module"
	done
fi

rm -f "$stage"/etc/ssh/ssh_host_* "$stage/etc/machine-id" \
	"$stage/var/lib/dbus/machine-id" "$stage/root/.ssh/authorized_keys"
[ ! -e "$stage/root/.ssh/authorized_keys" ]
[ -z "$(find "$stage/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit)" ]
grep -qx 'PasswordAuthentication no' "$stage/etc/ssh/sshd_config"
grep -qx 'PermitRootLogin prohibit-password' "$stage/etc/ssh/sshd_config"
! find "$stage" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .

find "$stage" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output")"
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output.tmp"
mv -T -- "$output.tmp" "$output"
gzip -t "$output"
sha256sum "$output"
echo "PASS deterministic credential-free P2 $storage_mode bounded-write/read-only-runtime persistent-root initramfs"
