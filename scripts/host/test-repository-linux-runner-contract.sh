#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
runner=$repo/scripts/host/test-repository-linux.sh

[ -f "$runner" ] && [ ! -L "$runner" ] && [ -x "$runner" ]
[ "$(grep -Fc 'shared_tests=(' "$runner")" -eq 1 ]
[ "$(grep -Fc 'tier_tests=()' "$runner")" -eq 1 ]
for token in \
	'DURATION %s %dms' \
	'isolated_tests=(' \
	'parallel_pids=(' \
	'for test_path in "${tests[@]}"' \
	'fail "sequential offline test failed: $test_path"' \
	'cancel-in-progress: true'; do
	case $token in
		'cancel-in-progress: true')
			grep -Fq "$token" "$repo/.github/workflows/offline-smoke.yml"
			;;
		*) grep -Fq "$token" "$runner" ;;
	esac
done

shared=$(sed -n '/^shared_tests=(/,/^)/p' "$runner" |
	sed -n 's|^[[:space:]]*\(scripts/[^[:space:]]*\)$|\1|p')
[ -n "$shared" ]
duplicates=$(printf '%s\n' "$shared" | sort | uniq -d)
[ -z "$duplicates" ] || {
	echo "FAIL shared repository test is duplicated: $duplicates" >&2
	exit 1
}
for isolated in $(sed -n '/^isolated_tests=(/,/^)/p' "$runner" |
	sed -n 's|^[[:space:]]*\(scripts/[^[:space:]]*\)$|\1|p'); do
	printf '%s\n' "$shared" | grep -Fxq "$isolated" || {
		echo "FAIL isolated suite is outside the shared test list: $isolated" >&2
		exit 1
	}
done

echo 'PASS repository runner defines shared tests once, times each suite, and isolates parallel work explicitly'
