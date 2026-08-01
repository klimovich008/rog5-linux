#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
candidate=$repo/configs/recovery-candidates/headless-netroot-early-diag-v1.json
adapter=$repo/scripts/host/prepare-recovery-candidate.py
builder=$repo/scripts/host/build-corrected-headless-candidate-offline.sh
rebuild=$repo/scripts/host/rebuild-headless-network-root-initramfs.sh

for path in "$candidate" "$adapter" "$builder" "$rebuild"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing diagnostic-candidate input: ${path#"$repo"/}"
done
bash -n "$builder"
bash -n "$rebuild"

for token in \
	'"candidate": "headless-netroot-early-diag-v1"' \
	'"status": "offline"' \
	'"authority": "none"' \
	'"bundle": "headless-netroot-early-diag-v1"' \
	'"profile": "diagnostic-initramfs-v1"' \
	'"target_id": "headless-netroot-early-diag"' \
	'"root_tree_sha256": "f4affd6d83f3af48259c7d7f650e91461465b59e045519310ac81bb5d71a0087"' \
	'"root_seal_sha256": "42ef8388bb771fbd0dd8141939b042a89037ea1cf1bec9288f7a3ae51455210a"' \
	'"root_tree_entries": "37735"' \
	'"rollback_timeout": "600"' \
	'"target_timeout": "480"' \
	'"a660_command_manifest_sha256": "99f194b32171c9c9f09d28636e351bba4cb34751997e1aa174e3466bd758a1d2"' \
	'"size": 6010870' \
	'"sha256": "10cc407e2bb5a9c9b63fd7eb30c7fc785d78b587e0c7c0b32346f7b1a50ce35c"'; do
	grep -Fq -- "$token" "$candidate" ||
		fail "diagnostic candidate omits fixed token: $token"
done

for token in \
	'"diagnostic-initramfs-v1"' \
	'"network-root-v1"'; do
	grep -Fq -- "$token" "$adapter" ||
		fail "candidate adapter omits offline profile: $token"
done
for token in \
	'headless-netroot-early-diag-v1:' \
	'expected_profile=diagnostic-initramfs-v1' \
	'expected_candidate_sha=7081a0c77158ed695e62751e152baff101b18a9b364640c0cbffd6ef8ba1c6e8' \
	'expected_manifest=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76' \
	'offline candidate record identity changed' \
	'offline candidate manifest identity changed' \
	'grep -Fxq "profile=$expected_profile"'; do
	grep -Fq -- "$token" "$builder" ||
		fail "candidate twin-builder omits diagnostic contract: $token"
done

if grep -Eq \
	'\b(fastboot|adb|sudo|pkexec|ssh|scp|systemctl)\b|/dev/(sd|nvme|ufs)' \
	"$candidate" "$rebuild"; then
	fail 'diagnostic candidate path contains live, privilege, or storage transport'
fi
if grep -Eq '\b(fastboot|adb|sudo|pkexec|systemctl)\b|/dev/(sd|nvme|ufs)' \
	"$adapter"; then
	fail 'candidate adapter contains phone, privilege, or storage transport'
fi
if grep -Eq '\b(fastboot|adb|sudo|pkexec|systemctl)\b|/dev/(sd|nvme|ufs)' \
	"$builder"; then
	fail 'offline bundle builder contains phone, privilege, or storage transport'
fi
for token in \
	'deployment_build=${ROG5_DEPLOYMENT_BUILD:-0}' \
	'offline build rejects deployment credential inputs' \
	'openssl genpkey -algorithm ED25519' \
	'private signing-key snapshot survived candidate build'; do
	grep -Fq -- "$token" "$builder" ||
		fail "offline bundle builder omits isolation contract: $token"
done

echo 'PASS early-target diagnostic candidate is fixed, authority-free, twin-buildable, and transport-free'
