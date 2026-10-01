#!/bin/sh
# Compose a reduced-reservation ("memslim") DTB for RAM trials from the
# production board.dtb d10 (platform-dp4-btmtc-memx-l11off-dtb-d10, bundle
# main-k111-d10-261001b). Opt-in only: never the default until a RAM trial
# per part has passed (plan: test-results/2026-10-01-memory-footprint.md).
#
#   compose-memslim-dtb.sh BASE_DTB OUTPUT PART[,PART...]
#
# Each part hands RAM that the production DT reserves back to Linux. The
# evidence for every range is the ASUS 5.4 wrapper's own boot (stockcap-c1:
# its runtime FDT, CMA placement and subsystem table) and the stock lahaina
# DT: none of it is a static secure carve-out, the subsystems that would own
# it are OFFLINING under the wrapper, and its CMA pools are plain DMA heaps
# or per-allocation HYP_CMA heaps with no user in the recovery wrapper. That
# makes them candidates, not proof: nobody has captured the wrapper's
# hypervisor assignments right before kexec, so each part needs its own RAM
# trial with SEA monitoring before it can become a default. Kept on purpose: hyp, AOP, cmd-db, SMEM,
# cpucp, the CDSP secure heap (an ION secure carve-out the wrapper creates
# at boot), the PIL regions Linux or the bisect kit boots
# (ADSP, SLPI, CDSP, GPU zap, video), SPSS and IPA (tiny), the memshare pool
# 0xd8000000 (modem memshare), removed_mem 0xd8800000, ramoops, the splash
# and DFPS regions, memx, and in the 0xedc00000 span the wrapper's mem_dump
# (registered with TZ as the crash dump table), sp (the SPSS ION HYP_CMA
# heap), cnss_wlan (WLAN is ONLINE
# under the wrapper: the chip may DMA there until ath11k resets it), the
# fastrpc/ION DSP pools and qseecom/qseecom_ta (TZ rejected PAS metadata at
# 0xfe400000 inside qseecom: test-results/2026-07-25-network-root-adsp-live.md).
#
# Parts:
#   stockcma  196 MiB, 0xcbc00000-0xd7ffffff. Stock places the reusable CMA
#             pools secure_display (164 MiB, ION HYP_CMA: assigned per
#             allocation only, secure UI never runs under the wrapper) and
#             linux,cma (32 MiB) here; the stock FDT has no reg for the
#             upstream sm8350.dtsi hyp_reserved/trustedvm/qrtr/neuron nodes
#             (the wrapper's trustedvm stays OFFLINING; Haven logs "HYPX NOT
#             ENABLED"). Deletes memory@cbc00000 (no phandle), disables
#             memory@d0000000, @d0800000, @d7ef7000, @d7f00000, @d7f80000.
#   pil       266 MiB. PIL carve-outs of subsystems neither the wrapper
#             (OFFLINING) nor Linux ever boots: modem 0x8b800000 (256 MiB;
#             its only consumer remoteproc@4080000 must be disabled),
#             camera 0x85200000 and cvp 0x85c00000 (5 MiB each). Disables
#             the three nodes (phandles stay valid).
#   ionpool   128 MiB of the 288 MiB span 0xedc00000-0xffbfffff: the
#             wrapper's audio_cma (0xedc00000, 28 MiB) and non_secure_display
#             (0xf3800000, 100 MiB), both ION DMA heaps (no hypervisor
#             assignment). memory@edc00000 (no phandle) becomes
#             memory@ef800000 (64 MiB: mem_dump + sp) + memory@f9c00000
#             (96 MiB, cnss_wlan up to qseecom_ta).
#
# Disabled reserved-memory nodes keep their reg: the loader's verifier still
# counts them in its overlap check, and Linux skips nodes whose status is
# not okay. Markers: / rog5,memslim = PARTS, / rog5,memslim-base =
# production-dtb-d10. Prints the output's SHA-256. Checks every node it
# changes and that nothing else in the tree changed.
set -eu
base=${1:?usage: compose-memslim-dtb.sh BASE_DTB OUTPUT PART[,PART...]}
output=${2:?missing output}
parts=${3:?missing part}
# production DTB d10 (main-k111-d10-261001b); another base must be
# requalified (reserved-memory map, consumers) and reviewed first.
expected_base=${EXPECTED_MEMSLIM_BASE_SHA256:-dda8b280da1ee6a4d4c85c663008551757f9766b278dc93dfeba0b875114788e}
base_name=production-dtb-d10
[ -f "$base" ] && [ ! -L "$base" ] || { echo 'FAIL base DTB' >&2; exit 1; }
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] ||
	{ echo 'FAIL base DTB is not the reviewed production DTB' >&2; exit 1; }
[ ! -e "$output" ] && [ ! -L "$output" ] || { echo 'FAIL output exists' >&2; exit 1; }
stockcma=0 pil=0 ionpool=0 count=0
for part in $(printf '%s\n' "$parts" | tr ',' ' '); do
	case $part in
		stockcma) stockcma=1 ;;
		pil) pil=1 ;;
		ionpool) ionpool=1 ;;
		*) echo "FAIL unknown part $part" >&2; exit 1 ;;
	esac
	count=$((count + 1))
done
[ "$count" -gt 0 ] || { echo 'FAIL missing part' >&2; exit 1; }
[ "$((stockcma + pil + ionpool))" = "$count" ] || { echo 'FAIL repeated part' >&2; exit 1; }

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
dtb=$work/memslim.dtb
dtc -q -I dtb -O dtb -p 4096 -o "$dtb" "$base"
rm=/reserved-memory

# reg of NODE is exactly "HI LO SHI SLO" (fdtget -t x).
reg_is() {
	[ "$(fdtget -t x "$dtb" "$rm/$1" reg 2>/dev/null)" = "$2" ] ||
		{ echo "FAIL $rm/$1 reg is not <$2>" >&2; exit 1; }
}
mapped() { ! fdtget "$dtb" "$rm/$1" no-map >/dev/null 2>&1 || { echo "FAIL $rm/$1 is no-map" >&2; exit 1; }; }
nomap() { fdtget "$dtb" "$rm/$1" no-map >/dev/null 2>&1 || { echo "FAIL $rm/$1 is not no-map" >&2; exit 1; }; }
no_phandle() {
	! fdtget "$dtb" "$rm/$1" phandle >/dev/null 2>&1 || { echo "FAIL $rm/$1 has a phandle" >&2; exit 1; }
}
active() {
	case $(fdtget "$dtb" "$rm/$1" status 2>/dev/null || echo okay) in okay) ;; *)
		echo "FAIL $rm/$1 is not active" >&2; exit 1 ;; esac
}
# No memory-region property anywhere names the phandle of NODE, except in
# the nodes listed (which must be disabled).
consumers_disabled() {
	node=$1; shift
	# no phandle: nothing can reference the node
	ph=$(fdtget -t u "$dtb" "$rm/$node" phandle 2>/dev/null) || return 0
	# dtc prints cells as 0x%02x: compare the hex digits without leading zeros
	dtc -q -I dtb -O dts "$dtb" 2>/dev/null | awk -v ph="$(printf '%x' "$ph")" '
		/^[ \t]*[^ \t].*\{[ \t]*$/ { path[++d] = $1; next }
		/^[ \t]*\};/ { d--; next }
		/memory-region =/ {
			line = $0; gsub(/[<>;,]/, " ", line); n = split(line, w, /[ \t]+/)
			for (i = 1; i <= n; i++) {
				if (substr(w[i], 1, 2) != "0x") continue
				h = tolower(substr(w[i], 3)); sub(/^0+/, "", h)
				if (h == ph) { s = ""; for (j = 2; j <= d; j++) s = s "/" path[j]; print s }
			}
		}' >"$work/users"
	while read -r user; do
		ok=0
		for allowed in "$@"; do [ "$user" = "$allowed" ] && ok=1; done
		[ "$ok" = 1 ] || { echo "FAIL $rm/$node is used by $user" >&2; exit 1; }
		[ "$(fdtget "$dtb" "$user" status 2>/dev/null)" = disabled ] ||
			{ echo "FAIL $user (user of $rm/$node) is not disabled" >&2; exit 1; }
	done <"$work/users"
}
disable() { active "$1"; fdtput -t s "$dtb" "$rm/$1" status disabled; }

# The kept reservations must survive every part (checked again at the end).
check_kept() {
	reg_is memory@34a000000 '3 4a000000 0 4000000'; nomap memory@34a000000     # memx
	reg_is memory@d8000000 '0 d8000000 0 800000'; nomap memory@d8000000       # memshare
	reg_is memory@d8800000 '0 d8800000 0 a800000'; nomap memory@d8800000      # removed_mem
	reg_is memory@80c00000 '0 80c00000 0 4600000'; nomap memory@80c00000      # CDSP secure heap
	reg_is memory@9b800000 '0 9b800000 0 400000'                               # ramoops
	reg_is memory@e5000000 '0 e5000000 0 2300000'; nomap memory@e5000000      # splash
	for n in memory@34a000000 memory@d8000000 memory@d8800000 memory@80c00000 memory@9b800000 \
		memory@e5000000 memory@86100000 memory@88200000 memory@89700000 memory@8b51a000 \
		memory@85700000 memory@8b600000 memory@8b500000 memory@8b510000; do
		active "$n"
	done
}

check_kept
fdtput -t s "$dtb" / rog5,memslim "$parts"
fdtput -t s "$dtb" / rog5,memslim-base "$base_name"

if [ "$stockcma" = 1 ]; then
	reg_is memory@cbc00000 '0 cbc00000 0 4400000'; mapped memory@cbc00000; no_phandle memory@cbc00000
	reg_is memory@d0000000 '0 d0000000 0 800000'
	reg_is memory@d0800000 '0 d0800000 0 76f7000'
	reg_is memory@d7ef7000 '0 d7ef7000 0 9000'
	reg_is memory@d7f00000 '0 d7f00000 0 80000'
	reg_is memory@d7f80000 '0 d7f80000 0 80000'
	fdtput -r "$dtb" "$rm/memory@cbc00000"
	for n in memory@d0000000 memory@d0800000 memory@d7ef7000 memory@d7f00000 memory@d7f80000; do
		consumers_disabled "$n"
		disable "$n"
	done
fi
if [ "$pil" = 1 ]; then
	modem=/soc@0/remoteproc@4080000
	[ "$(fdtget "$dtb" "$modem" compatible 2>/dev/null)" = qcom,sm8350-mpss-pas ] &&
		[ "$(fdtget "$dtb" "$modem" status 2>/dev/null)" = disabled ] ||
		{ echo "FAIL $modem is not the disabled MPSS" >&2; exit 1; }
	reg_is memory@8b800000 '0 8b800000 0 10000000'; nomap memory@8b800000
	reg_is memory@85200000 '0 85200000 0 500000'; nomap memory@85200000
	reg_is memory@85c00000 '0 85c00000 0 500000'; nomap memory@85c00000
	consumers_disabled memory@8b800000 "$modem"
	consumers_disabled memory@85200000
	consumers_disabled memory@85c00000
	for n in memory@8b800000 memory@85200000 memory@85c00000; do disable "$n"; done
fi
if [ "$ionpool" = 1 ]; then
	reg_is memory@edc00000 '0 edc00000 0 12000000'; mapped memory@edc00000; no_phandle memory@edc00000
	! fdtget "$dtb" "$rm/memory@ef800000" reg >/dev/null 2>&1 &&
		! fdtget "$dtb" "$rm/memory@f9c00000" reg >/dev/null 2>&1 ||
		{ echo 'FAIL ionpool target nodes already exist' >&2; exit 1; }
	fdtput -r "$dtb" "$rm/memory@edc00000"
	# mem_dump (TZ crash dump table), sp (SPSS HYP_CMA) and
	# cnss_wlan..qseecom_ta stay reserved, mapped and non-reusable like the
	# span they come from.
	fdtput -c "$dtb" "$rm/memory@ef800000"
	fdtput -t x "$dtb" "$rm/memory@ef800000" reg 0 0xef800000 0 0x4000000
	fdtput -c "$dtb" "$rm/memory@f9c00000"
	fdtput -t x "$dtb" "$rm/memory@f9c00000" reg 0 0xf9c00000 0 0x6000000
fi

check_kept
dtc -q -I dtb -O dtb -o "$output.tmp.$$" "$dtb"

# Nothing outside /reserved-memory and the two markers changed.
dtc -q -I dtb -O dts "$base" | awk '/^\treserved-memory \{/ { skip = 1 } !skip { print } skip && /^\t\};/ { skip = 0 }' >"$work/a"
dtc -q -I dtb -O dts "$output.tmp.$$" | awk '/^\treserved-memory \{/ { skip = 1 } !skip { print } skip && /^\t\};/ { skip = 0 }' |
	grep -v '^	rog5,memslim' >"$work/b"
cmp -s "$work/a" "$work/b" || { rm -f "$output.tmp.$$"; echo 'FAIL the tree changed outside /reserved-memory' >&2; exit 1; }
mv "$output.tmp.$$" "$output"
sha256sum "$output" | cut -d ' ' -f 1
