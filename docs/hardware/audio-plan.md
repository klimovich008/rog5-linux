# Audio plan (milestone 7)

Research only (2026-09-24); nothing has run. Sources: the ASUS 5.4 tree in the
migration archive (`kernel-src/msm-5.4`), the 7.2.7 kernel source and the
production config.

## Hardware (ASUS stock DT, `ZS673KS-EVB-overlay.dts:1271-1604`)

The usual Qualcomm path is **off** on the ROG5: `wcd938x_codec`,
`wsa883x_0221/0222`, SoundWire `swr0/1/2` are disabled and the sound card sets
`qcom,wcd-disabled`. Audio uses external chips over MI2S and I2C:

| Part | Bus / address | Pins, supplies | DAI |
|---|---|---|---|
| Cirrus CS35L45 "RCV" (earpiece) | QUP SE17 I2C (`i2c17@88c000`) 0x30 | reset GPIO104, IRQ GPIO90, S10B 1.8 V | SENARY_MI2S (SoC master), RX mask 2 / TX mask 1, LPI GPIO10–13 |
| Cirrus CS35L45 "SPK" | same bus, 0x31 | reset GPIO105, IRQ GPIO2 | same |
| ESS ES928x headset DAC | same bus, 0x49 | reset GPIO88, 3.3 V en GPIO124, 1.8 V en pm8350b GPIO5 | PRI_MI2S_RX / QUAT_MI2S_TX (codec master), TLMM 125/126/128; ASUS jack detection |
| Digital mics 0–5 | LPASS TX/VA macros | VA MIC BIAS1, `va-vdd-micb` = L2C | — |

Stock DSP interface: APR/Elite (q6afe/q6asm/q6adm), not AudioReach.
The stock machine driver also votes the SMB1399 charge pump out of LCM during
audio (`lahaina.c:4252-4275`).

## Upstream 7.2.7

- `sm8350.dtsi` has the ADSP, APR (q6core/q6afe/q6asm/q6adm) and `lpass_tlmm`,
  but no LPASS RX/TX/VA/WSA macro or SoundWire nodes; no macro driver lists
  sm8350; no upstream sm8350 board has a sound card.
- `sound/soc/qcom/sm8250.c` has no sm8350 compatible and no SENARY MI2S clock
  setup.
- CS35L45 has a mainline driver (DSP-less ASP_RX→DAC works, without speaker
  protection); `CONFIG_SND_SOC_CS35L45_I2C` is **not set** in the build.
- ES928x has no mainline driver.
- The production boot already starts the ADSP (`adsp.mdt` from the stock
  modem partition); the audio protection domain is untested.

## First steps, in order

1. Capture one digital microphone: TX/VA macro DT nodes (sm8250 layout,
   checked registers), sm8350 compatibles in the macro drivers, a sound card.
   No amplifier powered, so no speaker risk.
2. Earpiece CS35L45 (0x30) playback: enable `i2c17`, the amp node, an s10b
   1.8 V regulator and a VPH supply, the q6afe SENARY_MI2S_RX DAI, LPI I2S
   pinctrl GPIO10–13, a machine compatible with a SENARY clock patch to
   sm8250.c, `CONFIG_SND_SOC_CS35L45_I2C=m`. Short, quiet tones only.
3. Speaker amp (0x31) with the stock CS35L45 tuning (`cs35l45-{spk,rcv}-*`
   from the vendor partition, mapped to mainline's `cs35l45` part name).
4. Headset: a new ES928x driver plus ASUS jack detection.

## Risks

No DSP speaker protection or thermal limit without the stock tuning; the stock
boost-current/LDPM settings may be unsupported; a wrong q6afe clock or port can
crash the ADSP, which battery telemetry depends on; LPI GPIO10/11 are shared
with the (disabled) WSA SoundWire pins. Unknown: which DMIC is which mic, which
physical speaker "RCV" drives.

## Speaker protection firmware (2026-10-01, pending bring-up)

Stock loudness comes from the CS35L45 CSPL tuning, not from gain registers
(both paths run 0 dB digital, 19 dBV analog). Pieces:
- kernel 0121: firmware named by DT `cirrus,dsp-part-name`
  (`cirrus/cs35l45-{rcv,spk}-dsp1-spk-{prot,cali}.{wmfw,bin}`); 0122: the
  vendor BOOST_LPMODE/BPE IL limit/LDPM/pilot/BBPE settings only while the
  protection firmware runs (`snd_soc_cs35l45.vendor_prot_regs=0` turns it off
  at the next DSP start); 0123 (cs_dsp: coefficient write errors fail the
  load, pre_load_coeff hook) + 0124: calibration controls read-only,
  CAL_STATUS cleared before the .bin loads, and the core does not start
  unless DSP memory holds CAL_R 7728-10454, CAL_STATUS 1, CAL_CHECKSUM CAL_R + 1;
- audio DT: `cirrus,dsp-part-name`, GPIO1 = MDSYNC as on stock;
- `scripts/device/install-rog5-speaker-firmware`: copies the firmware from the
  phone's own vendor_a (SHA-256 checked) and the factory CAL_R from
  persist:/audio/{rcv,spk}_cal_val, appends CAL_R/CAL_STATUS/CAL_CHECKSUM to the
  installed prot `.bin` (the kernel writes them before the core starts), writes
  `/var/lib/rog5/speaker/` and `/etc/rog5/speaker-dsp.conf` (`amps=`: off);
- `initramfs/production-audio-route`: per enabled amplifier sets DSP_RX1/2 and
  DSP_RX5/6/7 (VDD_BATTMON/VDD_BSTMON/CLASSH_TGT), preloads, checks the
  calibration read-back and CSPL_STATE/ERRORNO, optional stock "music" delta,
  then DACPCM = DSP_TX1; direct path on any failure. `89-rog5-alsa-state.rules`
  keeps `alsactl restore` away from the DSP controls.
Blobs and calibration stay on the phone; none of them is in the repository.
