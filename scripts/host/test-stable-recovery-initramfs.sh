#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output_root=${1:-}
base=$repo/artifacts/recovery-stage-v18/rog5-recovery-initramfs.cpio.gz
wrapper_config=$repo/artifacts/recovery-stage-v18/config-5.4.210-kexec-stage-builtin-recovery
kexec_apk=$repo/artifacts/recovery-inputs/kexec-tools-2.0.32-r2.apk
xz_apk=$repo/artifacts/recovery-inputs/xz-libs-5.8.3-r0.apk
zstd_apk=$repo/artifacts/recovery-inputs/zstd-libs-1.5.7-r2.apk
base_image=localhost/rog5-persistent-root-verifier:alpine-3.24
verifier_image=localhost/rog5-recovery-bundle-verifier:alpine-3.24-openssl-3.5.7

for command in chmod cmp cp cpio cut find git grep gzip head locale mkdir \
	mktemp openssl podman realpath rm sed sha256sum sort stat tail touch; do
	command -v "$command" >/dev/null ||
		fail "missing stable-recovery test command: $command"
done
for input in "$base" "$wrapper_config" "$kexec_apk" "$xz_apk" "$zstd_apk"; do
	[[ -f $input && ! -L $input ]] ||
		fail "missing regular ignored recovery input: $input"
done
[[ $(sha256sum "$base" | cut -d ' ' -f 1) == \
	852b02a2cbcb2dfd43598269ff1b2b10cb1542e90ab7a7aa32d1a26c7cc645fc ]] ||
	fail 'unexpected accepted v18 recovery-base hash'
[[ $(sha256sum "$wrapper_config" | cut -d ' ' -f 1) == \
	df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f ]] ||
	fail 'unexpected accepted v18 wrapper-config hash'
for setting in \
	CONFIG_KEXEC=y \
	CONFIG_MEMFD_CREATE=y \
	CONFIG_NAMESPACES=y \
	CONFIG_NET_NS=y \
	CONFIG_SECCOMP=y \
	CONFIG_SECCOMP_FILTER=y \
	CONFIG_TMPFS=y \
	CONFIG_USB_CONFIGFS=y \
	CONFIG_USB_F_ACM=y \
	CONFIG_USB_F_NCM=y
do
	grep -qx "$setting" "$wrapper_config" ||
		fail "wrapper kernel lacks fixed-control prerequisite: $setting"
done
grep -qx '# CONFIG_SCSI_SCAN_ASYNC is not set' "$wrapper_config" ||
	fail 'wrapper SCSI scan policy changed from the reviewed contract'
for setting in CONFIG_SCSI_UFSHCD=y CONFIG_SCSI_UFS_QCOM=y; do
	grep -qx "$setting" "$wrapper_config" ||
		fail "wrapper kernel lacks measured UFS topology prerequisite: $setting"
done

for image in "$base_image" "$verifier_image"; do
	podman image exists "$image" ||
		fail "missing pinned local AArch64 image: $image"
	[[ $(podman image inspect "$image" --format '{{.Architecture}}') == arm64 ]] ||
		fail "build image is not arm64: $image"
done
[[ $(podman image inspect "$base_image" --format '{{.Id}}') == \
	d5fb16636fadea937b74dc3e062617d74a12577fd3fcc3f61fec24d0f7364495 ]] ||
	fail 'unexpected base AArch64 builder image ID'
[[ $(podman image inspect "$base_image" --format '{{.Digest}}') == \
	sha256:750150c51c8b5085d322ecaa5363356bb31ee243d6efab1035bd15f5ffe52355 ]] ||
	fail 'unexpected base AArch64 builder digest'
[[ $(podman image inspect "$verifier_image" --format '{{.Id}}') == \
	e2e90f8ad3cfc4f9b7660ee8828fcae008792f05567fb9b4efd3ab0102063d8e ]] ||
	fail 'unexpected verifier AArch64 builder image ID'
[[ $(podman image inspect "$verifier_image" --format '{{.Digest}}') == \
	sha256:b4946b74324785d005aa3067dd18788f90cc65215a519c8735dce03aa01d1268 ]] ||
	fail 'unexpected verifier AArch64 builder digest'
locale -a | grep -qx 'en_US.utf8' ||
	fail 'cross-locale reproducibility test requires en_US.utf8'
if [[ -n $output_root ]]; then
	output_root=$(realpath -m "$output_root")
	case $output_root in
		"$repo"/build/*) ;;
		*) fail 'retained output root must be below the ignored build directory' ;;
	esac
	git -C "$repo" check-ignore -q "$output_root" ||
		fail 'retained output root is not ignored by Git'
	[[ ! -d $output_root ||
		-z $(find "$output_root" -mindepth 1 -maxdepth 1 -print -quit) ]] ||
		fail 'refusing nonempty retained output root'
fi

test_tmp=$(mktemp -d)
trap 'rm -rf -- "$test_tmp"' EXIT HUP INT TERM

build_static() {
	image=$1
	build_script=$2
	source_file=$3
	output=$4
	podman run --rm --network=none --platform linux/arm64 \
		-v "$repo:/workspace:ro,Z" \
		-v "$test_tmp:/out:Z" \
		"$image" \
		"/workspace/$build_script" \
		"/workspace/$source_file" "/out/$output"
}

for suffix in a b; do
	build_static "$base_image" \
		scripts/device/build-recovery-control.sh \
		tools/recovery_control/rog5-recovery-control.c \
		"rog5-recovery-control-$suffix"
	build_static "$base_image" \
		scripts/device/build-recovery-bundle-fetcher.sh \
		tools/recovery_control/rog5-bundle-fetch.c \
		"rog5-bundle-fetch-$suffix"
	build_static "$verifier_image" \
		scripts/device/build-recovery-bundle-verifier.sh \
		tools/recovery_control/rog5-bundle-verify.c \
		"rog5-bundle-verify-$suffix"
done
for binary in rog5-recovery-control rog5-bundle-fetch rog5-bundle-verify; do
	cmp "$test_tmp/$binary-a" "$test_tmp/$binary-b"
done

# The ephemeral private key exists only in the pipeline and is never written.
openssl genpkey -algorithm ED25519 2>/dev/null |
	openssl pkey -pubout -outform DER 2>/dev/null |
	tail -c 32 >"$test_tmp/ephemeral-public.raw"
chmod 0600 "$test_tmp/ephemeral-public.raw"
[[ $(stat -c %s "$test_tmp/ephemeral-public.raw") == 32 ]]

for suffix in a b; do
	case $suffix in
		a) build_locale=C; build_timezone=UTC ;;
		b) build_locale=en_US.utf8; build_timezone=Pacific/Kiritimati ;;
	esac
	LC_ALL=$build_locale TZ=$build_timezone \
		"$repo/scripts/device/build-stable-recovery-initramfs.sh" \
			"$base" "$repo/initramfs/recovery-init" \
			"$test_tmp/rog5-recovery-control-a" \
			"$test_tmp/rog5-bundle-fetch-a" \
			"$test_tmp/rog5-bundle-verify-a" \
			"$kexec_apk" "$xz_apk" "$zstd_apk" \
			"$test_tmp/ephemeral-public.raw" \
			"$test_tmp/stable-recovery-$suffix.cpio.gz"
	"$repo/scripts/device/verify-stable-recovery-initramfs.sh" \
		"$test_tmp/stable-recovery-$suffix.cpio.gz" \
		"$repo/initramfs/recovery-init" \
		"$test_tmp/rog5-recovery-control-a" \
		"$test_tmp/rog5-bundle-fetch-a" \
		"$test_tmp/rog5-bundle-verify-a" \
		"$test_tmp/ephemeral-public.raw"
done
cmp "$test_tmp/stable-recovery-a.cpio.gz" \
	"$test_tmp/stable-recovery-b.cpio.gz"

expect_init_rejection() {
	name=$1
	init=$2
	expected=$3
	if "$repo/scripts/device/build-stable-recovery-initramfs.sh" \
		"$base" "$init" \
		"$test_tmp/rog5-recovery-control-a" \
		"$test_tmp/rog5-bundle-fetch-a" \
		"$test_tmp/rog5-bundle-verify-a" \
		"$kexec_apk" "$xz_apk" "$zstd_apk" \
		"$test_tmp/ephemeral-public.raw" \
		"$test_tmp/should-not-build-$name.cpio.gz" \
		>"$test_tmp/$name.log" 2>&1
	then
		fail "unsafe recovery init passed the builder: $name"
	fi
	grep -Fqx "$expected" "$test_tmp/$name.log"
}

cp -p "$repo/initramfs/recovery-init" "$test_tmp/shell-init"
printf '%s\n' "setsid sh -c 'exec sh -i </dev/ttyGS0 >/dev/ttyGS0 2>&1'" \
	>>"$test_tmp/shell-init"
expect_init_rejection shell "$test_tmp/shell-init" \
	'FAIL recovery init contains a legacy shell, credential, SSH, or network override'

cp -p "$repo/initramfs/recovery-init" "$test_tmp/dhcp-init"
printf '%s\n' 'udhcpc -i usb0' >>"$test_tmp/dhcp-init"
expect_init_rejection dhcp "$test_tmp/dhcp-init" \
	'FAIL recovery init contains a legacy shell, credential, SSH, or network override'

sed '\|/usr/libexec/rog5-recovery-control &|d' \
	"$repo/initramfs/recovery-init" >"$test_tmp/no-control-init"
chmod 0755 "$test_tmp/no-control-init"
expect_init_rejection no-control "$test_tmp/no-control-init" \
	'FAIL recovery init does not start the fixed responder'

sed '\|ip address add 169.254.77.2/30 dev usb0|d' \
	"$repo/initramfs/recovery-init" >"$test_tmp/no-address-init"
chmod 0755 "$test_tmp/no-address-init"
expect_init_rejection no-address "$test_tmp/no-address-init" \
	'FAIL recovery init lacks the fixed device address'

sed '\|^bundle_root=/run/rog5-bundles$|d' \
	"$repo/initramfs/recovery-init" >"$test_tmp/no-bundle-root-init"
chmod 0755 "$test_tmp/no-bundle-root-init"
expect_init_rejection no-bundle-root "$test_tmp/no-bundle-root-init" \
	'FAIL recovery init lacks the exact volatile bundle root'

head -c 31 "$test_tmp/ephemeral-public.raw" >"$test_tmp/short-public.raw"
if "$repo/scripts/device/build-stable-recovery-initramfs.sh" \
	"$base" "$repo/initramfs/recovery-init" \
	"$test_tmp/rog5-recovery-control-a" \
	"$test_tmp/rog5-bundle-fetch-a" \
	"$test_tmp/rog5-bundle-verify-a" \
	"$kexec_apk" "$xz_apk" "$zstd_apk" \
	"$test_tmp/short-public.raw" \
	"$test_tmp/should-not-build.cpio.gz" \
	>"$test_tmp/short-key.log" 2>&1
then
	fail '31-byte public key passed the stable recovery builder'
fi
grep -qx 'FAIL Ed25519 public key must contain exactly 32 raw bytes' \
	"$test_tmp/short-key.log"

head -c 32 /dev/zero >"$test_tmp/zero-public.raw"
if "$repo/scripts/device/build-stable-recovery-initramfs.sh" \
	"$base" "$repo/initramfs/recovery-init" \
	"$test_tmp/rog5-recovery-control-a" \
	"$test_tmp/rog5-bundle-fetch-a" \
	"$test_tmp/rog5-bundle-verify-a" \
	"$kexec_apk" "$xz_apk" "$zstd_apk" \
	"$test_tmp/zero-public.raw" \
	"$test_tmp/should-not-build-zero.cpio.gz" \
	>"$test_tmp/zero-key.log" 2>&1
then
	fail 'all-zero public key passed the stable recovery builder'
fi
grep -qx 'FAIL Ed25519 public key must not be all zero' \
	"$test_tmp/zero-key.log"

repack_fixture() {
	stage=$1
	output=$2
	find "$stage" -exec touch -h -d '@1681862400' {} +
	(
		cd "$stage"
		find . -mindepth 1 -print0 | LC_ALL=C sort -z |
			cpio --null -o --quiet --format=newc --owner=0:0 \
				--reproducible
	) | gzip -n >"$output"
}

expect_archive_rejection() {
	name=$1
	archive=$2
	expected=$3
	if "$repo/scripts/device/verify-stable-recovery-initramfs.sh" \
		"$archive" "$repo/initramfs/recovery-init" \
		"$test_tmp/rog5-recovery-control-a" \
		"$test_tmp/rog5-bundle-fetch-a" \
		"$test_tmp/rog5-bundle-verify-a" \
		"$test_tmp/ephemeral-public.raw" \
		>"$test_tmp/$name.log" 2>&1
	then
		fail "unsafe stable-recovery archive passed verification: $name"
	fi
	grep -Fqx "$expected" "$test_tmp/$name.log"
}

credential_stage=$test_tmp/credential-stage
mkdir "$credential_stage"
gzip -dc "$test_tmp/stable-recovery-a.cpio.gz" |
	(cd "$credential_stage" && cpio -idm --quiet --no-absolute-filenames)
mkdir -p "$credential_stage/root/.ssh"
printf '%s\n' 'test-only-forbidden-authorized-key' \
	>"$credential_stage/root/.ssh/authorized_keys"
chmod 0600 "$credential_stage/root/.ssh/authorized_keys"
repack_fixture "$credential_stage" "$test_tmp/credential.cpio.gz"
expect_archive_rejection credential "$test_tmp/credential.cpio.gz" \
	'FAIL legacy access or credential path exists in stable recovery'

setid_stage=$test_tmp/setid-stage
mkdir "$setid_stage"
gzip -dc "$test_tmp/stable-recovery-a.cpio.gz" |
	(cd "$setid_stage" && cpio -idm --quiet --no-absolute-filenames)
cp "$setid_stage/bin/busybox" "$setid_stage/usr/bin/rog5-setid-fixture"
chmod 4755 "$setid_stage/usr/bin/rog5-setid-fixture"
repack_fixture "$setid_stage" "$test_tmp/setid.cpio.gz"
expect_archive_rejection setid "$test_tmp/setid.cpio.gz" \
	'FAIL set-ID file exists in stable recovery'

unlocked_stage=$test_tmp/unlocked-stage
mkdir "$unlocked_stage"
gzip -dc "$test_tmp/stable-recovery-a.cpio.gz" |
	(cd "$unlocked_stage" && cpio -idm --quiet --no-absolute-filenames)
sed -i 's/^root:[^:]*/root:/' "$unlocked_stage/etc/shadow"
repack_fixture "$unlocked_stage" "$test_tmp/unlocked.cpio.gz"
expect_archive_rejection unlocked "$test_tmp/unlocked.cpio.gz" \
	'FAIL stable recovery root account is not locked'

legacy_stage=$test_tmp/legacy-stage
mkdir "$legacy_stage"
gzip -dc "$test_tmp/stable-recovery-a.cpio.gz" |
	(cd "$legacy_stage" && cpio -idm --quiet --no-absolute-filenames)
mkdir -p "$legacy_stage/opt/legacy/bin"
cp "$legacy_stage/bin/busybox" "$legacy_stage/opt/legacy/bin/login"
chmod 0755 "$legacy_stage/opt/legacy/bin/login"
repack_fixture "$legacy_stage" "$test_tmp/legacy.cpio.gz"
expect_archive_rejection legacy "$test_tmp/legacy.cpio.gz" \
	'FAIL legacy login or DHCP entry point exists in stable recovery'

shadow_mode_stage=$test_tmp/shadow-mode-stage
mkdir "$shadow_mode_stage"
gzip -dc "$test_tmp/stable-recovery-a.cpio.gz" |
	(cd "$shadow_mode_stage" && cpio -idm --quiet --no-absolute-filenames)
chmod 0644 "$shadow_mode_stage/etc/shadow"
repack_fixture "$shadow_mode_stage" "$test_tmp/shadow-mode.cpio.gz"
expect_archive_rejection shadow-mode "$test_tmp/shadow-mode.cpio.gz" \
	'FAIL stable recovery shadow database has an unsafe mode'

sha256sum \
	"$test_tmp/rog5-recovery-control-a" \
	"$test_tmp/rog5-bundle-fetch-a" \
	"$test_tmp/rog5-bundle-verify-a" \
	"$test_tmp/stable-recovery-a.cpio.gz" \
	"$test_tmp/stable-recovery-b.cpio.gz"
if [[ -n $output_root ]]; then
	mkdir -p "$output_root/initramfs-a" "$output_root/initramfs-b"
	cp "$test_tmp/stable-recovery-a.cpio.gz" \
		"$output_root/initramfs-a/rog5-stable-recovery.cpio.gz"
	cp "$test_tmp/stable-recovery-b.cpio.gz" \
		"$output_root/initramfs-b/rog5-stable-recovery.cpio.gz"
	cp "$test_tmp/ephemeral-public.raw" \
		"$output_root/ephemeral-public.raw"
	chmod 0600 "$output_root/ephemeral-public.raw"
	sha256sum \
		"$output_root/initramfs-a/rog5-stable-recovery.cpio.gz" \
		"$output_root/initramfs-b/rog5-stable-recovery.cpio.gz" \
		"$output_root/ephemeral-public.raw"
fi
echo 'PASS reproducible stable-recovery integration with ephemeral public-key test boundary'
