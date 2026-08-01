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
		if (allow_count != 2)
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
grep -Fq \
	'build/early-target-diagnostic-deployment-20260801-production/wrapper/repack/stable-recovery-a.avb.img' \
	"$policy" ||
	fail 'the admitted diagnostic wrapper is absent from temporary-boot policy'

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
