# Generation 146 key-only account correction

Result: **OFFLINE PASS; ADMITTED ONCE.** Never flash or retry after entry.

Generation 145 passed UFS, userdata identity, and storage lock, then reported
`runtime/nologin-identity`. The sealed archive has no `/etc/nologin`; the
earlier OpenSSH `Not allowed at this time` came from the builder's `root:!`
shadow entry, which locks public-key authentication too.

Generation 146 accepts exact nologin absence or one empty regular file and
sets root's shadow field to `x`, which is invalid as a password but does not
lock the account. `PasswordAuthentication no`, keyboard-interactive disabled,
and `PermitRootLogin prohibit-password` remain exact. All storage-write bounds
remain unchanged.
