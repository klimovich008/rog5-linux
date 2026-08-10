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
	*'Successor v2 was consumed before any phone boot'*'Successor v3 was then consumed once after exact-head run `31395428663`'*'V5 is consumed and must never be retried. The leading unproven cause is a post-COMMIT recovery execution failure because `CLAIMED` was returned before the Haven handoff and `kexec -e`. V6 (`43613a11…8eb0a`) preserves the exact raw wrapper and adds one bounded host STATUS request after `CLAIMED`; a returned recovery responder now exposes its terminal state and error, while actual recovery-USB departure remains the target-transition path. Its deterministic AVB generation took 1.529 seconds; the claim is unissued and it has not been booted.'*) ;;
	*)
		echo 'FAIL current status does not consume v2/v3/v4/v5 and identify the unissued v6 successor' >&2
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

echo 'PASS current status consumes Generation 12/v2/v3/v4/v5 and records the unissued v6 successor'
