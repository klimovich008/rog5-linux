#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
artifact_manifest=$repo/manifests/artifacts.tsv
rebuild_provenance=$repo/artifacts/early-target-diagnostic-v4/early-target-diagnostic-initramfs-rebuild.txt
legacy_candidate=$repo/configs/recovery-candidates/headless-netroot-early-diag-v1.json
candidate=$repo/configs/recovery-candidates/headless-netroot-early-diag-v2.json
adapter=$repo/scripts/host/prepare-recovery-candidate.py
builder=$repo/scripts/host/build-corrected-headless-candidate-offline.sh
builder_impl=$repo/scripts/host/build-corrected-headless-candidate-offline-impl.sh
rebuild=$repo/scripts/host/rebuild-headless-network-root-initramfs.sh

for path in "$legacy_candidate" "$candidate" "$adapter" "$builder" \
	"$builder_impl" "$rebuild"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing diagnostic-candidate input: ${path#"$repo"/}"
done
/usr/bin/python3 -m py_compile "$builder"
bash -n "$builder_impl"
bash -n "$rebuild"

for token in \
	'"candidate": "headless-netroot-early-diag-v2"' \
	'"status": "offline"' \
	'"authority": "none"' \
	'"bundle": "headless-netroot-early-diag-v2"' \
	'"profile": "diagnostic-initramfs-v1"' \
	'"target_id": "headless-netroot-early-diag-v2"' \
	'"root_tree_sha256": "f4affd6d83f3af48259c7d7f650e91461465b59e045519310ac81bb5d71a0087"' \
	'"root_seal_sha256": "42ef8388bb771fbd0dd8141939b042a89037ea1cf1bec9288f7a3ae51455210a"' \
	'"root_tree_entries": "37735"' \
	'"rollback_timeout": "600"' \
	'"target_timeout": "480"' \
	'"a660_command_manifest_sha256": "99f194b32171c9c9f09d28636e351bba4cb34751997e1aa174e3466bd758a1d2"' \
	'"path": "artifacts/early-target-diagnostic-v4/rog5-early-target-diagnostic-initramfs.cpio.gz"' \
	'"size": 6013387' \
	'"sha256": "23022b9627f5b8253226db6fe71e94d6196c8129cc50afae3b2ca1b8fdb182d4"'; do
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
	'headless-netroot-early-diag-v2:' \
	'expected_profile=diagnostic-initramfs-v1' \
	'expected_candidate_sha=d4877ceea4af5f8ffc491520f722a8cbe41e45a32714f78e7b316f0630f8a90b' \
	'expected_manifest=ddccf8025190097219f5a7bd8ef32f2b8ad9feed024ae00ecd07e0f446520034' \
	'offline candidate record identity changed' \
	'offline candidate manifest identity changed' \
	'grep -Fxq "profile=$expected_profile"'; do
	grep -Fq -- "$token" "$builder_impl" ||
		fail "candidate twin-builder omits diagnostic contract: $token"
done

[[ $(sha256sum "$legacy_candidate" | cut -d ' ' -f 1) == \
	7081a0c77158ed695e62751e152baff101b18a9b364640c0cbffd6ef8ba1c6e8 ]] ||
	fail 'legacy diagnostic candidate identity changed'

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
	"$builder" "$builder_impl"; then
	fail 'offline bundle builder contains phone, privilege, or storage transport'
fi
for token in \
	'deployment_build=${ROG5_DEPLOYMENT_BUILD:-0}' \
	'offline build rejects deployment credential inputs' \
	'openssl genpkey -algorithm ED25519' \
	'private signing-key snapshot survived candidate build'; do
	grep -Fq -- "$token" "$builder_impl" ||
		fail "offline bundle builder omits isolation contract: $token"
done

echo 'PASS early-target diagnostic candidate is fixed, authority-free, twin-buildable, and transport-free'
# Ignored artifacts are optional in clean CI, but any present rebuild evidence
# must exactly match its repository-owned inventory row.
if [[ -e $rebuild_provenance || -L $rebuild_provenance ]]; then
	[[ -f $rebuild_provenance && ! -L $rebuild_provenance ]] ||
		fail 'present diagnostic rebuild provenance is unsafe'
	relative=${rebuild_provenance#"$repo"/}
	read -r recorded_size recorded_sha < <(
		awk -F '\t' -v name="$relative" \
			'$1 == name && $5 == "no" { count++; size=$2; sha=$3 }
			 END { if (count != 1) exit 1; print size, sha }' \
			"$artifact_manifest"
	) || fail 'present diagnostic rebuild provenance lacks one ignored-artifact row'
	[[ $(stat -c '%s' "$rebuild_provenance") == "$recorded_size" &&
		$(sha256sum "$rebuild_provenance" | cut -d ' ' -f 1) == "$recorded_sha" ]] ||
		fail 'present diagnostic rebuild provenance differs from its inventory row'
fi
