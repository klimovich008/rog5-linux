# Generation 24 precheck-USB persistent-root live result

Status: **CONSUMED; no target USB; exact Alpine fallback passed; never retry**.

The sole RAM-only cycle consumed claim
`persistent-root-storage-read-v3-live-v1`, transferred and verified the exact
signed bundle, and recovery accepted correlated `COMMIT_EXEC`. Recovery USB
disconnected at host wall epoch `1786518060.880778879`. A 100 ms independent
USB monitor never observed `ROG5 persistent root`; exact Alpine enumerated at
`1786518086.448114484`, a 25.567-second blackout. No phone-storage write was
performed.

Generation 24 had already moved rollback arming and NCM setup before command-
line/release validation and every userspace UFS operation. The absent target
product therefore disproves the Generation-23 ordering explanation. It does
not distinguish kernel entry/unpack failure from failure before successful
UDC binding. The 18.162-second forced-Alpine reboot baseline leaves roughly
7.4 seconds for the target leg, but reset-class and disconnect-fiducial
differences make that an approximate upper bound, not a direct measurement.

The lifecycle then hit a host-only classification defect: fallback detection
asked NetworkManager for ownership while the exact Alpine interface was still
transitioning. Final strict SSH fallback proof, host cleanup, Steam TCP/8081
socket restoration, and durable `FALLBACK_RETURNED` resolution nevertheless
passed. The successor uses the existing USB-ancestry fallback check and no
longer depends on transient NetworkManager state for this classification.

Fallback pstore was empty, but the fallback command line did not map the
target ramoops region; the result remains inconclusive. No PMIC reset-reason
field was available. Private logs and exact boot identities remain outside
Git.
