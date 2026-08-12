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
	'fetch --no-tags --prune origin' \
	'refs/heads/$branch:refs/remotes/origin/$branch' \
	'headless-ssh-v2' \
	'headless-core-v3' \
	'ROG5_DEPLOYMENT_BUILD_PROFILE' \
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

mkdir -p "$test_root/bin"
cat >"$test_root/bin/git" <<'EOF'
#!/bin/sh
case $* in
	*'status --porcelain'*) exit 0 ;;
	*'branch --show-current'*) printf '%s\n' agent/linux-recovery-host ;;
	*'rev-parse --abbrev-ref --symbolic-full-name @{u}'*)
		printf '%s\n' origin/agent/linux-recovery-host
		;;
	*'fetch --no-tags --prune origin refs/heads/agent/linux-recovery-host:refs/remotes/origin/agent/linux-recovery-host'*)
		printf '%s\n' fetch >>"$MOCK_GIT_CALLS"
		: >"$MOCK_GIT_FETCHED"
		;;
	*'rev-parse HEAD'*) printf '%s\n' stale-checkpoint ;;
	*'rev-parse origin/agent/linux-recovery-host'*)
		if [ -e "$MOCK_GIT_FETCHED" ]; then
			printf '%s\n' fresh-remote-checkpoint
		else
			printf '%s\n' stale-checkpoint
		fi
		;;
	*) exit 1 ;;
esac
EOF
cat >"$test_root/bin/realpath" <<'EOF'
#!/bin/sh
printf '%s\n' inspected >>"$MOCK_PRIVATE_INSPECTION"
exec /usr/bin/realpath "$@"
EOF
chmod 0755 "$test_root/bin/git" "$test_root/bin/realpath"
if PATH="$test_root/bin:$PATH" \
	MOCK_GIT_CALLS="$test_root/git.calls" \
	MOCK_GIT_FETCHED="$test_root/git.fetched" \
	MOCK_PRIVATE_INSPECTION="$test_root/private.inspection" \
	ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD=1 \
	ALLOW_PHONE_CREDENTIAL_USE=1 \
	"$builder" "$test_root/private-source" "$test_root/private-output" \
	>"$test_root/stale.out" 2>"$test_root/stale.err"; then
	fail 'deployment-root builder accepted a stale origin checkpoint'
fi
grep -Fxq fetch "$test_root/git.calls" ||
	fail 'deployment-root checkpoint did not fetch its exact branch'
grep -Fq 'checkpoint differs from its origin peer' "$test_root/stale.err" ||
	fail 'deployment-root stale checkpoint returned the wrong refusal'
[[ ! -e $test_root/private.inspection ]] ||
	fail 'deployment-root inspected a private path before checkpoint refusal'

if grep -Eq \
	'\b(fastboot|adb|scp|systemctl|pkexec|sudo)\b|/dev/(sd|nvme|ufs)' \
	"$builder"; then
	fail 'deployment-root builder contains phone, privilege, or storage transport'
fi

echo 'PASS deployment-root builder is guarded, private, reproducible, and transport-free'
