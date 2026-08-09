#!/bin/sh
set -eu

archive=${1:?usage: verify-stable-recovery-initramfs.sh ARCHIVE INIT_OR_DASH CONTROL FETCHER VERIFIER PUBLIC_KEY CONTRACT EXPECTED_ARCHIVE_SHA256_OR_DASH}
init=${2:?missing recovery init}
control=${3:?missing recovery responder}
fetcher=${4:?missing recovery bundle fetcher}
verifier=${5:?missing recovery bundle verifier}
public_key=${6:?missing raw Ed25519 public key}
contract=${7:?missing stable-recovery init contract}
expected_archive_sha256=${8:?missing stable-recovery archive identity}
export LC_ALL=C
export TZ=UTC

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in awk basename cat cmp cpio cut find grep gzip mktemp od readelf rm \
	sed sha256sum stat tr; do
	command -v "$command" >/dev/null ||
		fail "missing initramfs verifier command: $command"
done
for input in "$archive" "$control"; do
	[ -f "$input" ] && [ -r "$input" ] && [ ! -L "$input" ] ||
		fail "unsafe or missing verifier input: $(basename "$input")"
done
case $contract in
	exact-a600000-v1)
		[ -f "$init" ] && [ -r "$init" ] && [ ! -L "$init" ] ||
			fail 'unsafe or missing exact recovery init'
		for input in "$fetcher" "$verifier" "$public_key"; do
			[ -f "$input" ] && [ -r "$input" ] && [ ! -L "$input" ] ||
				fail "unsafe or missing verifier input: $(basename "$input")"
		done
		[ "$expected_archive_sha256" = - ] ||
			fail 'exact recovery verification does not accept an external archive identity'
		;;
	observation-only-a600000-v1)
		[ -f "$init" ] && [ -r "$init" ] && [ ! -L "$init" ] ||
			fail 'unsafe or missing exact recovery init'
		[ "$fetcher" = - ] && [ "$verifier" = - ] &&
			[ "$public_key" = - ] ||
			fail 'observation-only verification rejects mutating component inputs'
		[ "$expected_archive_sha256" = - ] ||
			fail 'observation-only verification does not accept an external archive identity'
		;;
	historical-pinned-v1)
		[ "$init" = - ] ||
			fail 'historical verification must use its pinned embedded init'
		for input in "$fetcher" "$verifier" "$public_key"; do
			[ -f "$input" ] && [ -r "$input" ] && [ ! -L "$input" ] ||
				fail "unsafe or missing verifier input: $(basename "$input")"
		done
		case $expected_archive_sha256 in
			*[!0-9a-f]*|'')
				fail 'historical recovery archive identity is not canonical'
				;;
		esac
		[ "${#expected_archive_sha256}" -eq 64 ] &&
			[ "$expected_archive_sha256" != \
			0000000000000000000000000000000000000000000000000000000000000000 ] ||
			fail 'historical recovery archive identity is not canonical'
		[ "$(sha256sum "$archive" | awk '{ print $1 }')" = \
			"$expected_archive_sha256" ] ||
			fail 'historical recovery archive identity mismatch'
		;;
	*) fail "unsupported stable-recovery init contract: $contract" ;;
esac
gzip -t "$archive"

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
gzip -dc "$archive" | cpio -itv 2>/dev/null >"$stage/archive.list"
awk 'NF && ($3 != "root" || $4 != "root") { exit 1 }' \
	"$stage/archive.list" ||
	fail 'initramfs archive contains a non-root owner or group'
gzip -dc "$archive" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)

case $contract in
	exact-a600000-v1|observation-only-a600000-v1)
		cmp "$stage/init" "$init"
		;;
esac
cmp "$stage/usr/libexec/rog5-recovery-control" "$control"
[ "$(stat -c %a "$stage/init")" = 755 ]
case $contract in
	exact-a600000-v1|historical-pinned-v1)
		cmp "$stage/usr/libexec/rog5-bundle-fetch" "$fetcher"
		cmp "$stage/usr/libexec/rog5-bundle-verify" "$verifier"
		cmp "$stage/etc/rog5/recovery-bundle-ed25519.pub" "$public_key"
		[ "$(stat -c %a "$stage/etc/rog5/recovery-bundle-ed25519.pub")" = 600 ]
		[ "$(stat -c %s "$stage/etc/rog5/recovery-bundle-ed25519.pub")" -eq 32 ]
		[ "$(stat -c %h "$stage/etc/rog5/recovery-bundle-ed25519.pub")" -eq 1 ]
		[ "$(od -An -tx1 -v "$stage/etc/rog5/recovery-bundle-ed25519.pub" |
			tr -d ' \n')" != \
			0000000000000000000000000000000000000000000000000000000000000000 ]
		[ "$(stat -c %a "$stage/usr/sbin/kexec")" = 755 ]
		;;
	observation-only-a600000-v1)
		for path in \
			usr/libexec/rog5-bundle-fetch \
			usr/libexec/rog5-bundle-verify \
			etc/rog5/recovery-bundle-ed25519.pub \
			usr/sbin/kexec
		do
			[ ! -e "$stage/$path" ] && [ ! -L "$stage/$path" ] ||
				fail "observation-only recovery retains mutating path: $path"
		done
		[ -z "$(find "$stage" \( -type f -o -type l \) \
			-name kexec -print -quit)" ] ||
			fail 'observation-only recovery retains a kexec entry point'
		;;
esac
[ -f "$stage/etc/shadow" ] && [ ! -L "$stage/etc/shadow" ] ||
	fail 'unsafe or missing stable recovery shadow database'
[ "$(stat -c %a "$stage/etc/shadow")" = 600 ] ||
	fail 'stable recovery shadow database has an unsafe mode'
[ "$(stat -c %h "$stage/etc/shadow")" -eq 1 ] ||
	fail 'stable recovery shadow database has multiple links'
root_password=$(
	sed -n 's/^root:\([^:]*\):.*/\1/p' "$stage/etc/shadow"
)
[ "$root_password" = '!' ] || fail 'stable recovery root account is not locked'
legacy_entry=$(
	find "$stage" \( -type f -o -type l \) \
		\( -name login -o -name passwd -o -name chpasswd -o \
			-name udhcpc -o -name udhcpc6 -o \
			-path '*/udhcpc/*' \) \
		! -path "$stage/etc/passwd" -print -quit
)
[ -z "$legacy_entry" ] ||
	fail 'legacy login or DHCP entry point exists in stable recovery'

binary_list=usr/libexec/rog5-recovery-control
case $contract in
	exact-a600000-v1|historical-pinned-v1)
		binary_list="$binary_list usr/libexec/rog5-bundle-fetch usr/libexec/rog5-bundle-verify"
		;;
esac
for binary in $binary_list
do
	[ "$(stat -c %a "$stage/$binary")" = 755 ]
	readelf -h "$stage/$binary" | grep -q 'Machine:.*AArch64'
	if readelf -l "$stage/$binary" | grep -q INTERP; then
		fail "$binary has a dynamic interpreter"
	fi
done
case $contract in
	exact-a600000-v1|historical-pinned-v1)
		[ "$(sha256sum "$stage/usr/sbin/kexec" | cut -d ' ' -f 1)" = \
			5e5d0a78b3f0bcf3921ff060f4dce5011cbac24b5e12fedeb8ca03ea5b40d015 ]
		;;
esac

[ -z "$(find "$stage" \
	\( -name authorized_keys -o -name 'ssh_host_*' -o -name sshd -o \
		-name dropbear -o -name getty -o -name '*private*.key' -o \
		-name '*private*.pem' \) -print -quit)" ] ||
	fail 'legacy access or credential path exists in stable recovery'
[ -z "$(find "$stage" -type f -perm /6000 -print -quit)" ] ||
	fail 'set-ID file exists in stable recovery'
if grep -rIl 'BEGIN .*PRIVATE KEY' "$stage" >/dev/null 2>&1; then
	fail 'private-key material exists in stable recovery'
fi
if grep -Eq \
	'sh[[:space:]]+-i|setsid[[:space:]]+sh|authorized_keys|ssh-keygen|/usr/sbin/sshd|rog5\.recovery_(cidr|gateway)|udhcpc' \
	"$stage/init"; then
	fail 'stable recovery init contains a legacy control or network path'
fi

grep -Fq 'pid=%s\nstarttime=%s\n' "$stage/init"
grep -Fq 'expected_wrapper_physical_count=116' "$stage/init"
grep -Fq 'mount -t pstore -o ro pstore /sys/fs/pstore' "$stage/init"
grep -Fq '/run/rog5-postmortem.status' "$stage/init"
grep -Fq "grep -Eq '^session=[0-9a-f]{32}$'" "$stage/init"
grep -Fq 'ip address add 169.254.77.2/30 dev usb0' "$stage/init"
grep -Fq 'bundle_root=/run/rog5-bundles' "$stage/init"
grep -Fq "mkdir -p \"\$bundle_root\"" "$stage/init"
grep -Fq "chown 0:0 \"\$bundle_root\"" "$stage/init"
grep -Fq "chmod 0700 \"\$bundle_root\"" "$stage/init"
case $contract in
	exact-a600000-v1|observation-only-a600000-v1)
		grep -Fxq \
			'/usr/libexec/rog5-recovery-control --mode "$recovery_mode" &' \
			"$stage/init" ||
			fail 'current recovery does not bind the responder mode'
		grep -Fxq 'recovery_mode_file=/etc/rog5/recovery-mode' \
			"$stage/init" ||
			fail 'current recovery lacks its sealed mode path'
		[ -f "$stage/etc/rog5/recovery-mode" ] &&
			[ ! -L "$stage/etc/rog5/recovery-mode" ] &&
			[ "$(stat -c %a "$stage/etc/rog5/recovery-mode")" = 444 ] &&
			[ "$(stat -c %h "$stage/etc/rog5/recovery-mode")" = 1 ] ||
			fail 'current recovery mode file has unsafe metadata'
		case $contract in
			exact-a600000-v1)
				[ "$(cat "$stage/etc/rog5/recovery-mode")" = full-v1 ] ||
					fail 'full recovery mode identity mismatch'
				;;
			observation-only-a600000-v1)
				[ "$(cat "$stage/etc/rog5/recovery-mode")" = \
					observation-only-v1 ] ||
					fail 'observation-only recovery mode identity mismatch'
				;;
		esac
		grep -Fxq 'expected_udc=a600000.dwc3' "$stage/init" ||
			fail 'stable recovery lacks the exact expected UDC identity'
		grep -Fxq 'udc_class_dir=/sys/class/udc' "$stage/init" ||
			fail 'stable recovery lacks the fixed UDC class directory'
		for helper in udc_candidate_count validate_expected_udc_once \
			validate_expected_udc expected_udc_is_bound \
			select_expected_udc bind_expected_udc
		do
			grep -Fxq "$helper() {" "$stage/init" ||
				fail "stable recovery lacks exact UDC helper: $helper"
		done
		if grep -Fq '[ -n "$udc" ] || udc=$(basename "$candidate")' \
			"$stage/init"; then
			fail 'stable recovery retains arbitrary UDC fallback'
		fi
		;;
	historical-pinned-v1)
		grep -Fxq '/usr/libexec/rog5-recovery-control &' "$stage/init" ||
			fail 'historical recovery lacks its pinned responder start shape'
		grep -Fxq 'if ! echo "$udc" >"$gadget/UDC"; then' \
			"$stage/init" ||
			fail 'historical recovery lacks its pinned UDC bind shape'
		;;
esac

lease_line=$(grep -n '^watchdog_lease=/run/rog5-recovery-watchdog.lease$' \
	"$stage/init" | cut -d: -f1)
isolation_count=$(
	grep -c '^if ! isolate_storage; then$' "$stage/init" || true
)
[ "$isolation_count" -eq 2 ] ||
	fail 'stable recovery must invoke storage isolation exactly twice'
isolation_lines=$(
	grep -n '^if ! isolate_storage; then$' "$stage/init" | cut -d: -f1
)
pre_storage_line=$(printf '%s\n' "$isolation_lines" | sed -n '1p')
post_storage_line=$(printf '%s\n' "$isolation_lines" | sed -n '2p')
pre_contract_line=$(
	grep -n 'ASUS wrapper storage topology mismatch before USB configuration' \
		"$stage/init" | cut -d: -f1
)
post_contract_line=$(
	grep -n 'ASUS wrapper storage topology mismatch after device-node rescan' \
		"$stage/init" | cut -d: -f1
)
case $contract in
	exact-a600000-v1|observation-only-a600000-v1)
		control_line=$(grep -n \
			'^/usr/libexec/rog5-recovery-control --mode "\$recovery_mode" &$' \
			"$stage/init" | cut -d: -f1)
		;;
	historical-pinned-v1)
		control_line=$(grep -n '^/usr/libexec/rog5-recovery-control &$' \
			"$stage/init" | cut -d: -f1)
		;;
esac
bundle_root_line=$(grep -n '^bundle_root=/run/rog5-bundles$' \
	"$stage/init" | cut -d: -f1)
bundle_mode_line=$(grep -Fn "chmod 0700 \"\$bundle_root\"" \
	"$stage/init" | cut -d: -f1)
postmortem_line=$(grep -n '^if ! snapshot_postmortem; then$' \
	"$stage/init" | cut -d: -f1)
session_line=$(grep -n 'rog5-control/session' "$stage/init" |
	sed -n '1s/:.*//p')
case $contract in
	exact-a600000-v1|observation-only-a600000-v1)
		# shellcheck disable=SC2016
		bind_line=$(grep -n '^if ! udc=\$(bind_expected_udc); then$' \
			"$stage/init" | cut -d: -f1)
		;;
	historical-pinned-v1)
		# shellcheck disable=SC2016
		bind_line=$(grep -n '^if ! echo "\$udc" >"\$gadget/UDC"; then$' \
			"$stage/init" | cut -d: -f1)
		;;
esac
for value in "$lease_line" "$pre_storage_line" "$pre_contract_line" \
	"$post_storage_line" "$post_contract_line" "$control_line" \
	"$bundle_root_line" "$bundle_mode_line" "$postmortem_line" \
	"$session_line" "$bind_line"; do
	case $value in *[!0-9]*|'') fail 'cannot prove stable recovery ordering' ;; esac
done
[ "$lease_line" -lt "$pre_storage_line" ]
[ "$pre_storage_line" -lt "$pre_contract_line" ]
[ "$pre_contract_line" -lt "$post_storage_line" ]
[ "$post_storage_line" -lt "$post_contract_line" ]
[ "$lease_line" -lt "$postmortem_line" ]
[ "$postmortem_line" -lt "$control_line" ]
[ "$post_contract_line" -lt "$control_line" ]
[ "$bundle_root_line" -lt "$bundle_mode_line" ]
[ "$bundle_mode_line" -lt "$control_line" ]
[ "$control_line" -le "$session_line" ]
[ "$session_line" -lt "$bind_line" ]

echo "PASS stable recovery archive: contract=$contract; fixed responder/session before USB bind, mode-bound payload surface, no interactive shell or SSH"
