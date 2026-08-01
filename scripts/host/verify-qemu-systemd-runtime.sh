#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $# == 1 ]] || fail 'usage: verify-qemu-systemd-runtime.sh RUNTIME_CPIO_GZ'
archive=$(realpath -e -- "$1") || fail 'cannot resolve systemd runtime archive'
expected_size=8345703
expected_sha256=97832e75302d312cdbf2c1ae8d8ba6f028fcd5f698c925b1606a836f569390e3
for command_name in cpio cut file find grep gzip mktemp python3 readelf \
	readlink realpath sha256sum stat strings wc; do
	command -v "$command_name" >/dev/null ||
		fail "missing systemd runtime verification command: $command_name"
done
[[ -f $archive && ! -L $archive && -r $archive ]] ||
	fail 'systemd runtime archive is absent, linked, or unreadable'
[[ $(stat -c %s "$archive") == "$expected_size" ]] ||
	fail 'systemd runtime archive size changed'
[[ $(sha256sum "$archive" | cut -d ' ' -f 1) == "$expected_sha256" ]] ||
	fail 'systemd runtime archive hash changed'
gzip -t "$archive" || fail 'systemd runtime archive is not valid gzip'

work=$(mktemp -d)
trap 'find "$work" -depth -delete 2>/dev/null || true' EXIT HUP INT TERM
gzip -dc "$archive" |
	(cd "$work" && cpio -idm --quiet --no-absolute-filenames)

[[ ! -e $work/etc && ! -e $work/root && ! -e $work/home &&
	! -e $work/var && -L $work/lib && $(readlink "$work/lib") == usr/lib ]] ||
	fail 'systemd runtime carries mutable host or user state'
[[ $(find "$work" -type f | wc -l) == 37 ]] ||
	fail 'systemd runtime regular-file count changed'
[[ $(find "$work" -type l | wc -l) == 7 ]] ||
	fail 'systemd runtime symlink count changed'
[[ -f $work/usr/share/rog5-qemu-systemd/runtime-files.sha256 &&
	$(wc -l <"$work/usr/share/rog5-qemu-systemd/runtime-files.sha256") == 36 ]] ||
	fail 'systemd runtime manifest shape changed'
(
	cd "$work"
	sha256sum -c usr/share/rog5-qemu-systemd/runtime-files.sha256 >/dev/null
) || fail 'systemd runtime file manifest mismatch'

systemd=$work/usr/lib/systemd/systemd
file "$systemd" |
	grep -q 'ELF 64-bit LSB pie executable, ARM aarch64' ||
	fail 'systemd runtime PID 1 is not AArch64 PIE'
readelf -l "$systemd" |
	grep -Fq 'Requesting program interpreter: /lib/ld-linux-aarch64.so.1' ||
	fail 'systemd runtime interpreter changed'
for marker in \
	'format=rog5-qemu-systemd-runtime-v1' \
	'closure=recursive-dt-needed' \
	'elf_count=14' \
	'systemd=260.2-2' \
	'libgcc=16.1.1+r12+g301eb08fa2c5-1' \
	'boot_authority=none' \
	'phone_storage=absent'; do
	grep -Fqx "$marker" \
		"$work/usr/share/rog5-qemu-systemd/PROVENANCE" ||
		fail "systemd runtime provenance changed: $marker"
done
[[ -f $work/usr/share/doc/systemd/LICENSES/LGPL-2.0-or-later.txt ]] ||
	fail 'systemd runtime lacks its license corpus'
for license_path in \
	usr/share/licenses/libgcc/RUNTIME.LIBRARY.EXCEPTION \
	usr/share/licenses/spdx/GFDL-1.3-or-later.txt \
	usr/share/licenses/spdx/GPL-2.0-or-later.txt \
	usr/share/licenses/spdx/GPL-3.0-or-later.txt \
	usr/share/licenses/spdx/LGPL-2.1-or-later.txt; do
	[[ -f $work/$license_path && ! -L $work/$license_path ]] ||
		fail "systemd runtime lacks component license: $license_path"
done

python3 - "$work" <<'PY'
from pathlib import Path, PurePosixPath
import os
import subprocess
import sys

root = Path(sys.argv[1]).resolve(strict=True)
elf_count = 0
for path in root.rglob("*"):
    relative = path.relative_to(root)
    if path.is_symlink():
        target = PurePosixPath(os.readlink(path))
        if target.is_absolute():
            resolved = root.joinpath(*target.parts[1:])
        else:
            resolved = path.parent.joinpath(*target.parts)
        try:
            resolved.resolve(strict=True).relative_to(root)
        except (FileNotFoundError, ValueError) as error:
            raise SystemExit(f"unsafe runtime symlink: {relative}") from error
        continue
    if not path.is_file():
        continue
    result = subprocess.run(
        ("readelf", "-h", str(path)),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode != 0:
        continue
    if "Machine:" not in result.stdout or "AArch64" not in result.stdout:
        raise SystemExit(f"non-AArch64 ELF in runtime: {relative}")
    elf_count += 1
if elf_count != 14:
    raise SystemExit(f"unexpected runtime ELF count: {elf_count}")
PY

if grep -rIlE 'BEGIN ([A-Z0-9]+ )?PRIVATE KEY|ssh-(rsa|ed25519) ' \
	"$work" >/dev/null; then
	fail 'systemd runtime contains private key or SSH identity material'
fi
if find "$work" \( -type b -o -type c -o -type p -o -type s \) |
	grep -q .; then
	fail 'systemd runtime contains a device, FIFO, or socket'
fi

echo 'PASS sealed credential-free AArch64 systemd runtime closure'
