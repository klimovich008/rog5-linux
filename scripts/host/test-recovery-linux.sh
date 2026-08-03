#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd -P)
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
		if (allow_count > 1)
			exit 16
		for (name in allowed)
			if (!(name in found))
				exit 17
	}
' "$policy" "$manifest" ||
	fail 'temporary-boot policy is malformed or not uniquely manifest-backed'

grep -Fq \
	'artifacts/recovery-stage-v18/boot-5.4.210-kexec-stage-builtin-recovery.avb.img' \
	"$policy" ||
	fail 'the accepted v18 staging image is absent from temporary-boot policy'
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
	fail 'the offline generation-4 recovery is present in temporary-boot policy'
fi
awk -F '\t' -v name="$generation4" '
	$1 == name && $2 == "100663296" &&
	$3 == "220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d" &&
	$4 ~ /^unbooted generation-4 timeout-lattice diagnostic recovery/ { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$manifest" || fail 'generation-4 offline artifact inventory is not exact'

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
printf '%s\n' 'accepted temporary recovery fixture' >"$accepted"
printf '%s\n' 'consumed recovery fixture' >"$consumed"
accepted_name=${accepted#"$mock_repo"/}
consumed_name=${consumed#"$mock_repo"/}
accepted_size=$(stat -c %s "$accepted")
consumed_size=$(stat -c %s "$consumed")
accepted_hash=$(sha256sum "$accepted" | cut -d ' ' -f 1)
consumed_hash=$(sha256sum "$consumed" | cut -d ' ' -f 1)

{
	printf 'name\tsize\tsha256\trole\ttracked\n'
	printf '%s\t%s\t%s\taccepted fixture\tno\n' \
		"$accepted_name" "$accepted_size" "$accepted_hash"
	printf '%s\t%s\t%s\tconsumed fixture\tno\n' \
		"$consumed_name" "$consumed_size" "$consumed_hash"
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
