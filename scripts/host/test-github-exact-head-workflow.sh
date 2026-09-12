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
	'ref: ${{ github.sha }}' \
	'expected=${{ github.sha }}' \
	'candidate-publication:' \
	'needs: [head-exact, panel-driver, board-production]' \
	'ref: ${{ needs.head-exact.outputs.head_sha }}' \
	'test "$actual" = "${{ needs.head-exact.outputs.head_sha }}"' \
	'test "${{ needs.head-exact.outputs.head_sha }}" = "${{ github.event.pull_request.head.sha }}"' \
	'candidate=$(python3 -c' \
	'expected_candidate_sha=$(python3 -c' \
	'test "$candidate_sha" = "$expected_candidate_sha"' \
	'scripts/host/generate-power-usb-active.py' \
	'format=rog5-reviewed-candidate-publication-v1' \
	'candidate_sha256=%s' \
	'authority=none' \
	'uses: actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f # v6' \
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

# The explicit runner refuses missing mandatory commands rather than skipping
# their checks. Both exact-head and merge jobs must install their providers.
python3 - "$workflow" <<'PYTHON'
from pathlib import Path
import re
import subprocess
import sys

workflow = Path(sys.argv[1]).read_text()
for job in ('head-exact', 'merge-compat'):
    match = re.search(r'^  ' + re.escape(job) + r':\n(.*?)(?=^  \S|\Z)',
                      workflow, re.MULTILINE | re.DOTALL)
    if not match:
        raise SystemExit('FAIL missing workflow job: ' + job)
    for package in ('bubblewrap', 'qemu-user-static'):
        if not re.search(r'^            ' + re.escape(package) + r'(?: \\)?$',
                         match.group(1), re.MULTILINE):
            raise SystemExit('FAIL ' + job + ' omits mandatory package: ' + package)
print('PASS head/merge mandatory bwrap and qemu-aarch64-static providers')
board = re.search(r'^  board-production:\n(.*?)(?=^  \S|\Z)',
                  workflow, re.MULTILINE | re.DOTALL).group(1)
expression = re.search(r"^\s+'(\^\(.*?)' <<<", board, re.MULTILINE).group(1)
for path, selected in (
        ('scripts/host/check-production-build-diagnostics.py', True),
        ('scripts/host/test-production-build-diagnostics.py', True),
        ('docs/current-state.md', False)):
    result = subprocess.run(['grep', '-Eq', expression], input=path + '\n', text=True)
    if result.returncode not in (0, 1) or (result.returncode == 0) != selected:
        raise SystemExit('FAIL exact-board scope does not match: ' + path)
retention = board.split('name: Retain exact-board results and validation logs', 1)[1]
if ('always()' not in retention or 'build/board-production/*.json' not in retention or
        'build/board-production/*.log' not in retention):
    raise SystemExit('FAIL exact-board diagnostics are not retained on failure')
print('PASS exact-board diagnostic path selection and failure receipt retention')
PYTHON

echo 'PASS pull-request CI proves exact head, intentional merge compatibility, and exact reviewed-candidate publication'
