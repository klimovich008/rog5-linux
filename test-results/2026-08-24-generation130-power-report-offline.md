# Generation 130 early power/USB report

Result: **OFFLINE PASS; ADMITTED ONCE.** Never flash or retry after entry.

Primary question: which exact power/USB loader boundary follows the now-proven
target NCM path, or does the loader pass and permit UFS/SSH/image staging?

The stager now reuses the existing seven-field stage protocol after exact
NCM/carrier and before the loader. A terminal `power-usb-*` result is sanitized,
published once per second, and held for ten seconds before slot-A fallback.
No new shell, SSH, storage, or kernel surface is added. Target twins are
`3814d298...401af0`; manifest is `f333316a...3222915`; Generation-130 recovery
is `a1cc3db2...ec3923`. Focused tests and active tier pass.
