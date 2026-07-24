# Network-root SSH key refresh

Status: **PASS artifact-only; phone boot not run**. The host reboot erased the
earlier private key because it intentionally lived only in tmpfs. Booting the
otherwise accepted Arch root would therefore have produced a key-only SSH
server with no usable client credential.

A dedicated Ed25519 key was generated outside the repository. Its private
half remains on the development host at mode 0600 and was not copied into any
artifact. Only the public half was supplied to the existing rootfs staging
pipeline.

The pipeline started from the signed Arch Linux ARM input, removed its generic
kernel, installed the requested current package set, injected the exact
`7.1.4-g7a5cef0db479` modules and pinned A660 firmware, and verified locked
password accounts plus key-only SSH. It then archived the root and re-extracted
it into a second clean volume for the independent ownership, mode, xattr,
identity, networking, systemd, desktop, module, and firmware checks.

- Size: 2,007,186,653 bytes
- SHA-256:
  `8711b34cf454a3f3eef04f12650ef0622ee575d80942e418e1c61f45679aa717`
- Source commit:
  `8c35d4e72382fab6217d510e17108fca60d3bd6f`

Direct archive extraction confirmed that both root and `rog5` authorized-key
files exactly match the external public key. A repeated isolated NFSv4.2 mount
then read both mode-0600 files and matched them to the host public key. This
test also exposed and fixed the NFSv4 startup-grace race: server readiness now
waits for the explicit 10-second grace to end.

The subsequent authorized live step added the same public key to the
persistent fallback authorization file while preserving its previous file as
an on-device backup. Key-only fallback login then passed across a complete
reboot, and both root and `rog5` login passed in the Arch diagnostic target.
The private key never left the development host.
