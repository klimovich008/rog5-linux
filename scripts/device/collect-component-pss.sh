#!/bin/sh
set -u

root=${ROG5_METRICS_ROOT:-}
case $root in
	''|/*) ;;
	*)
		echo 'ERROR ROG5_METRICS_ROOT must be empty or absolute' >&2
		exit 2
		;;
esac

desktop_count=0
desktop_readable=0
desktop_pss=0
browser_count=0
browser_readable=0
browser_pss=0
remote_count=0
remote_readable=0
remote_pss=0
managed_count=0
managed_readable=0
managed_pss=0

for status in "$root"/proc/[0-9]*/status; do
	[ -r "$status" ] || continue
	name=$(awk '$1 == "Name:" { print $2; exit }' "$status" 2>/dev/null)
	case $name in
		kwin_wayland|plasmashell|kded6|kglobalacceld|kactivitymanage|\
		kscreen_backend|ksmserver|xdg-desktop-por)
			category=desktop
			desktop_count=$((desktop_count + 1))
			;;
		chromium|chrome|chrome_crashpad)
			category=browser
			browser_count=$((browser_count + 1))
			;;
		Xvnc|Xtigervnc|krdpserver|openbox|ttyd|websockify|x11vnc)
			category=remote
			remote_count=$((remote_count + 1))
			;;
		*) continue ;;
	esac
	managed_count=$((managed_count + 1))

	smaps=${status%/status}/smaps_rollup
	[ -r "$smaps" ] || continue
	pss=$(awk '$1 == "Pss:" { print $2; exit }' "$smaps" 2>/dev/null)
	case $pss in ''|*[!0-9]*) continue ;; esac
	managed_readable=$((managed_readable + 1))
	managed_pss=$((managed_pss + pss))
	case $category in
		desktop)
			desktop_readable=$((desktop_readable + 1))
			desktop_pss=$((desktop_pss + pss))
			;;
		browser)
			browser_readable=$((browser_readable + 1))
			browser_pss=$((browser_pss + pss))
			;;
		remote)
			remote_readable=$((remote_readable + 1))
			remote_pss=$((remote_pss + pss))
			;;
	esac
done

emit_category() {
	label=$1
	count=$2
	readable=$3
	pss=$4
	printf '%s_process_count=%s\n' "$label" "$count"
	printf '%s_pss_readable_count=%s\n' "$label" "$readable"
	if [ "$count" -eq "$readable" ]; then
		printf '%s_pss_kib=%s\n' "$label" "$pss"
	else
		printf '%s_pss_kib=unavailable\n' "$label"
	fi
}

emit_category desktop "$desktop_count" "$desktop_readable" "$desktop_pss"
emit_category browser "$browser_count" "$browser_readable" "$browser_pss"
emit_category remote "$remote_count" "$remote_readable" "$remote_pss"
emit_category managed "$managed_count" "$managed_readable" "$managed_pss"

# Process arguments, environments, descriptors, network identity, and
# credentials are intentionally outside this redacted evidence format.
