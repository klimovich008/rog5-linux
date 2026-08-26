# Generation 201 upstream watchdog reset

Result: **FAIL; consumed; never retry.**

The exact running-kernel ABI module removed the Generation-200 load rejection.
After target NCM enumerated, no reporter frame was accepted; the host observed
an NCM TX watchdog at about 11 seconds, target USB loss at about 13 seconds,
and exact slot-A unauthorized recovery USB 18 seconds later. Durable intent
resolved `FALLBACK_RETURNED`. No phone-storage write path existed.

Generation 200 stayed alive when the ABI-mismatched module did not load, so the
new loss correlates with actually loading/arming upstream `qcom,kpss-wdt`.
Matching register offsets are insufficient proof that the upstream clock,
bark/bite, interrupt and secure-reset semantics match ASUS downstream
`qcom,msm-watchdog`. This upstream-module architecture is stopped.

Claude Opus review was attempted but the installed organization has disabled
Claude Code subscription access. No credential was used. The next watchdog
work must port or wrap the retained ASUS/QTI downstream core semantics and
remain read-only until independently proven.
