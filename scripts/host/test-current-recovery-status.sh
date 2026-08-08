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
	*'A host-only, unissued stage-75/current-cycle-postmortem successor is the active work and has no boot authority.'*) ;;
	*)
		echo 'FAIL current status does not identify the unissued no-authority successor' >&2
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

echo 'PASS current status consumes Generation 12 and keeps its successor unissued without boot authority'
