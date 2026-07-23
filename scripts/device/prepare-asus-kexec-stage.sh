#!/bin/sh
set -eu

archive=${1:?usage: prepare-asus-kexec-stage.sh SOURCE_ARCHIVE SOURCE_DIR PATCH_DIR}
source_dir=${2:?missing source directory}
patch_dir=${3:?missing patch directory}
expected=3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8

[ -r "$archive" ] || { echo 'FAIL missing ASUS source archive' >&2; exit 1; }
[ "$(sha256sum "$archive" | cut -d ' ' -f 1)" = "$expected" ] || {
	echo 'FAIL ASUS source archive hash mismatch' >&2
	exit 1
}

marker=$source_dir/.rog5-kexec-source
if [ -r "$marker" ]; then
	grep -qx "source_sha256=$expected" "$marker"
	prepared=true
else
	prepared=false
	mkdir -p "$source_dir"
	[ -z "$(find "$source_dir" -mindepth 1 -maxdepth 1 -print -quit)" ] || {
		echo 'FAIL refusing nonempty unverified source directory' >&2
		exit 1
	}
	tar -xzf "$archive" -C "$source_dir" --strip-components=2
fi

for patch_file in "$patch_dir"/*.patch; do
	if patch --batch --forward --dry-run -d "$source_dir" -p1 < "$patch_file" >/dev/null 2>&1; then
		patch --batch --forward -d "$source_dir" -p1 < "$patch_file"
	elif patch --batch --reverse --dry-run -d "$source_dir" -p1 < "$patch_file" >/dev/null 2>&1; then
		continue
	else
		echo "FAIL cannot reconcile $(basename "$patch_file")" >&2
		exit 1
	fi
done

{
	printf 'source_sha256=%s\n' "$expected"
	sha256sum "$patch_dir"/*.patch
} > "$marker"

if [ "$prepared" = true ]; then
	echo 'PASS reconciled ASUS 5.4.210 kexec-stage patch set'
else
	echo 'PASS prepared ASUS 5.4.210 kexec-stage source'
fi
