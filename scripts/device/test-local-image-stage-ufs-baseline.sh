#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-ufs-baseline-init

sh -n "$init"
for contract in \
	'expected_physical_count=116' \
	'ROG5 local image stage' \
	'publish_stage PASS count-116' \
	'phy-qcom-qmp-ufs.ko ufshcd-core.ko ufshcd-pltfrm.ko ufs-qcom.ko' \
	'rog5.ufs_discovery=1' \
	'rog5.persistent_ro=1'; do
	grep -Fq "$contract" "$init" || {
		echo "FAIL missing UFS baseline contract: $contract" >&2
		exit 1
	}
done
for forbidden in \
	rog5-load-persistent-power-usb \
	rog5-install-local-arch-image \
	sshd ssh-keygen blockdev '/dev/sd' 'mount -t ext4' userdata; do
	if grep -Fq "$forbidden" "$init"; then
		echo "FAIL UFS baseline exposes forbidden surface: $forbidden" >&2
		exit 1
	fi
done

echo 'PASS minimal UFS baseline has NCM observability and no power or storage path'
