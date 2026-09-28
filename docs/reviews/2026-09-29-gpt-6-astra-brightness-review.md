**The evidence establishes coarse brightness, but does not establish that the last byte disappears on the wire.** I found no brightness-packet construction bug in the supplied source. I did find flaws in the proposed diagnostics, including an invalid interpretation of `0x45`, and evidence that weakens the leading clock hypothesis.

No files were modified and no phone access was performed. Kernel references below use the supplied r71 source; r125’s changes are assessed from 0074/0075.

The strongest corrections to the earlier analysis are:

- **E1’s TE-line readback is invalid.** `0x44` sets the tearing scanline; `0x45` reads the current scanline. `09 00`, `09 80`, or another value cannot establish whether `44 09 80` arrived intact. The older trial actually records that scanline advances. See [mipi_display.h:126](/home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source/include/video/mipi_display.h:126) and [trial:136](/home/deck/.local/state/rog5-prod-boot-20260923/test-results/2026-09-23-production-display-gpu-trial.md:136).
- **“HS does not work” is too broad.** HS short `34` and `51 03` worked. Continuous clock was already tried and did not restore HS long writes. This points toward packet shape, length, or handling, and demotes a simple missing-clock explanation. See [trial:139](/home/deck/.local/state/rog5-prod-boot-20260923/test-results/2026-09-23-production-display-gpu-trial.md:139).
- **A successful unrelated read does not validate brightness readback.** Working `0x0A` establishes some return-path functionality. It does not establish that `0x52` is supported, returns two bytes, or reports the applied brightness register rather than a shadow. Conversely, unchanged `03 00` would not distinguish transmission loss from DDIC write masking.
- **“Full” needs a better measurement.** The original measurement used a 500 mA input limit, which can conceal differences at high brightness. Thus `51 FF = full` versus `51 03 FF = 768` deserves controlled comparison before using it to infer different decoding rules. See [trial:127](/home/deck/.local/state/rog5-prod-boot-20260923/test-results/2026-09-23-production-display-gpu-trial.md:127).

The packet-construction audit substantially lowers the probability of a straightforward software off-by-one.

`mipi_dsi_dcs_set_display_brightness_large()` builds `{hh,ll}`. `mipi_dsi_dcs_write()` prepends `51`, and `_write_buffer()` selects DCS long write because the resulting length is three. There is no duplicated command or omitted parameter. Using `_buffer(dsi, {51,hh,ll}, 3)` would produce the same message. See [drm_mipi_dsi.c:1501](/home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/gpu/drm/drm_mipi_dsi.c:1501), [1046](/home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/gpu/drm/drm_mipi_dsi.c:1046), and [923](/home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/gpu/drm/drm_mipi_dsi.c:923).

For channel zero, the MSM command buffer is:

```text
03 00 39 C0 | 51 hh ll FF
WC=3          payload  alignment fill
```

Its DMA length is eight bytes. `C0` means long packet plus last packet in **MSM’s memory format**; it is not the transmitted ECC. The final `FF` is outside WC. Stock uses the same rounding and alignment fill. See [mainline dsi_host.c:1331](/home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/gpu/drm/msm/dsi/dsi_host.c:1331) and [stock dsi_ctrl.c:1112](/home/deck/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dsi/dsi_ctrl.c:1112).

This gives two useful deductions:

- Losing the final **DMA-buffer** byte would lose alignment fill, not `ll`.
- The previously hazardous four-byte DCS write also fits an eight-byte DMA buffer. Its hang does not demonstrate a DMA-length boundary crossing; WC and packet contents changed.

Likewise, the last-packet bit is not suspicious by itself. Stock explicitly sets it when submitting a final command, and its brightness descriptor is a single final command. Mainline’s one-message-per-transfer behavior is consistent with that. See [stock dsi_ctrl.c:1686](/home/deck/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dsi/dsi_ctrl.c:1686) and [dsi_iris6_pq.c:2439](/home/deck/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dsi/iris/dsi_iris6_pq.c:2439).

LP handling also looks internally consistent: the helper converts device LPM mode into `MIPI_DSI_MSG_USE_LPM`; the host defaults command DMA to LP, temporarily selects HS when requested, then restores LP. The internal maximum-return-size message’s missing LPM flag is **not independently evidence of an HS transfer**: it goes directly through the already-prepared transaction. See [helper:448](/home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/gpu/drm/drm_mipi_dsi.c:448), [host:873](/home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/gpu/drm/msm/dsi/dsi_host.c:873), and [host:2166](/home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/gpu/drm/msm/dsi/dsi_host.c:2166).

A literal physical truncation also needs an explanation for packet integrity: long packets contain WC, payload, and checksum. Removing `ll` does not automatically turn the remainder into a valid one-parameter command. Partial register updates remain possible, but are an additional DDIC-behavior hypothesis. [Espressif’s DSI protocol documentation](https://github.com/espressif/esp-iot-solution/blob/master/docs/en/display/lcd/mipi_dsi_lcd.rst) describes that packet structure.

**Below 256 being black follows directly from removing 0045’s workaround.** Production maps every nonzero request to `0100`, `0200`, or `0300`; 0075 instead sends the requested value, with only the 1→2 and 9→10 substitutions. Consequently, requests below 256 now send `51 00 ll`. See [panel driver:418](/home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/gpu/drm/panel/panel-asus-rog5-ams678.c:418) and [0075:53](/home/deck/.local/state/rog5-prod-boot-20260923/patches/linux-7.2.7/0075-drm-panel-asus-rog5-ams678-send-the-full-10-bit-DBV.patch:53).

That supports the empirical relation:

```text
applied brightness ≈ F(hh & 3), with little or no observed dependence on ll
```

It does **not** establish where `ll` stops mattering. It might be lost, rejected, masked, retained from an earlier value, or stored without affecting emission. It strongly disfavors ordinary little-endian interpretation: `00 FF` would then represent a large value rather than darkness. Stock’s “inverted DBV” is a byte swap, not bitwise inversion; the stock caller and Iris builder together produce the same `hh ll` order. See [stock dsi_panel.c:696](/home/deck/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dsi/dsi_panel.c:696) and [Iris builder:2455](/home/deck/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dsi/iris/dsi_iris6_pq.c:2455).

My ranking for the original/raw-write behavior is below. The first two remain close; neither is demonstrated.

| Rank | Hypothesis and evidence | What would falsify or substantially weaken it |
|---|---|---|
| **1** | **DDIC interpretation or latching depends on packet shape/state.** Deterministic dependence on `hh`, plus different short/long and LP/HS behavior, fits selective acceptance better than an assumed universal missing tail. A short write may update a different subset of the register or use different precision semantics. | Verified complete long writes producing normal fine luminance in the same state; or packet capture demonstrating that the low byte never reaches the DDIC. |
| **2** | **A fault in the direct long-command path: host timing/packet emission or Iris ABYP electrical/state behavior.** HS shorts working while HS longs fail supports this class. Correct source buffers do not prove correct electrical transmission. | Trustworthy, stimulus-dependent `0x52` readback containing both written bytes substantially weakens loss-before-register hypotheses. A post-Iris capture would localize it decisively. |
| **3** | **DDIC initialization/control state suppresses fine brightness.** Possible, but specific claims about lower-byte protection need evidence. Mainline already sends stock’s `53 20`, and stock labels `53 20`/`53 28` as one-frame/20-frame dimming. Ordinary stock brightness updates do not wrap `0x51` in an unlock sequence. | Correct control readback and normal behavior after a demonstrably equivalent initialization weaken this. `0x54=20` alone cannot exclude hidden vendor state. |
| **4** | **Measurement, software mapping, or another writer obscures the experiment.** Certain for production sysfs quantization; possible contamination of raw tests. The retained snapshot has automatic brightness and idle dimming enabled. | Serialized direct packets, stable display state, and exclusion of intervening brightness writes reproduce the same coarse result. |
| **5** | **Simple endian/bit-inversion, WC/rounding/last-bit bug, or globally absent HS clock.** Source formation is correct; stock byte order agrees; continuous clock already failed; HS shorts worked. | These are already weakened. Reopen them only with an actual differing descriptor/register state or transmitted packet. |

For rank 3, the relevant controls are [mainline panel:320](/home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/gpu/drm/panel/panel-asus-rog5-ams678.c:320) and [stock dimming definitions:1080](/home/deck/.local/state/rog5-kernel-compare-20260927/stock/arch/arm64/boot/dts/vendor/qcom/dsi-panel-ams678-er2-fhd-plus-dsc-cmd.dtsi:1080). Both `20` and `28` enable BCTRL; their difference is not evidence of a DBV precision selector. I would not add a generic LCD “backlight-on” bit to this OLED’s stock value.

There **is** a concrete initialization mismatch worth retaining: stock explicitly sends `EC 19` and `E4 10` as DCS **long** packets with WC=2. The generated driver’s sequence helper selects **short** packets for those same two-byte buffers. Stock labels that block ERR-FG configuration, so this is not yet a brightness explanation. See [stock panel commands:909](/home/deck/.local/state/rog5-kernel-compare-20260927/stock/arch/arm64/boot/dts/vendor/qcom/dsi-panel-ams678-er2-fhd-plus-dsc-cmd.dtsi:909) versus [mainline panel:130](/home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/gpu/drm/panel/panel-asus-rog5-ams678.c:130).

For Iris specifically, the source supports a narrower conclusion than either earlier account:

- `iris_abyp_send_panel_cmd()` forwards the original command set to the host, without brightness-specific rewriting or software length restriction. Stock uses it for the long initialization sequence. See [ABYP forwarding:1127](/home/deck/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dsi/iris/dsi_iris6_lightup_ocp.c:1127) and [lightup:3125](/home/deck/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dsi/iris/dsi_iris6_lightup.c:3125).
- The documented 120/124-byte splitting concerns **PT OCP encapsulation**, not an ABYP three-byte limit. See [PT splitting:415](/home/deck/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dsi/iris/dsi_iris6_lightup_ocp.c:415).
- GRCP exit support shows that Iris control circuitry can remain reachable in bypass. It does not prove that Iris intercepts or answers standard `0x51/0x52/0x53/0x54`. I found no such ABYP filter in the inspected code. See [GRCP:498](/home/deck/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dsi/iris/dsi_iris6_lp.c:498).

Thus ABYP’s exact hardware transparency remains unverified; firmware/source behavior alone cannot certify it.

**The most informative allowed experiment is one controlled packet-shape and history comparison**, rather than another slider sweep. This is a proposal only.

Use a fixed moderate white patch on black, stable screen state, and one serialized writer. Let each brightness settle for about half a second. Record raw read return lengths and bytes alongside observed luminance.

1. Establish LP read controls with `0x0A`, repeated `0x45`, and `0x54`. Treat unsupported/error/short responses explicitly. Read `0x52` as two bytes, but do not presume it is valid merely because the others work.
2. Compare LP short writes `51 01`, `51 55`, `51 A9`. All have the same low two parameter bits; an eight-bit interpretation predicts substantially different levels, whereas “only parameter bits 1:0 matter” predicts equal levels.
3. After each of the distinct short seeds `51 55` and `51 A9`, independently test LP long `51 01 00` and `51 01 FF`, reading `0x52` after every write. Re-seed before each long write. This tests both low-byte sensitivity and retained state.
4. Compare LP `51 00 FF` against `51 01 00` to reproduce the boundary.
5. From a known LP `51 02 00` baseline, compare HS short `51 01` and HS long `51 01 FF`, restoring the baseline before each. Read back through LP so the write-mode comparison does not also change the return path.

Finish by restoring the previously known brightness through an allowed packet.

| Hypothesis | Predicted distinguishing result |
|---|---|
| DDIC receives both bytes but suppresses fine output | `0x52` tracks `0100` versus `01FF`, while luminance stays equal. This requires credible readback provenance. |
| Low byte is not accepted, or is lost | Both long writes give the same applied/read value; changing short seeds may reveal retention rather than zeroing. This cannot by itself locate the loss. |
| Short packet selects different precision semantics | `01`, `55`, and `A9` differ despite identical low two bits. This falsifies the earlier universal “one parameter means DBV[9:8]” assumption. |
| Whole long packet is rejected | The prior seed remains effective after the long write, rather than a reproducible `hh`-selected level being applied. |
| HS long path specifically fails | HS short changes the baseline; HS long leaves it unchanged. Successful HS reads would not contradict this. |
| Software overwrite/measurement artifact | Isolated writes reveal fine changes, or readback/luminance changes later without another test write. |
| Swapped-byte interpretation | Boundary and within-block changes follow `ll`; `00FF` does not behave like zero. |

If `0x52` remains uninformative, this experiment still tests short-write semantics, whole-packet rejection, and history dependence. **No experiment restricted to these endpoint operations can guarantee separation of host loss, Iris loss, and DDIC write masking.**

The lab module is useful in concept, but I would correct it before treating results as decisive:

- Its normal `bl` calls construct the intended packets and cannot emit a padded brightness payload.
- It changes shared `dsi->mode_flags` under only `lab_lock`. The panel uses another lock. A panel write can therefore acquire the wrong mode, or a save/restore can overwrite another change. The host mutex serializes transfers after message construction; it does not fix this race. See [lab:70](/tmp/claude-1000/-home-deck-Projects-rog-phone-linux-migration/2cc1c994-1a4f-4a0b-aca7-41804577680f/scratchpad/brightness-investigation/rog5_dsi_lab/rog5_dsi_lab.c:70) and [host:1775](/home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/gpu/drm/msm/dsi/dsi_host.c:1775).
- `b1` is uninitialized on the short-write path but is evaluated at `payload[1] = b1`. Initialize it and assign it only for two-parameter writes. Parsing also accepts trailing tokens and mode prefixes; use exact token validation. See [lab:119](/tmp/claude-1000/-home-deck-Projects-rog-phone-linux-migration/2cc1c994-1a4f-4a0b-aca7-41804577680f/scratchpad/brightness-investigation/rog5_dsi_lab/rog5_dsi_lab.c:119).
- Reads must require the expected returned length. A zero-byte return is not `00 00`. The existing lab prints the length, which is helpful.
- The register-dump path ignores runtime-PM errors; its GPIO writer bypasses driver ownership. Neither belongs in this experiment.
- The web lab’s displayed `51 hh ll` is calculated from the requested sysfs value, not observed transmission. It is wrong under 0045 and for 0075’s substitutions. See [web lab:117](/home/deck/.local/state/rog5-prod-boot-20260923/scripts/host/rog5-brightness-lab.py:117).

**I found no justified minimal brightness fix.** The concrete corrections I would make are:

1. **Lab:** construct explicit `mipi_dsi_msg` objects with per-message LP flags, avoiding mutation of `dsi->mode_flags`; coordinate the experiment with panel lifecycle/brightness locking. Fix parsing and `b1` initialization.
2. **MSM read-path bug:** for short responses, `dsi_cmd_dma_rx()` initializes only four bytes of local `reg[16]`, then copies all sixteen. Limit the copy to `cnt * sizeof(u32)` initialized bytes. Normal short-response decoding uses only the valid first bytes, so this does not explain coarse brightness; unexpected response forms need explicit rejection rather than decoding unread data. See [dsi_host.c:1482](/home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/gpu/drm/msm/dsi/dsi_host.c:1482).
3. **Stock-init fidelity:** preserve explicit long-packet type for `EC 19` and `E4 10`, with their existing payload lengths. That is a separate fidelity correction, not a demonstrated brightness repair.