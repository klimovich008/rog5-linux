#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/host/prepare-headless-ssh-deployment-root.sh
test_root=$(mktemp -d)
trap 'rm -rf -- "$test_root"' EXIT HUP INT TERM
guard_error=$test_root/guard.err

[[ -f $builder && ! -L $builder && -x $builder ]] ||
	fail 'deployment-root builder is missing or unsafe'
bash -n "$builder"

if "$builder" >/dev/null 2>"$guard_error"; then
	fail 'deployment-root builder ran without explicit guards'
fi
grep -Fq 'set ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD=1' \
	"$guard_error" ||
	fail 'deployment-root build guard did not precede argument parsing'

for token in \
	'ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD' \
	'ALLOW_PHONE_CREDENTIAL_USE' \
	'outside the repository' \
	'repository must be clean' \
	'origin peer' \
	'headless-ssh-v2' \
	'--network none' \
	'find root -xdev -print0 >/tmp/root-files.unsorted' \
	'LC_ALL=C sort -z /tmp/root-files.unsorted' \
	'--null --no-recursion --format paxr' \
	'headless-network-root.py prepare' \
	'headless-network-root.py verify' \
	'verify-steam-deck-builder.sh' \
	'a660-runtime-publish.py' \
	'--stage "$stage" --output "$output"' \
	'deployment package retained a fixture identity' \
	'install -m 0400 "$work/root.tar.gz"' \
	'install -m 0444 "$work/manifest"' \
	'authority=none'; do
	grep -Fq -- "$token" "$builder" ||
		fail "deployment-root builder omits contract token: $token"
done

if grep -Eq \
	'\b(fastboot|adb|scp|systemctl|pkexec|sudo)\b|/dev/(sd|nvme|ufs)' \
	"$builder"; then
	fail 'deployment-root builder contains phone, privilege, or storage transport'
fi

echo 'PASS deployment-root builder is guarded, private, reproducible, and transport-free'
