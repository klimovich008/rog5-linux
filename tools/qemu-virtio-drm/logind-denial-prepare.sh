#!/usr/bin/bash
# Sourced only by the isolated VM PID1 fixture; changes guest RAM only.
stage_fuse_helper() {
    local source=$1 target=$2 resolved_source resolved_target
    [[ -f $source && -s $source && -r $source && -x $source && ! -L $source ]] || {
        echo 'FAIL regular executable FUSE helper source unavailable' >&2; return 1;
    }
    [[ -L $target ]] || {
        echo 'FAIL unexpected FUSE helper staging target' >&2; return 1;
    }
    # cp -as preserves /./ in symlink text. Require the same canonical source
    # path, not identical spelling or merely equal bytes/a shared inode.
    resolved_source=$(readlink -e -- "$source") || return $?
    resolved_target=$(readlink -e -- "$target") || return $?
    [[ $resolved_target == "$resolved_source" ]] || {
        echo 'FAIL unexpected FUSE helper staging target' >&2; return 1;
    }
    rm -- "$target" || return $?
    cp -- "$source" "$target" || return $?
    chown 0:0 "$target" || return $?
    chmod 4755 "$target" || return $?
    cmp -s -- "$source" "$target" || return $?
}
[[ $$ == 1 && $EUID == 0 && -d /sys/bus/virtio/devices ]]
read -r expected < /run/session-sha256
[[ $expected =~ ^[0-9a-f]{64}$ ]]
[[ $(sha256sum /run/payload/session.tar.gz) == "$expected "* ]]
mkdir /run/session /run/original-bin /run/session-bin
# The host verifies the full regular-file inventory before exposing the archive.
tar -xzf /run/payload/session.tar.gz -C /run/session
mount --bind /usr/bin /run/original-bin
cp -as /run/original-bin/. /run/session-bin/
for name in denial-mobile-session denial-session deniald denialctl; do
    [[ ! -e /run/session-bin/$name && ! -L /run/session-bin/$name ]]
    ln -s /run/session/usr/bin/$name /run/session-bin/$name
done
# The mobile entry intentionally rejects a symlinked PAM helper.
rm /run/session-bin/unix_chkpwd
cp /usr/bin/unix_chkpwd /run/session-bin/unix_chkpwd
chown 0:0 /run/session-bin/unix_chkpwd
chmod 6755 /run/session-bin/unix_chkpwd
# Preserve the authenticated fuse3 package's root:root 04755 helper metadata.
# The read-only mapped runtime keeps a non-setuid copy; only this RAM copy changes.
stage_fuse_helper /run/original-bin/fusermount3 /run/session-bin/fusermount3
mount --bind /run/session-bin /usr/bin
mkdir -p /etc/denial /etc/systemd/user
cp /run/session/usr/lib/systemd/user/denial-session.target /etc/systemd/user/
cat > /etc/denial/session.conf <<'CONF'
# Same GPU: reuse the DRM descriptor obtained through logind for rendering.
DENIAL_DRM_DEVICE=/dev/dri/card0
DENIAL_RENDER_DEVICE=/dev/dri/card0
DENIAL_OUTPUT_CONFIG=/run/mobile-home/outputs.conf
DENIAL_FLUTTER_BUNDLE=/run/session/usr/lib/denial/flutter
DENIAL_RUST_LOG=deniald=info,smithay=info
CONF
chmod 755 /etc/denial
chmod 644 /etc/denial/session.conf
: > /run/mobile-home/outputs.conf
chown 1000:1000 /run/mobile-home/outputs.conf
chmod 600 /run/mobile-home/outputs.conf
# Package extraction did not execute GTK's cache hooks; derive caches in RAM.
mkdir -p /run/gtk-runtime/schemas /run/gtk-runtime/mime/packages
timeout -k 1 10 glib-compile-schemas --strict --targetdir=/run/gtk-runtime/schemas /usr/share/glib-2.0/schemas
cp /usr/share/mime/packages/*.xml /run/gtk-runtime/mime/packages/
XDG_DATA_DIRS=/run/gtk-runtime:/usr/local/share:/usr/share timeout -k 1 10 update-mime-database /run/gtk-runtime/mime
[[ -s /run/gtk-runtime/schemas/gschemas.compiled && -s /run/gtk-runtime/mime/mime.cache ]]
echo 'PASS session payload staged in guest RAM; original runtime unchanged'
