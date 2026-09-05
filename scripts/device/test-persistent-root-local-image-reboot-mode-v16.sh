#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
candidate=$repo/configs/recovery-candidates/persistent-root-local-image-reboot-mode-v16.json
v15=$repo/configs/recovery-candidates/persistent-root-local-image-restart2-v15.json
manifest=$repo/manifests/persistent-root-local-image-reboot-mode-v16-generation109.manifest
policy=$repo/manifests/temporary-boot-images.tsv
fragment=$repo/configs/kernel/rog5-persistent-root-power-usb.fragment
runner=$repo/scripts/host/run-persistent-root-storage-live-cycle.py

python3 - "$candidate" "$v15" <<'PY'
import json
from pathlib import Path
import sys

current = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
previous = json.loads(Path(sys.argv[2]).read_text(encoding="ascii"))
assert current["candidate"] == "persistent-root-local-image-reboot-mode-v16"
assert current["status"] == "consumed"
assert current["authority"] == "none"
assert previous["status"] == "consumed"
assert current["artifacts"]["Image"]["sha256"] == "1a1958fe72201a3cb1fa7bdfc203ab5132cd236c5e4f95cdd13cc825bdf9ce22"
assert current["artifacts"]["Image"] != previous["artifacts"]["Image"]
assert current["artifacts"]["board.dtb"] == previous["artifacts"]["board.dtb"]
assert current["artifacts"]["initramfs.cpio.gz"]["sha256"] == "b5f322533b358856336466d893c04dd36624b194cc0190b09d1eb23ef80cae62"
PY

grep -Fxq 'CONFIG_NVMEM_SPMI_SDAM=y' "$fragment"
grep -Fxq 'CONFIG_NVMEM_REBOOT_MODE=y' "$fragment"
grep -Fq 'target_config_sha256=15e1ea493ac1e654ef9f162ec9134207522ead67660dc16ab62771d9a9e638d6' "$manifest"
grep -Fq 'rollback_policy=pmk8350-nvmem-reboot-mode-built-in-and-runtime-proven' "$manifest"
grep -Fq 'build/persistent-root-local-image-reboot-mode-v16-generation109-20260823-r1/repack/stable-recovery-a.avb.img' "$policy"
! grep -Fq 'persistent-root-local-image-reboot-mode-v16-generation109-live-v1' "$runner"

image=$repo/artifacts/persistent-root-local-image-reboot-mode-v16/Image
initramfs=$repo/artifacts/persistent-root-local-image-reboot-mode-v16/initramfs.cpio.gz
if [ -f "$image" ] && [ -f "$initramfs" ]; then
	[ "$(stat -c %s "$image")" = 38191616 ]
	[ "$(sha256sum "$image" | cut -d ' ' -f 1)" = \
		1a1958fe72201a3cb1fa7bdfc203ab5132cd236c5e4f95cdd13cc825bdf9ce22 ]
	[ "$(stat -c %s "$initramfs")" = 23810940 ]
	[ "$(sha256sum "$initramfs" | cut -d ' ' -f 1)" = \
		b5f322533b358856336466d893c04dd36624b194cc0190b09d1eb23ef80cae62 ]
	stage=$(mktemp -d)
	trap 'find "$stage" -depth -delete' EXIT HUP INT TERM
	gzip -dc "$initramfs" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
	grep -Fq "fail_stage 'Qualcomm reboot-mode path is unavailable' reboot-mode 15" "$stage/init"
	[ "$(sha256sum "$stage/usr/libexec/rog5-reboot-bootloader" | cut -d ' ' -f 1)" = \
		68d6a69e597e9fa86ee956ee9fadc15f4283e7dd2a6032b924449330bb3e4785 ]
fi

echo 'PASS consumed V16 proves PMK8350 reboot-mode fastboot fallback after repeated directory failure'
