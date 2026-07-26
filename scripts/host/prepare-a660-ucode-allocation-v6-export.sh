#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
archive=${1:-$repo/artifacts/a660-ucode-allocation-build-a/modules.tar.gz}
firmware_root=${2:-$repo/artifacts/firmware/linux-firmware-20260622}
helper_build=${3:-$repo/artifacts/a660-firmware-request-only-open-helper-a}
base_root=${4:-/var/lib/rog5-network-root-a660-registration-v3}
export_root=${5:-/var/lib/rog5-network-root-a660-ucode-allocation-v6}
release=7.1.4-rog5-a660reg1
archive_hash=ad3c4b441db6d2701e0e6bb945c1a4bf52d284e209873cb4b9250014386da680
msm_hash=fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45
helper_hash=d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae
acceptance=$repo/manifests/acceptance/a660-registration-v3-live.accepted
acceptance_sha=8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f
acceptance_report_sha=2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79
rejection=$repo/test-results/2026-07-26-a660-ucode-allocation-v5-live-rejected.md
rejection_sha=0c65c98cc03a49d9e5c8a15b391dbe2b6014b5e791a8659c06cd7c2d0bf52fb9
relocation_verifier=$repo/scripts/device/verify-a660-ucode-vmap-relocations.sh
relocation_verifier_sha=56d63a17b6c89454691dbd74539c299d99e99b341831358d6f673f128a3181ae
runtime_builder=$repo/scripts/device/build-a660-ucode-allocation-v6-runtime.sh
runtime_verifier=$repo/scripts/device/verify-a660-ucode-allocation-v6-runtime-sources.sh

[[ $EUID == 0 ]] || fail 'run through PolicyKit; do not share a sudo password'
for command in chmod chown cmp cp cut find install mktemp modinfo mv \
	readlink realpath rm sha256sum stat tar; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
for tool in "$relocation_verifier" "$runtime_builder" "$runtime_verifier"; do
	[[ -x $tool ]] || fail "missing executable verifier or builder: $tool"
done
[[ $base_root == /var/lib/rog5-network-root-a660-registration-v3 ]] ||
	fail 'base export path is not exact'
[[ $export_root == /var/lib/rog5-network-root-a660-ucode-allocation-v6 ]] ||
	fail 'candidate export path is not exact'
[[ -d $base_root && ! -L $base_root ]] ||
	fail 'accepted registration-v3 export is absent'
[[ ! -e $export_root ]] || fail 'candidate export already exists'

archive=$(realpath -e "$archive")
firmware_root=$(realpath -e "$firmware_root")
helper_build=$(realpath -e "$helper_build")
[[ $archive == \
	"$repo/artifacts/a660-ucode-allocation-build-a/modules.tar.gz" ]] ||
	fail 'module archive path is not accepted Build A'
[[ $firmware_root == \
	"$repo/artifacts/firmware/linux-firmware-20260622" ]] ||
	fail 'firmware root path is not accepted'
[[ $helper_build == \
	"$repo/artifacts/a660-firmware-request-only-open-helper-a" ]] ||
	fail 'open-helper build path is not accepted Build A'
[[ $(sha256sum "$archive" | cut -d ' ' -f 1) == "$archive_hash" ]] ||
	fail 'module archive hash mismatch'
[[ $(sha256sum "$rejection" | cut -d ' ' -f 1) == "$rejection_sha" ]] ||
	fail 'v5 live rejection report hash mismatch'
[[ $(sha256sum "$relocation_verifier" | cut -d ' ' -f 1) == \
	"$relocation_verifier_sha" ]] ||
	fail 'compiler-relocation verifier hash mismatch'

"$repo/scripts/device/verify-a660-registration-v3-live-acceptance.sh" \
	"$repo/test-results/2026-07-26-a660-registration-v3-live-accepted.md" \
	"$acceptance" >/dev/null
[[ $(sha256sum "$acceptance" | cut -d ' ' -f 1) == "$acceptance_sha" ]]
"$repo/scripts/device/verify-a660-firmware-request-only-open-helper.sh" \
	"$helper_build" >/dev/null
"$relocation_verifier" \
	"$repo/artifacts/a660-ucode-allocation-build-a/drivers/gpu/drm/msm/msm.ko" \
	>/dev/null
"$repo/scripts/host/test-consume-a660-ucode-allocation-v5.sh" >/dev/null
"$repo/scripts/host/verify-a660-registration-export.sh" \
	"$base_root" /var/lib/rog5-network-root-v1 >/dev/null

sqe=$firmware_root/qcom/a660_sqe.fw
gmu=$firmware_root/qcom/a660_gmu.bin
zap=$firmware_root/qcom/sm8350/a660_zap.mbn
for input in "$sqe" "$gmu" "$zap"; do
	[[ -f $input && ! -L $input ]] || fail "firmware input is not exact: $input"
done
[[ $(sha256sum "$sqe" | cut -d ' ' -f 1) == \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 ]]
[[ $(sha256sum "$gmu" | cut -d ' ' -f 1) == \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 ]]
[[ $(sha256sum "$zap" | cut -d ' ' -f 1) == \
	5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d ]]

stage=$export_root.partial.$$
[[ ! -e $stage ]] || fail 'candidate partial path already exists'
work=$(mktemp -d /var/tmp/rog5-a660-ucode-allocation-v6-export.XXXXXX)
succeeded=0
report_retained_stage() {
	rm -rf "$work"
	if [[ $succeeded != 1 && -e $stage ]]; then
		echo "INFO retained failed candidate export for inspection: $stage" >&2
	fi
}
trap report_retained_stage EXIT

install -d -m 0755 "$stage"
cp -a --reflink=always "$base_root/." "$stage/"
rm -f -- \
	"$stage/usr/local/sbin/rog5-a660-registration-baseline" \
	"$stage/usr/local/sbin/rog5-a660-registration-probe" \
	"$stage/etc/rog5/a660-registration-export"

member=lib/modules/$release/kernel/drivers/gpu/drm/msm/msm.ko
tar -xzf "$archive" -C "$work" "$member"
[[ $(sha256sum "$work/$member" | cut -d ' ' -f 1) == "$msm_hash" ]]
"$relocation_verifier" "$work/$member" >/dev/null
install -Dm0644 "$work/$member" \
	"$stage/usr/lib/modules/$release/kernel/drivers/gpu/drm/msm/msm.ko"
install -Dm0644 "$sqe" "$stage/usr/lib/firmware/qcom/a660_sqe.fw"
install -Dm0644 "$gmu" "$stage/usr/lib/firmware/qcom/a660_gmu.bin"
rm -f -- "$stage/usr/lib/firmware/qcom/sm8350/a660_zap.mbn"

helper=$helper_build/rog5-a660-firmware-request-only-open
[[ $(sha256sum "$helper" | cut -d ' ' -f 1) == "$helper_hash" ]]
install -Dm0755 "$helper" \
	"$stage/usr/local/libexec/rog5-a660-ucode-allocation-v6-open"

baseline=$work/rog5-a660-ucode-allocation-v6-baseline
probe=$work/rog5-a660-ucode-allocation-v6-probe
"$runtime_builder" "$baseline" "$probe" >/dev/null
"$runtime_verifier" "$baseline" "$probe" >/dev/null
install -Dm0755 "$baseline" \
	"$stage/usr/local/sbin/rog5-a660-ucode-allocation-v6-baseline"
install -Dm0755 "$probe" \
	"$stage/usr/local/sbin/rog5-a660-ucode-allocation-v6-probe"
install -Dm0444 "$acceptance" \
	"$stage/etc/rog5/a660-registration-v3-live.accepted"

seal=$stage/etc/rog5/a660-ucode-allocation-v6-export
{
	printf 'diagnostic_generation=v6\n'
	printf 'base_export=rog5-network-root-a660-registration-v3\n'
	printf 'kernel_release=%s\n' "$release"
	printf 'module_archive_sha256=%s\n' "$archive_hash"
	printf 'msm_module_sha256=%s\n' "$msm_hash"
	printf 'sqe_firmware_sha256=%s\n' \
		d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76
	printf 'gmu_firmware_sha256=%s\n' \
		8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7
	printf 'zap_firmware_sha256=%s\n' \
		5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d
	printf 'zap=absent\n'
	printf 'helper_sha256=%s\n' "$helper_hash"
	printf 'baseline_sha256=%s\n' \
		"$(sha256sum "$baseline" | cut -d ' ' -f 1)"
	printf 'probe_sha256=%s\n' \
		"$(sha256sum "$probe" | cut -d ' ' -f 1)"
	printf 'registration_acceptance=ACCEPTED_A660_REGISTRATION_V3\n'
	printf 'registration_acceptance_sha256=%s\n' "$acceptance_sha"
	printf 'registration_report_sha256=%s\n' "$acceptance_report_sha"
	printf 'predecessor=v5_live_rejected_consumed\n'
	printf 'predecessor_report_sha256=%s\n' "$rejection_sha"
	printf 'predecessor_consumption_commit=86b6663\n'
	printf 'compiler_policy=PINNED_MSM_RELOCATIONS\n'
	printf 'compiler_verifier_sha256=%s\n' "$relocation_verifier_sha"
	printf 'firmware_policy=SQE_GMU_ONLY_ZAP_ABSENT\n'
	printf 'open_policy=EXACTLY_ONE_EUCLEAN\n'
	printf 'trace_policy=PID_FILTERED_LOGICAL_VMAP_BALANCE\n'
	printf 'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL\n'
	printf 'v5_reuse=FORBIDDEN\n'
} >"$seal"
chown root:root "$seal"
chmod 0444 "$seal"
chmod 0555 "$stage"

"$repo/scripts/host/verify-a660-ucode-allocation-v6-export.sh" \
	"$stage" "$base_root"
mv "$stage" "$export_root"
succeeded=1
echo "PASS prepared A660 ucode-allocation v6 export at $export_root"
