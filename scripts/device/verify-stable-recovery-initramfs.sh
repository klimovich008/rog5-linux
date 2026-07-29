#!/bin/sh
set -eu

archive=${1:?usage: verify-stable-recovery-initramfs.sh ARCHIVE INIT CONTROL FETCHER VERIFIER PUBLIC_KEY}
init=${2:?missing recovery init}
control=${3:?missing recovery responder}
fetcher=${4:?missing recovery bundle fetcher}
verifier=${5:?missing recovery bundle verifier}
public_key=${6:?missing raw Ed25519 public key}
export LC_ALL=C
export TZ=UTC

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in awk basename cmp cpio cut find grep gzip mktemp od readelf rm \
	sed sha256sum stat tr; do
	command -v "$command" >/dev/null ||
		fail "missing initramfs verifier command: $command"
done
for input in "$archive" "$init" "$control" "$fetcher" "$verifier" \
	"$public_key"; do
	[ -f "$input" ] && [ -r "$input" ] && [ ! -L "$input" ] ||
		fail "unsafe or missing verifier input: $(basename "$input")"
done
gzip -t "$archive"

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
gzip -dc "$archive" | cpio -itv 2>/dev/null >"$stage/archive.list"
awk 'NF && ($3 != "root" || $4 != "root") { exit 1 }' \
	"$stage/archive.list" ||
	fail 'initramfs archive contains a non-root owner or group'
gzip -dc "$archive" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)

cmp "$stage/init" "$init"
cmp "$stage/usr/libexec/rog5-recovery-control" "$control"
cmp "$stage/usr/libexec/rog5-bundle-fetch" "$fetcher"
cmp "$stage/usr/libexec/rog5-bundle-verify" "$verifier"
cmp "$stage/etc/rog5/recovery-bundle-ed25519.pub" "$public_key"
[ "$(stat -c %a "$stage/init")" = 755 ]
[ "$(stat -c %a "$stage/etc/rog5/recovery-bundle-ed25519.pub")" = 600 ]
[ "$(stat -c %s "$stage/etc/rog5/recovery-bundle-ed25519.pub")" -eq 32 ]
[ "$(stat -c %h "$stage/etc/rog5/recovery-bundle-ed25519.pub")" -eq 1 ]
[ "$(od -An -tx1 -v "$stage/etc/rog5/recovery-bundle-ed25519.pub" |
	tr -d ' \n')" != \
	0000000000000000000000000000000000000000000000000000000000000000 ]
[ "$(stat -c %a "$stage/usr/sbin/kexec")" = 755 ]
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

for binary in \
	usr/libexec/rog5-recovery-control \
	usr/libexec/rog5-bundle-fetch \
	usr/libexec/rog5-bundle-verify
do
	[ "$(stat -c %a "$stage/$binary")" = 755 ]
	readelf -h "$stage/$binary" | grep -q 'Machine:.*AArch64'
	if readelf -l "$stage/$binary" | grep -q INTERP; then
		fail "$binary has a dynamic interpreter"
	fi
done
[ "$(sha256sum "$stage/usr/sbin/kexec" | cut -d ' ' -f 1)" = \
	5e5d0a78b3f0bcf3921ff060f4dce5011cbac24b5e12fedeb8ca03ea5b40d015 ]

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
grep -Fq '/usr/libexec/rog5-recovery-control &' "$stage/init"
grep -Fq "grep -Eq '^session=[0-9a-f]{64}$'" "$stage/init"
grep -Fq 'ip address add 169.254.77.2/30 dev usb0' "$stage/init"

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
control_line=$(grep -n '^/usr/libexec/rog5-recovery-control &$' \
	"$stage/init" | cut -d: -f1)
postmortem_line=$(grep -n '^if ! snapshot_postmortem; then$' \
	"$stage/init" | cut -d: -f1)
session_line=$(grep -n 'rog5-control/session' "$stage/init" |
	sed -n '1s/:.*//p')
# shellcheck disable=SC2016
bind_line=$(grep -n '^if ! echo "\$udc" >"\$gadget/UDC"; then$' \
	"$stage/init" | cut -d: -f1)
for value in "$lease_line" "$pre_storage_line" "$pre_contract_line" \
	"$post_storage_line" "$post_contract_line" "$control_line" \
	"$postmortem_line" "$session_line" "$bind_line"; do
	case $value in *[!0-9]*|'') fail 'cannot prove stable recovery ordering' ;; esac
done
[ "$lease_line" -lt "$pre_storage_line" ]
[ "$pre_storage_line" -lt "$pre_contract_line" ]
[ "$pre_contract_line" -lt "$post_storage_line" ]
[ "$post_storage_line" -lt "$post_contract_line" ]
[ "$lease_line" -lt "$postmortem_line" ]
[ "$postmortem_line" -lt "$control_line" ]
[ "$post_contract_line" -lt "$control_line" ]
[ "$control_line" -le "$session_line" ]
[ "$session_line" -lt "$bind_line" ]

echo 'PASS stable recovery archive: fixed responder/session before USB bind, pinned loader, public trust root only, no interactive shell or SSH'
