# Generation 118 postmortem observer

Date: 2026-08-24

Result: **CONSUMED; PSTORE PRESENT BUT NOT TARGET-LINEAGE.** Never retry or flash.

The observation-only raw recovery is unchanged at
`37d4c10beca3fd7fb2c17e46a7b150d88e1957b50ac43e0ed012feaa09e7546a`.
Only deterministic AVB generation 11 is new, producing
`4fef0b9acd38bf06009db1c26314e6ec910b32a06f251012b4efc2910c13325c`.

One RAM-only boot asks one question: does retained ramoops identify the last
Generation 118 staging step? The recovery contains no kexec, bundle fetch,
payload execution, network-root, or phone-storage surface. Empty pstore remains
inconclusive.

The sole observation boot reached ACM and reported one retained record:

- state `PRESENT`;
- records `1`;
- bytes `161854`;
- SHA-256
  `513d06add4ab038634808e2706b555f37ecb951f4953d46f38b70b14431c689e`;
- lineage `NONE`.

The bounded tail contains the ASUS recovery kernel's `kexec` CPU-shutdown
sequence at about 27.95 seconds, not a Generation 118 initramfs failure marker.
It therefore proves retention of the preceding recovery console but does not
classify the target stop. Absence of target lineage remains inconclusive. The
next discriminator must leave target behavior unchanged and encode each
pre-NCM failure boundary in a distinct return delay.
