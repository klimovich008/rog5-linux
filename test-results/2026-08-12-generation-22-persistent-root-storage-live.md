# Generation 22 read-only persistent-root live result

Status: **CONSUMED; never retry or flash**.

The sole RAM-only lifecycle completed the exact signed-bundle transfer and a
correlated recovery `COMMIT_EXEC`. Recovery USB disconnected at host monotonic
time `11323.501029`. No `ROG5 persistent root` USB product enumerated. Exact
Alpine enumerated at `11348.756037`, a 25.255-second blackout, and strict SSH
proved fallback boot identity `909764d3-e879-44ab-bb61-3f0049073e29`.

The lifecycle's first error—failure to leave the old recovery profile
deferred—was a host transition-classification defect: Alpine had already
re-enumerated while that check still required the recovery USB product. It is
not evidence of a host cleanup leak. Final fallback profile restoration,
intent resolution as `FALLBACK_RETURNED`, and host cleanup passed.

Because target USB never appeared, retained evidence cannot distinguish an
early target panic, command-line/release rejection, or failure before UDC
binding. Alpine's pstore filesystem was initially unmounted. A bounded
temporary mount showed zero records and was removed immediately; the empty
result is inconclusive, not proof that no crash occurred. No PMIC reset-reason
field was available. The target made no authorized phone-storage write.

Private evidence remains outside Git under the mode-0700 lifecycle directory.
Generation 22's policy row is removed, inventory role is consumed, and its
exact claim remains irreversible.
