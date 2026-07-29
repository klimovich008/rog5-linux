#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ ! -t 0 ]] ||
	fail 'pipe a self-contained, credential-free review prompt on stdin'
for command in claude timeout; do
	command -v "$command" >/dev/null ||
		fail "missing review command: $command"
done
claude_help=$(claude --help)
for capability in \
	'--safe-mode' \
	'--tools <tools...>' \
	'--no-session-persistence' \
	'dontAsk'; do
	grep -Fq -- "$capability" <<<"$claude_help" ||
		fail "installed Claude CLI lacks required boundary: $capability"
done

model=${CLAUDE_REVIEW_MODEL:-opus}
timeout_seconds=${CLAUDE_REVIEW_TIMEOUT_SECONDS:-180}
[[ $model && $model != *$'\n'* ]] ||
	fail 'invalid Claude review model'
if [[ ! $timeout_seconds =~ ^[0-9]+$ ]] ||
	((timeout_seconds < 30 || timeout_seconds > 600)); then
	fail 'CLAUDE_REVIEW_TIMEOUT_SECONDS must be between 30 and 600'
fi

exec timeout --foreground --signal=TERM --kill-after=5s \
	"${timeout_seconds}s" \
	claude \
	--safe-mode \
	-p \
	--model "$model" \
	--effort low \
	--tools '' \
	--permission-mode dontAsk \
	--no-session-persistence \
	--output-format text
