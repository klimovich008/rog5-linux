# Generation 23 persistent-root storage live result

Status: **CONSUMED; target rejected; exact Alpine fallback passed; never retry**.

The sole RAM-only cycle consumed claim
`persistent-root-storage-read-v2-live-v1`, transferred and verified the exact
signed bundle, and recovery accepted correlated `COMMIT_EXEC`. Recovery USB
disconnected at host monotonic `14557.081030`. No `ROG5 persistent root` USB
product appeared. Exact Alpine enumerated on the same physical port at
`14582.411050`, a 25.330-second blackout. Strict pinned SSH, fallback identity,
host cleanup, and Steam-socket restoration passed. No phone-storage write was
performed.

Generation 23 did not establish the intended early observation: its initramfs
still parsed and validated command-line identity and running kernel release
before arming rollback and configuring USB. A separate forced-Alpine reboot
measured `16032.169036` disconnect to `16050.331041` USB enumeration, or
18.162 seconds. Subtracting that baseline leaves approximately 7.168 seconds
for the mainline leg. This strongly matches the five-second invalid-command-
line failure delay plus kernel/init startup. It is timing evidence, not direct
proof of `/proc/cmdline` content; an early panic or other reset remains
possible.

Alpine `/sys/fs/pstore` contained no record. Empty pstore is inconclusive.
Generation 23 is removed from active boot policy and must never be retried.
