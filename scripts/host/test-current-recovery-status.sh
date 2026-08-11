#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
readme=$repo/README.md
roadmap=$repo/ROADMAP.md
current=$repo/docs/current-state.md
active=$repo/docs/active-context.md

for document in "$readme" "$roadmap" "$current" "$active"; do
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

echo 'PASS current status consumes Generation 12/v2/v3/v4/v5/v6/v7/v8/v9/v10 and the observer, and records the corrected mainline UDC'
