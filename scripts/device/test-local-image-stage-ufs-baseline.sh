#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-ufs-baseline-init

sh -n "$init"
! grep -Fxq 'set -f' "$init" || {
	echo 'FAIL UFS baseline disables the fixed sysfs globs it relies on' >&2
	exit 1
}
for contract in \
	'expected_topology_count=116' \
	'ROG5 local image stage' \
	'publish_stage FAIL count-116' \
	'phy-qcom-qmp-ufs.ko ufshcd-core.ko ufshcd-pltfrm.ko ufs-qcom.ko' \
	'rog5.ufs_discovery=1' \
	'rog5.persistent_ro=1'; do
	grep -Fq "$contract" "$init" || {
		echo "FAIL missing UFS baseline contract: $contract" >&2
		exit 1
	}
done
for forbidden in \
	rog5-install-local-arch-image \
	sshd ssh-keygen blockdev '/dev/sd' 'mount -t ext4' userdata; do
	if grep -Fq "$forbidden" "$init"; then
		echo "FAIL UFS baseline exposes forbidden surface: $forbidden" >&2
		exit 1
	fi
done

loader=$(grep -n '/sbin/rog5-load-persistent-power-usb' "$init" | cut -d: -f1)
ufs=$(grep -n 'for module in phy-qcom-qmp-ufs[.]ko' "$init" | cut -d: -f1)
[ -n "$loader" ] && [ -n "$ufs" ] && [ "$loader" -lt "$ufs" ] || {
	echo 'FAIL power/USB loader must precede the UFS module chain' >&2
	exit 1
}

echo 'PASS minimal UFS baseline loads proven power/USB dependencies before UFS and exposes no storage path'
