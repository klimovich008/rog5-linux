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
	*'Successor v2 was consumed before any phone boot'*'Successor v3 was then consumed once after exact-head run `31395428663`'*'The implementation successor now requires exactly that three-name inventory, selects only `a600000.dwc3`, and rejects unknown, missing, renamed, extra, or changing entries. The v4 production candidate (`ee662ab9…6752`) booted once and proved exact recovery ACM/NCM, but the host rejected the recovery ancestry because the invocation supplied short USB name `1-1.2` instead of its full canonical physical path. No control session, payload, NFS, or target ran; the 180-second rollback returned exact Alpine. V4 is consumed. V5 (`e4ae6373…c722`) changes only the deterministic AVB generation over the unchanged clean-twin raw wrapper; its claim is unissued and it has not been booted.'*) ;;
	*)
		echo 'FAIL current status does not consume v2/v3/v4 and identify the unissued v5 successor' >&2
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

echo 'PASS current status consumes Generation 12/v2/v3/v4 and records the unissued v5 successor'
