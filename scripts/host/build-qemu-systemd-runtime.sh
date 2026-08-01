#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $# == 2 ]] ||
	fail 'usage: build-qemu-systemd-runtime.sh SOURCE_ROOT_ARCHIVE OUTPUT'
source_archive=$(realpath -e -- "$1") || fail 'cannot resolve source archive'
output=$2
expected_source_size=536747283
expected_source_sha256=60fed48c8714a3f3b2082f95a04e913f32dfc74ed4c262e5b3d6e924a39a9c3b
epoch=1681862400

for command_name in bsdtar cpio cut dirname find gzip ln mkdir mktemp python3 \
	readelf realpath sha256sum sort stat touch xargs; do
	command -v "$command_name" >/dev/null ||
		fail "missing systemd runtime build command: $command_name"
done
[[ -f $source_archive && ! -L $source_archive && -r $source_archive ]] ||
	fail 'source root archive is absent, linked, or unreadable'
[[ $(stat -c %s "$source_archive") == "$expected_source_size" ]] ||
	fail 'source root archive size changed'
[[ $(sha256sum "$source_archive" | cut -d ' ' -f 1) == \
	"$expected_source_sha256" ]] || fail 'source root archive hash changed'
case $output in
	/*) ;;
	*) fail 'systemd runtime output path must be absolute' ;;
esac
output_parent=$(dirname -- "$output")
[[ -d $output_parent && ! -L $output_parent ]] ||
	fail 'systemd runtime output parent is absent or linked'
[[ ! -e $output && ! -L $output ]] ||
	fail 'systemd runtime output already exists'

work=$(mktemp -d)
output_stage=
cleanup() {
	if [[ -n ${output_stage:-} && -e $output_stage ]]; then
		find "$output_stage" -maxdepth 0 -delete 2>/dev/null || true
	fi
	find "$work" -depth -delete 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM
mkdir "$work/all" "$work/closure"

bsdtar --no-xattrs -xpf "$source_archive" -C "$work/all" \
	'root/usr/lib/*.so*' \
	'root/usr/lib/systemd/systemd' \
	'root/usr/lib/systemd/systemd-executor' \
	'root/usr/lib/systemd/*.so*' \
	'root/usr/share/doc/systemd/LICENSES/*' \
	'root/usr/share/licenses/brotli/*' \
	'root/usr/share/licenses/libgcc/*' \
	'root/usr/share/licenses/openssl/*' \
	'root/usr/share/licenses/spdx/GFDL-1.3-or-later.txt' \
	'root/usr/share/licenses/spdx/GPL-2.0-or-later.txt' \
	'root/usr/share/licenses/spdx/GPL-3.0-or-later.txt' \
	'root/usr/share/licenses/spdx/LGPL-2.1-or-later.txt' \
	'root/usr/share/licenses/systemd/*' \
	'root/usr/share/licenses/zlib/*' \
	'root/usr/share/licenses/zstd/*'

python3 - "$work/all/root" "$work/closure" <<'PY'
from collections import deque
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys

source = Path(sys.argv[1]).resolve(strict=True)
destination = Path(sys.argv[2]).resolve(strict=True)
search = (source / "usr/lib/systemd", source / "usr/lib")
queue = deque(
    (
        source / "usr/lib/systemd/systemd",
        source / "usr/lib/systemd/systemd-executor",
        source / "usr/lib/systemd/libsystemd-core-260.2-2.so",
        source / "usr/lib/systemd/libsystemd-shared-260.2-2.so",
        source / "usr/lib/ld-linux-aarch64.so.1",
    )
)
needed_pattern = re.compile(r"Shared library: \[(.+?)\]")
seen: set[Path] = set()


def copy_chain(path: Path) -> Path:
    while True:
        try:
            relative = path.relative_to(source)
        except ValueError as error:
            raise SystemExit(f"dependency escapes extracted root: {path}") from error
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            target = os.readlink(path)
            if output.is_symlink():
                if os.readlink(output) != target:
                    raise SystemExit(f"conflicting dependency link: {relative}")
            elif output.exists():
                raise SystemExit(f"dependency link replaced by file: {relative}")
            else:
                output.symlink_to(target)
            path = (path.parent / target).resolve(strict=True)
            continue
        if not path.is_file():
            raise SystemExit(f"dependency is not a regular file: {relative}")
        if not output.exists():
            shutil.copy2(path, output)
        elif not output.is_file() or output.is_symlink():
            raise SystemExit(f"dependency file replaced by link: {relative}")
        return path


while queue:
    binary = copy_chain(queue.popleft())
    if binary in seen:
        continue
    seen.add(binary)
    result = subprocess.run(
        ("readelf", "-d", str(binary)),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"cannot inspect ELF dependencies: {binary}")
    for line in result.stdout.splitlines():
        match = needed_pattern.search(line)
        if match is None:
            continue
        library = match.group(1)
        for directory in search:
            candidate = directory / library
            if candidate.exists() or candidate.is_symlink():
                queue.append(candidate)
                break
        else:
            raise SystemExit(f"missing dependency {library} for {binary}")

if len(seen) != 14:
    raise SystemExit(f"unexpected systemd ELF closure size: {len(seen)}")
(destination / "lib").symlink_to("usr/lib")
for package in ("brotli", "libgcc", "openssl", "systemd", "zlib", "zstd"):
    license_source = source / "usr/share/licenses" / package
    if not license_source.is_dir() or license_source.is_symlink():
        raise SystemExit(f"missing license directory: {package}")
    shutil.copytree(
        license_source,
        destination / "usr/share/licenses" / package,
        symlinks=True,
    )
spdx_destination = destination / "usr/share/licenses/spdx"
spdx_destination.mkdir(parents=True, exist_ok=True)
for license_name in (
    "GFDL-1.3-or-later.txt",
    "GPL-2.0-or-later.txt",
    "GPL-3.0-or-later.txt",
    "LGPL-2.1-or-later.txt",
):
    license_source = source / "usr/share/licenses/spdx" / license_name
    if not license_source.is_file() or license_source.is_symlink():
        raise SystemExit(f"missing SPDX license text: {license_name}")
    shutil.copy2(license_source, spdx_destination / license_name)
systemd_licenses = source / "usr/share/doc/systemd/LICENSES"
if not systemd_licenses.is_dir() or systemd_licenses.is_symlink():
    raise SystemExit("missing systemd license corpus")
shutil.copytree(
    systemd_licenses,
    destination / "usr/share/doc/systemd/LICENSES",
    symlinks=True,
)

provenance = destination / "usr/share/rog5-qemu-systemd/PROVENANCE"
provenance.parent.mkdir(parents=True, exist_ok=True)
provenance.write_text(
    "format=rog5-qemu-systemd-runtime-v1\n"
    "source_archive_size=536747283\n"
    "source_archive_sha256="
    "60fed48c8714a3f3b2082f95a04e913f32dfc74ed4c262e5b3d6e924a39a9c3b\n"
    "closure=recursive-dt-needed\n"
    "elf_count=14\n"
    "systemd=260.2-2\n"
    "glibc=2.43+r22+g8362e8ce10b2-2\n"
    "libgcc=16.1.1+r12+g301eb08fa2c5-1\n"
    "openssl=3.6.2-2\n"
    "brotli=1.2.0-1\n"
    "zlib=1:1.3.2-3\n"
    "zstd=1.5.7-3\n"
    "boot_authority=none\n"
    "phone_storage=absent\n",
    encoding="ascii",
)
PY

manifest=$work/closure/usr/share/rog5-qemu-systemd/runtime-files.sha256
(
	cd "$work/closure"
	find . -type f ! -path './usr/share/rog5-qemu-systemd/runtime-files.sha256' \
		-print0 | sort -z | xargs -0 sha256sum
) >"$manifest"
find "$work/closure" -exec touch -h -d "@$epoch" {} +
output_stage=$(mktemp "$output_parent/.qemu-systemd-runtime.XXXXXX")
(
	cd "$work/closure"
	find . -mindepth 1 -print0 | sort -z |
		cpio --null -o --quiet --format=newc --owner=0:0 --reproducible
) | gzip -n >"$output_stage"
gzip -t "$output_stage"
ln "$output_stage" "$output" 2>/dev/null ||
	fail 'systemd runtime output appeared during build'
find "$output_stage" -maxdepth 0 -delete
output_stage=

printf 'format=rog5-qemu-systemd-runtime-build-v1\n'
printf 'size=%s\n' "$(stat -c %s "$output")"
printf 'sha256=%s\n' "$(sha256sum "$output" | cut -d ' ' -f 1)"
