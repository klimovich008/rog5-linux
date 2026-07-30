#!/bin/sh
set -eu

base=${1:?usage: build-stable-recovery-initramfs.sh BASE INIT CONTROL FETCHER VERIFIER KEXEC_APK XZ_APK ZSTD_APK PUBLIC_KEY OUTPUT}
init=${2:?missing recovery init}
control=${3:?missing recovery responder}
fetcher=${4:?missing recovery bundle fetcher}
verifier=${5:?missing recovery bundle verifier}
kexec_apk=${6:?missing kexec package}
xz_apk=${7:?missing xz-libs package}
zstd_apk=${8:?missing zstd-libs package}
public_key=${9:?missing raw Ed25519 public key}
output=${10:?missing output}
base_profile=${ROG5_RECOVERY_BASE_PROFILE:-historical-v18}
case $base_profile in
	historical-v18)
		expected_base=852b02a2cbcb2dfd43598269ff1b2b10cb1542e90ab7a7aa32d1a26c7cc645fc
		;;
	reconstructed-v18r-v1)
		expected_base=da573d089cd617e088624b6d6bf711e193a4df5367843293e2e5ba543556e51d
		;;
	*)
		echo "FAIL unsupported recovery base profile: $base_profile" >&2
		exit 1
		;;
esac
epoch=1681862400
export LC_ALL=C
export TZ=UTC

fail() {
	echo "FAIL $*" >&2
	exit 1
}

check_hash() {
	actual=$(sha256sum "$1" | cut -d ' ' -f 1)
	[ "$actual" = "$2" ] ||
		fail "input hash mismatch: $(basename "$1")"
}

check_regular() {
	[ -f "$1" ] && [ -r "$1" ] && [ ! -L "$1" ] ||
		fail "unsafe or missing regular input: $(basename "$1")"
}

check_static_aarch64() {
	check_regular "$1"
	[ -x "$1" ] || fail "input is not executable: $(basename "$1")"
	readelf -h "$1" | grep -q 'Machine:.*AArch64' ||
		fail "input is not AArch64: $(basename "$1")"
	if readelf -l "$1" | grep -q 'INTERP'; then
		fail "input has a dynamic interpreter: $(basename "$1")"
	fi
}

for command in basename cpio cut dirname find grep gzip install mkdir \
	mktemp mv od readelf rm sed sha256sum sort stat tar touch tr; do
	command -v "$command" >/dev/null ||
		fail "missing initramfs build command: $command"
done
for input in "$base" "$init" "$kexec_apk" "$xz_apk" "$zstd_apk" \
	"$public_key"; do
	check_regular "$input"
done
[ -x "$init" ] || fail 'recovery init is not executable'
check_hash "$base" "$expected_base"
check_hash "$kexec_apk" \
	bd8b6951f862af1123972b521c355c655b7a2f40c2bf9cfe700edd590a101c94
check_hash "$xz_apk" \
	76dce86852903fef7adba0285d816e5ce9ffbe9fb3ca86bbb349b97afaba1f63
check_hash "$zstd_apk" \
	2bb5136c89f5b0bbe1554c8915a3b520d5aa63ae2a51d4d821eb81698db5a818
[ "$(stat -c %s "$public_key")" -eq 32 ] ||
	fail 'Ed25519 public key must contain exactly 32 raw bytes'
public_key_hex=$(od -An -tx1 -v "$public_key" | tr -d ' \n')
[ "$public_key_hex" != \
	0000000000000000000000000000000000000000000000000000000000000000 ] ||
	fail 'Ed25519 public key must not be all zero'
check_static_aarch64 "$control"
check_static_aarch64 "$fetcher"
check_static_aarch64 "$verifier"

if grep -Eq \
	'sh[[:space:]]+-i|setsid[[:space:]]+sh|authorized_keys|ssh-keygen|/usr/sbin/sshd|udhcpc|rog5\.recovery_(cidr|gateway)' \
	"$init"; then
	fail 'recovery init contains a legacy shell, credential, SSH, or network override'
fi
grep -Fq '/usr/libexec/rog5-recovery-control &' "$init" ||
	fail 'recovery init does not start the fixed responder'
grep -Fq '169.254.77.2/30' "$init" ||
	fail 'recovery init lacks the fixed device address'
for contract in \
	'bundle_root=/run/rog5-bundles' \
	"mkdir -p \"\$bundle_root\"" \
	"chown 0:0 \"\$bundle_root\"" \
	"chmod 0700 \"\$bundle_root\""
do
	grep -Fq "$contract" "$init" ||
		fail 'recovery init lacks the exact volatile bundle root'
done
grep -Fq 'mount -t pstore -o ro pstore /sys/fs/pstore' "$init" ||
	fail 'recovery init does not mount the postmortem store'
grep -Fq '/run/rog5-postmortem.status' "$init" ||
	fail 'recovery init does not publish bounded postmortem status'

stage=$(mktemp -d)
output_directory=$(dirname "$output")
output_name=$(basename "$output")
mkdir -p "$output_directory"
temporary=$(mktemp "$output_directory/.${output_name}.tmp.XXXXXX")
cleanup() {
	rm -rf -- "$stage"
	rm -f -- "$temporary"
}
trap cleanup EXIT HUP INT TERM

gzip -dc "$base" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
install -m 0755 "$init" "$stage/init"
install -D -m 0755 "$control" \
	"$stage/usr/libexec/rog5-recovery-control"
install -D -m 0755 "$fetcher" \
	"$stage/usr/libexec/rog5-bundle-fetch"
install -D -m 0755 "$verifier" \
	"$stage/usr/libexec/rog5-bundle-verify"
install -D -m 0600 "$public_key" \
	"$stage/etc/rog5/recovery-bundle-ed25519.pub"

rm -rf "$stage/etc/ssh" "$stage/root/.ssh" "$stage/run/sshd" \
	"$stage/usr/lib/ssh"
rm -f "$stage"/etc/ssh_host_* "$stage"/etc/machine-id \
	"$stage"/var/lib/dbus/machine-id \
	"$stage"/usr/share/udhcpc/default.script \
	"$stage"/sbin/getty "$stage"/usr/sbin/getty \
	"$stage"/usr/sbin/sshd "$stage"/usr/bin/scp \
	"$stage"/usr/bin/sftp "$stage"/usr/bin/ssh \
	"$stage"/usr/bin/ssh-add "$stage"/usr/bin/ssh-agent \
	"$stage"/usr/bin/ssh-keygen "$stage"/usr/bin/ssh-keyscan
find "$stage" \( -type f -o -type l \) \
	\( -name login -o -name passwd -o -name chpasswd -o \
		-name udhcpc -o -name udhcpc6 \) \
	! -path "$stage/etc/passwd" -exec rm -f -- {} +
find "$stage" \( -type f -o -type l \) -path '*/udhcpc/*' \
	-exec rm -f -- {} +
[ -f "$stage/etc/shadow" ] && [ ! -L "$stage/etc/shadow" ] ||
	fail 'unsafe or missing shadow database'
[ "$(grep -c '^root:' "$stage/etc/shadow")" -eq 1 ] ||
	fail 'shadow database lacks exactly one root account'
sed -i 's/^root:[^:]*/root:!/' "$stage/etc/shadow"
root_password=$(
	sed -n 's/^root:\([^:]*\):.*/\1/p' "$stage/etc/shadow"
)
[ "$root_password" = '!' ] || fail 'root account is not locked'

tar --warning=no-unknown-keyword -xf "$kexec_apk" -C "$stage" \
	usr/sbin/kexec
tar --warning=no-unknown-keyword -xf "$xz_apk" -C "$stage" \
	usr/lib/liblzma.so.5 usr/lib/liblzma.so.5.8.3
tar --warning=no-unknown-keyword -xf "$zstd_apk" -C "$stage" \
	usr/lib/libzstd.so.1 usr/lib/libzstd.so.1.5.7

readelf -h "$stage/usr/sbin/kexec" | grep -q 'Machine:.*AArch64' ||
	fail 'packaged kexec is not AArch64'
readelf -l "$stage/usr/sbin/kexec" |
	grep -q 'Requesting program interpreter: /lib/ld-musl-aarch64.so.1' ||
	fail 'packaged kexec has an unexpected interpreter'
for library in libc.musl-aarch64.so.1 liblzma.so.5 libz.so.1 libzstd.so.1; do
	readelf -d "$stage/usr/sbin/kexec" |
		grep -q "Shared library: \\[$library\\]" ||
		fail "packaged kexec lacks dependency $library"
done
for path in \
	lib/ld-musl-aarch64.so.1 \
	usr/lib/liblzma.so.5 \
	usr/lib/libz.so.1 \
	usr/lib/libzstd.so.1
do
	[ -e "$stage/$path" ] ||
		fail "initramfs lacks kexec runtime path $path"
done

[ -z "$(find "$stage" -type f \
	\( -name authorized_keys -o -name 'ssh_host_*' -o \
		-name '*private*.key' -o -name '*private*.pem' \) -print -quit)" ] ||
	fail 'credential-like file remains in recovery initramfs'
[ -z "$(find "$stage" -type f -perm /6000 -print -quit)" ] ||
	fail 'set-ID file remains in recovery initramfs'
if grep -rIl 'BEGIN .*PRIVATE KEY' "$stage" >/dev/null 2>&1; then
	fail 'private-key material remains in recovery initramfs'
fi

find "$stage" -exec touch -h -d "@$epoch" {} +
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$temporary"
gzip -t "$temporary"
mv -T -- "$temporary" "$output"
trap - EXIT HUP INT TERM
rm -rf -- "$stage"

sha256sum "$init" "$control" "$fetcher" "$verifier" "$public_key" "$output"
printf '%s\n' \
	"PASS deterministic fixed-control recovery initramfs; base_profile=$base_profile; public key only; no SSH or interactive ACM shell"
