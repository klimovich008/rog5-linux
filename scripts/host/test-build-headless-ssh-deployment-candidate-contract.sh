#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
wrapper=$repo/scripts/host/build-headless-ssh-deployment-candidate.sh
builder=$repo/scripts/host/build-corrected-headless-candidate-offline.sh
stager=$repo/scripts/host/stage-headless-ssh-deployment-signing-inputs.py
runbook=$repo/docs/minimal-headless-live-cycle.md
test_root=$(mktemp -d)
trap 'rm -rf -- "$test_root"' EXIT HUP INT TERM

for script in "$wrapper" "$builder"; do
	[[ -f $script && ! -L $script && -x $script ]] ||
		fail "deployment-candidate builder is missing: ${script#"$repo"/}"
	bash -n "$script"
done
[[ -f $stager && ! -L $stager && -x $stager ]] ||
	fail 'deployment signing-input stager is missing or unsafe'
grep -Fq -- '--bundle headless-ssh-network-root-v3-r2' "$runbook" ||
	fail 'deployment runbook does not explicitly select the fresh successor bundle'

if "$wrapper" "$test_root/output" \
	>"$test_root/wrapper.out" 2>"$test_root/wrapper.err"; then
	fail 'deployment wrapper ran without explicit guards'
fi
grep -Fq 'set ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD=1' \
	"$test_root/wrapper.err" ||
	fail 'deployment wrapper did not enforce its first guard'

if ROG5_DEPLOYMENT_BUILD=0 \
	ROG5_DEPLOYMENT_CANDIDATE_RECORD="$test_root/candidate" \
	ROG5_DEPLOYMENT_SIGNING_KEY="$test_root/key" \
	"$builder" "$repo/build/rejected-deployment-inputs" \
	>"$test_root/offline.out" 2>"$test_root/offline.err"; then
	fail 'offline builder accepted deployment credential inputs'
fi
grep -Fq 'offline build rejects deployment credential inputs' \
	"$test_root/offline.err" ||
	fail 'offline builder did not reject deployment inputs before use'

for token in \
	'ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD' \
	'ALLOW_PHONE_CREDENTIAL_USE' \
	'ROG5_DEPLOYMENT_BUILD=1' \
	'ROG5_DEPLOYMENT_CANDIDATE_RECORD' \
	'ROG5_DEPLOYMENT_SIGNING_KEY' \
	'headless-ssh-network-root-v3' \
	'headless-ssh-network-root'; do
	grep -Fq "$token" "$wrapper" ||
		fail "deployment-candidate wrapper omits token: $token"
done

for token in \
	'credentialed build is limited to the SSH deployment candidate' \
	'stage-headless-ssh-deployment-signing-inputs.py' \
	'rog5-headless-ssh-deployment-signing-inputs-v1' \
	'--staged-key "$private_key"' \
	'--staged-candidate "$candidate_record"' \
	'--raw-public-key "$public_key"' \
	'--candidate-record' \
	'--candidate-record-sha256' \
	'staged deployment candidate identity changed' \
	'bundle_id_a=' \
	'--trust-key "$public_key" "$bundle_id_a"' \
	'private signing-key snapshot survived candidate build' \
	'authority=none'; do
	grep -Fq -- "$token" "$builder" ||
		fail "shared deployment builder omits token: $token"
done

if grep -Eq '\b(fastboot|adb|scp|systemctl|pkexec|sudo)\b|/dev/(sd|nvme|ufs)' \
	"$wrapper" "$builder" "$stager"; then
	fail 'deployment-candidate wrapper contains phone, privilege, or storage transport'
fi

echo 'PASS deployment recovery build executes guarded input staging and remains authority-free and transport-free'
