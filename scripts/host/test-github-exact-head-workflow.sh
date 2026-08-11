#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
workflow=$repo/.github/workflows/offline-smoke.yml

[ -f "$workflow" ] && [ ! -L "$workflow" ] || {
	echo 'FAIL exact-head workflow is missing or linked' >&2
	exit 1
}

for token in \
	'group: offline-smoke-${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}' \
	'cancel-in-progress: true' \
	'head-exact:' \
	'ref: ${{ github.event.pull_request.head.sha || github.sha }}' \
	'expected=${{ github.event.pull_request.head.sha || github.sha }}' \
	'actual=$(git rev-parse HEAD)' \
	'test "$actual" = "$expected"' \
	'head_sha=$actual' \
	'merge-compat:' \
	'ref: refs/pull/${{ github.event.pull_request.number }}/merge' \
	'expected=${{ github.sha }}' \
	'candidate-publication:' \
	'needs: head-exact' \
	'ref: ${{ needs.head-exact.outputs.head_sha }}' \
	'test "$actual" = "${{ needs.head-exact.outputs.head_sha }}"' \
	'test "${{ needs.head-exact.outputs.head_sha }}" = "${{ github.event.pull_request.head.sha }}"' \
	'test "$candidate_sha" = d4877ceea4af5f8ffc491520f722a8cbe41e45a32714f78e7b316f0630f8a90b' \
	'format=rog5-reviewed-candidate-publication-v1' \
	'candidate_sha256=%s' \
	'authority=none' \
	'uses: actions/upload-artifact@v6' \
	'name: reviewed-candidate-${{ needs.head-exact.outputs.head_sha }}' \
	'if-no-files-found: error'; do
	grep -Fq "$token" "$workflow" || {
		echo "FAIL exact-head workflow contract missing: $token" >&2
		exit 1
	}
done

head_line=$(grep -n '^  head-exact:' "$workflow" | cut -d: -f1)
merge_line=$(grep -n '^  merge-compat:' "$workflow" | cut -d: -f1)
publication_line=$(grep -n '^  candidate-publication:' "$workflow" |
	cut -d: -f1)
[ "$head_line" -lt "$merge_line" ] && [ "$merge_line" -lt "$publication_line" ]

echo 'PASS pull-request CI proves exact head, intentional merge compatibility, and exact reviewed-candidate publication'
