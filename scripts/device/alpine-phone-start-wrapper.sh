#!/bin/sh
set -u

ROG5_PHONE_START_BASE=${ROG5_PHONE_START_BASE:-/usr/local/libexec/rog5-phone-start-base}
ROG5_SCREEN_BUTTON_START=${ROG5_SCREEN_BUTTON_START:-/usr/local/sbin/rog5-screen-button-openrc-start.sh}
ROG5_SCREEN_BUTTON_LOG=${ROG5_SCREEN_BUTTON_LOG:-/var/log/rog5-screen-button.log}
phone_start_base=$ROG5_PHONE_START_BASE
screen_button_start=$ROG5_SCREEN_BUTTON_START
screen_button_log=$ROG5_SCREEN_BUTTON_LOG

if [ -x "$screen_button_start" ]; then
	"$screen_button_start" >>"$screen_button_log" 2>&1 || true
fi

[ -x "$phone_start_base" ] || {
	echo "ERROR base phone launcher is not executable: $phone_start_base" >&2
	exit 1
}
exec "$phone_start_base" "$@"
