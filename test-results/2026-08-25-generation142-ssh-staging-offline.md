# Generation 142 key-only SSH staging

Result: **CONSUMED BY HOST NM RACE; NO TARGET ACCEPTANCE OR WRITE.** Never
retry or flash.

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

The sole cycle transferred and committed the target, then host cleanup saw the
new NCM interface before NetworkManager exposed either ownership field and
failed before target acceptance. No stage, SSH transfer, installer, mount, or
storage-write evidence exists. Exact fastboot fallback and cleanup passed.
