# Generation 142 key-only SSH staging

Result: **OFFLINE PASS; ADMITTED ONCE.** Never flash or retry after entry.

Generation 141 passed power/USB, complete UFS topology, userdata identity,
storage lock, and target host-key pinning. OpenSSH then rejected every pre-auth
connection with `Not allowed at this time`; the sealed initramfs contained an
empty regular `/etc/nologin`. No image transfer, installer, mount, or storage
write occurred.

Generation 142 proves that exact zero-byte regular-file identity, removes it,
and verifies absence before starting the otherwise unchanged key-only sshd.
The exact Arch gzip, userdata-only installer, complete relock, watchdog, and
built-in fastboot return remain unchanged.

Target twins are `dd7546ca...8c66e000`; manifest is
`33352761...36ed831f`; Generation-142 recovery is
`246d5c37...2af3ea28`. Raw stable recovery remains unchanged.
