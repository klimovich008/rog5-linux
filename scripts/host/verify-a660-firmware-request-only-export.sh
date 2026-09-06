#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
root=${1:?usage: verify-a660-firmware-request-only-export.sh ROOT BASE_ROOT}
base_root=${2:-/var/lib/rog5-network-root-a660-registration-v3}
release=7.1.4-rog5-a660reg1
archive_hash=04149f41648f12925a6f04261eed96bfecdd6174a10462c82c36213fef0d1bc9
msm_hash=eb2df946472603d932d63a25f5350535b104303e5db6ac8dc66273647460b082
helper_hash=d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae
acceptance_sha=8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f
acceptance_report_sha=2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79

for command in cmp cut file find grep mktemp modinfo readelf realpath rm \
	sha256sum sort stat strings wc xargs; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[[ -d $root && ! -L $root ]] || fail 'candidate export is not a directory'
[[ -d $base_root && ! -L $base_root ]] ||
	fail 'registration-v3 base export is not a directory'
root=$(realpath -e "$root")
base_root=$(realpath -e "$base_root")
[[ $root != / && $base_root != / && $root != "$base_root" ]] ||
	fail 'unsafe or aliased export roots'
[[ $(stat -c '%u:%g:%a' "$root") == 0:0:555 ]] ||
	fail 'candidate export root is not root-owned mode 0555'

"$repo/scripts/host/verify-a660-registration-export.sh" \
	"$base_root" /var/lib/rog5-network-root-v1 >/dev/null
"$repo/scripts/device/verify-a660-firmware-request-only-runtime-sources.sh" \
	"$repo/scripts/device/check-network-root-a660-firmware-request-only-baseline.sh" \
	"$repo/scripts/device/probe-network-root-a660-firmware-request-only.sh" \
	>/dev/null

seal=$root/etc/rog5/a660-firmware-request-only-export
[[ -f $seal && ! -L $seal ]]
[[ $(stat -c '%u:%g:%a' "$seal") == 0:0:444 ]]
for identity in \
	'firmware_request_generation=v4' \
	'base_export=rog5-network-root-a660-registration-v3' \
	"kernel_release=$release" \
	"module_archive_sha256=$archive_hash" \
	"msm_module_sha256=$msm_hash" \
	'sqe_firmware_sha256=d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76' \
	'gmu_firmware_sha256=8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7' \
	'zap_firmware_sha256=5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d' \
	'zap=absent' \
	"helper_sha256=$helper_hash" \
	'registration_acceptance=ACCEPTED_A660_REGISTRATION_V3' \
	"registration_acceptance_sha256=$acceptance_sha" \
	"registration_report_sha256=$acceptance_report_sha" \
	'firmware_policy=SQE_GMU_ONLY_ZAP_ABSENT' \
	'open_policy=EXACTLY_ONE_EUCLEAN'
do
	grep -Fqx "$identity" "$seal" ||
		fail "firmware-request-only seal omits: $identity"
done

baseline=$root/usr/local/sbin/rog5-a660-firmware-request-only-baseline
probe=$root/usr/local/sbin/rog5-a660-firmware-request-only-probe
helper=$root/usr/local/libexec/rog5-a660-firmware-request-only-open
acceptance=$root/etc/rog5/a660-registration-v3-live.accepted
for source_target in \
	"$repo/scripts/device/check-network-root-a660-firmware-request-only-baseline.sh:$baseline:755" \
	"$repo/scripts/device/probe-network-root-a660-firmware-request-only.sh:$probe:755" \
	"$repo/manifests/acceptance/a660-registration-v3-live.accepted:$acceptance:444"
do
	source=${source_target%%:*}
	remainder=${source_target#*:}
	target=${remainder%:*}
	mode=${source_target##*:}
	cmp "$source" "$target"
	[[ $(stat -c '%u:%g:%a' "$target") == "0:0:$mode" ]] ||
		fail "installed source metadata changed: $target"
done
grep -qx \
	"baseline_sha256=$(sha256sum "$baseline" | cut -d ' ' -f 1)" "$seal"
grep -qx "probe_sha256=$(sha256sum "$probe" | cut -d ' ' -f 1)" "$seal"
[[ $(sha256sum "$acceptance" | cut -d ' ' -f 1) == "$acceptance_sha" ]]
"$repo/scripts/device/verify-a660-registration-v3-live-acceptance.sh" \
	"$repo/test-results/2026-07-26-a660-registration-v3-live-accepted.md" \
	"$acceptance" >/dev/null

[[ -f $helper && ! -L $helper ]]
[[ $(stat -c '%u:%g:%a:%s' "$helper") == 0:0:755:896 ]]
[[ $(sha256sum "$helper" | cut -d ' ' -f 1) == "$helper_hash" ]]
file "$helper" |
	grep -Fq \
	'ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), statically linked, stripped'
if readelf -lW "$helper" |
	grep -Eq '(^|[[:space:]])(INTERP|DYNAMIC)([[:space:]]|$)'
then
	fail 'installed open helper gained an interpreter or dynamic segment'
fi
[[ $(strings -a "$helper" | grep -Fxc '/dev/dri/renderD128') == 1 ]]
[[ $(strings -a "$helper" | grep -Fxc 'OPEN_ERRNO=117') == 1 ]]

module_root=$root/usr/lib/modules/$release
[[ -d $module_root && ! -L $module_root ]]
[[ $(find "$module_root" -type f -name '*.ko' | wc -l) == 7 ]]
[[ $(stat -c '%u:%g:%a' "$module_root/modules.dep") == 0:0:644 ]]

verify_module() {
	local relative=$1 hash=$2 name=$3 depends=$4
	local module=$module_root/kernel/$relative
	[[ -f $module && ! -L $module ]]
	[[ $(stat -c '%u:%g:%a' "$module") == 0:0:644 ]]
	[[ $(sha256sum "$module" | cut -d ' ' -f 1) == "$hash" ]]
	[[ $(modinfo -F name "$module") == "$name" ]]
	[[ $(modinfo -F depends "$module") == "$depends" ]]
	[[ $(modinfo -F vermagic "$module") == \
		"$release SMP preempt mod_unload aarch64" ]]
	readelf -S "$module" | grep -Eq '[[:space:]][.]BTF[[:space:]]'
}

verify_module drivers/clk/qcom/gpucc-sm8350.ko \
	c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563 \
	gpucc_sm8350 ''
verify_module drivers/gpu/drm/drm_exec.ko \
	71c32424623f826bb6b7f217fb84f624721d90e53eb89cc9d205af66aca9f886 \
	drm_exec ''
verify_module drivers/gpu/drm/drm_gpuvm.ko \
	981d3f322e18c3b815de7dcba0f829d2ca36f25c85347bb233e7e1baa73386f8 \
	drm_gpuvm drm_exec
verify_module drivers/gpu/drm/scheduler/gpu-sched.ko \
	f53fba10fe10cfeca45abc6d808ca2f5a116832b9595de8f09af66206204b1f4 \
	gpu_sched ''
verify_module drivers/soc/qcom/mdt_loader.ko \
	001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3 \
	mdt_loader ''
verify_module drivers/soc/qcom/ubwc_config.ko \
	4220552fbf17562128c956c3cfdbb8abd22e26f2c6a7f22e94422ef34b10e587 \
	ubwc_config ''
verify_module drivers/gpu/drm/msm/msm.ko "$msm_hash" \
	msm 'drm_exec,drm_gpuvm,gpu-sched,mdt_loader,ubwc_config'
modinfo -p "$module_root/kernel/drivers/gpu/drm/msm/msm.ko" |
	grep -Fxq \
	'firmware_request_only:Request exact A660 firmware once and reject DRM open before GPU power (bool)'

firmware_root=$root/usr/lib/firmware
verify_payload() {
	local file=$1 hash=$2
	[[ -f $file && ! -L $file ]]
	[[ $(stat -c '%u:%g:%a' "$file") == 0:0:644 ]]
	[[ $(sha256sum "$file" | cut -d ' ' -f 1) == "$hash" ]]
}
verify_payload "$firmware_root/qcom/a660_sqe.fw" \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76
verify_payload "$firmware_root/qcom/a660_gmu.bin" \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7
[[ ! -e $firmware_root/qcom/sm8350/a660_zap.mbn ]]
[[ $(find "$root" -xdev -type f \
	\( -name a660_sqe.fw -o -name a660_gmu.bin -o -name a660_zap.mbn \) |
	wc -l) == 2 ]]

for removed in \
	usr/local/sbin/rog5-a660-registration-baseline \
	usr/local/sbin/rog5-a660-registration-probe \
	etc/rog5/a660-registration-export
do
	[[ ! -e $root/$removed ]] ||
		fail "consumed registration-v3 control remains: $removed"
done
for relative in \
	root/.ssh/authorized_keys \
	home/rog5/.ssh/authorized_keys \
	etc/ssh/ssh_host_ed25519_key \
	etc/ssh/ssh_host_ed25519_key.pub
do
	cmp "$root/$relative" "$base_root/$relative"
	[[ $(stat -c '%u:%g:%a' "$root/$relative") == \
		"$(stat -c '%u:%g:%a' "$base_root/$relative")" ]]
done

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
unchanged_manifest() {
	local tree=$1
	find "$tree" -xdev \
		! -path "$tree/etc/rog5" \
		! -path "$tree/usr/lib/firmware/qcom" \
		! -path "$tree/usr/local" \
		! -path "$tree/usr/local/sbin" \
		! -path "$tree/usr/lib/modules/$release/kernel/drivers/gpu/drm/msm/msm.ko" \
		! -path "$tree/usr/lib/firmware/qcom/a660_sqe.fw" \
		! -path "$tree/usr/lib/firmware/qcom/a660_gmu.bin" \
		! -path "$tree/usr/lib/firmware/qcom/sm8350/a660_zap.mbn" \
		! -path "$tree/usr/local/libexec" \
		! -path "$tree/usr/local/libexec/*" \
		! -path "$tree/usr/local/sbin/rog5-a660-registration-baseline" \
		! -path "$tree/usr/local/sbin/rog5-a660-registration-probe" \
		! -path "$tree/usr/local/sbin/rog5-a660-firmware-request-only-baseline" \
		! -path "$tree/usr/local/sbin/rog5-a660-firmware-request-only-probe" \
		! -path "$tree/etc/rog5/a660-registration-export" \
		! -path "$tree/etc/rog5/a660-firmware-request-only-export" \
		! -path "$tree/etc/rog5/a660-registration-v3-live.accepted" \
		-printf '%P|%y|%m|%U|%G|%s|%l\n' | sort
}
unchanged_manifest "$base_root" >"$work/base.metadata"
unchanged_manifest "$root" >"$work/candidate.metadata"
cmp "$work/base.metadata" "$work/candidate.metadata"

unchanged_hashes() {
	local tree=$1
	(
		cd "$tree"
		find . -xdev -type f \
			! -path "./usr/lib/modules/$release/kernel/drivers/gpu/drm/msm/msm.ko" \
			! -path './usr/lib/firmware/qcom/a660_sqe.fw' \
			! -path './usr/lib/firmware/qcom/a660_gmu.bin' \
			! -path './usr/lib/firmware/qcom/sm8350/a660_zap.mbn' \
			! -path './usr/local/libexec/*' \
			! -path './usr/local/sbin/rog5-a660-registration-baseline' \
			! -path './usr/local/sbin/rog5-a660-registration-probe' \
			! -path './usr/local/sbin/rog5-a660-firmware-request-only-baseline' \
			! -path './usr/local/sbin/rog5-a660-firmware-request-only-probe' \
			! -path './etc/rog5/a660-registration-export' \
			! -path './etc/rog5/a660-firmware-request-only-export' \
			! -path './etc/rog5/a660-registration-v3-live.accepted' \
			-print0 | sort -z | xargs -0 sha256sum
	)
}
unchanged_hashes "$base_root" >"$work/base.sha256"
unchanged_hashes "$root" >"$work/candidate.sha256"
cmp "$work/base.sha256" "$work/candidate.sha256"

echo 'PASS A660 firmware-request-only v4 export modules=7 firmware=2 zap=absent helper=exact credentials=preserved base=registration-v3'
