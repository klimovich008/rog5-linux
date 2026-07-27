#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
source_file=$repo/tools/persistent-root-verify.c
root_tool=$repo/scripts/device/persistent-root-tool.py

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in cc python3 sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing verifier test command: $command"
done
[ -f "$source_file" ] ||
	fail "missing persistent-root verifier source: $source_file"
[ -x "$root_tool" ] ||
	fail "missing persistent-root sealing oracle: $root_tool"

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
verifier=$work/persistent-root-verify
cc -std=c11 -O2 -Wall -Wextra -Werror "$source_file" -o "$verifier"

make_fixture() {
	case_name=$1
	root=$work/$case_name/root
	seal=$root/.rog5-persistent-seal
	mkdir -p "$root"
	python3 - "$root" <<'PY'
import os
from pathlib import Path
import sys

root = Path(sys.argv[1])
(root / "etc/rog5").mkdir(parents=True)
(root / "usr/lib/rog5").mkdir(parents=True)
(root / "var/empty").mkdir(parents=True)
(root / "etc/rog5/build").write_bytes(b"fixture\n")
payload = root / "usr/lib/rog5/payload"
payload.write_bytes(b"payload\n")
payload.chmod(0o640)
os.setxattr(payload, b"user.rog5", b"preserved")
os.link(payload, root / "usr/lib/rog5/payload-hardlink")
os.symlink("../../etc/rog5/build", root / "usr/lib/rog5/build-link")
(root / ".rog5-persistent-seal").touch()
PY
	tree_report=$("$root_tool" seal "$root")
	{
		printf '%s\n' 'seal_format=rog5-persistent-root-v1'
		printf '%s\n' 'generation=arch-a'
		printf '%s\n' 'source_archive_size=1'
		printf '%s\n' \
			'source_archive_sha256=0000000000000000000000000000000000000000000000000000000000000000'
		printf '%s\n' 'promotion_state=UNBOOTED'
		printf '%s\n' "$tree_report"
	} >"$seal"
	chmod 0444 "$seal"
	seal_hash=$(sha256sum "$seal" | cut -d ' ' -f 1)
}

expect_fail() {
	label=$1
	shift
	if "$@" >"$work/$label.out" 2>&1; then
		fail "persistent-root verifier accepted mutation: $label"
	fi
}

make_fixture pristine
"$verifier" "$root" "$seal" "$seal_hash" |
	grep -Eq '^PASS persistent root matches anchored seal entries=[1-9][0-9]* tree_sha256=[0-9a-f]{64}$'

expect_fail wrong-seal-anchor "$verifier" "$root" "$seal" \
	1111111111111111111111111111111111111111111111111111111111111111

make_fixture content
printf '%s\n' mutation >>"$root/usr/lib/rog5/payload"
expect_fail content "$verifier" "$root" "$seal" "$seal_hash"

make_fixture mode
chmod 0600 "$root/usr/lib/rog5/payload"
expect_fail mode "$verifier" "$root" "$seal" "$seal_hash"

make_fixture symlink
ln -snf ../../var/empty "$root/usr/lib/rog5/build-link"
expect_fail symlink "$verifier" "$root" "$seal" "$seal_hash"

make_fixture xattr
python3 - "$root/usr/lib/rog5/payload" <<'PY'
import os
import sys

os.setxattr(sys.argv[1], b"user.rog5", b"changed")
PY
expect_fail xattr "$verifier" "$root" "$seal" "$seal_hash"

make_fixture seal-mode
chmod 0644 "$seal"
expect_fail seal-mode "$verifier" "$root" "$seal" "$seal_hash"

make_fixture promotion
chmod 0644 "$seal"
sed -i 's/^promotion_state=UNBOOTED$/promotion_state=GOOD/' "$seal"
chmod 0444 "$seal"
seal_hash=$(sha256sum "$seal" | cut -d ' ' -f 1)
expect_fail promotion "$verifier" "$root" "$seal" "$seal_hash"

make_fixture unsupported
mkfifo "$root/unsupported"
expect_fail unsupported "$verifier" "$root" "$seal" "$seal_hash"

echo 'PASS anchored persistent-root verifier matches the Python seal and rejects seal, content, metadata, link, xattr, state, and type mutations'
