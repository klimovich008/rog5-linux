# Generation 134 UFS binding classifier

Result: **CONSUMED; RUNTIME UFS PLATFORM DEVICE ABSENT.** Never retry or flash.

After two zero-device UFS cycles, systematic debugging and a bounded Opus review
ranked missing/deferred platform binding above DT RMTFS differences. Independent
checks prove `CONFIG_BLK_DEV_SD=y`, generic `qcom,ufshc` alias compatibility,
and present DT suppliers.

The target changes only the zero-count branch to report: platform count,
unbound platform, bound with zero SCSI hosts, or SCSI hosts with zero blocks.
Target twins are `885065e1...d61d709`; manifest is
`479cc3f9...36f8e03`; Generation-134 recovery is
`e09090c7...9f0ebf1`. No storage access is added.

Live result: exact terminal stage was `ufs-ready/ufs-platform-0`. Therefore no
runtime platform device name matched the UFS controller MMIO address after the
g359 module chain. No SCSI host, block device, mount, SSH, installer, or storage
write occurred; exact slot-A fallback and intent resolution passed. The next
experiment must inspect the runtime device-tree node/status and must not alter
UFS driver code or timeout policy first.
