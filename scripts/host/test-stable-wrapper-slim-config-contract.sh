#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
profile=$repo/configs/kernel/rog5-stable-wrapper-slim-v1.json
fragment=$repo/configs/kernel/rog5-stable-wrapper-slim-v1.fragment
auditor=$repo/scripts/host/verify-stable-wrapper-slim-config.py
hostile_test=$repo/scripts/host/test-stable-wrapper-slim-config.py
generator=$repo/scripts/host/generate-stable-wrapper-slim-config.sh
seal_tool=$repo/scripts/host/kernel-source-seal.py
expected_profile=3fb9eaf91f32cf01c09cc8653feb4a52c421f4a95bdd8e022576211ad7cff9f0
expected_fragment=a302ef08910b24a638da63230e6496f3c93a2828baa3ed6e51d7cbc393916231
expected_auditor=6d988b18c3ae70f5bd91be8e6051119911886be0b4eaeb3759eddf3f5a8ac744
expected_seal_tool=b5ed3261a858680b05a3a7247e2d7948e722f71be812fcdc66972594d22c097a

for path in "$auditor" "$hostile_test" "$generator" "$seal_tool"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable slim-config input: ${path#"$repo"/}"
	case $path in
		*.py) python3 -m py_compile "$path" ;;
		*) bash -n "$path" ;;
	esac
done
for path in "$profile" "$fragment"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing slim-config policy input: ${path#"$repo"/}"
done

for pair in \
	"$profile:$expected_profile" \
	"$fragment:$expected_fragment" \
	"$auditor:$expected_auditor" \
	"$seal_tool:$expected_seal_tool"; do
	path=${pair%:*}
	expected=${pair##*:}
	[[ $(sha256sum "$path" | cut -d ' ' -f 1) == "$expected" ]] ||
		fail "slim-config cross-file identity changed: ${path#"$repo"/}"
done
for token in \
	"$expected_profile" \
	"$expected_fragment" \
	"$expected_auditor" \
	"$expected_seal_tool" \
	'profile and fragment identities disagree' \
	'profile and generator builder IDs disagree' \
	'profile and generator builder digests disagree'; do
	grep -Fq "$token" "$generator" ||
		fail "slim-config generator omits cross-file identity: $token"
done

for token in \
	rog5-stable-wrapper-slim-profile-v1 \
	experiment \
	'"authority": "none"' \
	df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f \
	a302ef08910b24a638da63230e6496f3c93a2828baa3ed6e51d7cbc393916231 \
	bee39a247b4eef5f5282bad7e09b75853b851ed8b9161981803a08d53b4ac8fb \
	592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a \
	CONFIG_USB_DWC3_GADGET \
	CONFIG_SCSI_UFS_QCOM \
	CONFIG_QCOM_RPMH; do
	grep -Fq "$token" "$profile" ||
		fail "slim-config profile omits identity or requirement: $token"
done
for token in \
	'CONFIG_LOCALVERSION="-qgki-perf-kexec-stage-builtin-recovery-slim-v1"' \
	'CONFIG_USB_DWC3_GADGET=y' \
	'# CONFIG_MODULES is not set' \
	'# CONFIG_DRM is not set' \
	'# CONFIG_SOUND is not set' \
	'CONFIG_MEDIA_SUPPORT=y' \
	'# CONFIG_MEDIA_USB_SUPPORT is not set' \
	'CONFIG_HID=y' \
	'# CONFIG_HID_GENERIC is not set' \
	'# CONFIG_NETFILTER is not set'; do
	grep -Fqx "$token" "$fragment" ||
		fail "slim-config fragment omits reviewed delta: $token"
done
for token in \
	'--network=none' \
	'kernel-source-seal.py' \
	'refusing existing slim-config output' \
	'status=experiment' \
	'authority=none'; do
	grep -Fq -- "$token" "$generator" ||
		fail "slim-config generator omits guard: $token"
done

if grep -Eq \
	'\b(fastboot|adb|ssh|scp|sudo|pkexec|systemctl)\b|/dev/(sd|nvme|ufs)' \
	"$auditor" "$generator"; then
	fail 'slim-config path contains phone, privilege, or storage transport'
fi
if grep -Eq '\b(subprocess|socket|requests|urllib)\b' "$auditor"; then
	fail 'slim-config auditor unexpectedly exposes process or network clients'
fi

python3 "$hostile_test"
echo 'PASS stable-wrapper slimming audit is identity-bound, hostile-tested, hardware-free, and non-authoritative'
