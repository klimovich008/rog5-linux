# Generation 193 mainline Stage-2 read-only pass

Result: **PASS; consumed; never retry.**

Generation 193 completed the current full responder, signed kexec handoff,
mainline UFS, local Arch, systemd, strict key-only SSH, read-only diagnostics,
controlled reboot, and exact slot-A fastboot return in 339.080 seconds.

The target proved:

- p23 `userdata`: start 18821440, size 408997568 sectors, read-only;
- p24 `arch_root_a`: start 427819008, size 67108824 sectors, read-only;
- 117 physical block nodes and exactly two read-only/norecovery backing mounts;
- battery 8701000 uV, 301 deci-C, status Full;
- side USB online at 5012000 uV with 312000 uA input;
- 30 thermal zones, maximum 39500 milli-C;
- zero blocked UFS queries/SCSI commands, journal recovery events, or UFS errors;
- exact source image and boot-critical identities;
- intent outcome `TARGET_ACCEPTED` and exact slot-A fastboot at 8718 mV.

Private evidence is retained at
`/home/deck/.local/state/rog5-generation193-live-20260826-r1`.

No p24 write path existed in this candidate. The previously authorized Stage-2
clone may now be implemented as one bounded p24-only operation using the proven
high-speed UFS and charging runtime, followed by exact hash, filesystem grow,
native seal, read-only mount, systemd/SSH, and recovery validation.
