#!/bin/sh
set -eu

base=${1:?usage: build-persistent-slotb-recovery-initramfs.sh BASE INIT EXECUTOR|embedded-ram OUTPUT [SIGNED_BUNDLE]}
init=${2:?missing recovery init}
executor=${3:?missing local loader executor}
output=${4:?missing output}
embedded_bundle=${5:-}
[ "$#" -eq 4 ] || [ "$#" -eq 5 ] || exit 1
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
reboot_source=$repo/tools/reboot_bootloader/rog5-reboot-bootloader.c
selector_loader=$repo/initramfs/persistent-slotb-loader-init
trial_helper=$repo/$(cat "$repo/configs/persistent-trial-helper.path")
# A persistent boot_b rebuild keeps the helper release the installed wrapper
# carries (ROG5_TRIAL_HELPER=artifacts/persistent-trial-state-vN/...), so a
# fix to init or the loader does not also change the trial-state helper.
if [ -n "${ROG5_TRIAL_HELPER:-}" ]; then
	printf '%s\n' "$ROG5_TRIAL_HELPER" |
		grep -Eqx 'artifacts/persistent-trial-state-v[1-9][0-9]*/rog5-persistent-trial-state' || {
		echo 'FAIL ROG5_TRIAL_HELPER is not a retained trial-state helper' >&2
		exit 1
	}
	trial_helper=$repo/$ROG5_TRIAL_HELPER
fi
expected_base=d2f46588b46b615eae907ef98e2108fbcc06efc330ffa40136f6e89bdc39ddbc
# Another phone's wrapper: ROG5_RECOVERY_BASE_SHA256 pins its own recovery
# base (with its own trust key, BusyBox, kexec and verifier builds), and
# ROG5_DEVICE_PROFILE renders the selector loader with its device profile
# (the caller passes a rendered recovery init as INIT).
reference_base=1
if [ -n "${ROG5_RECOVERY_BASE_SHA256:-}" ] &&
	[ "$ROG5_RECOVERY_BASE_SHA256" != "$expected_base" ]; then
	printf '%s\n' "$ROG5_RECOVERY_BASE_SHA256" | grep -Eqx '[0-9a-f]{64}' || {
		echo 'FAIL ROG5_RECOVERY_BASE_SHA256 must be 64 hex digits' >&2
		exit 1
	}
	expected_base=$ROG5_RECOVERY_BASE_SHA256
	reference_base=0
fi
expected_trial_helper=$(cut -d ' ' -f 1 "$(dirname "$trial_helper")/SHA256SUMS")
epoch=1681862400

fail() { echo "FAIL $*" >&2; exit 1; }

for command in basename chmod clang cmp cpio cut dirname find grep gzip install \
	mkdir mktemp mv readelf rm sha256sum sort stat touch tr; do
	command -v "$command" >/dev/null || fail "missing local-loader build command: $command"
done
for input in "$base" "$init" "$selector_loader" "$trial_helper" \
	"$reboot_source"; do
	[ -f "$input" ] && [ -r "$input" ] && [ ! -L "$input" ] ||
		fail "unsafe local-loader input: $(basename "$input")"
done
[ -x "$init" ] || fail 'init must be executable'
if [ -n "$embedded_bundle" ]; then
	[ "$executor" = embedded-ram ] || fail 'embedded bundle requires generated RAM executor'
	[ -d "$embedded_bundle" ] && [ ! -L "$embedded_bundle" ] || fail 'unsafe embedded bundle'
	name=$(basename "$embedded_bundle")
	[ "${#name}" -le 64 ] && printf '%s\n' "$name" | grep -Eq '^[a-z0-9][a-z0-9._-]{0,63}$' || fail 'invalid embedded bundle name'
	case $name in *..*) fail 'invalid embedded bundle name' ;; esac
	[ "$(printf '%s' "$name" | tr -d '\n')" = "$name" ] || fail 'multiline embedded bundle name'
else
	[ "$executor" != embedded-ram ] && [ -f "$executor" ] && [ ! -L "$executor" ] &&
		[ -x "$executor" ] || fail 'executor must be an exact executable file'
fi
[ -x "$selector_loader" ] && [ -x "$trial_helper" ] ||
	fail 'selector loader and trial helper must be executable'
[ "$(sha256sum "$trial_helper" | cut -d ' ' -f 1)" = \
	"$expected_trial_helper" ] || fail 'persistent trial helper identity changed'
[ ! -e "$output" ] && [ ! -L "$output" ] || fail 'local-loader output already exists'
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] ||
	fail 'unexpected live-proven recovery archive'

stage=$(mktemp -d)
output_directory=$(dirname "$output")
mkdir -p "$output_directory"
temporary=$(mktemp "$output_directory/.loader-recovery.tmp.XXXXXX")
cleanup() {
	rm -rf -- "$stage"
	rm -f -- "$temporary" "$temporary.selector-loader"
}
trap cleanup EXIT HUP INT TERM
if [ -n "${ROG5_DEVICE_PROFILE:-}" ]; then
	python3 "$repo/scripts/host/rog5-device-profile" render \
		--profile "$ROG5_DEVICE_PROFILE" "$selector_loader" \
		"$temporary.selector-loader" || fail 'cannot render the selector loader'
	selector_loader=$temporary.selector-loader
fi

gzip -dc "$base" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
install -m 0755 "$init" "$stage/init"
if [ "$reference_base" = 1 ]; then
	[ "$(sha256sum "$stage/usr/libexec/rog5-bundle-verify" | cut -d ' ' -f 1)" = \
		c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb ] ||
		fail 'bundle verifier identity changed'
	[ "$(sha256sum "$stage/usr/sbin/kexec" | cut -d ' ' -f 1)" = \
		5e5d0a78b3f0bcf3921ff060f4dce5011cbac24b5e12fedeb8ca03ea5b40d015 ] ||
		fail 'kexec identity changed'
	[ "$(sha256sum "$stage/etc/rog5/recovery-bundle-ed25519.pub" | cut -d ' ' -f 1)" = \
		cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ] ||
		fail 'local bundle trust key changed'
else
	# The caller pinned this base by hash; its members are its own builds.
	for member in usr/libexec/rog5-bundle-verify usr/sbin/kexec etc/rog5/recovery-bundle-ed25519.pub; do
		[ -f "$stage/$member" ] && [ ! -L "$stage/$member" ] || fail "recovery base lacks $member"
	done
	[ "$(stat -c %s "$stage/etc/rog5/recovery-bundle-ed25519.pub")" = 32 ] ||
		fail 'recovery base trust key is not a raw 32-byte Ed25519 key'
	sha256sum "$stage/usr/libexec/rog5-bundle-verify" "$stage/usr/sbin/kexec" \
		"$stage/etc/rog5/recovery-bundle-ed25519.pub" | sed 's#  .*/#  #' >&2
fi

rm -f -- "$stage/usr/libexec/rog5-recovery-control" \
	"$stage/usr/libexec/rog5-bundle-fetch"
chmod 0644 "$stage/etc/rog5/recovery-mode"
printf '%s\n' persistent-slotb-loader-v1 >"$stage/etc/rog5/recovery-mode"
chmod 0444 "$stage/etc/rog5/recovery-mode"
if [ -n "$embedded_bundle" ]; then
	# Packaging is not admission. The unchanged sealed verifier authenticates
	# the signature and every payload again before the shared kexec tail.
	embedded_root=$stage/usr/share/rog5/ram-bundles
	[ ! -e "$embedded_root" ] && [ ! -L "$embedded_root" ] || fail 'embedded root already exists'
	mkdir -p "$embedded_root/$name"
	chmod 0700 "$embedded_root" "$embedded_root/$name"
	count=0
	for input in "$embedded_bundle"/* "$embedded_bundle"/.[!.]* "$embedded_bundle"/..?*; do
		[ -e "$input" ] || [ -L "$input" ] || continue
		file=$(basename "$input")
		case $file in Image|board.dtb|initramfs.cpio.gz|manifest|manifest.sig) ;; *) fail 'unexpected embedded file' ;; esac
		[ -f "$input" ] && [ ! -L "$input" ] && [ "$(stat -c %h "$input")" = 1 ] || fail 'unsafe embedded file'
		install -m 0600 "$input" "$embedded_root/$name/$file"
		cmp "$input" "$embedded_root/$name/$file"
		count=$((count + 1))
	done
	[ "$count" -eq 5 ] && [ "$(stat -c %s "$embedded_root/$name/manifest.sig")" = 64 ] || fail 'incomplete embedded bundle'
	manifest_hash=$(sha256sum "$embedded_root/$name/manifest" | cut -d ' ' -f 1)
	printf '#!/bin/sh\nset -eu\nexec /usr/libexec/rog5-selector-v2-loader existing-recovery-ram %s %s\n' \
		"$name" "$manifest_hash" >"$stage/usr/libexec/rog5-persistent-slotb-local-loader"
	chmod 0755 "$stage/usr/libexec/rog5-persistent-slotb-local-loader"
else
	install -m 0755 "$executor" "$stage/usr/libexec/rog5-persistent-slotb-local-loader"
fi
install -m 0755 "$selector_loader" "$stage/usr/libexec/rog5-selector-v2-loader"
install -m 0755 "$trial_helper" "$stage/usr/libexec/rog5-persistent-trial-state"

clang --target=aarch64-linux-gnu -fuse-ld=lld -nostdlib -static \
	-fno-builtin -Wall -Wextra -Werror -fno-pic -fno-pie \
	-fno-stack-protector -Wl,-e,_start -Wl,--build-id=none \
	-Wl,-z,noexecstack -o "$stage/usr/libexec/rog5-reboot-bootloader" \
	"$reboot_source"
readelf -h "$stage/usr/libexec/rog5-reboot-bootloader" |
	grep -q 'Machine:.*AArch64' || fail 'reboot helper is not AArch64'

cmp "$stage/init" "$init"
if [ -z "$embedded_bundle" ]; then
	cmp "$stage/usr/libexec/rog5-persistent-slotb-local-loader" "$executor"
fi
cmp "$stage/usr/libexec/rog5-selector-v2-loader" "$selector_loader"
cmp "$stage/usr/libexec/rog5-persistent-trial-state" "$trial_helper"
[ "$(cat "$stage/etc/rog5/recovery-mode")" = persistent-slotb-loader-v1 ]
[ ! -e "$stage/usr/libexec/rog5-recovery-control" ]
[ ! -e "$stage/usr/libexec/rog5-bundle-fetch" ]
[ -x "$stage/usr/libexec/rog5-bundle-verify" ]
[ -x "$stage/usr/sbin/kexec" ]

find "$stage" -exec touch -h -d "@$epoch" {} +
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$temporary"
gzip -t "$temporary"
mv -T -- "$temporary" "$output"
trap - EXIT HUP INT TERM
rm -rf -- "$stage"

sha256sum "$init" "$output"
echo 'PASS deterministic canonical-recovery local signed-bundle loader initramfs'
