# Generation 33 QMP-UFS PHY control live result

Status: **consumed; target NCM disappeared during the PHY-only control; exact fallback passed; never retry**.

The sole RAM-only cycle reused the Generation 32 Image, UFS-enabled DTB,
modules, and clean-twin initramfs. The target established NCM, waited for
stable carrier and the fixed pre-module delay, then loaded only
`phy-qcom-qmp-ufs.ko`. The initramfs contract did not load UFS core, platform,
or Qualcomm host modules and did not enumerate, read, mount, or write storage.

Exact retained host events (+0200):

- target NCM enumeration: 20:08:31.192;
- carrier observed: 20:08:31.411;
- exact NetworkManager profile active: 20:08:33.029;
- target USB disconnect: 20:08:42.611, 11.419 seconds after enumeration;
- Alpine USB enumeration: 20:09:00.521;
- fallback profile restoration: 20:09:02.808;
- strict fallback identity: 20:09:05.075;
- intent resolution as `FALLBACK_RETURNED`: 20:09:07.761.

The target's one-second stable-carrier wait and three-second pre-module delay
place `insmod` at approximately 20:08:35.4; this is inferred rather than a
transported target timestamp. The target disappeared approximately 7.2 seconds
later. The nearly identical Generation 32 lifetime does not distinguish module
relocation/driver registration from QMP-UFS platform binding or a shared fixed
timer.

NetworkManager successfully activated the exact profile. The runner then lost
the interface between its target-identity sample and its NetworkManager
inventory query and initially reported an inspection failure. This is an
observation race, not evidence that NetworkManager setup failed; the Generation
34 runner rechecks the anchored USB identity and classifies disappearance as
the terminal event.

The pinned Alpine identity returned with a maximum reported temperature of
42.5 degrees C. No cycle-specific PMIC reset reason was retained and pstore
remains inconclusive. Generation 34 therefore loads the same module with only
the QMP-UFS PHY device-tree node disabled, separating module registration from
platform bind/probe without allowing UFS access.
