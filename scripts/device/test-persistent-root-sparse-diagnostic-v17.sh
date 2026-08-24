#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
candidate=$repo/configs/recovery-candidates/persistent-root-sparse-diagnostic-v17.json
v16=$repo/configs/recovery-candidates/persistent-root-local-image-reboot-mode-v16.json
initramfs=$repo/artifacts/persistent-root-sparse-diagnostic-v17/initramfs.cpio.gz
runner=$repo/scripts/host/run-persistent-root-storage-live-cycle.py
gate=$repo/scripts/host/run-stable-recovery-live-gate.sh

python3 - "$candidate" "$v16" <<'PY'
import json
from pathlib import Path
import sys

current = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
previous = json.loads(Path(sys.argv[2]).read_text(encoding="ascii"))
assert current["candidate"] == "persistent-root-sparse-diagnostic-v17"
assert current["status"] == "consumed"
assert previous["status"] == "consumed"
assert current["artifacts"]["Image"] == previous["artifacts"]["Image"]
assert current["artifacts"]["board.dtb"] == previous["artifacts"]["board.dtb"]
assert current["artifacts"]["initramfs.cpio.gz"]["sha256"] == "9b34cb5b49b6028fba7cd7becbb76ada14e469894916a19778f3c65b043e8ba0"
PY

if [ -f "$initramfs" ]; then
	[ "$(stat -c %s "$initramfs")" = 23810785 ]
	[ "$(sha256sum "$initramfs" | cut -d ' ' -f 1)" = \
		9b34cb5b49b6028fba7cd7becbb76ada14e469894916a19778f3c65b043e8ba0 ]
	stage=$(mktemp -d)
	trap 'find "$stage" -depth -delete' EXIT HUP INT TERM
	gzip -dc "$initramfs" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
	grep -Fq '1 32 1086 8224 8225 9278 14680096 14688288 14688289' "$stage/init"
	grep -Fq '"raw-b${probe_block}-${probe_hash}"' "$stage/init"
fi
grep -Fq 'persistent-root-sparse-diagnostic-v17-generation110-live-v1' "$gate"
grep -Fq 'if current.state == "FAIL":' "$runner"

echo 'PASS consumed V17 proves ABL sparse userdata staging is ineffective'
