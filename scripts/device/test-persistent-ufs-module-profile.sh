#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-persistent-ufs-module-profile.sh
builder=$repo/scripts/device/build-persistent-root-initramfs.sh
read_only_archive=${READ_ONLY_ARCHIVE:-$repo/artifacts/persistent-native-root-v4/initramfs.cpio.gz}
local_write_archive=${LOCAL_WRITE_ARCHIVE:-$repo/artifacts/local-image-direct-v49/initramfs.cpio.gz}
release=7.1.4-g359318de534f

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in mktemp; do
	command -v "$command" >/dev/null ||
		fail "missing UFS profile test command: $command"
done
for path in "$verifier" "$builder"; do
	[ -x "$path" ] || fail "missing executable UFS profile source: $path"
done

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

exercise_profiles() {
	read_only_modules=$1
	local_write_modules=$2
	"$verifier" "$read_only_modules" "$release" read-only >/dev/null
	"$verifier" "$local_write_modules" "$release" local-write >/dev/null

	if "$verifier" "$read_only_modules" "$release" local-write \
		>"$work/out" 2>"$work/err"; then
		fail 'local-write profile accepted the stale low-speed UFS core'
	fi
	grep -Fq 'local-write UFS core lacks the exact high-speed implementation' \
		"$work/err" || fail 'stale local-write profile returned the wrong reason'

	if "$verifier" "$local_write_modules" "$release" read-only \
		>"$work/out" 2>"$work/err"; then
		fail 'read-only profile accepted the writable high-speed UFS core'
	fi
	grep -Fq 'read-only UFS core is not the exact discovery implementation' \
		"$work/err" || fail 'writable read-only profile returned the wrong reason'
}

mkdir "$work/shims" "$work/synthetic-read-only" "$work/synthetic-local-write"
for root in "$work/synthetic-read-only" "$work/synthetic-local-write"; do
	for module in phy-qcom-qmp-ufs.ko ufs-qcom.ko ufshcd-core.ko \
		ufshcd-pltfrm.ko; do
		: >"$root/$module"
	done
done
printf '%s\n' \
	'ROG5 UFS discovery: optional device writes and high-speed gear switch disabled' \
	>"$work/synthetic-read-only/ufshcd-core.ko"
printf '%s\n' \
	'ROG5 UFS bounded data-write high-speed gear switch enabled' \
	>"$work/synthetic-local-write/ufshcd-core.ko"

cat >"$work/shims/modinfo" <<'EOF'
#!/bin/sh
set -eu
[ "$1" = -F ] && [ "$#" -eq 3 ]
field=$2
module=${3##*/}
case $module in
	phy-qcom-qmp-ufs.ko) name=phy_qcom_qmp_ufs; depends= ;;
	ufshcd-core.ko) name=ufshcd_core; depends= ;;
	ufshcd-pltfrm.ko) name=ufshcd_pltfrm; depends=ufshcd-core ;;
	ufs-qcom.ko) name=ufs_qcom; depends=ufshcd-pltfrm,ufshcd-core ;;
	*) exit 1 ;;
esac
case $field in
	name) printf '%s\n' "$name" ;;
	depends) printf '%s\n' "$depends" ;;
	vermagic) printf '%s SMP preempt mod_unload aarch64\n' 7.1.4-g359318de534f ;;
	*) exit 1 ;;
esac
EOF
cat >"$work/shims/readelf" <<'EOF'
#!/bin/sh
set -eu
case $1 in
	-h)
		printf '%s\n' '  Type: REL (Relocatable file)' '  Machine: AArch64'
		;;
	-SW)
		printf '%s\n' \
			'  [68] .gnu.linkonce.this_module PROGBITS 0000000000000000 02dbc0 000500 00 WA 0 0 64' \
			'  [77] .BTF PROGBITS 0000000000000000 27c577 00f492 00 0 0 1'
		;;
	*) exit 1 ;;
esac
EOF
cat >"$work/shims/strings" <<'EOF'
#!/bin/sh
set -eu
[ "$#" -eq 1 ]
cat "$1"
EOF
chmod 0755 "$work/shims/modinfo" "$work/shims/readelf" "$work/shims/strings"
(
	PATH=$work/shims:$PATH
	export PATH
	exercise_profiles "$work/synthetic-read-only" "$work/synthetic-local-write"
)

for path in "$read_only_archive" "$local_write_archive"; do
	if [ -e "$path" ] || [ -L "$path" ]; then
		[ -f "$path" ] && [ ! -L "$path" ] ||
			fail "unsafe retained UFS profile fixture: $path"
	fi
done
if [ -f "$read_only_archive" ] && [ -f "$local_write_archive" ]; then
	for command in cpio gzip; do
		command -v "$command" >/dev/null ||
			fail "missing retained UFS integration command: $command"
	done
	mkdir "$work/read-only" "$work/local-write"
	gzip -dc "$read_only_archive" |
		(cd "$work/read-only" && cpio -idm --quiet --no-absolute-filenames)
	gzip -dc "$local_write_archive" |
		(cd "$work/local-write" && cpio -idm --quiet --no-absolute-filenames)
	exercise_profiles "$work/read-only/rog5-ufs-modules" \
		"$work/local-write/rog5-ufs-modules"
else
	echo 'SKIP retained UFS binary profile fixtures are absent' >&2
fi

grep -Fq 'verify-persistent-ufs-module-profile.sh' "$builder" ||
	fail 'persistent initramfs builder does not invoke the UFS profile verifier'
grep -Fq 'ufs_module_profile=${PERSISTENT_UFS_MODULE_PROFILE:-$storage_mode}' \
	"$builder" || fail 'persistent builder does not separate storage and module profiles'
grep -Fq '"$ufs_module_profile"' "$builder" ||
	fail 'persistent initramfs builder omits the exact UFS module profile'
grep -Fq 'PERSISTENT_UFS_MODULE_PROFILE must be read-only or local-write' \
	"$builder" || fail 'persistent builder does not fail closed on module profile'

echo 'PASS persistent initramfs rejects cross-profile UFS module composition'
