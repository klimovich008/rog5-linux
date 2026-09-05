# ARM64 systemd QEMU runtime

`runtime.cpio.gz` is a CI-only, credential-free runtime closure for proving
that the early-target diagnostic units execute under a real ARM64 systemd PID
1. It is not a phone image, server root filesystem, recovery payload, or
boot-authorized artifact.

The archive contains systemd 260.2 PID 1 and service executor binaries,
OpenSSH 10.3 client/server/session/auth executables, their recursive
`DT_NEEDED` ELF closure, the `libmount` runtime dependency required by
systemd's mount-option parser, package license text, and a provenance/file-hash
manifest. It contains no `/etc`, users, SSH identity material, private keys,
package database, phone data, kernel, DTB, modules, or boot tooling. Every test
host/client key is created in the runner's temporary directory and destroyed
on exit. The source is the accepted local Arch root archive whose size and
SHA-256 are sealed by the builder.

Rebuild and verify from the repository root:

```sh
mkdir -p /absolute/output/directory
scripts/host/build-qemu-systemd-runtime.sh \
  artifacts/arch/rog5-arch-headless-ssh-v2-network-root-7.1.4/root.tar.gz \
  /absolute/output/directory/runtime.cpio.gz
scripts/host/verify-qemu-systemd-runtime.sh \
  /absolute/output/directory/runtime.cpio.gz
cmp artifacts/qemu-systemd-arm64-v1/runtime.cpio.gz \
  /absolute/output/directory/runtime.cpio.gz
```

The accepted source archive is intentionally not published by Git. The small
derived closure is tracked so GitHub can run the systemd gate without access to
the key-bound deployment root or a mutable package mirror. Its provenance
records exact Arch package versions. Upstream source and license information is
available from the [systemd](https://github.com/systemd/systemd),
[glibc](https://sourceware.org/glibc/),
[OpenSSL](https://github.com/openssl/openssl),
[OpenSSH](https://github.com/openssh/openssh-portable),
[MIT Kerberos](https://github.com/krb5/krb5),
[Brotli](https://github.com/google/brotli),
[zlib](https://github.com/madler/zlib), and
[Zstandard](https://github.com/facebook/zstd) projects; the applicable bundled
license texts are retained inside the runtime archive.
