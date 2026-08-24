# Generation 127 ConfigFS bind errno

Consumed; bind success, host R7 failure. Never retry or flash. Twin initramfs
`4144e1bd...eced9a`, manifest `107b7217...9b4396b`, recovery
`5a1b1e8a...64867c`.

Recovery USB departed at `14:17:04.199600`; the target product enumerated at
`14:17:06.495509`, disconnected at `14:18:36.360500`, and exact slot-A
fastboot appeared at `14:18:41.213508`. The 89.864-second target dwell selects
the classifier's 90-second bind-success branch. The host activated the exact
NetworkManager profile but its shared NCM allowlist omitted
`ROG5_local_image_stage`, so it filtered out the target until fallback. This is
R7, not a kernel failure. No target network configuration, SSH, installer, or
phone-storage write ran. Exact fallback and intent resolution passed.
