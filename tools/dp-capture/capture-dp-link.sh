#!/bin/sh
# Read-only capture of what a PC (e.g. the Steam Deck, amdgpu) negotiated with a
# DP/USB-C display chain: DRM state, amdgpu link settings and the sink's DPCD
# (including an HDMI protocol converter's config registers), for comparison with
# the phone. Run as root while the display shows a picture:
#   sudo sh capture-dp-link.sh [connector, default DP-1] > capture.txt
# Only reads: debugfs files and DPCD through /dev/drm_dp_auxN (read(2) only).
set -u
conn=${1:-DP-1}
card=$(ls -d /sys/class/drm/card*-"$conn" 2>/dev/null | head -1)
[ -n "$card" ] || { echo "no connector $conn" >&2; exit 1; }
cardn=$(basename "$card" | sed 's/-.*//; s/card//')
dbg=/sys/kernel/debug/dri/$cardn
echo "== $card status=$(cat "$card/status") enabled=$(cat "$card/enabled") dpms=$(cat "$card/dpms")"
echo "== modes"; cat "$card/modes"
echo "== debugfs $dbg/$conn"
for f in link_settings output_bpc dp_dsc_clock_en dp_dsc_slice_width dp_dsc_bits_per_pixel \
	 dp_dsc_fec_support psr_state force_yuv420_output dp_max_bpc current_backlight; do
	[ -r "$dbg/$conn/$f" ] && { echo "-- $f"; cat "$dbg/$conn/$f" 2>&1 | head -12; }
done
echo "== active CRTC mode"
awk '/^crtc/{c=$0} /enable=1|active=1/{a=1} /mode:/{if(a){print c; print; a=0}}' "$dbg/state" 2>/dev/null | head -8
aux=$(ls -d "$card"/drm_dp_aux* 2>/dev/null | head -1)
[ -n "$aux" ] || aux=$(ls -d "$card"/*/drm_dp_aux* 2>/dev/null | head -1)
dev=/dev/$(basename "${aux:-none}")
echo "== DPCD via $dev"
dpcd() { # addr count label
	printf '%-28s %06x: ' "$3" "$1"
	dd if="$dev" bs=1 skip=$(( $1 )) count=$2 status=none 2>/dev/null | od -An -tx1 | tr -s ' \n' ' '
	echo
}
[ -c "$dev" ] && {
	dpcd 0x0000 16 'receiver caps'
	dpcd 0x0080 16 'downstream port caps'
	dpcd 0x0100 16 'link config (rate/lanes/..)'
	dpcd 0x0107 2  'downspread/coding'
	dpcd 0x0200 16 'link status'
	dpcd 0x0210 8  'symbol error counts'
	dpcd 0x0600 1  'sink power state'
	dpcd 0x2002 4  'sink count/esi'
	dpcd 0x200c 4  'lane status esi'
	dpcd 0x3030 16 'PCON 0x3030'
	dpcd 0x3040 16 'PCON 0x3040'
	dpcd 0x3050 16 'PCON config 0x3050'
	dpcd 0x0500 16 'branch OUI/id'
	dpcd 0x0510 16 'branch hw/fw'
}
