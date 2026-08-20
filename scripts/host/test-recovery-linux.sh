#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd -P)
set +u
. "$repo/scripts/host/generated-power-usb-active.sh"
set -u
recovery=$repo/scripts/host/recovery-linux.sh
policy=$repo/manifests/temporary-boot-images.tsv
manifest=$repo/manifests/artifacts.tsv

[ -x "$recovery" ] || fail "missing executable recovery wrapper: $recovery"
[ -r "$policy" ] || fail "missing temporary-boot policy: $policy"
[ -r "$manifest" ] || fail "missing artifact manifest: $manifest"
sh -n "$recovery"

awk -F '\t' '
	NR == FNR {
		if (FNR == 1) {
			if ($1 != "name" || $2 != "status" || $3 != "basis")
				exit 10
			next
		}
		if ($1 == "" || $3 == "" || seen_policy[$1]++)
			exit 11
		if ($2 != "allow" && $2 != "deny" && $2 != "revoked")
			exit 12
		if ($2 == "allow") {
			allowed[$1] = 1
			allow_count++
		}
		next
	}
	FNR == 1 {
		if ($1 != "name" || $2 != "size" || $3 != "sha256")
			exit 13
		next
	}
	$1 in allowed {
		if (seen_manifest[$1]++)
			exit 14
		if ($2 !~ /^[0-9]+$/ || $3 !~ /^[0-9a-f]{64}$/)
			exit 15
		found[$1] = 1
	}
	END {
		if (allow_count != 3)
			exit 16
		for (name in allowed)
			if (!(name in found))
				exit 17
	}
' "$policy" "$manifest" ||
	fail 'temporary-boot policy is malformed or not uniquely manifest-backed'

awk -F '\t' '
	$1 == "artifacts/recovery-stage-v18/boot-5.4.210-kexec-stage-builtin-recovery.avb.img" &&
	$2 == "revoked" &&
	$3 == "twice-live-accepted historical staging image; superseded as active authority by the corrected diagnostic lifecycle; never flash" {
		count++
	}
	END { exit count == 1 ? 0 : 1 }
' "$policy" ||
	fail 'the exact revoked v18 staging row is absent from temporary-boot policy'
consumed_diagnostic='build/early-target-diagnostic-deployment-20260801-production/wrapper/repack/stable-recovery-a.avb.img'
if grep -Fq "$consumed_diagnostic" "$policy"; then
	fail 'the consumed diagnostic wrapper remains in temporary-boot policy'
fi
awk -F '\t' -v name="$consumed_diagnostic" '
	$1 == name && $4 ~ /^consumed production-signed temporary recovery/ {
		count++
	}
	END { exit count == 1 ? 0 : 1 }
' "$manifest" ||
	fail 'the consumed diagnostic wrapper is not retained exactly in inventory'
consumed_corrected='build/early-target-diagnostic-deployment-20260801-fetch-policy-r2-production/wrapper/repack/stable-recovery-a.avb.img'
if grep -Fq "$consumed_corrected" "$policy"; then
	fail 'the consumed corrected wrapper remains in temporary-boot policy'
fi
awk -F '\t' -v name="$consumed_corrected" '
	$1 == name &&
	$4 ~ /^consumed production-signed fetch-policy-corrected diagnostic recovery/ {
		count++
	}
	END { exit count == 1 ? 0 : 1 }
' "$manifest" ||
	fail 'the consumed corrected wrapper is not retained exactly in inventory'
listener_successor='build/early-target-diagnostic-deployment-20260802-listener-r3-production/wrapper/repack/stable-recovery-a.avb.img'
if awk -F '\t' -v name="$listener_successor" \
	'$1 == name { found=1 } END { exit !found }' "$policy"
then
	fail 'the consumed listener-corrected successor remains in temporary-boot policy'
fi
awk -F '\t' -v name="$listener_successor" '
	$1 == name && $2 == "100663296" &&
	$3 == "332889a83f541ed0e17c94656836c512a35b5bfd6bbbaf735d2f5f6b94b51830" &&
	$4 ~ /^consumed generation-1 AVB wrapper/ { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'the listener-corrected successor inventory is not exact'
nfs_gated_successor='build/early-target-diagnostic-deployment-20260802-nfs-gated-r4-production/wrapper/repack/stable-recovery-a.avb.img'
if awk -F '\t' -v name="$nfs_gated_successor" \
	'$1 == name { found=1 } END { exit !found }' "$policy"
then
	fail 'the consumed NFS-gated successor remains in temporary-boot policy'
fi
awk -F '\t' -v name="$nfs_gated_successor" '
	$1 == name && $2 == "100663296" &&
	$3 == "70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1" &&
	$4 ~ /^consumed generation-2 AVB wrapper/ { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'the NFS-gated successor inventory is not exact'
generation3='build/early-target-diagnostic-deployment-20260802-fresh-fetch-r5-production/wrapper/repack/stable-recovery-a.avb.img'
if awk -F '\t' -v name="$generation3" '
	$1 == name { found=1 }
	END { exit found ? 0 : 1 }
' "$policy"
then
	fail 'the consumed generation-3 recovery remains in temporary-boot policy'
fi
awk -F '\t' -v name="$generation3" '
	$1 == name && $2 == "100663296" &&
	$3 == "eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6" &&
	$4 ~ /^consumed generation-3 fresh-fetch diagnostic recovery/ { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'generation-3 consumed artifact inventory is not exact'
generation4='build/stable-recovery-generation4-timeout-lattice-20260803-a/repack/stable-recovery-a.avb.img'
if awk -F '\t' -v name="$generation4" '
	$1 == name { found=1 }
	END { exit found ? 0 : 1 }
' "$policy"
then
	fail 'the consumed generation-4 recovery remains in temporary-boot policy'
fi
awk -F '\t' -v name="$generation4" '
	$1 == name && $2 == "100663296" &&
	$3 == "220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d" &&
	$4 ~ /^consumed generation-4 timeout-lattice diagnostic recovery/ &&
	$4 ~ /45-second NFS readiness deadline expired/ &&
	$4 ~ /COMMIT was never sent and no target ran/ &&
	$4 ~ /retain offline only; never retry or flash$/ { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'generation-4 consumed artifact inventory is not exact'
generation5='build/stable-recovery-generation5-choreography-20260803-a/repack/stable-recovery-a.avb.img'
awk -F '\t' -v name="$generation5" '
	$1 == name { count++ }
	END { exit count == 0 ? 0 : 1 }
' "$policy" ||
	fail 'consumed generation-5 recovery remains boot-allowlisted'
awk -F '\t' -v name="$generation5" '
	$1 == name && $2 == "100663296" &&
	$3 == "abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a" &&
	$4 ~ /^consumed generation-5 host-choreography diagnostic recovery/ &&
	$4 ~ /complete 46163787-byte bundle transfer/ &&
	$4 ~ /NFSv4\.2 readiness gate failed before COMMIT/ &&
	$4 ~ /execution_started remained NO and no target ran/ &&
	$4 ~ /retain offline only; never retry or flash$/ { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'generation-5 consumed artifact inventory is not exact'
generation6='build/stable-recovery-generation6-signal-fix-20260803-a/repack/stable-recovery-a.avb.img'
awk -F '\t' -v name="$generation6" '
	$1 == name { count++ }
	END { exit count == 0 ? 0 : 1 }
' "$policy" || fail 'consumed generation-6 recovery remains boot-allowlisted'
awk -F '\t' -v name="$generation6" '
	$1 == name && $2 == "100663296" &&
	$3 == "6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398" &&
	$4 == "consumed generation-6 signal-mask-corrected host diagnostic recovery; one RAM-only recovery boot reached verified recovery ACM/NCM and completed the 46163787-byte signed-bundle transfer; recovery control produced no output and no PREPARED record; independently, the diagnostic collector reached its fixed 120-second ACM deadline with zero target frames; no COMMIT intent existed and no target ran; anchored Alpine restoration and strict SSH fallback passed; automated final host cleanup verification failed because production udev ID_MODEL=ROG_Phone_5_Linux_Server does not match the verifier-required ROG5_ prefix, while independent read-only residue checks passed; retain offline only; never retry or flash" &&
	$5 == "no" { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'generation-6 consumed artifact inventory is not exact'
generation7='build/stable-recovery-generation7-deferred-profile-fix-20260803-a/repack/stable-recovery-a.avb.img'
awk -F '\t' -v name="$generation7" '
	$1 == name { count++ }
	END { exit count == 0 ? 0 : 1 }
' "$policy" || fail 'consumed generation-7 recovery remains boot-allowlisted'
awk -F '\t' -v name="$generation7" '
	$1 == name && $2 == "100663296" &&
	$3 == "d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901" &&
	$4 == "consumed generation-7 deferred-profile-corrected host diagnostic recovery; one RAM-only recovery boot reached verified recovery ACM/NCM and completed the 46163787-byte signed-bundle transfer; recovery control produced no output and no PREPARED record; independently, the diagnostic collector rejected after its fixed 120-second ACM-stability deadline with zero target frames; no COMMIT intent existed and no target ran; anchored Alpine profile restoration and strict SSH fallback passed; final host cleanup proof failed because the deferred interface exposed an unexpected NetworkManager association and the post-fallback continuous clean dwell did not complete before its deadline, while independent read-only residue checks were clean; retain offline only; never retry or flash" &&
	$5 == "no" { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'generation-7 consumed artifact inventory is not exact'
generation8='build/stable-recovery-generation8-nmcli-empty-field-fix-20260803-a/repack/stable-recovery-a.avb.img'
awk -F '\t' -v name="$generation8" '
	$1 == name { count++ }
	END { exit count == 0 ? 0 : 1 }
' "$policy" || fail 'consumed generation-8 recovery remains boot-allowlisted'
awk -F '\t' -v name="$generation8" '
	$1 == name && $2 == "100663296" &&
	$3 == "f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415" &&
	$4 == "consumed generation-8 NetworkManager-empty-field-corrected host diagnostic recovery; one RAM-only recovery boot reached verified recovery ACM/NCM and completed the 46163787-byte signed-bundle transfer; recovery returned no PREPARED record and the terminal identity-stability rejection did not label whether it sampled initial recovery or replay discovery after transport loss; Generation-9 timing makes replay of watchdog fallback plausible but does not retroactively prove that phase; independently, the diagnostic collector rejected after its fixed ACM-stability deadline with zero target frames; no COMMIT intent existed and no target ran; exact Alpine fallback returned after the pre-commit failure; final host cleanup proof failed because the lifecycle could not inspect the empty root-owned mode-0600 NFS export table; independent read-only checks found no NFS listener, service, kernel threads, export mount, or lifecycle marker; retain offline only; never retry or flash" &&
	$5 == "no" { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'generation-8 consumed artifact inventory is not exact'
generation9='build/stable-recovery-generation9-acm-classifier-20260803-a/repack/stable-recovery-a.avb.img'
awk -F '\t' -v name="$generation9" '
	$1 == name { count++ }
	END { exit count == 0 ? 0 : 1 }
' "$policy" || fail 'consumed generation-9 recovery remains boot-allowlisted'
awk -F '\t' -v name="$generation9" '
	$1 == name && $2 == "100663296" &&
	$3 == "b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008" &&
	$4 == "consumed generation-9 recovery-ACM-classifier diagnostic wrapper; one RAM-only recovery boot reached verified recovery ACM/NCM and completed the 46163787-byte signed-bundle transfer after PREPARE; recovery returned no PREPARED response and recovery USB disconnected about 178 seconds after enumeration; the terminal classifier reported product-mismatch in all 216 samples, one transition, no identity-field changes, and no truncation, but did not label the discovery phase; the complete transfer and USB timeline support replay discovery of Alpine after transport loss as the best interpretation, not direct phase evidence; recovery rejected before COMMIT, the diagnostic collector rejected at its ACM-stability preflight with zero frames and zero dropped USB events, no COMMIT intent existed, and no target ran; exact Alpine fallback returned and final host cleanup proof passed; retain offline only; never retry or flash" &&
	$5 == "no" { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'generation-9 consumed artifact inventory is not exact'
generation10='build/stable-recovery-generation10-prepare-progress-20260803-a/repack/stable-recovery-a.avb.img'
awk -F '\t' -v name="$generation10" '
	$1 == name { count++ }
	END { exit count == 0 ? 0 : 1 }
' "$policy" || fail 'consumed generation-10 recovery remains boot-allowlisted'
awk -F '\t' -v name="$generation10" '
	$1 == name && $2 == "100663296" &&
	$3 == "b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51" &&
	$4 == "consumed generation-10 PREPARE-progress-instrumented diagnostic recovery; one RAM-only recovery boot reached verified recovery ACM/NCM and accepted PREPARE; the responder emitted REQUEST_ACCEPTED and the one-transfer host sent all 46163787 signed-bundle bytes, but the ACM transport closed before FETCH_COMPLETE or PREPARED; replay discovery reported stable product-mismatch in all 216 samples with phase=prepare-replay and no identity changes; the diagnostic collector expired after its fixed 120-second ACM-stability deadline with zero frames; restricted NFSv4.2 reached pre-COMMIT readiness, but no COMMIT intent existed and no target ran; exact Alpine fallback, strict SSH, profile restoration, and final host cleanup passed; retain offline only; never retry or flash" &&
	$5 == "no" { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'generation-10 consumed artifact inventory is not exact'
generation11='build/stable-recovery-generation11-ncm-progress-20260804-a/repack/stable-recovery-a.avb.img'
generation12='build/stable-recovery-generation12-host-confinement-fix-20260804-a/repack/stable-recovery-a.avb.img'
awk -F '\t' -v name="$generation12" '
	$2 == "allow" {
		allow_count++
	}
	$1 == name { generation12_count++ }
	END { exit allow_count == 3 && generation12_count == 0 ? 0 : 1 }
' "$policy" || fail 'temporary-boot policy retains generation-12 admission'
power_image=$POWER_USB_OUTPUT_ROOT/wrapper/repack/stable-recovery-a.avb.img
awk -F '\t' -v name="$power_image" -v basis="$POWER_USB_BOOT_POLICY_BASIS" '
	$1 == name && $2 == "allow" && $3 == basis && NF == 3 { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$policy" || fail 'active power/USB admission is not exact'
awk -F '\t' -v name="$generation12" '
	$1 == name && $2 == "100663296" &&
	$3 == "615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6" &&
	$4 ~ /^consumed generation-12 host-confinement-corrected diagnostic recovery/ &&
	$4 ~ /stage 70 nfs-mount-begin/ && $4 ~ /FALLBACK_RETURNED/ &&
	$4 ~ /never retry or flash$/ && $5 == "no" { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'generation-12 consumed artifact inventory is not exact'
awk -F '\t' -v name="$generation11" '
	$1 == name { count++ }
	END { exit count == 0 ? 0 : 1 }
' "$policy" || fail 'consumed generation-11 recovery remains boot-allowlisted'
awk -F '\t' -v name="$generation11" '
	$1 == name && $2 == "100663296" &&
	$3 == "8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562" &&
	$4 == "consumed generation-11 receive-only NCM-progress diagnostic recovery; one RAM-only recovery boot reached verified recovery ACM/NCM; the privileged serve-progress-deferred host path started the exact receive-only 8081 collector, but its post-start listener-confinement check failed before the bundle-server ready marker; capture ended PARTIAL/NO_ADMISSION with zero records and authority=NONE; early-target diagnostic ACM never became stable and produced zero frames with zero dropped USB events; no recovery PREPARE or COMMIT intent existed and no target ran; exact Alpine fallback, strict SSH, profile restoration, host cleanup, and Steam socket restoration passed; retain offline only; never retry or flash" &&
	$5 == "no" { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'generation-11 consumed artifact inventory is not exact'
generation20='build/ssh-acceptance-v20-fatal-token-boundary-fix-20260812-r1/wrapper/repack/stable-recovery-a.avb.img'
awk -F '\t' -v name="$generation20" '
	$1 == name { count++ }
	END { exit count == 0 ? 0 : 1 }
' "$policy" || fail 'consumed Generation 20 recovery remains boot-allowlisted'
awk -F '\t' -v name="$generation20" '
	$1 == name && $2 == "100663296" &&
	$3 == "cacd0164d7d1d581f6fa4cb8926d7fea655be92e333c84635de953dd7d816b39" &&
	$4 ~ /^consumed token-delimited-fatal-filter SSH recovery/ &&
	$4 ~ /NFSv4\.2 at target boot 4\.930s/ &&
	$4 ~ /strict key-only SSH and runtime acceptance at 379\.548s/ &&
	$4 ~ /pstore was unavailable and remains inconclusive/ &&
	$4 ~ /never retry or flash$/ && $5 == "no" { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'Generation 20 consumed artifact inventory is not exact'

if grep -Eq \
	'fastboot[[:space:]]+(flash|erase)|dd[[:space:]].*of=/dev/|mkfs|parted|sgdisk' \
	"$recovery"
then
	fail 'recovery wrapper contains a persistent-write path'
fi
grep -Fq 'no payload execution is currently authorized' "$recovery" ||
	fail 'recovery wrapper does not deny legacy payload execution'
grep -Fq 'docs/recovery-control-plane.md' "$recovery" ||
	fail 'recovery wrapper does not point to the replacement control plane'
if grep -Fq 'network-root-acm.py' "$recovery" ||
	grep -Fq 'ALLOW_ATTENDED_KEXEC=1' "$recovery" ||
	grep -Fq 'socat' "$recovery"
then
	fail 'recovery wrapper reintroduced legacy ACM execute guidance or socat'
fi

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
mock_repo=$stage/repo
mock_bin=$stage/bin
install -d -m 0755 \
	"$mock_repo/scripts/host" \
	"$mock_repo/manifests" \
	"$mock_repo/artifacts/recovery-stage-v18" \
	"$mock_repo/artifacts/consumed" \
	"$mock_bin"
install -m 0755 "$recovery" "$mock_repo/scripts/host/recovery-linux.sh"

accepted=$mock_repo/artifacts/recovery-stage-v18/accepted.avb.img
consumed=$mock_repo/artifacts/consumed/consumed.avb.img
lifecycle=$mock_repo/build/stable-recovery-generation-fixture/repack/recovery.avb.img
install -d -m 0755 "$(dirname "$lifecycle")"
printf '%s\n' 'accepted temporary recovery fixture' >"$accepted"
printf '%s\n' 'consumed recovery fixture' >"$consumed"
printf '%s\n' 'lifecycle recovery fixture' >"$lifecycle"
accepted_name=${accepted#"$mock_repo"/}
consumed_name=${consumed#"$mock_repo"/}
lifecycle_name=${lifecycle#"$mock_repo"/}
accepted_size=$(stat -c %s "$accepted")
consumed_size=$(stat -c %s "$consumed")
lifecycle_size=$(stat -c %s "$lifecycle")
accepted_hash=$(sha256sum "$accepted" | cut -d ' ' -f 1)
consumed_hash=$(sha256sum "$consumed" | cut -d ' ' -f 1)
lifecycle_hash=$(sha256sum "$lifecycle" | cut -d ' ' -f 1)

{
	printf 'name\tsize\tsha256\trole\ttracked\n'
	printf '%s\t%s\t%s\tunbooted accepted fixture\tno\n' \
		"$accepted_name" "$accepted_size" "$accepted_hash"
	printf '%s\t%s\t%s\tconsumed fixture\tno\n' \
		"$consumed_name" "$consumed_size" "$consumed_hash"
	printf '%s\t%s\t%s\tunbooted generation fixture\tno\n' \
		"$lifecycle_name" "$lifecycle_size" "$lifecycle_hash"
} >"$mock_repo/manifests/artifacts.tsv"
{
	printf 'name\tstatus\tbasis\n'
	printf '%s\tallow\taccepted fixture\n' "$accepted_name"
} >"$mock_repo/manifests/temporary-boot-images.tsv"

calls=$stage/fastboot-calls
cat >"$mock_bin/fastboot" <<'MOCK'
#!/bin/sh
set -eu
case $* in
	--version)
		echo 'fastboot version mock'
		;;
	devices)
		printf 'MOCKSERIAL\tfastboot\n'
		;;
	'-s MOCKSERIAL getvar product')
		printf '%sproduct: %s\n' \
			"${MOCK_FASTBOOT_PREFIX:-}" \
			"${MOCK_FASTBOOT_PRODUCT:-lahaina}" >&2
		;;
	*)
		printf '%s\n' "$*" >>"$MOCK_FASTBOOT_CALLS"
		exit 1
		;;
esac
MOCK
chmod 0755 "$mock_bin/fastboot"

output=$(BOOT_IMAGE=$accepted \
	FASTBOOT=$mock_bin/fastboot \
	MOCK_FASTBOOT_CALLS=$calls \
	"$mock_repo/scripts/host/recovery-linux.sh" preflight)
printf '%s\n' "$output" |
	grep -Fq "PASS Linux recovery preflight image_sha256=$accepted_hash" ||
	fail 'accepted fixture did not pass recovery preflight'

output=$(BOOT_IMAGE=$accepted \
	FASTBOOT=$mock_bin/fastboot \
	MOCK_FASTBOOT_CALLS=$calls \
	MOCK_FASTBOOT_PREFIX='(bootloader) ' \
	"$mock_repo/scripts/host/recovery-linux.sh" preflight)
printf '%s\n' "$output" |
	grep -Fq "PASS Linux recovery preflight image_sha256=$accepted_hash" ||
	fail 'legacy-prefixed fastboot product did not pass recovery preflight'

{
	printf 'name\tstatus\tbasis\n'
	printf '%s\tallow\tone fixture lifecycle; never flash\n' "$lifecycle_name"
} >"$mock_repo/manifests/temporary-boot-images.tsv"
set +e
output=$(BOOT_IMAGE=$lifecycle \
	FASTBOOT=$mock_bin/fastboot \
	MOCK_FASTBOOT_CALLS=$calls \
	"$mock_repo/scripts/host/recovery-linux.sh" preflight 2>&1)
status=$?
set -e
[ "$status" -ne 0 ] || fail 'generation lifecycle image passed the generic recovery wrapper'
printf '%s\n' "$output" |
	grep -Fq 'generation diagnostic recovery requires the one-shot lifecycle controller' ||
	fail 'generation lifecycle bypass did not report the controller boundary'

{
	printf 'name\tstatus\tbasis\n'
	printf '%s\tallow\taccepted fixture\n' "$accepted_name"
} >"$mock_repo/manifests/temporary-boot-images.tsv"

set +e
output=$(BOOT_IMAGE=$consumed \
	FASTBOOT=$mock_bin/fastboot \
	MOCK_FASTBOOT_CALLS=$calls \
	"$mock_repo/scripts/host/recovery-linux.sh" preflight 2>&1)
status=$?
set -e
[ "$status" -ne 0 ] || fail 'manifest-only consumed image passed preflight'
printf '%s\n' "$output" |
	grep -Fq 'temporary boot is not authorized' ||
	fail 'manifest-only denial did not report the policy boundary'

set +e
output=$(BOOT_IMAGE=$accepted \
	FASTBOOT=$mock_bin/fastboot \
	MOCK_FASTBOOT_CALLS=$calls \
	MOCK_FASTBOOT_PRODUCT=other-board \
	"$mock_repo/scripts/host/recovery-linux.sh" preflight 2>&1)
status=$?
set -e
[ "$status" -ne 0 ] || fail 'wrong fastboot product passed preflight'
printf '%s\n' "$output" |
	grep -Fq 'unexpected fastboot product: other-board' ||
	fail 'wrong fastboot product did not report the device boundary'

set +e
output=$(BOOT_IMAGE=$accepted \
	FASTBOOT=$mock_bin/fastboot \
	MOCK_FASTBOOT_CALLS=$calls \
	"$mock_repo/scripts/host/recovery-linux.sh" boot 2>&1)
status=$?
set -e
[ "$status" -ne 0 ] || fail 'temporary boot ran without its explicit guard'
printf '%s\n' "$output" |
	grep -Fq 'set ALLOW_TEMPORARY_BOOT=1' ||
	fail 'missing temporary-boot guard was not reported'

printf '%s\tallow\tduplicate fixture\n' "$accepted_name" \
	>>"$mock_repo/manifests/temporary-boot-images.tsv"
set +e
output=$(BOOT_IMAGE=$accepted \
	FASTBOOT=$mock_bin/fastboot \
	MOCK_FASTBOOT_CALLS=$calls \
	"$mock_repo/scripts/host/recovery-linux.sh" preflight 2>&1)
status=$?
set -e
[ "$status" -ne 0 ] || fail 'duplicate temporary-boot policy row passed'
printf '%s\n' "$output" |
	grep -Fq 'temporary boot is not authorized' ||
	fail 'duplicate policy row did not fail closed'

{
	printf 'name\tstatus\tbasis\n'
	printf '%s\tallow\taccepted fixture\n' "$accepted_name"
	printf '%s\t\tmissing status duplicate\n' "$accepted_name"
} >"$mock_repo/manifests/temporary-boot-images.tsv"
set +e
output=$(BOOT_IMAGE=$accepted \
	FASTBOOT=$mock_bin/fastboot \
	MOCK_FASTBOOT_CALLS=$calls \
	"$mock_repo/scripts/host/recovery-linux.sh" preflight 2>&1)
status=$?
set -e
[ "$status" -ne 0 ] || fail 'empty-status duplicate policy row passed'
printf '%s\n' "$output" |
	grep -Fq 'temporary boot is not authorized' ||
	fail 'empty-status duplicate policy row did not fail closed'

{
	printf 'name\tstatus\tbasis\n'
	printf '%s\tallow\taccepted fixture\n' "$accepted_name"
} >"$mock_repo/manifests/temporary-boot-images.tsv"
printf '%s\t\t\tduplicate manifest fixture\tno\n' "$accepted_name" \
	>>"$mock_repo/manifests/artifacts.tsv"
set +e
output=$(BOOT_IMAGE=$accepted \
	FASTBOOT=$mock_bin/fastboot \
	MOCK_FASTBOOT_CALLS=$calls \
	"$mock_repo/scripts/host/recovery-linux.sh" preflight 2>&1)
status=$?
set -e
[ "$status" -ne 0 ] || fail 'empty-field duplicate manifest row passed'
printf '%s\n' "$output" |
	grep -Fq 'expected one manifest row' ||
	fail 'empty-field duplicate manifest row did not fail closed'

[ ! -s "$calls" ] || fail 'recovery wrapper issued an unexpected fastboot command'

echo 'PASS recovery wrapper separates artifact inventory from boot authority'
