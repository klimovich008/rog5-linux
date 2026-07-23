# Linux 7.1.4 clean-build reproducibility - 2026-07-23

Status: **PASS** for the credential-free Linux 7.1.4 kernel/DTB/module core
after v8 and v10 exposed two independent reproducibility faults. This is not a
complete recovery bundle or a boot candidate.

## Inputs

- Linux source commit:
  `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`
- Builder image:
  `sha256:e0a20f4bca9fad3a218f034ce79083f5dcaa02355db4e7bb81672e0df41d4359`
- Config fragment SHA-256:
  `9ace4a115c08c541b26d8dbf553ba4efc18024f79cb4e306b096c17c5bd27ab2`
- Network access: disabled
- Source and repository mounts: read-only
- Output: two independently created empty Docker volumes

## v8 result

Both builds passed the mainline verifier independently. The final
configuration and every upstream/ASUS/recovery DTB were byte-identical:

- `.config`:
  `378d158257ecb0f88e5d47393b859e6800b67b656f230a3ba4a445fd9362a0da`
- ASUS skeleton DTB:
  `e1b7ec966d5ad66febaeb10e7bbff0d92b7e83ab4159d9727e5a175b719bedeb`
- USB2-only recovery DTB:
  `255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6`

The kernel and modules did not reproduce:

| Product | v8a SHA-256 | v8b SHA-256 |
|---|---|---|
| `Image` | `40e2c66bdadc3ecfd42c42efee0cab26e03f1e821154197efd729c69a86b9bca` | `bb0a471493a9f57beafda14333ff9477c872b30beb340844cf78e64725465ca0` |
| `Image.gz` | `6d133fcf95b5fb5c3da0b07884b227b6ab119baca41e3ebbd7103cb8295ff4a6` | `10f7d74827a04036ddcedaec7c4821b4a6e24feb73622041a3a697b78e8026ec` |
| modules archive | `4286d2b46e570d5dca2d07e21a203b8cdaec72514661245748577d34ef355158` | `aa8131db4556a1e76d1a77e075564cc46ddb5bb398ff88b875c68bbcf6a0217c` |

No v8 product is a boot candidate.

## Root causes

Linux 7.1.4 `drivers/gpu/drm/msm/registers/gen_header.py` stores GPU register
variants in a Python `set` and iterates it without sorting. Python's randomized
default hash seed therefore changed the order of the generated
`drivers/gpu/drm/msm/generated/a6xx.xml.h`.

Different explicit hash seeds reproduced the two v8 header hashes exactly.
Only five Adreno objects differed among 7,292 inspected objects, and their
non-debug content matched. The generated-header checksum changed DWARF line
data, which then changed the embedded BTF section by 23 bytes, the ELF build
ID, `Image`, and base BTF IDs in the installed modules. Kernel version,
timestamp, source revision, compiler, config, image size, generated version
headers, archive timestamps, and gzip metadata matched.

Two speculative runs that serialized only `pahole` were stopped before
completion once the generator-level cause was proved; none of their outputs is
accepted or staged.

Fresh v10 builds then pinned the Python hash seed and produced byte-identical
generated headers:

- `a6xx.xml.h`:
  `55ae3dc006f26629ad0b5de50144edb6f37d9fb5b58957c248041cbf2a8e19b8`

Their final BTF sections still differed by 35 bytes. That changed resolved BTF
IDs, ELF build IDs, `Image`, and module BTF even though source, generated GPU
header, config, timestamps, and non-debug object content matched. Linux 7.1
derives `pahole`'s parallel job count from top-level make flags; `pahole` 1.25
did not emit stable BTF ordering across the 8-job and 7-job builds.

| Product | v10a SHA-256 | v10b SHA-256 |
|---|---|---|
| `Image` | `a24eb6d525b396079114f661559676a6c4571ffbbd2bdc59c5fb0f9f2a3ec059` | `2490ee45d35467f7e7601e1ef35753b86051701003bcee7704b04e41992fe721` |
| modules archive | `a5d52fea944a7bedf0ed438afb2c9ba91fc02f3842ac9f988fe6fc0620114b75` | `4af223951c515cb94225bf11290f49eccd30cf83eb9d0d2ccba04f4312576bff` |

No v10 product is a boot candidate.

## Corrective gate

`build-mainline.sh` now exports `PYTHONHASHSEED=0` before the first make.
It also passes `JOBS=1` as a Kbuild command-line variable, which serializes
only `pahole` while normal compilation retains the requested parallel job
count. Build metadata records both controls, and the verifier rejects metadata
without them. This preserves the pristine pinned upstream source. The verifier
also checks the uncompressed `Image` against the hash-checked compressed image.

## v11 result

Two fresh offline builds used the same pinned inputs but different normal
compile scheduling (`-j8` and `-j7`). Both passed the mainline verifier and
ASUS DTB gates independently. `compare-mainline-builds.sh` then confirmed
byte-identical final configuration, generated GPU header, raw/compressed
kernel, deterministic modules archive, build metadata, five upstream
comparison DTBs, ASUS skeleton, and USB2-only recovery DTB.

| Product | Size | SHA-256 |
|---|---:|---|
| `.config` | 242,168 | `378d158257ecb0f88e5d47393b859e6800b67b656f230a3ba4a445fd9362a0da` |
| `a6xx.xml.h` | 586,233 | `55ae3dc006f26629ad0b5de50144edb6f37d9fb5b58957c248041cbf2a8e19b8` |
| `Image` | 38,406,656 | `4d6f3ecaa8d2af0b1e1fddd0655af469e867d596f8f3eae0a20583b058fbe697` |
| `Image.gz` | 14,316,874 | `e58794d71d49966d5524df7ed9996b749d2fd422447a34b4f429a01d0ed6f0b7` |
| modules archive | 303,171,236 | `4c6670fff534366601ff521a60ca448e8f2dcd25b92a04b70b0d7ecc6ffedd0a` |
| build metadata | 1,324 | `f6e461e4b1c5e11f9dfcdd9f46a397ee2f85ea70dc47c4219cb41d9fa8e4fabf` |
| ASUS skeleton DTB | 102,719 | `e1b7ec966d5ad66febaeb10e7bbff0d92b7e83ab4159d9727e5a175b719bedeb` |
| USB2 recovery DTB | 102,774 | `255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6` |

These v11 products may supply the kernel, modules, and DTBs for the next
recovery/rootfs rebuild. The target/staging initramfs, ASUS 5.4 wrapper, boot
image, and nine-file release manifest still require a complete rebuild and
verification. No v11 product has been booted or written to the phone.
