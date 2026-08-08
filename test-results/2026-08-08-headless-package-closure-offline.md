# Exact headless package closure — offline

Date: 2026-08-08

Result: **PASS — the active minimal SSH root has one exact 152-package
dependency closure, and future staging rejects every package drift.**

## Defect

The root verifier rejected a short list of desktop, browser, GPU, radio, and
agent packages. That did not prove the complete installed package set: an
unlisted GUI or workload dependency could enter under another package name
while the denylist remained green.

## Accepted closure

`packaging/arch/headless-package-closure.txt` is the byte-exact sorted
`pacman -Q` record from both retained active-root layers:

- key-bound source archive: 536,750,378 bytes, SHA-256
  `2abe8c533179da598c37939ff8ebb4667a243bd8140c2d497237e41fbea72e6a`;
- sealed network root: 536,747,283 bytes, SHA-256
  `60fed48c8714a3f3b2082f95a04e913f32dfc74ed4c262e5b3d6e924a39a9c3b`;
- package rows: 152;
- closure SHA-256:
  `135862912935df91bb3305302e959498f9d5cf240a0ee74283abbf0bfa251f8b`.

The requested package list remains only `attr`, `diffutils`, and `openssh`.
The remaining rows are the immutable base/dependency closure, not additional
requested workloads.

## Enforcement

The staged-root verifier now compares the tracked closure against both the
sealed `/etc/rog5/packages.txt` record and a newly collected, byte-sorted
`pacman -Q` result. The generic shell validator rejects linked, unreadable,
empty, malformed, duplicate, unsorted, count-mismatched, or byte-different
inventories before the staged root can pass.

The four-case hostile suite covers twelve concrete mutations: package add,
remove, version change, reorder, duplicate, blank row, comment, extra field,
invalid package name, CRLF, linked expected input, and linked actual input.
It failed before implementation in 0.074 seconds and passed afterward in
0.172 seconds. The final focused set, including both existing headless source
contracts and the repository-runner contract, passed in 0.360 seconds.

## Boundary

This strengthens release identity without changing the accepted source root,
sealed network root, candidate, kernel, DTB, initramfs, or runtime behavior.
No root rebuild, credential, network service, phone access, signing, or boot
occurred.
