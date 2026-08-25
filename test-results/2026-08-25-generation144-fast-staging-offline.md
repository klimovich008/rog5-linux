# Generation 144 immediate target activation

Result: **OFFLINE PASS; ADMITTED ONCE.** Never flash or retry after entry.

Generation 143 proved the NetworkManager ownership-gap classification but
returned to fastboot before host-key readiness. The host waited for a complete
post-COMMIT cleanup proof even though the bundle server had already completed
and logged canonical listener, firewall, address, export, and profile cleanup.

Generation 144 removes only that redundant wait and activates the target
profile immediately after the bundle server exits cleanly. Final fallback and
host cleanup remain mandatory. The target differs only by fresh bundle
identity; UFS, SSH, exact Arch image, installer, relock, and reboot bytes are
otherwise unchanged.
