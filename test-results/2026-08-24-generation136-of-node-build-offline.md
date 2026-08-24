# Generation 136 exact OF-node target checkpoint

Result: **CONSUMED; EXACT OF-NODE PLATFORM COUNT ZERO.** Never retry or flash.

The target scans every platform device and accepts only an `of_node` symlink
that resolves to the exact runtime UFS DT node, independent of platform-device
basename. Target twins are byte-identical at
`ee1afba10527d7324c4dc596918f7bc1cb14be7858b540acbbbb3de2fe04f2ed`.

Signed bundle twins verify with manifest
`4c10245dfc2651f7eae4c4f466a632b7bd01c04dfe2c81f03354bf8a56159b69`.
Authority-free Generation-136 recovery is
`c654a28f4ed8834dbd84e863c61ee87b2c9e4e37e10df877a8804c5e20ab9051`;
its raw stable-recovery payload is unchanged. Policy, one-use claim, candidate
admission was recorded before the sole cycle.

Live result: exact terminal detail remained `ufs-dt-okay-platform-0` even when
platform devices were matched by resolved `of_node` identity. This proves the
current g359 Image/DT pair creates no UFS platform device. No SCSI host, block,
mount, SSH, installer, or storage write occurred; slot-A fallback passed. The
next cycle must use the live-proven g359 UFS Image/DT pair rather than adding
more instrumentation to this broken combined pair.
