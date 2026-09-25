# Audio debug modules (not in the production kernel)

Out-of-tree replacements used in the 2026-09-25 RAM trials. Build each one
against the r17 object tree:

    make -C ~/.local/state/rog5-kernel-7.2.7-build-r17/objects M=<dir> ARCH=arm64 LLVM=1 modules

Then swap the `.ko` into a copy of the module package.

- `apr-debug.c` (r4 variant): upstream `drivers/soc/qcom/apr.c` with an
  `apr_send_pkt` hex dump. It also rewrites `ASM_DATA_CMD_WRITE_V2` to
  `buf_size` 0. Earlier variants withheld RUN (r58) or WRITE (r64), or only
  dumped packets (r54).
- `q6asm-dai-run-before-write.patch`: queue playback periods only after
  `ASM_SESSION_CMD_RUN`, as the vendor stack does (r65). Correct, but not
  sufficient on its own.

Results are in `test-results/2026-09-24-power-idle-ddr.md`.
