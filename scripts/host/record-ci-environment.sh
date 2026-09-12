#!/bin/sh
# Receipts describe the actual runner, not a reproducibility claim about latest apt.
set -eu
output=${1:?usage: record-ci-environment.sh NEW_OUTPUT_DIRECTORY}
[ ! -e "$output" ] && [ ! -L "$output" ] || { echo 'FAIL environment output exists' >&2; exit 1; }
mkdir -p "$output"
uname -a > "$output/kernel.txt"
if command -v dpkg-query >/dev/null; then
 dpkg-query -W -f '${binary:Package}\t${Version}\n' > "$output/packages.tsv"
elif command -v pacman >/dev/null; then
 pacman -Q > "$output/packages.tsv"
else
 printf 'NOT RUN package inventory: supported query tool unavailable\n' > "$output/packages.tsv"
fi
{
 for tool in git make cc clang ld.lld llvm-ar llvm-readelf dtc python3 dt-validate dt-doc-validate; do
  if command -v "$tool" >/dev/null; then
   printf 'tool=%s\n' "$tool"
   command -v "$tool"
   sha256sum "$(command -v "$tool")"
   "$tool" --version 2>&1 || printf 'version_command_failed=%s\n' "$tool"
  else
   printf 'NOT AVAILABLE %s\n' "$tool"
  fi
 done
} > "$output/tools.txt"
sha256sum "$output/kernel.txt" "$output/packages.tsv" "$output/tools.txt" > "$output/sha256sums.txt"
echo "PASS actual runner environment recorded: $output"
