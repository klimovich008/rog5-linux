# Generation 38 QMP-UFS fixed-rate-symbol-clocks live result

Status: **consumed; target NCM disappeared; exact fallback passed; never retry or flash**.

Generation 38 temporarily booted the exact signed RAM-only candidate once.
The target configured its exact NCM gadget, waited for stable carrier, and
loaded only `phy-qcom-qmp-ufs.ko`. The diagnostic SM8350 probe allocated its
clock table and registered all three fixed-rate symbol clocks, then was
designed to return before OF clock-provider publication, cleanup-action
registration, PHY creation, or OF PHY-provider registration. UFS core,
platform, and host modules were absent, so no UFS enumeration or phone-storage
access was possible.

Exact retained host events (+0200):

- claim entered: 23:49:52.878;
- recovery product enumerated: 23:50:21.743;
- COMMIT intent created: approximately 23:50:42.814;
- recovery USB disconnected: 23:50:48.636;
- target product enumerated: 23:50:49.136;
- target carrier observed: 23:50:49.339;
- target USB disconnected: 23:51:00.412, 11.276 seconds after enumeration and
  11.073 seconds after carrier;
- Alpine enumerated: 23:51:18.575;
- exact fallback profile active: 23:51:20.472;
- strict fallback identity recorded: 23:51:23.124;
- intent resolved `FALLBACK_RETURNED`: 23:51:26.040.

Generation 37 disappeared after 11.275 seconds and Generation 36 completed a
12.294-second control window. Generation 38's only retained target delta was
returning after the three fixed-clock registrations but before OF provider
publication. The result therefore clears provider publication and its cleanup
action, and localizes the failure to allocation or one of the three clock
registrations. It does not distinguish those four operations.

The one-transfer server completed the signed bundle transfer, while the
recovery controller completed COMMIT before the server process emitted its
final cleanup markers. The lifecycle treated that successful-controller-first
ordering as a failure. This was a separate host cleanup race: fallback profile
restoration, strict fallback identity, intent resolution, and final host
cleanup all passed. It does not change the target hardware boundary.

The pinned Alpine fallback returned with boot ID
`bfc70c51-8c7a-4ec8-a229-d84897d0eb6d`; maximum later-reported temperature was
approximately 39.5 degrees C. Pstore was empty and no PMIC reset-reason field
was available, so reset cause remains unknown. Generation 38's exact claim is
irreversibly consumed and must never be retried.

Retained private evidence:
`/home/deck/.local/state/rog5-generation38-live-20260812.8PNSAN2s`.
