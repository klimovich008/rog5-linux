#!/bin/sh
set -eu

meta=${1:?usage: verify-build-meta-hash.sh META ABSOLUTE_SUFFIX ACTUAL}
suffix=${2:?missing recorded-path suffix}
actual=${3:?missing actual input}

case $suffix in
	/*) ;;
	*) echo 'FAIL metadata suffix must be absolute' >&2; exit 1 ;;
esac
[ -s "$meta" ] && [ -s "$actual" ] || {
	echo 'FAIL missing metadata or actual input' >&2
	exit 1
}

expected=$(awk -v suffix="$suffix" '
	length($2) >= length(suffix) && substr($2, 1, 1) == "/" &&
		substr($2, length($2) - length(suffix) + 1) == suffix { print $1 }
' "$meta")
[ "$(printf '%s\n' "$expected" |
	awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] || {
	echo "FAIL metadata does not contain one exact $suffix record" >&2
	exit 1
}
[ "$(sha256sum "$actual" | cut -d ' ' -f 1)" = "$expected" ] || {
	echo "FAIL metadata hash mismatch for $suffix" >&2
	exit 1
}
