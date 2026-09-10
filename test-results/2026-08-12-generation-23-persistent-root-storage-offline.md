# Generation 23 early-USB persistent-root successor

Status: **OFFLINE-READY; unbooted; RAM-only; never flash**.

Generation 23 fixes three defects demonstrated by Generation 22:

1. `persistent-root-init` configured USB only after UFS discovery, power,
   read-only lock, userdata resolution, and inventory, leaving every earlier
   failure observationally identical. Exact NCM now binds immediately after
   the 600-second rollback watchdog and before UFS discovery.
2. The host lifecycle required the old recovery product to remain present
   while proving post-COMMIT cleanup. It now proves listener, firewall,
   address, NFS, and host-snapshot cleanup without requiring a USB product
   that `COMMIT_EXEC` is expected to replace.
3. Host-key bootstrap could wait its full cold-boot budget after Alpine had
   already returned. It now detects the exact fallback product on the anchored
   physical port and terminates that wait.

Fail-first focused timings were 0.448 seconds for the target ordering test,
0.133 seconds for the lifecycle tests, and 0.206 seconds for host-key
bootstrap. Corrected runs passed in 0.462, 0.131, and 0.241 seconds.

The modified initramfs clean twins built in 0.860 and 0.851 seconds and are
byte-identical: 6,121,343 bytes, SHA-256
`07469df6dcf6fe2d480cec077ea91818dd9bc837661b2903fbfb002898c45dbb`.
The unchanged Image is `854397a7…b4a13`; the unchanged DTB is
`72c0db7c…f48c2`. Signed bundle twins reproduce with manifest
`4b56111b…aa567`. The byte-distinct Generation-23 AVB wrapper is
`ac508ef9…54502`; its raw recovery payload remains unchanged at
`06732992…c4aff`.

The candidate still forces all physical block devices read-only and mounts
userdata only as ext4 `ro,noload`, with a tmpfs OverlayFS upper. It neither
creates nor writes the planned bounded local filesystem image. A physical
cycle remains a separate one-use action.

The final repository `ci` tier passed in 6 minutes 1.322 seconds. During the
first complete runs, exact-identity checks rejected stale transitive pins for
the artifact inventory, compatibility profile, claim consumer, recovery gate,
and retention executor contract. Each pin was refreshed only after its direct
focused suite passed; the final run completed with no failures.
