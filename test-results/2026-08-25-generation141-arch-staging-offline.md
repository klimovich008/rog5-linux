# Generation 141 local Arch staging

Result: **OFFLINE PASS; ADMITTED ONCE.** Never flash or retry after entry.

Generation 140 passed exact power/USB telemetry, NCM, all four UFS modules, the
complete 116-node topology, and built-in fastboot return. The full staging init
had the same `set -f` and physical-only counter defects, now corrected to the
proven Generation-140 behavior.

Generation 141 keeps the exact Image, DTB, modules, firmware, power loader,
reboot mode, target SSH key, and sealed installer. It transfers only the exact
649,960,943-byte gzip SHA-256 `41f75ab6...d83ba88`, then the target installer
may create only `/rog5/images/arch-local-a.ext4` inside exact userdata before
relocking every block node and returning to fastboot.

Target twins are `d56fab0e...9ef1cfc`; manifest is
`d4fa6160...c78501d4`; Generation-141 recovery is
`0cf74133...977f210b`. Raw stable recovery remains unchanged.
