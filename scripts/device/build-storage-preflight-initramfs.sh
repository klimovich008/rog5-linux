#!/bin/sh
set -eu

base=${1:?usage: build-storage-preflight-initramfs.sh BASE INIT SGDISK_APK POPT_APK LIBGCC_APK LIBSTDCXX_APK MUSL_APK LIBUUID_APK OUTPUT}
init=${2:?missing recovery init}
sgdisk_apk=${3:?missing sgdisk package}
popt_apk=${4:?missing popt package}
libgcc_apk=${5:?missing libgcc package}
libstdcpp_apk=${6:?missing libstdc++ package}
musl_apk=${7:?missing musl package}
libuuid_apk=${8:?missing libuuid package}
output=${9:?missing output}
epoch=1681862400
export LC_ALL=C
export TZ=UTC

fail() {
	echo "FAIL $*" >&2
	exit 1
}

check_hash() {
	actual=$(sha256sum "$1" | cut -d ' ' -f 1)
	[ "$actual" = "$2" ] || fail "input hash mismatch: $(basename "$1")"
}

for command in basename chmod cpio cut dirname find grep gzip install mkdir \
	mktemp mv readelf rm sed sha256sum sort stat tar touch; do
	command -v "$command" >/dev/null ||
		fail "missing storage-preflight build command: $command"
done
for input in "$base" "$init" "$sgdisk_apk" "$popt_apk" "$libgcc_apk" \
	"$libstdcpp_apk" "$musl_apk" "$libuuid_apk"; do
	[ -f "$input" ] && [ -r "$input" ] && [ ! -L "$input" ] ||
		fail "unsafe storage-preflight input: $(basename "$input")"
done
[ -x "$init" ] || fail 'storage-preflight init is not executable'
[ ! -e "$output" ] && [ ! -L "$output" ] ||
	fail 'storage-preflight output already exists'

check_hash "$base" da573d089cd617e088624b6d6bf711e193a4df5367843293e2e5ba543556e51d
check_hash "$sgdisk_apk" b37f3d8ce629ee38132e308ef0c7e6e6d661e308c02975718a69ceb94136dcb5
check_hash "$popt_apk" 5eb2037c453c870f31a1db4f1235f8ac2a27f8d401421cb5662f2ff6f1bea94b
check_hash "$libgcc_apk" 369aaa6e9d099a737bad6dd3e6c2fe7bb1547ca26d22b94ee0411228f709b403
check_hash "$libstdcpp_apk" 2302e766d4e4926038ec166ecb85837ee884576115236ddb565e3a5fca4a11d7
check_hash "$musl_apk" 5e9674b7f41152fe2119093b5cb4c13eaaadb19c2d5422b2d7267913e663ee6e
check_hash "$libuuid_apk" d2f69552b05184ba205dbc8aa0e79f8a080fcf746ec5e5e25eb89d66fbbe6db6

for contract in \
	'storage-preflight-v2)' \
	'run_storage_preflight() {' \
	'serve_storage_preflight_report() {' \
	'stty -F /dev/ttyGS0 raw -echo -echonl -opost clocal cread' \
	'exec 3>/dev/ttyGS0' \
	'cat "$report" >&3' \
	'/usr/bin/sgdisk -v "$disk"' \
	'/sbin/e2fsck -fn "$userdata"' \
	'/usr/sbin/resize2fs -P "$userdata"' \
	'ROG5_STORAGE_PREFLIGHT_V2 status=RUNNING' \
	'ROG5_STORAGE_PREFLIGHT_V2 status=FAIL' \
	'ROG5_STORAGE_PREFLIGHT_V2 status=PASS'
do
	grep -Fq "$contract" "$init" ||
		fail "recovery init lacks storage-preflight contract: $contract"
done
if grep -Eq 'sgdisk[[:space:]].*--(delete|new|zap)|blockdev[[:space:]]+--setrw|resize2fs[[:space:]]+"\$userdata"([[:space:]]|$)|mkfs\.ext4[[:space:]]+"\$' "$init"; then
	fail 'storage-preflight init contains a storage mutation command'
fi

stage=$(mktemp -d)
output_directory=$(dirname "$output")
mkdir -p "$output_directory"
output_name=$(basename "$output")
temporary=$(mktemp "$output_directory/.${output_name}.tmp.XXXXXX")
cleanup() {
	rm -rf -- "$stage"
	rm -f -- "$temporary"
}
trap cleanup EXIT HUP INT TERM

gzip -dc "$base" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
install -m 0755 "$init" "$stage/init"

rm -rf "$stage/etc/ssh" "$stage/root/.ssh" "$stage/run/sshd" \
	"$stage/usr/lib/ssh"
rm -f "$stage"/etc/ssh_host_* "$stage"/etc/machine-id \
	"$stage"/var/lib/dbus/machine-id \
	"$stage"/usr/share/udhcpc/default.script \
	"$stage"/sbin/getty "$stage"/usr/sbin/getty \
	"$stage"/usr/sbin/sshd "$stage"/usr/bin/scp \
	"$stage"/usr/bin/sftp "$stage"/usr/bin/ssh \
	"$stage"/usr/bin/ssh-add "$stage"/usr/bin/ssh-agent \
	"$stage"/usr/bin/ssh-keygen "$stage"/usr/bin/ssh-keyscan \
	"$stage"/usr/libexec/rog5-recovery-control \
	"$stage"/usr/libexec/rog5-bundle-fetch \
	"$stage"/usr/libexec/rog5-bundle-verify \
	"$stage"/usr/sbin/kexec \
	"$stage"/etc/rog5/recovery-bundle-ed25519.pub
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
mkdir -p "$stage/etc/rog5"
printf '%s\n' storage-preflight-v2 >"$stage/etc/rog5/recovery-mode"
chmod 0444 "$stage/etc/rog5/recovery-mode"

tar --warning=no-unknown-keyword -xf "$musl_apk" -C "$stage" \
	lib/ld-musl-aarch64.so.1 lib/libc.musl-aarch64.so.1
tar --warning=no-unknown-keyword -xf "$sgdisk_apk" -C "$stage" usr/bin/sgdisk
tar --warning=no-unknown-keyword -xf "$popt_apk" -C "$stage" \
	usr/lib/libpopt.so.0 usr/lib/libpopt.so.0.0.2
tar --warning=no-unknown-keyword -xf "$libgcc_apk" -C "$stage" \
	usr/lib/libgcc_s.so.1
tar --warning=no-unknown-keyword -xf "$libstdcpp_apk" -C "$stage" \
	usr/lib/libstdc++.so.6 usr/lib/libstdc++.so.6.0.34
tar --warning=no-unknown-keyword -xf "$libuuid_apk" -C "$stage" \
	usr/lib/libuuid.so.1 usr/lib/libuuid.so.1.3.0

readelf -h "$stage/usr/bin/sgdisk" | grep -q 'Machine:.*AArch64' ||
	fail 'packaged sgdisk is not AArch64'
readelf -l "$stage/usr/bin/sgdisk" |
	grep -q 'Requesting program interpreter: /lib/ld-musl-aarch64.so.1' ||
	fail 'packaged sgdisk has an unexpected interpreter'
for library in libuuid.so.1 libpopt.so.0 libstdc++.so.6 libgcc_s.so.1 \
	libc.musl-aarch64.so.1; do
	readelf -d "$stage/usr/bin/sgdisk" |
		grep -q "Shared library: \[$library\]" ||
		fail "packaged sgdisk lacks dependency $library"
done
for path in lib/ld-musl-aarch64.so.1 usr/lib/libuuid.so.1 \
	usr/lib/libpopt.so.0 usr/lib/libstdc++.so.6 usr/lib/libgcc_s.so.1 \
	sbin/e2fsck usr/sbin/resize2fs usr/sbin/dumpe2fs sbin/mkfs.ext4; do
	[ -e "$stage/$path" ] || fail "initramfs lacks storage tool path $path"
done
[ -L "$stage/usr/sbin/partprobe" ] &&
	[ "$(readlink "$stage/usr/sbin/partprobe")" = /bin/busybox ] ||
	fail 'initramfs lacks the fixed BusyBox partprobe applet link'
[ -L "$stage/bin/stty" ] &&
	[ "$(readlink "$stage/bin/stty")" = /bin/busybox ] ||
	fail 'initramfs lacks the fixed BusyBox stty applet link'

[ -z "$(find "$stage" -type f \
	\( -name authorized_keys -o -name 'ssh_host_*' -o \
		-name '*private*.key' -o -name '*private*.pem' \) -print -quit)" ] ||
	fail 'credential-like file remains in storage-preflight initramfs'
[ -z "$(find "$stage" -type f -perm /6000 -print -quit)" ] ||
	fail 'set-ID file remains in storage-preflight initramfs'
if grep -rIl 'BEGIN .*PRIVATE KEY' "$stage" >/dev/null 2>&1; then
	fail 'private-key material remains in storage-preflight initramfs'
fi

find "$stage" -exec touch -h -d "@$epoch" {} +
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$temporary"
gzip -t "$temporary"
mv -T -- "$temporary" "$output"
trap - EXIT HUP INT TERM
rm -rf -- "$stage"

sha256sum "$init" "$output"
echo 'PASS deterministic read-only storage-preflight initramfs; no shell, SSH, trust key, kexec, or storage mutation path'
