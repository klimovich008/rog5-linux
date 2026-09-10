#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
candidate=$repo/configs/recovery-candidates/persistent-root-local-image-any-prior-v13.json
v12=$repo/configs/recovery-candidates/persistent-root-local-image-any-prior-v12.json

python3 - "$candidate" "$v12" <<'PY'
import json
from pathlib import Path
import sys

current = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
previous = json.loads(Path(sys.argv[2]).read_text(encoding="ascii"))
assert current["candidate"] == "persistent-root-local-image-any-prior-v13"
assert current["status"] == "consumed"
assert previous["status"] == "consumed"
assert current["profile"] == previous["profile"]
assert current["target_release"] == previous["target_release"]
assert current["artifacts"] == previous["artifacts"]
PY

echo 'PASS consumed V13 changed only signed identity; active lifecycle is tested separately'
