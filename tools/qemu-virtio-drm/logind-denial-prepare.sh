#!/usr/bin/bash
# Sourced only by the isolated VM PID1 fixture; changes guest RAM only.
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
