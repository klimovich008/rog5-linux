# Generation 210 p24 postmortem

Result: **FAIL-CLOSED; consumed; never retry.**

The read-only target emitted `inspect READ`, found ext4 magic, then failed exact
`dumpe2fs`. Exact slot-A fastboot and `FALLBACK_RETURNED` passed; all devices
remained read-only.

p24 is a partial/corrupt source clone, not a mountable or repairable completed
filesystem. The next bounded writer must overwrite every known allocated source
extent from the verified local image before fsck/grow/seal; it must not resume
`e2image` or infer completeness from the ext4 magic.
