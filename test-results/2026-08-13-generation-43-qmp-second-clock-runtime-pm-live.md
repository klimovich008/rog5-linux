# Generation 43 QMP-UFS second-clock runtime-PM live result

Status: **consumed; clock proof invalidated; exact fallback passed; never retry or flash**.

Generation 43 temporarily booted the exact signed RAM-only candidate once.
Subsequent exact-input review found that its initramfs expected kernel release
`7.1.4-gcdf38b1ddebb`, while its manifest and running kernel identified
`7.1.4-gad56d4021003`. The initramfs configures NCM before checking that
identity, then takes the bounded 25-second release-failure path. It therefore
could not have reached the deferred QMP-UFS `insmod` call. UFS core, platform,
and host modules were absent, so no UFS enumeration or phone-storage access
was possible.

The target reached stable NCM in 60.264 seconds and preserved the exact USB
identity, route, address, NetworkManager state, and non-drop firewall state for
the full 12.014-second control window. Exact Alpine fallback then returned with
boot ID `0d9cf09b-5f22-4c7f-bb41-93e414f1725c`; strict fallback identity,
profile restoration, host cleanup, and intent resolution as
`FALLBACK_RETURNED` all passed. Maximum reported fallback temperature was
39.8 degrees C.

The old host runner treated twelve seconds of stable NCM as proof that the
module returned. That criterion was ambiguous because NCM was already active
during the longer release-failure delay. Generation 43 therefore proves only
stable target NCM and exact fallback under its kernel; it does not clear the
second clock. Generation 42 remains valid because its running release exactly
matched the initramfs expectation and proves the first fixed-rate clock.

The successor must bind its exact release into the generated initramfs and
receive an exact target-originated record after `insmod` returns before its NCM
control window can pass. It may cross the unresolved second and third clocks
together while still returning before OF provider publication.

Fallback pstore was empty and no cycle-specific PMIC reset reason was
available. Both observations are inconclusive. Generation 43's exact claim is
irreversibly consumed and must never be retried.

Retained private evidence:
`/home/deck/.local/state/rog5-generation43-live-20260813.1wcgdCGR`.
