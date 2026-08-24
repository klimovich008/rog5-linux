# Generation 135 runtime UFS device-tree classifier

Result: **OFFLINE PASS; ADMITTED ONCE.** Never flash or retry after entry.

Primary question: does the running target expose the exact UFS DT node with
status `okay`, and if so does OF platform population still omit its device?

The classifier reads only the exact runtime DT node/status before the existing
platform scan. Target twins are `fbe4512a...bc9683`; manifest is
`a55460c6...bd6f8f`; Generation-135 recovery is
`bf0de9be...8f99a8`. Kernel, sealed DTB, modules, reporter, storage scope, and
fallback are unchanged.
