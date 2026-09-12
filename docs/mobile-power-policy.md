# Mobile power and session policy proposal

This is a separate, uninstalled mobile policy. The accepted headless health,
radio-refused readiness and Wi-Fi preparation remain unchanged: USB power is
required and Wi-Fi power saving is disabled for latency. The radio-refused path
is a guarded headless recovery condition, not evidence of a usable local shell.

[The offline evaluator](../scripts/host/assess-mobile-power.py) accepts only
identity-bound, fresh complete telemetry and a working local interface. Its
fixtures cover battery-only startup, cable removal, degraded networking,
stale/mismatched observations, missing zones and thermal/voltage/capacity
boundaries. No fixture acknowledges a persistent trial or authorizes hardware.
No boot or runtime consumer selects this evaluator. Its `assess_private` entry
reads the ignored mode-0600 device profile, requires independently supplied
runtime identity and matching observed product/slot/USB topology, and grants no
authority. Historical sealed boot and capture consumers keep their identity
bytes; migrating them is not accomplished by changing this new policy.

The proposal retains the intersection of current voltage gates (8.4–8.8 V),
Good battery health, battery temperature below 40 C and all expected thermal
zones below 60 C. The thermal inventory must come from the exact qualified
kernel; a list supplied by an arbitrary caller is not telemetry validation.
Samples must be no more than five seconds old and cable-removal comparisons
must remain in the same boot. These are observation limits, not charging targets.

The provisional capacity thresholds are 50% to begin, 40% to continue and a
20-percentage-point nominal reserve. They do **not** establish remaining energy
or a safe ten-minute runtime. Capacity calibration, dual-cell voltage/current
interpretation, measured load, telemetry failure response and actual shutdown
margin are BLOCKED pending exact-device measurement. The last r131 health
receipt contains a guard result, not the raw telemetry needed to qualify this
policy. Historical July telemetry is not current-kernel qualification.

With local recovery/UI working, a network outage can leave a candidate local
session usable. Headless health is not relaxed. Wi-Fi power saving requires its
own latency, reconnect and energy measurements before enabling it. Cable removal,
suspend/wake, idle drain and charging each need separate physical qualification.
This proposal does not explain S06 or R01; both failures remain open.

The [mobile contract](../configs/mobile/acceptance.json) separates software proof
from candidate-bound physical proof. The [session policy](../configs/mobile/session-policy.json)
and [sysusers fragment](../packaging/arch/mobile/sysusers.conf) define a non-root
user and default-off remote services for a future mobile composition. They are
not installed into the headless image. A regular desktop plus remote services
is not mobile-shell qualification.
