#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
target=scripts/host/test-run-stable-recovery-live-gate.sh
gate=scripts/host/run-stable-recovery-live-gate.sh
if [[ -n ${GATE_TEST_REVISION:-} ]]; then
	source_text=$(git -C "$repo" show "$GATE_TEST_REVISION:$target") ||
		fail "cannot read $target at $GATE_TEST_REVISION"
	gate_text=$(git -C "$repo" show "$GATE_TEST_REVISION:$gate") ||
		fail "cannot read $gate at $GATE_TEST_REVISION"
else
	source_text=$(<"$repo/$target")
	gate_text=$(<"$repo/$gate")
fi

policy_section=$(sed -n \
	'/^for generation3_profile in /,/^if \[\[ -d \$generation3_root \]\]; then$/p' \
	<<<"$source_text")
artifact_section=$(sed -n \
	'/^if \[\[ -d \$generation3_root \]\]; then$/,/^run_stage75_v2_policy() {$/p' \
	<<<"$source_text")

[[ -n $policy_section && -n $artifact_section ]] ||
	fail 'cannot isolate retained policy and artifact-preflight sections'
if grep -Eq 'for generation[0-9]+_profile in' <<<"$artifact_section"; then
	fail 'retained bytes are reverified once per offline/live policy profile'
fi

for generation in {3..12}; do
	pair=$(grep -F -A1 \
		"headless-diagnostic-generation${generation}-offline-v1 | \\" \
		<<<"$gate_text" || true)
	grep -Fq \
		"headless-diagnostic-generation${generation}-live-v1)" \
		<<<"$pair" ||
		fail "generation $generation offline/live profiles do not share one artifact contract"
	for mode in offline live; do
		grep -Fq \
			"headless-diagnostic-generation${generation}-${mode}-v1" \
			<<<"$policy_section" ||
			fail "generation $generation lost $mode policy coverage"
	done
	grep -Fq \
		"ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation${generation}-offline-v1" \
		<<<"$artifact_section" ||
		fail "generation $generation lacks its canonical retained-byte preflight"
	count=$(grep -c \
		"^[[:space:]]*generation${generation}_artifact=\$(" \
		<<<"$artifact_section" || true)
	[[ $count == 1 ]] ||
		fail "generation $generation has $count retained-byte preflight sites"
done

if grep -Eq \
	'ROG5_STABLE_RECOVERY_PROFILE=.*generation[0-9]+-live-v1' \
	<<<"$artifact_section"; then
	fail 'live policy names still trigger duplicate retained-byte preflight'
fi

echo 'PASS retained recovery bytes are preflighted once per distinct retained tree while both policies remain covered'
