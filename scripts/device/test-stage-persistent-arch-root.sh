#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
stage_root=$repo/scripts/device/stage-persistent-arch-root.sh
root_tool=$repo/scripts/device/persistent-root-tool.py
inspector=$repo/scripts/device/inspect-persistent-layout.sh

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in awk bsdtar getfattr gzip grep mktemp python3 \
	setfattr sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing test command: $command"
done
for path in "$stage_root" "$root_tool" "$inspector"; do
	[ -x "$path" ] || fail "missing executable persistent staging tool: $path"
done

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

mkdir -p "$work/bin"
cat >"$work/bin/df" <<'EOF'
#!/bin/sh
set -eu
printf '%s\n' 'Filesystem 1024-blocks Used Available Capacity Mounted on'
printf '/dev/sda23 250000000 50000000 200000000 20%% %s\n' "${1:?}"
EOF
chmod 0755 "$work/bin/df"
PATH=$work/bin:$PATH
export PATH

make_layout() {
	base=$1
	sys=$base/sys/class/block
	mounts=$base/proc/mounts
	cmdline=$base/proc/cmdline
	root=$base/root
	mkdir -p "$sys/sda" "$sys/sde" "$base/proc" "$root"
	printf '%s\n' 494927872 >"$sys/sda/size"
	printf '%s\n' 4718592 >"$sys/sde/size"
	printf '%s\n' marker >"$root/.rog5-linux-root"
	printf '/dev/sda23 %s ext4 rw,relatime 0 0\n' "$root" >"$mounts"
	printf '%s\n' 'console=tty0 androidboot.slot_suffix=_b quiet' >"$cmdline"

	make_partition "$sys" sda19 19 4108352 14680064 super
	make_partition "$sys" sda22 22 18788672 32768 metadata
	make_partition "$sys" sda23 23 18821440 476106392 userdata
	make_partition "$sys" sde11 11 688176 196608 boot_a
	make_partition "$sys" sde14 14 885200 128 vbmeta_a
	make_partition "$sys" sde23 23 1482168 196608 vendor_boot_a
	make_partition "$sys" sde35 35 2367416 196608 boot_b
	make_partition "$sys" sde38 38 2564440 128 vbmeta_b
	make_partition "$sys" sde47 47 3161408 196608 vendor_boot_b
}

make_partition() {
	sys=$1 name=$2 number=$3 start=$4 size=$5 label=$6
	path=$sys/$name
	mkdir -p "$path"
	printf '%s\n' "$number" >"$path/partition"
	printf '%s\n' "$start" >"$path/start"
	printf '%s\n' "$size" >"$path/size"
	printf 'DEVNAME=%s\nPARTNAME=%s\n' "$name" "$label" >"$path/uevent"
}

expect_fail() {
	label=$1
	shift
	if "$@" >"$work/$label.out" 2>&1; then
		fail "accepted persistent staging mutation: $label"
	fi
}

source=$work/source
mkdir -p "$source/etc/pacman.d/gnupg" "$source/etc/rog5" \
	"$source/usr/lib/rog5" "$source/var/empty"
printf '%s\n' fixture >"$source/etc/rog5/build"
printf '%s\n' payload >"$source/usr/lib/rog5/payload"
chmod 0640 "$source/usr/lib/rog5/payload"
setfattr -n user.rog5 -v preserved "$source/usr/lib/rog5/payload"
ln -s ../../etc/rog5/build "$source/usr/lib/rog5/build-link"
safe_tar=$work/safe.tar
safe_archive=$work/safe.tar.gz
(
	cd "$source"
	bsdtar --acls --xattrs --fflags -cpf "$safe_tar" .
)
gzip -n -c "$safe_tar" >"$safe_archive"
safe_size=$(stat -c %s "$safe_archive")
safe_hash=$(sha256sum "$safe_archive" | awk '{ print $1 }')

"$root_tool" archive "$safe_archive" |
	grep -Eq '^archive_entries=[1-9][0-9]*$'

python3 - "$work" <<'PY'
import io
import pathlib
import tarfile
import sys

root = pathlib.Path(sys.argv[1])

with tarfile.open(root / "unsafe.tar.gz", "w:gz") as archive:
    payload = b"escape\n"
    member = tarfile.TarInfo("../escape")
    member.size = len(payload)
    archive.addfile(member, io.BytesIO(payload))

with tarfile.open(root / "device.tar.gz", "w:gz") as archive:
    member = tarfile.TarInfo("./dev/unsafe")
    member.type = tarfile.CHRTYPE
    member.devmajor = 1
    member.devminor = 3
    archive.addfile(member)

with tarfile.open(root / "credential.tar.gz", "w:gz") as archive:
    payload = b"not-a-real-key\n"
    member = tarfile.TarInfo("./etc/ssh/ssh_host_ed25519_key")
    member.size = len(payload)
    archive.addfile(member, io.BytesIO(payload))

with tarfile.open(root / "pacman-key.tar.gz", "w:gz") as archive:
    payload = b"not-a-real-key\n"
    member = tarfile.TarInfo(
        "./etc/pacman.d/gnupg/private-keys-v1.d/fixture.key"
    )
    member.size = len(payload)
    archive.addfile(member, io.BytesIO(payload))

with tarfile.open(root / "pacman-key-dir.tar.gz", "w:gz") as archive:
    member = tarfile.TarInfo("./etc/pacman.d/gnupg/private-keys-v1.d")
    member.type = tarfile.DIRTYPE
    archive.addfile(member)

with tarfile.open(root / "pacman-revocation.tar.gz", "w:gz") as archive:
    payload = b"not-a-real-revocation\n"
    member = tarfile.TarInfo(
        "./etc/pacman.d/gnupg/openpgp-revocs.d/fixture.rev"
    )
    member.size = len(payload)
    archive.addfile(member, io.BytesIO(payload))

with tarfile.open(root / "pacman-trustdb.tar.gz", "w:gz") as archive:
    payload = b"not-a-real-trustdb\n"
    member = tarfile.TarInfo("./etc/pacman.d/gnupg/trustdb.gpg")
    member.size = len(payload)
    archive.addfile(member, io.BytesIO(payload))

with tarfile.open(root / "reserved-seal.tar.gz", "w:gz") as archive:
    payload = b"forged\n"
    member = tarfile.TarInfo("./.rog5-persistent-seal")
    member.size = len(payload)
    archive.addfile(member, io.BytesIO(payload))
PY

expect_fail unsafe-path "$root_tool" archive "$work/unsafe.tar.gz"
expect_fail device-node "$root_tool" archive "$work/device.tar.gz"
expect_fail embedded-credential "$root_tool" archive "$work/credential.tar.gz"
expect_fail embedded-pacman-key \
	"$root_tool" archive "$work/pacman-key.tar.gz"
expect_fail embedded-pacman-key-directory \
	"$root_tool" archive "$work/pacman-key-dir.tar.gz"
expect_fail embedded-pacman-revocation \
	"$root_tool" archive "$work/pacman-revocation.tar.gz"
expect_fail embedded-pacman-trustdb \
	"$root_tool" archive "$work/pacman-trustdb.tar.gz"
expect_fail reserved-seal "$root_tool" archive "$work/reserved-seal.tar.gz"

layout=$work/layout
make_layout "$layout"
sys=$layout/sys/class/block
mounts=$layout/proc/mounts
cmdline=$layout/proc/cmdline
root=$layout/root

run_stage() {
	"$stage_root" --fixture "$sys" "$mounts" "$cmdline" "$root" \
		"$safe_size" "$safe_hash" "$safe_archive"
}

expect_fail unarmed run_stage
[ ! -e "$root/rog5" ] ||
	fail 'unarmed staging changed the fixture root'

expect_fail wrong-hash env ALLOW_ROG5_PERSISTENT_STAGE=1 \
	"$stage_root" --fixture "$sys" "$mounts" "$cmdline" "$root" \
	"$safe_size" \
	0000000000000000000000000000000000000000000000000000000000000000 \
	"$safe_archive"
[ ! -e "$root/rog5" ] ||
	fail 'identity rejection changed the fixture root'

ALLOW_ROG5_PERSISTENT_STAGE=1 run_stage >"$work/stage.out"
grep -Eq \
	'^PASS persistent Arch root staged generation=arch-a entries=[1-9][0-9]* tree_sha256=[0-9a-f]{64} publication=atomic-unbooted$' \
	"$work/stage.out"

final=$root/rog5/roots/arch-a
partial=$root/rog5/roots/arch-a.partial
seal=$final/.rog5-persistent-seal
[ -d "$final" ] && [ ! -e "$partial" ] ||
	fail 'successful staging did not publish only the final root'
[ "$(cat "$final/usr/lib/rog5/payload")" = payload ]
[ "$(stat -c %a "$final/usr/lib/rog5/payload")" = 640 ]
[ "$(getfattr --only-values -n user.rog5 \
	"$final/usr/lib/rog5/payload" 2>/dev/null)" = preserved ]
[ "$(readlink "$final/usr/lib/rog5/build-link")" = ../../etc/rog5/build ]
[ -f "$seal" ] && [ ! -L "$seal" ] && [ "$(stat -c %a "$seal")" = 444 ]
grep -Fxq 'seal_format=rog5-persistent-root-v1' "$seal"
grep -Fxq 'generation=arch-a' "$seal"
grep -Fxq "source_archive_size=$safe_size" "$seal"
grep -Fxq "source_archive_sha256=$safe_hash" "$seal"
grep -Fxq 'promotion_state=UNBOOTED' "$seal"
"$root_tool" verify "$final" "$seal" >/dev/null
chmod 0644 "$seal"
expect_fail seal-mode "$root_tool" verify "$final" "$seal"
chmod 0444 "$seal"
"$root_tool" verify "$final" "$seal" >/dev/null
[ ! -e "$root/rog5/state/good" ] && [ ! -e "$root/rog5/state/next" ] ||
	fail 'staging selected or promoted an unbooted root'

seal_hash=$(sha256sum "$seal" | awk '{ print $1 }')
expect_fail existing-final env ALLOW_ROG5_PERSISTENT_STAGE=1 \
	"$stage_root" --fixture "$sys" "$mounts" "$cmdline" "$root" \
	"$safe_size" "$safe_hash" "$safe_archive"
[ "$(sha256sum "$seal" | awk '{ print $1 }')" = "$seal_hash" ] ||
	fail 'existing-root refusal changed the published seal'

printf '%s\n' mutation >>"$final/usr/lib/rog5/payload"
expect_fail tree-mutation "$root_tool" verify "$final" "$seal"

interrupted_layout=$work/interrupted
make_layout "$interrupted_layout"
interrupted_sys=$interrupted_layout/sys/class/block
interrupted_mounts=$interrupted_layout/proc/mounts
interrupted_cmdline=$interrupted_layout/proc/cmdline
interrupted_root=$interrupted_layout/root

expect_fail interrupted env \
	ALLOW_ROG5_PERSISTENT_STAGE=1 \
	ROG5_PERSISTENT_TEST_INTERRUPT=after-extract \
	"$stage_root" --fixture \
	"$interrupted_sys" "$interrupted_mounts" "$interrupted_cmdline" \
	"$interrupted_root" "$safe_size" "$safe_hash" "$safe_archive"
[ -d "$interrupted_root/rog5/roots/arch-a.partial" ] &&
	[ ! -e "$interrupted_root/rog5/roots/arch-a" ] ||
	fail 'interrupted staging exposed a final root'
expect_fail stale-partial env ALLOW_ROG5_PERSISTENT_STAGE=1 \
	"$stage_root" --fixture \
	"$interrupted_sys" "$interrupted_mounts" "$interrupted_cmdline" \
	"$interrupted_root" "$safe_size" "$safe_hash" "$safe_archive"

if grep -Eq \
	'ssh-keygen|wg[[:space:]]+genkey|openssl[[:space:]].*(genpkey|genrsa)|/dev/(sda|sdb|sdc|sdd|sde|sdf)' \
	"$stage_root" "$root_tool"
then
	fail 'persistent staging tool generates credentials or names block devices'
fi

echo 'PASS persistent Arch staging is identity-pinned, path-safe, metadata-preserving, credential-clean, interruption-safe, sealed, and atomic'
