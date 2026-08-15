#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
readme=$repo/README.md
roadmap=$repo/ROADMAP.md
current=$repo/docs/current-state.md
active=$repo/docs/active-context.md
charging=$repo/docs/asus-charging-recovery.md

for document in "$readme" "$roadmap" "$current" "$active" "$charging"; do
	[ -f "$document" ] && [ ! -L "$document" ] || {
		echo "FAIL current recovery status source is missing or linked: $document" >&2
		exit 1
	}
done

if grep -Fq 'No Generation-12 boot claim or phone boot occurred' "$roadmap"; then
	echo 'FAIL roadmap still describes consumed Generation 12 as unbooted' >&2
	exit 1
fi

normalized_status=$(tr '\n' ' ' <"$current")
normalized_active=$(tr '\n' ' ' <"$active")
normalized_charging=$(tr '\n' ' ' <"$charging")
case $normalized_status in
	*'Generation 12 is consumed and must never be retried; it is not pending live admission.'*) ;;
	*)
		echo 'FAIL current status does not permanently consume Generation 12' >&2
		exit 1
		;;
esac
case $normalized_status in
	*'Successor v2 was consumed before any phone boot'*'Successor v3 was then consumed once after exact-head run `31395428663`'*'V8 is consumed and must never be retried.'*'V8 r1 was superseded before claim or phone contact'*'V9 is consumed and must never be retried.'*'V10 (`fb5fce1…3452`) is consumed and must never be retried.'*'corrected observer (`a655d4b3…05b`) is also consumed and must never be retried.'*'mainline DT platform device and UDC are named'*'`a600000.usb`'*) ;;
	*)
		echo 'FAIL current status does not consume v2/v3/v4/v5/v6/v7/v8/v9/v10 and the observer or record the corrected mainline UDC' >&2
		exit 1
		;;
esac

grep -Fq 'Generation 12 is consumed and never reusable.' "$readme" || {
	echo 'FAIL README does not classify Generation 12 as consumed' >&2
	exit 1
}
grep -Fq 'Generation 12 is removed from boot policy, recorded' "$roadmap" || {
	echo 'FAIL roadmap does not record Generation 12 policy removal' >&2
	exit 1
}
case $normalized_active in
	*'Generation 12 is consumed and must never be retried.'*) ;;
	*)
		echo 'FAIL active context does not preserve Generation 12 refusal' >&2
		exit 1
		;;
esac

case $normalized_charging in
	*'fastboot -s "$ROG5_FASTBOOT_SERIAL" set_active a'*'fastboot -s "$ROG5_FASTBOOT_SERIAL" reboot recovery'*'battery-soc-ok` is exactly `yes`'*'fastboot -s "$ROG5_FASTBOOT_SERIAL" set_active b'*) ;;
	*)
		echo 'FAIL ASUS charging recovery does not preserve the battery and slot boundary' >&2
		exit 1
		;;
esac
case $normalized_charging in
	*'Do not flash `boot_a`, `boot_b`, `vendor_boot`, `misc`, or any other partition'*) ;;
	*)
		echo 'FAIL ASUS charging recovery does not preserve the no-flash boundary' >&2
		exit 1
		;;
esac
case $normalized_active in
	*'Active-slot metadata is temporarily A'*'Stage-1 claim remains unconsumed'*'asus-charging-recovery.md'*) ;;
	*)
		echo 'FAIL active context does not record the temporary slot-A charging hold' >&2
		exit 1
		;;
esac
grep -Fq 'docs/asus-charging-recovery.md' "$readme" || {
	echo 'FAIL README does not link the ASUS charging recovery runbook' >&2
	exit 1
}

case $normalized_status in
	*'Generation 20 is consumed, removed from temporary-boot policy, and must never be retried.'*) ;;
	*)
		echo 'FAIL current status does not permanently consume Generation 20' >&2
		exit 1
		;;
esac
case $normalized_active in
	*'Generation 20 is consumed, absent from boot policy, and'*'never reusable.'*) ;;
	*)
		echo 'FAIL active context does not permanently consume Generation 20' >&2
		exit 1
		;;
esac
normalized_roadmap=$(tr '\n' ' ' <"$roadmap")
case $normalized_roadmap in
	*'Generation 20 is consumed and removed from boot policy.'*) ;;
	*)
		echo 'FAIL roadmap does not record Generation 20 policy removal' >&2
		exit 1
		;;
esac

echo 'PASS current status records consumed generations, the corrected mainline UDC, and the temporary slot-A charging hold'
