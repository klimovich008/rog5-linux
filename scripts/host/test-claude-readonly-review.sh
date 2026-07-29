#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
wrapper=$repo/scripts/host/claude-readonly-review.sh
test_tmp=$(mktemp -d)
trap 'rm -rf -- "$test_tmp"' EXIT HUP INT TERM
fake_bin=$test_tmp/bin
mkdir "$fake_bin"

cat >"$fake_bin/claude" <<'SH'
#!/bin/sh
if [ "${1-}" = --help ]; then
	printf '%s\n' \
		'--safe-mode' \
		'--tools <tools...>' \
		'--no-session-persistence' \
		'dontAsk'
	exit 0
fi
printf '%s\n' "$@" >"$CLAUDE_ARGS_LOG"
while IFS= read -r line; do
	printf '%s\n' "$line"
done >"$CLAUDE_STDIN_LOG"
printf '%s\n' 'REVIEW OK'
SH
chmod 755 "$fake_bin/claude"

[[ -f $wrapper && ! -L $wrapper && -x $wrapper ]] ||
	fail 'missing executable Claude review wrapper'
bash -n "$wrapper"

export CLAUDE_ARGS_LOG=$test_tmp/args
export CLAUDE_STDIN_LOG=$test_tmp/stdin
output=$(
	printf '%s\n' 'public review context only' |
		PATH="$fake_bin:/usr/bin:/bin" \
		CLAUDE_REVIEW_MODEL=opus \
		CLAUDE_REVIEW_TIMEOUT_SECONDS=30 \
		"$wrapper"
)
[[ $output == 'REVIEW OK' ]] ||
	fail 'review wrapper did not return the reviewer output'
grep -Fxq -- '--safe-mode' "$CLAUDE_ARGS_LOG" ||
	fail 'review wrapper does not isolate customizations'
grep -Fxq -- '--tools' "$CLAUDE_ARGS_LOG" ||
	fail 'review wrapper does not set an explicit tool boundary'
mapfile -t claude_args <"$CLAUDE_ARGS_LOG"
tools_value_found=false
for ((index = 0; index < ${#claude_args[@]}; index++)); do
	if [[ ${claude_args[index]} == --tools ]]; then
		((index + 1 < ${#claude_args[@]})) ||
			fail 'review wrapper omitted the tools value'
		[[ -z ${claude_args[index + 1]} ]] ||
			fail 'review wrapper exposed a Claude tool'
		tools_value_found=true
		break
	fi
done
[[ $tools_value_found == true ]] ||
	fail 'review wrapper omitted the tools boundary'
grep -Fxq -- '--permission-mode' "$CLAUDE_ARGS_LOG" ||
	fail 'review wrapper does not set a permission mode'
grep -Fxq -- 'dontAsk' "$CLAUDE_ARGS_LOG" ||
	fail 'review wrapper can wait on a hidden permission prompt'
grep -Fxq -- '--no-session-persistence' "$CLAUDE_ARGS_LOG" ||
	fail 'review wrapper persists external review sessions'
grep -Fxq -- 'public review context only' "$CLAUDE_STDIN_LOG" ||
	fail 'review prompt did not stay on stdin'
if grep -Fq -- 'dangerously-skip-permissions' "$CLAUDE_ARGS_LOG"; then
	fail 'review wrapper bypasses Claude permissions'
fi

if printf '%s\n' prompt |
	PATH="$fake_bin:/usr/bin:/bin" \
	CLAUDE_REVIEW_TIMEOUT_SECONDS=0 \
	"$wrapper" >/dev/null 2>&1; then
	fail 'review wrapper accepted an unbounded/invalid timeout'
fi

echo 'PASS Claude advisory reviews are safe-mode, tool-free, nonpersistent, stdin-only, and time-bounded'
