# Hardware video decode/encode (Iris v2 on SM8350)

Status 2026-10-02 (k120 preparation): k117 F1 passed H.264/HEVC 300/300,
compliance 48/48 and idle, but removal still hard-hung after `mark: remove`.
F2r still rejected stock-sized VP9 references (0x1003); F3 is unrun. Host-only
successor patches 0172-0178 add removal instrumentation and isolated opt-in
experiments. [Stock comparison/review](../reviews/2026-10-02-video-iris-k120.md),
[host results](../../test-results/2026-10-02-video-iris-k120-host.md),
[k120 trials](#k120-trials). No successor phone result is claimed.

Status 2026-10-02 (k117): k116 is the installed default (H.264/HEVC decode
bit-exact, compliance 48/48; [k116 trials](../../test-results/2026-10-02-video-iris-k116-ram-trials.md)).
Its trials left VP9 with every reference buffer rejected and a phone reset
on a module reload; kernel k117 (0169-0171) addresses both and prepares the
staged encoder boot: [k117 trials](#k117-trials). Earlier:

Status 2026-10-02 (k116): k115's trials found the cause of the decode-end
crash (the dummy EOS address) and made H.264 and HEVC decode work
bit-exactly ([test-results/2026-10-02-video-iris-k115-ram-trials.md](../../test-results/2026-10-02-video-iris-k115-ram-trials.md));
kernel k116 makes that the SM8350 default and keeps VP9 and the encoder
behind load-time switches: [k116 trials](#k116-trials). Earlier:

Status 2026-10-02: the k114/d15 RAM trial (2026-10-01,
[test-results/2026-10-01-video-iris-k114-ram-trial.md](../../test-results/2026-10-01-video-iris-k114-ram-trial.md))
authenticated the OEM firmware and decoded H.264 bit-exactly, then hit a
firmware fatal error at the end of every decode session; the driver's
reload made it worse. Kernel k115 (patches 0157-0162, same firmware, DT d15
and platform values) adds diagnostics and contains the error; its bundle is
built, **not installed**. Trial sequence: [k115 trial](#k115-trial).

## The hardware

The SM8350 video block is a Qualcomm **Iris2** core ("VPU 2.0", the
generation of SM8250, 4 VPP pipes) driven by HFI gen1 firmware. Everything
below agrees between the three sources: the stock ASUS runtime FDT
(`~/.local/state/rog5-production-boot-20260923/trial-stockcap-c1-session/stock-fdt.dts`,
`qcom,vidc@aa00000` at line 23345, `qcom,venus@aab0000` at line 12748), the
ASUS lahaina sources (`~/Projects/rog-phone-linux-migration/kernel-src/msm-5.4`:
`arch/arm64/boot/dts/vendor/qcom/lahaina-vidc.dtsi`, `lahaina.dtsi:4586-4610`,
`drivers/clk/qcom/videocc-lahaina.c`, `techpack/video/msm/vidc/msm_vidc_platform.c`)
and the upstream node (`sm8350.dtsi` in v7.3).

| Item | Value |
|---|---|
| Registers, IRQ | 0x0aa00000 (1 MiB), GIC SPI 174 level-high |
| Clocks | `GCC_VIDEO_AXI0_CLK` (iface), `VIDEO_CC_MVS0C_CLK` (core/controller), `VIDEO_CC_MVS0_CLK` (vcodec0) |
| Power | GDSCs `MVS0C` (controller) and `MVS0` (core, HW-controlled), rails MMCX (video clocks) and MX (video PLLs) |
| Reset | `GCC_VIDEO_AXI0_CLK_ARES` (stock `video_axi_reset`); upstream also `VIDEO_CC_MVS0C_CLK_ARES` |
| Core clock | 240 / 338 / 366 / 444 MHz = MVS0 RCG 720 / 1014 / 1098 / 1332 MHz / 3 (stock `qcom,allowed-clock-rates`); MMCX low_svs / svs / svs_l1 / nom (`videocc-lahaina.c:221-229`), PLL0 on MX svs / svs / svs_l1 / svs_l1 (`:78-86`) |
| Interconnects | cpu-cfg `APPSS_PROC -> SLAVE_VENUS_CFG`, video-mem `MASTER_VIDEO_P0 -> EBI1`; stock also votes `VIDEO_P0 -> LLCC` and uses the `vidsc0` LLCC slice |
| SMMU streams | non-secure `0x2100/0x400` (Linux); secure bitstream `0x2101/0x404`, pixel `0x2103/0x400`, non-pixel `0x2104/0x400` (VMIDs 9/10/11). Under the hypervisor those three already route to context banks 10, 9, 8; patch 0064 keeps the banks out of Linux's allocator (seen in every k113 boot log) |
| Firmware | PAS id 9 (`qcom,pas-id = <9>`), carve-out `pil_video_mem` 0x85700000 + 5 MiB (no-map; memslim keeps it), image `vpu20_4v` (`vidc,firmware-name`) |
| Content protection | `qcom_scm_mem_protect_video` with cp size 0x25800000 and non-pixel 0x01000000 + 0x24800000 (stock `__protect_cp_mem` derives them from the context-bank IOVA pools; the upstream iris VPU2 table has the same numbers) |

### Firmware

vendor_a `firmware/` holds `vpu20_1v`, `vpu20_2v` and `vpu20_4v` (`.mdt` +
`.b00-.b19` and a single `.mbn`; `_unsigned` copies of 1v/2v). The stock DT
asks for `vpu20_4v` (4 pipes = SM8350; 1v/2v are the 1- and 2-pipe
lahaina-family parts). Read-only inspection on 2026-10-01 (hash segment,
v6 MBN header):

| Image | Size | SHA-256 | Signing (sw_id, OEM ids, root cert SHA-256) |
|---|---|---|---|
| `vpu20_4v.mbn` | 2022804 | `16d8258c...e69d` | 0xe (video), 0x29/0x28, root `2c8bc18e...` |
| `vpu20_2v.mbn` | 2029364 | `4b8f3fd0...` | 0xe, 0/0, root `959b8d05...` |
| `vpu20_1v.mbn` | 2023572 | `934400ad...` | 0xe, 0/0, root `959b8d05...` |

`2c8bc18e` is the root of the ADSP image that TrustZone accepts on this phone
and of the vendor_a SLPI image that works; `959b8d05` is the generic QTI root
of the dsp-partition CDSP/SLPI images that TrustZone rejected with
`0x30001f` even under the stock kernel
([test-results/2026-09-24-power-idle-ddr.md](../../test-results/2026-09-24-power-idle-ddr.md),
"Stock ASUS 5.4 capture"). So vpu20_4v is both the right image and signed
the accepted way. Its ELF load span is 0x4ff020 bytes from 0xf500000,
relocatable, so it fits the 5 MiB carve-out. (Side note: vendor_a's
`cdsp.mdt` is OEM-signed with the accepted root too.)

`scripts/device/install-rog5-video-firmware` copies it (pinned SHA-256)
to `qcom/sm8350/vpu20_4v.mbn`; the blob never enters the repository.

## Upstream status

- Binding: `qcom,sm8250-venus.yaml` documents `"qcom,sm8350-iris",
  "qcom,sm8250-venus"` with the MX and MMCX power domains, already in v7.2
  (so in our 7.2.7 base).
- Driver: the iris driver binds the `qcom,sm8250-venus` fallback
  (`iris_platform_vpu2.c` `sm8250_data`: HFI gen1, decoder H.264/HEVC/VP9,
  encoder H.264/HEVC, OPP on MX + MMCX). With `CONFIG_VIDEO_QCOM_IRIS` the
  venus driver drops its sm8250 match, so only iris binds. No SM8350-specific
  driver code exists or is needed (Dmitry Baryshkov dropped the driver patches
  in v4 of the series for that reason).
- DT: "media: iris: enable SM8350 and SC8280XP support" v1-v6 (Dmitry
  Baryshkov, 2026-01 to 2026-05; v5:
  `20260512-iris-sc8280xp-v5-0-8cc251e83b58@oss.qualcomm.com`) added the
  `iris` and `videocc` nodes to `sm8350.dtsi`; they are in v7.3-rc5
  (`sm8350.dtsi:2756` and `:2822`), and `sm8350-hdk.dts` enables iris with
  `firmware-name = "qcom/vpu/vpu20_p4_sm8350.mbn"`, firmware "extracted from
  Android data" (not in linux-firmware). Tested on the SM8350 HDK with iris:
  v4l2-compliance 48/48; fluster H.264 154/447, HEVC 169/316, VP9 159/311
  with FFmpeg v4l2m2m; 10-bit (HEVC Main10) 0/11. Venus fails on SM8350 with
  a UC_REGION error. Reviewer bot (Sashiko) worried about MMCX scaling under
  the venus driver; irrelevant with iris, which attaches both OPP domains.
- Our d15 nodes are the upstream nodes byte for byte except `status` and the
  firmware path.

## How the stock (Android) stack does it

Sources: ASUS 5.4 `techpack/video/msm/vidc/*`, the stock runtime FDT and the
WW33 vendor_a partition (read-only on 2026-10-01).

- **Kernel driver** `msm_vidc` (techpack video, `msm_v4l2_vidc.c`), platform
  data `lahaina_data` (`msm_vidc_platform.c:2212`: `VPU_VERSION_IRIS2`, 4 VPP
  pipes, UBWC config). It registers V4L2 mem2mem decoder and encoder nodes
  (Android's `/dev/video32` and `/dev/video33`) and four context banks as
  child devices (`non_secure_cb`, `secure_non_pixel_cb`, `secure_bitstream_cb`,
  `secure_pixel_cb`; stockcap-c1 log: "Adding to iommu group 2..5").
- **Firmware load**: on the first session, `__load_fw()`
  (`hfi_common.c:3943-3990`) powers the core, then
  `subsystem_get_with_fwname("venus", "vpu20_4v")` asks the PIL node
  `qcom,venus@aab0000` (`qcom,pil-tz-generic`, PAS id 9, proxy votes on
  MVS0C GDSC, XO/core/AHB clocks at 200 MHz and `pil-venus` bandwidth) to
  load the split `vpu20_4v.mdt/.bNN` into `pil_video_mem` and authenticate it
  through TrustZone (`qcom_scm_pas_*`), then `__protect_cp_mem()`
  (`:3440`) sets the content-protection ranges, exactly the sequence the iris
  driver uses. HFI gen1 (`HFI_VIDEO_ARCH_OX`, `vidc_hfi_helper.h:23`), sys
  init at `hfi_common.c:1746`. `qcom,never-unload-fw` keeps it resident
  (`msm_vidc_platform.c:1164`); `qcom,sw-power-collapse` powers the core
  down between frames after 1.5 s idle.
- **Under our boot chain** the ASUS wrapper never starts it: the subsystem
  table shows `subsys10 name=venus state=OFFLINING`, all four video GDSCs
  `disabled` and msm_vidc probed but unused (stockcap-c1 `capture.txt:11`,
  `:125-128`, `:1187-1192`). The video PAS is therefore fresh when Linux
  loads it (no shutdown needed first).
- **Clocks and buses**: `qcom,allowed-clock-rates` 240/338/366/444 MHz chosen
  per load (`msm_vidc_clocks.c`), bus votes from the Iris2 bandwidth model
  (`msm_vidc_bus_iris2.c`) on venus-ddr and venus-llcc (1-15 GB/s), and the
  `vidsc0` LLCC slice for the core's reference frames.
- **Userspace**: Android `MediaCodec` -> the Codec2 HAL service
  `vendor.qti.media.c2@1.0-service` (vendor `bin/hw`, `etc/init/vendor.qti.media.c2@1.0-service.rc`)
  -> `libqcodec2_core/_basecodec/_v4l2codec` -> the V4L2 nodes of msm_vidc.
  The legacy OMX service (`android.hardware.media.omx@1.0-service`,
  `libOmxCore`) is still shipped; `init.qti.media.rc` picks the codec XML
  variant (`media_codecs_lahaina_vendor.xml` for this SKU vs. the 4K-capped
  `media_codecs_lahaina.xml`).
- **What it advertises** (`media_codecs_lahaina_vendor.xml`, kernel caps
  `lahaina_capabilities`, `msm_vidc_platform.c:432`):
  - decode H.264 and HEVC up to 8192x8192, 138240 MB/frame, 7.78 M MB/s
    (e.g. 1080p480, 2160p240, 4320p60), 220 / 160 Mbit/s; VP9 up to
    4096x4096 at 60 fps (kernel cap 4096x2304@60), 100 Mbit/s; MPEG-2 up to
    1080p30 (kernel only); 10-bit output as P010 / UBWC TP10
    (`msm_vdec.c:464-571`); secure (Widevine L1) decode up to 4K60 at
    40 Mbit/s with 3 instances; up to 16 sessions;
  - encode H.264 and HEVC up to 8192x4320 (24 fps), 4K120, 1080p480, 720p960,
    3.9 M MB/s, 220 / 160 Mbit/s, B-frames, 6 hier-P layers, LTR, intra
    refresh, HEVC CQ and HEIC (grid tiles); no VP9 encode, no secure encode.

### What mainline iris gives on top of that hardware

| | Stock msm_vidc | Mainline iris (sm8250 data, gen1) |
|---|---|---|
| Decode | H.264, HEVC, VP9, MPEG-2 | H.264, HEVC, VP9 (no MPEG-2) |
| Encode | H.264, HEVC, HEIC, CQ | H.264, HEVC |
| Max size | 8192x4320 (VP9 4096x2304) | 8192x8192 per frame, `max_core_mbps` 8K60 |
| 10-bit | yes (P010, TP10) | formats exist, gen1 path fails Main10 on SM8350 (0/11 upstream) |
| Secure playback | yes (CP banks, VMIDs) | no (only the non-secure bank; the content-protection SCM call is still made) |
| LLCC slice, bus model | vidsc0, Iris2 model | none; fixed bandwidth table, ICC max at power-on |
| Interface | V4L2 m2m + vendor extensions, Codec2 | stateful V4L2 m2m (FFmpeg `*_v4l2m2m`, GStreamer `v4l2*dec/enc`, mpv `v4l2m2m-copy`) |
| Output formats | NV12, UBWC NV12, P010, TP10 | NV12, QC08C (UBWC) |

## Our design

- **Kernel** (k114): `CONFIG_SM_VIDEOCC_8350=m` and `CONFIG_VIDEO_QCOM_IRIS=m`
  (`configs/kernel/rog5-video.fragment`, required in the build policy), and
  three patches:
  - 0154: when the firmware is loaded but never completes system init (no
    answer, an error answer, or a bad UC region), iris unloads it and powers
    the core off instead of leaving it powered in the error state; only the
    current attempt is torn down, with the IRQ quiesced outside the core
    lock (GPT-6.1-Sol found the deadlock and the stale-waiter race in the
    first version); firmware-load failures name the failing step and keep
    their error code; a successful TrustZone authentication is logged.
  - 0155: backport of the proposed binding change that allows the second
    `memory-region` (IOVA reservation).
  - 0156: diagnostic for the hypervisor: every translating S2CR route is read
    back on SM8350 and a dropped one is logged with its SMR and bank, at
    driver probe, before the video core is started.
- **DTB d15** = d13 + `dts/qcom/sm8350-asus-rog-phone5-video.dtso`, composed by
  `scripts/device/compose-video-dtb.sh` (base pinned to d13's SHA-256, so
  d13's own memslim check against d10 stays the reference; checks the
  carve-out and labels first, and afterwards that removing the three new
  nodes gives back d13 exactly). The third node is `/iris-iova`
  (`iommu-addresses = <&iris 0 0 0 0x25800000>`, no physical memory), the
  second `memory-region` of iris: IOVAs below 600 MiB are the content-protection
  ranges handed to TrustZone, and non-secure DMA there faults and can reboot
  the SoC (Vikash Garodia's 2026-08-07 series "media: iris: Restrict lower
  IOVA range for Venus and Iris", patch 08/22 for sm8350, proposed for
  stable, not merged yet; stock does the same with its `venus_ns` pool
  starting at 0x25800000). Upstream puts the node under `/reserved-memory`;
  d14 did the same and the slot-B loader's bundle verifier
  (`tools/recovery_control/rog5-bundle-verify.c:1468`, signed into boot_b)
  refused it ("reserved-memory child has no reg") when the first bundle was
  packaged, so d15 carries it as a root child: Linux only follows the
  `memory-region` phandle to `iommu-addresses` (`of_iommu_get_resv_regions()`,
  translated with the iris node's parent cells), fw_devlink does not parse
  `memory-region`, and a root child without `compatible` creates no device.
  d14 stays registered as the rejected composition. The overlay is not in the kernel build's
  `dt_sources`: compiled without its base it warns (reg format, default
  address cells), and the build fails on unreviewed warnings; like the other
  feature overlays it is checked by its composer and dt-validate instead.
- **Modules** load late, from the platform kit: `configs/production/video-modules.list`
  (`videocc_sm8350`, `qcom_iris`) via `rog5-video.service`, after Wi-Fi,
  Bluetooth, audio and sensors. Two reasons: (1) qcom_iris takes an apps
  SMMU context bank when it binds, and an early bank allocation broke the
  Wi-Fi firmware load once (audio, r39); (2) the root has no module tree, so
  nothing autoloads, and with fw_devlink strict the new nodes would keep the
  sync_state of GCC, the RPMh power domains and the four NoCs pending (boot
  levels) until both drivers bind. The bundle builder writes an empty video
  list for kernels without the modules (fallback bundles).
- **Firmware** is requested on the first open of a video node. udev's
  `v4l_id` opens both nodes as they appear, so with the firmware installed
  persistently the load happens when rog5-video.service runs at boot. The
  installer's `--runtime` mode puts it in the tmpfs firmware path for one
  boot, so the first load can be watched and a failure cannot repeat at the
  next boot.

## Applications

Measured 2026-10-02 on k116 (H.264/HEVC decoder exposed):

- **Chromium 153** has the V4L2 stateful decoder built in, but desktop Linux
  keeps it off until the `AcceleratedVideoDecoder` feature is enabled.
  `configs/chromium/chromium-flags.conf` (installed as
  `/etc/chromium-flags.conf`) enables it together with `V4L2VideoDecoder`,
  ANGLE on GLES and `--ignore-gpu-blocklist`; `72-rog5-v4l2-names.rules`
  adds the `/dev/video-dec0` / `/dev/video-enc0` names Chromium looks for.
  A 1080p30 H.264 clip decoded 711 frames in 24 s with no errors or software
  fallback; YouTube 1080p60 H.264 (avc1.64002a) kept the engine busy 100% of
  the time and the renderer dropped from ~120% to ~55% CPU. chrome://gpu
  still says "Video Decode: Software only" (ANGLE reports vendor 0x0000), so
  check the DevTools Media panel (`V4L2VideoDecoder`) instead.
- **Enabled by default since k123 (2026-10-03).** On k116 the firmware wedged
  under YouTube: Chromium closes its decoder CAPTURE-first, the driver sent
  FLUSH_OUTPUT while input was streaming, and the firmware never answered
  (sessions then failed to open and the core stayed powered until reboot).
  0211 sends FLUSH_ALL for an ordinary streamoff (as venus does) and 0210
  contains any later teardown failure; k123 passed the local and YouTube
  stress runs ([k116/k122/k123 trials](../../test-results/2026-10-02-video-iris-k123-ram-trial.md)).
  The installer ships `/etc/chromium-flags.conf` and `/etc/mpv/mpv.conf`
  (`hwdec=v4l2m2m-copy`); GStreamer apps (Showtime, WebKitGTK) already pick
  `v4l2h264dec`/`v4l2h265dec` by rank. Firefox is not configured yet.
- VP9 decodes in hardware since k125 (0212 stock-sized display buffers and
  per-buffer extradata, 0213 scratch release on restart), enabled by
  `/etc/modprobe.d/rog5-iris-vp9.conf` (`experimental_vp9=1 vp9_dpb_extra=1`):
  ffmpeg bit-exact, Chromium VP9 stress and YouTube VP9 clean; a resolution
  change stalls about 1 s. AV1 has no
  hardware decoder on SM8350; dav1d in software handles 1080p30 at 6.4x,
  1440p60 at 2.7x and 4K30 at 2.5x real time.

## Trial

Not run. Bundle, install, firmware and test steps: [Trial plan](#trial-plan).

## Trial plan

Bundle `main-k114-d15-261001a` (k114 + d15, try-once main; wrapper `boot-ram-128m.img` SHA-256 `cab1469544ee515154f64ac91255e97417339210d5012b1cd3b0ed27ba114c1a`, descriptor `trial-main-k114-d15-261001a/descriptor`; package under
`~/.local/state/rog5-production-boot-20260923/package-main-k114-d15-261001a/`).
Fallback stays `safe-k111-d10-261001a` (its DTB has no video node). Every
step below is read-only on the phone except the firmware installer (step 3)
and the install (step 5).

1. **RAM trial without firmware** (`production-ram-trial.py to-fastboot`, then
   `boot --wrapper <package>/boot-ram-128m.img --wrapper-sha256 <sha> --evidence <new dir> --stage-receiver`).
   Expect:
   - `rog5-platform-modules: video-modules loaded videocc_sm8350 qcom_iris`
     (after the audio and sensor lists) and `systemctl status rog5-video` active;
   - no `arm-smmu 15000000.iommu: S2CR... the hypervisor did not take the route`
     line (patch 0156; if it names SMR id 0x2100: stop, do not install
     firmware, see Risks);
   - `/sys/bus/platform/drivers/qcom-iris/aa00000.video-codec` and
     `/sys/bus/platform/drivers/sm8350-videocc/abf0000.clock-controller` exist,
     `/sys/class/video4linux/video*/name` = `qcom-iris-decoder`, `qcom-iris-encoder`;
   - `dmesg | grep 'sync_state() pending'` never names `aa00000.video-codec` or
     `abf0000.clock-controller` after rog5-video ran, and
     `/sys/kernel/debug/devices_deferred` does not list them;
   - udev's v4l_id open fails cleanly: `qcom-iris aa00000.video-codec:
     qcom/sm8350/vpu20_4v.mbn: request_firmware failed: -2`, `firmware download
     failed: -2`, `core init failed`; `video_cc_mvs0c_clk` and
     `video_cc_mvs0_clk` stay at enable count 0 in
     `/sys/kernel/debug/clk/clk_summary`;
   - the usual k113 checks (Wi-Fi up, audio, sensors, display, s2idle).
2. **Firmware for this boot only**, still in the RAM trial:
   `ssh root@169.254.77.2 sh -s -- --runtime < scripts/device/install-rog5-video-firmware`
   (copies vendor_a `vpu20_4v.mbn`, SHA-256 `16d8258c...e69d`, into the tmpfs
   firmware path), then `v4l2-ctl --list-devices`. Expect, in order:
   `vpu20_4v.mbn authenticated and out of reset (PAS 9)`, no
   `qcom_scm_mem_protect_video_var failed`, no uc_region / boot / system-init
   error, and `v4l2-ctl --list-devices` listing `qcom-iris` with both nodes.
   The core powers off 1.5 s after the last close (clk_summary enable
   counts back to 0, `pm_genpd_summary` `mvs0c_gdsc`/`mvs0_gdsc` off).
3. **Functional tests** (same boot; clips in `/var/tmp`, removed afterwards):
   - `v4l2-ctl -d /dev/videoD --all --list-formats-out --list-formats` for the
     decoder (OUTPUT H264/HEVC/VP9, CAPTURE NV12/QC08C) and the encoder
     (OUTPUT NV12/QC08C, CAPTURE H264/HEVC); `v4l2-compliance -d /dev/videoD`
     and `-d /dev/videoE` (upstream SM8350: 48/48 on the decoder).
   - Clips: `ffmpeg -f lavfi -i testsrc2=size=1920x1080:rate=30:duration=20`
     encoded with libx264 veryfast, libx265 ultrafast, libvpx-vp9 realtime, and
     a 3840x2160 H.264/HEVC pair.
   - Decode speed: `ffmpeg -hide_banner -benchmark -c:v h264_v4l2m2m -i clip -f null -`
     (then `hevc_v4l2m2m`, `vp9_v4l2m2m`), against the CPU baseline of
     2026-10-01 (1080p H.264 9.8x, HEVC 7.6x, VP9 8.4x realtime).
   - Decode correctness: `-pix_fmt yuv420p -f framemd5` from `h264_v4l2m2m`
     and from the software decoder must match frame for frame (H.264/HEVC
     decoding is bit-exact).
   - Encode: `ffmpeg -f lavfi -i testsrc2=size=1920x1080:rate=30:duration=20 -pix_fmt nv12 -c:v h264_v4l2m2m -b:v 8M out.mp4`
     (and `hevc_v4l2m2m`), fps against x264 veryfast 57 fps / x265 ultrafast
     31 fps, quality with `ffmpeg -i out.mp4 -i ref.y4m -lavfi psnr -f null -`.
   - GStreamer: `gst-inspect-1.0 video4linux2` lists `v4l2h264dec`,
     `v4l2h265dec`, `v4l2vp9dec`, `v4l2h264enc`, `v4l2h265enc`;
     `gst-launch-1.0 filesrc location=clip.mp4 ! qtdemux ! h264parse ! v4l2h264dec ! fakesink sync=false`;
     `gst-launch-1.0 videotestsrc num-buffers=600 ! video/x-raw,format=NV12,width=1920,height=1080,framerate=30/1 ! v4l2h264enc ! h264parse ! mp4mux ! filesink location=gst.mp4`.
   - mpv: `mpv --hwdec=v4l2m2m-copy --vo=null --frames=600 clip.mp4` must log
     `Using hardware decoding (v4l2m2m-copy)`; then on screen in Phosh.
   - Concurrency (the IOVA bug upstream reproduced with several browser tabs):
     four parallel `h264_v4l2m2m` decodes; no `Unhandled context fault`.
   - Cost: the same 60 s 1080p30 playback with `--hwdec=no` and
     `--hwdec=v4l2m2m-copy`, CPU from `/proc/stat` and, unplugged, battery
     current (`rog5-idle-power-sample`); interconnect votes in
     `/sys/kernel/debug/interconnect/interconnect_summary` (video-mem) during
     and after playback.
   - One s2idle cycle with the firmware resident, then decode again.
4. **Back to the installed chain**: `production-ram-trial.py fastboot-reboot`
   (or an ordinary reboot); the runtime firmware copy is gone with the RAM
   boot.
5. **Install** (only after a clean step 1-3), from a clean checkout of this
   branch: `python3 scripts/host/install-default-kernel.py --bundle-dir <package>/bundles/main-k114-d15-261001a --descriptor <trial dir>/descriptor --trust-key <raw key> --evidence <state>/install-main-k114-d15-261001a-preflight --address 10.77.0.2`
   (preflight), then the same with `--stage` and a new evidence directory;
   reboot, `PASS main-k114-d15-261001a committed healthy`, reboot again.
   Then the persistent firmware:
   `ssh root@10.77.0.2 sh -s < scripts/device/install-rog5-video-firmware`
   and one more reboot to see the boot-time load (`authenticated and out of
   reset` shortly after rog5-video.service).
6. **Back-out**: the firmware alone: `install-rog5-video-firmware --uninstall`
   (the drivers stay bound, the core stays off). The bundle: it is a try-once
   main, so a boot that does not commit falls back to safe-k111-d10; a
   committed install goes back by the selector (`selector.rollback-main-k114-d15-261001a`)
   or a fresh `rog5-make-bundle.py --role main --kernel k113 --dtb d13`.

### What a failure looks like

| Sign (dmesg) | Meaning |
|---|---|
| `arm-smmu ...: S2CR<n> (SMR id 0x2100 ...) ... the hypervisor did not take the route` | the hypervisor refused SID 0x2100 on the bank Linux picked; do not load firmware. Fix: add 0x2100 to `qcom_sm8350_dsp_sids` (banks >= 20, patch 0051) |
| `request_firmware failed: -2` | firmware not installed (expected before step 2) |
| `loading into 0x0000000085700000 (PAS 9 init/mem setup) failed: -22` (with qcom_scm errors) | TrustZone rejected the metadata or the memory region (what the CDSP got, `0x30001f`) |
| `auth and reset failed: <err>` | TrustZone rejected the image signature or the PAS state |
| `qcom_scm_mem_protect_video_var failed: <err>` | content-protection call refused; the image is shut down again |
| `invalid setting for uc_region` / `error booting up iris firmware` | the core did not accept its memory map / never raised CTRL_STATUS |
| `firmware did not complete system init (-110), powering the core off` | firmware started but never answered (0154 tore it down) |
| `Unhandled context fault ... cbfrsynra=0x2100` / `Unexpected global fault` | DMA outside the domain (IOVA hole, unmapped buffer) |
| hard reset during step 2 | likely the stream route: ramoops/`/sys/fs/pstore` after the reboot; the RAM trial means the next boot is the installed chain |

## k115 trial

Bundle `main-k115-d15-261002a` (k115 + d15, try-once main): package
`~/.local/state/rog5-production-boot-20260923/package-main-k115-d15-261002a/`,
wrapper `boot-ram-128m.img` SHA-256
`bb2aeeeb41b7218057c78ea5abe3f10d8f6fac412facad9f7826da3d5ea4302c`, descriptor
`trial-main-k115-d15-261002a/descriptor` (see [bundles.md](../bundles.md)). What k115 changes
(patches 0157-0162, see their commit messages and
[the review](../reviews/2026-10-02-gpt-6.1-sol-video-k115.md)):

- diagnostics: on a fatal error the driver prints the firmware's SFR text,
  the last 64 HFI packets in both directions and the firmware's own error
  messages (HFI debug config 0x18, like stock);
- containment: a fatal error or firmware watchdog is latched for the
  binding: no reload, every waiter and poll() is woken with an error, the
  firmware is shut down through TrustZone and only then is the core powered
  off; new opens fail with -EIO until `modprobe -r qcom_iris`;
- lifetime and buffers: instance reference counting, close order, no
  double completion of vb2 buffers, STOP/RELEASE errors propagated, answers
  matched to their command, one SESSION_END, firmware-visible memory kept
  until the firmware let go of it;
- IRQ and runtime PM no longer wait for each other; registers are only
  touched while the core is powered;
- experiments, off by default and switchable at run time in
  `/sys/module/qcom_iris/parameters/`: `eos_buffer=1` (real 4 KiB EOS buffer
  for the decoder drain, like stock) and `interframe_pc=0` (no firmware
  power collapse; read when the firmware is loaded). `fw_debug` (default
  24 = 0x18) sets the firmware message mask.

### One decode per boot

Each boot answers one question and ends at the first fatal error or kernel
warning. Phone address in a RAM trial: `169.254.77.2`.

1. RAM-boot the wrapper (`production-ram-trial.py to-fastboot`, then
   `boot --wrapper <package>/boot-ram-128m.img --wrapper-sha256 <sha>
   --evidence <new dir> --stage-receiver`).
2. Before any firmware: `dmesg | grep -E 'video-modules|qcom-iris|S2CR'`
   (expect `video-modules loaded videocc_sm8350 qcom_iris`, the
   request_firmware -2 failures, no S2CR line);
   `grep . /sys/module/qcom_iris/parameters/*` (expect `eos_buffer:N`,
   `fw_debug:24`, `interframe_pc:Y`);
   `for d in /sys/class/video4linux/video*; do echo $d $(cat $d/name); done`.
3. Test clip and software reference, made before the firmware exists:
   `ffmpeg -hide_banner -f lavfi -i testsrc2=size=1920x1080:rate=30:duration=10 -c:v libx264 -preset veryfast -pix_fmt yuv420p -y /var/tmp/t1080.mp4`
   and `ffmpeg -hide_banner -i /var/tmp/t1080.mp4 -pix_fmt yuv420p -f framemd5 -y /var/tmp/sw.md5`.
4. Keep the host from runtime-suspending the core (isolates host power
   collapse; the firmware's own inter-frame collapse is `interframe_pc`):
   `echo on > /sys/bus/platform/devices/aa00000.video-codec/power/control`.
   For the variant boots set the parameter now, before the firmware loads:
   boot B `echo 1 > /sys/module/qcom_iris/parameters/eos_buffer`,
   boot C `echo 0 > /sys/module/qcom_iris/parameters/interframe_pc`.
5. Firmware for this boot only:
   `ssh root@169.254.77.2 sh -s -- --runtime < scripts/device/install-rog5-video-firmware`.
6. Mark the log and decode once (the first open loads the firmware):
   `echo 'rog5: decode 1' > /dev/kmsg; timeout 60 ffmpeg -hide_banner -c:v h264_v4l2m2m -i /var/tmp/t1080.mp4 -pix_fmt yuv420p -f framemd5 -y /var/tmp/hw.md5; echo rc=$?`
   then `diff <(grep -v '^#' /var/tmp/sw.md5) <(grep -v '^#' /var/tmp/hw.md5) && echo IDENTICAL; grep -vc '^#' /var/tmp/hw.md5`
   (300 frames expected).
7. Wait 15 s idle, then `dmesg | grep -E 'qcom-iris|rog5: decode'` and save
   `dmesg > /var/tmp/k115-dmesg.txt` (copy it into the evidence directory).
   Stop this boot here if there is a `sys error`, `fatal firmware error`,
   `watchdog`, `WARNING` or `Unhandled context fault`.
8. Only after a clean step 6/7, same boot, one at a time, checking dmesg
   after each:
   - second decode (step 6 again);
   - GStreamer with explicit framing:
     `timeout 60 gst-launch-1.0 -e filesrc location=/var/tmp/t1080.mp4 ! qtdemux ! h264parse ! video/x-h264,stream-format=byte-stream,alignment=au ! v4l2h264dec ! video/x-raw,format=NV12 ! fakesink sync=false`;
   - encode with NV12 input (yuv420p is not an Iris encoder format):
     `timeout 60 ffmpeg -hide_banner -f lavfi -i testsrc2=size=1920x1080:rate=30:duration=10 -vf format=nv12 -pix_fmt nv12 -c:v h264_v4l2m2m -b:v 8M -an -y /var/tmp/enc.h264`,
     then `ffmpeg -hide_banner -i /var/tmp/enc.h264 -f null -` (frame count) and PSNR
     against the source;
   - full compliance logs: `v4l2-compliance -d /dev/videoD > /var/tmp/compl-dec.txt 2>&1`
     and the same for the encoder node (keep the whole files: k114 only had
     the totals 41/48 and 42/48).
9. `production-ram-trial.py fastboot-reboot` (or an ordinary reboot); the
   runtime firmware copy is gone with the RAM boot.

### Reading the diagnostics

After a fatal error the log shows, in this order:
`sys error (type: 1, session id:ff, data1:1, data2:...)`,
`fatal firmware error (sys error): no reload ...`, then a block
`diagnostics (sys error): state ..., attempt ...` with

- `SFR (size word 0x1000): <text>`: the firmware's own failure reason (the
  stock driver prints the same); `<empty>` means it wrote nothing;
- 64 lines `hfi t|r -<age> us: w0 .. w13`, oldest first: `t` sent, `r`
  received; `w0` packet size, `w1` packet type, `w2` session id (system
  packets have none), then the payload (EMPTY_BUFFER: w5 flags, 0x1 = EOS,
  w9 alloc_len, w10 filled_len, w11 input tag, w12 buffer address;
  FILL_BUFFER: w3 stream id (0 = the firmware's OUTPUT port, the
  internal reference/DPB buffers in split mode; 1 = OUTPUT2, the client's
  CAPTURE buffers), w4 offset, w5 alloc_len, w7 tag, w8 buffer address; see
  `iris_hfi_gen1_defines.h`). Sent types:
  0x10001 SYS_INIT, 0x10005 SYS_SET_PROPERTY, 0x10007 SESSION_INIT,
  0x10008 SESSION_END, 0x11001 SET_PROPERTY, 0x11002 SET_BUFFERS,
  0x211001 LOAD_RESOURCES, 0x211002 START, 0x211003 STOP, 0x211004
  EMPTY_BUFFER (input; the drain's EOS packet has buffer 0xdeadb000, or the
  EOS buffer's address with `eos_buffer=1`), 0x211005 FILL_BUFFER, 0x211008
  FLUSH, 0x21100b RELEASE_BUFFERS, 0x21100c RELEASE_RESOURCES. Received:
  0x20001 SYS_INIT done, 0x20006/0x20007 session init/end done, 0x21001
  EVENT_NOTIFY (w3 event id: 0x1 system error, 0x2 session error,
  0x1000003 sequence changed; w4/w5 its data), 0x221001-0x22100c the session answers (0x221007 EMPTY_BUFFER
  done, 0x221008 FILL_BUFFER done);
- `fw log: ...` lines: the firmware's last error messages (also printed
  live as `fw: ...`).

The last `t` lines before the first `r 21001` with w3 = 1 name the command
the firmware failed on; that is the question for the next variant. Then
`video core shut down after the fatal error` (TrustZone accepted the
shutdown) or `firmware shutdown (PAS) failed ...; keeping the video core
powered` (it did not: the core stays on until reboot). Do not reload the
module to retry: a reload reset the phone in the k116 trials (E2, wrapper
b). From k117 the module is pinned while firmware runs (`modprobe -r` says
"in use"); `echo 1 > /sys/bus/platform/devices/aa00000.video-codec/firmware_unload`
shuts an idle core down first. Load-time options belong in
`/etc/modprobe.d/` before the boot; a fresh boot is the test.

## k116 trials

Kernel k116 = k115 + patches 0163-0168, DTB d15 unchanged. RAM wrappers
(the RAM-trial launcher takes one boot per wrapper): `main-k116-d15-261002a`
(E1), `-b` (E2), `-c` (spare / E1 repeat), and `-d` kept for the dedicated
encoder boot. Wrappers (`boot-ram-128m.img` in
`~/.local/state/rog5-production-boot-20260923/package-<bundle>/`, descriptor
in `trial-<bundle>/`):

| Bundle | Use | Wrapper SHA-256 |
|---|---|---|
| `main-k116-d15-261002a` | E1 defaults | `f1269bdc5f1eb4cb39b1d61d8a0503cdafe8ba48ea0b31a0221dae3f5ef1c513` |
| `main-k116-d15-261002b` | E2 VP9 | `6a552bb2d53b1dbcd179e0e10576f9f12483f52485a91fb353c808856f11bf09` |
| `main-k116-d15-261002c` | spare / E1 repeat | `1e3cd55ca5f417e81c38487af87b5b8321248349c4a8367299bc2bf5489402a1` |
| `main-k116-d15-261002d` | later encoder boot | `19d5b0330695f2554f9ea5821446e66944684eccf48a0bc33386e03a19b1171b` |

What
changed for SM8350 (only for the `qcom,sm8350-iris` compatible, through its
own platform data and vpu ops), after the k115 trials and five GPT-6.1-Sol
deep dives (`docs/reviews/2026-10-02-gpt-6.1-sol-video-k115-deep-dive-*.md`):

- `HFI_PROPERTY_PARAM_SECURE_SESSION = 0` right after SESSION_INIT, before
  any buffer (stock does this for every non-secure session; VP9 failed at
  its first PERSIST SET_BUFFERS with "CP mode is UNKNOWN" without it);
- real 4 KiB EOS buffer for every drain, decoder and encoder (no dummy);
- power off and on in the stock Iris2 order (0167): the handshakes
  (X2RPMh = 3, AON MVP NOC, debug bridge 7 then 0) while both GDSCs, all
  clocks and the votes are still held; then clocks MVS0, MVS0C, AXI0; MVS0
  back to software control (checked) before both GDSCs go; then the
  bandwidth votes and a real OPP release (the old rate-0 call kept the
  lowest OPP's MX/MMCX votes). No CPU-NOC request (it never acknowledged:
  `CPU NOC LPI handshake timed out` at every k115 power off) and no TZ FIFO
  reset. Power on: votes, OPP, MVS0C, MVS0, reset, clocks, stock preset
  (clear bits 0x11 of +0xb0088 instead of writing 0). Power-collapse
  readiness as stock (PC_READY and WFI in the same read);
- firmware inter-frame power collapse always on (the `interframe_pc`
  switch is gone: C showed that turning it off alone stops the firmware);
- encoder node only with `experimental_encoder=1`, VP9 only with
  `experimental_vp9=1` (both module load time, 0444);
- `ubwc_config=1` (run time, applies at the next firmware load) sends the
  stock LPDDR5 UBWC config (60-byte packet); off by default;
- gen1 property packets are allocated for their wire structure (0166:
  profile/level and H.264 entropy wrote 4 bytes past their allocation;
  encoder-only properties, fixed for every gen1 user);
- robustness (0168): a failed resume keeps everything if TrustZone did not
  confirm the firmware suspend; bandwidth votes are cached only once
  applied; an unrequested flush answer no longer wraps the flush count;
- compliance: bus_info `platform:aa00000.video-codec`, no DEFAULT
  colorspace in formats;
- bring-up guards: `markers=1` prints a line before/after every risky
  step (core init, PM, power off), 16-word HFI trace, DMA window
  [0x25800000, 0xe0000000) enforced for every firmware-visible buffer,
  property and power-vote failures fail the stream-on.

Runtime PM: leave `power/control` at `auto` (the default and D's tested
state). The k115 report first blamed pinned runtime PM for an idle hang in
B; the live kmsg showed B went on decoding and hung at the encoder test,
like D, so the k116 guard against pinned runtime PM was dropped.

What the trials should show for 0167: no `NOC`, `debug bridge` or
`power off reported an error` lines after a power down; with `markers=1`
the lines `mark: power off: handshakes done: 0` and `mark: power off:
done: 0`. Any nonzero value names the step (the power off continues like
stock). `MVS0 stays under hardware control` means the core latched itself
off until reboot (the module stays pinned).

### Boot E1: defaults (wrapper a)

1. RAM-boot wrapper `a`. Before the firmware: `dmesg | grep -E
   'video-modules|qcom-iris|S2CR'` (expect `SM8350 OEM firmware mode:
   encoder off, VP9 off`); `ls /sys/class/video4linux/` (one node, the
   decoder); `grep . /sys/module/qcom_iris/parameters/*`.
2. Clips and references (software, before the firmware): the 1080p30 H.264
   clip as before and an HEVC one
   (`-c:v libx265 -preset ultrafast -pix_fmt yuv420p -y /var/tmp/t1080.hevc.mp4`),
   framemd5 of each with the software decoder.
3. `install-rog5-video-firmware --runtime`, then H.264 decode, compare
   (expect `IDENTICAL`, 300 frames); HEVC decode, compare; H.264 again.
4. Power off clean? Before the first decode
   `echo 1 > /sys/module/qcom_iris/parameters/markers`; after each idle
   power-down (5 s) `dmesg | grep -E 'NOC|debug bridge|power off|power domain|OPP release|MVS0|mark: power'`
   should show only `mark: power off: handshakes done: 0` and
   `mark: power off: done: 0` (k115: `CPU NOC LPI handshake timed out`
   every time). Also check that the core clock and both video GDSCs are off
   (`grep -E 'video_cc_mvs0|mvs0' /sys/kernel/debug/clk/clk_summary`,
   `grep -i mvs0 /sys/kernel/debug/pm_genpd/pm_genpd_summary`).
5. GStreamer `v4l2h264dec` with byte-stream/au caps (as in the k115 plan)
   and `v4l2h265dec`.
6. `v4l2-compliance -d /dev/videoN > /var/tmp/compl-dec.txt 2>&1` on a
   fresh session (expect the bus_info, colorspace and SOURCE_CHANGE
   failures gone).
7. 5 minutes idle with runtime PM auto, then one more decode; save
   `dmesg`.

### Boot E2: VP9 (wrapper b)

*Superseded: the reload below reset the phone (k116 E2, wrapper b); E2
was redone with the option in `/etc/modprobe.d` at boot (wrapper c). See
[k117 trials](#k117-trials).* Load-time switch: the module is loaded by `rog5-video.service` at boot, so
reload it before the firmware is installed:
`modprobe -r qcom_iris && modprobe -d /run/rog5-modules qcom_iris experimental_vp9=1`
(expect `VP9 EXPERIMENTAL`), then the firmware, an H.264 decode as a
control, and a VP9 clip
(`-c:v libvpx-vp9 -deadline realtime -cpu-used 8 -pix_fmt yuv420p -y /var/tmp/t1080.webm`)
with `ffmpeg -c:v vp9_v4l2m2m ... -f framemd5`. Watch for `session error`
and `CP mode` / `CP breached` in the firmware log; SECURE_SESSION=0 is in
the HFI trace as `00011001 ... 00001011 00000000`. Optionally a second VP9
decode after `echo 1 > /sys/module/qcom_iris/parameters/ubwc_config`
needs a firmware reload: rebind the module first.

### Later: encoder (wrapper d, dedicated boot)

*Superseded by the staged encoder boot of [k117](#k117-trials) (no module
reload; `scripts/device/rog5-video-encoder-trial`).*

Not before E1 has passed, on a fresh boot with no decode before it (B and
D both hung at encoder start, D 140 ms after the encode marker, right
after a controller power off). The encoder still has known open problems
(below); this boot only localises the hang. Two log paths, because a hard
hang loses the journal:

- External, live: on the host
  `socat -u UDP-RECV:6666 - | tee encoder-netconsole.log` (or `nc -lu 6666`,
  allow UDP 6666 in the host firewall); on the phone
  `modprobe -d /run/rog5-modules netconsole netconsole=@/<ncm-if>,6666@169.254.77.1/`
  (`<ncm-if>` = the USB NCM interface, see `ip -br link`; target MAC
  defaults to broadcast) and `dmesg -n 8`. Also keep `ssh root@<phone>
  'dmesg -w' > encoder-kmsg.log` running (that is what kept B's and D's
  last lines). Neither is guaranteed to flush the very last line.
- Persistent: the ramoops console (0x9b800000, 4 MiB) survives the reset,
  but the wrapper overwrites the start of its console zone. Before the test:
  `echo Y > /sys/module/printk/parameters/ignore_loglevel`, unbind the
  debug UART console (`echo 98c000.serial > /sys/bus/platform/drivers/msm_geni_serial/unbind`
  or the current driver name), and pad the log past 160 KB (e.g. 2000
  `echo pad-$i > /dev/kmsg`). After the reset (lands on the installed
  default, `main-k113-d13-261001a` today),
  `insmod rog5_ramdump-k113.ko` (host copy in
  `~/.local/state/rog5-encoder-trial/`, built for k113; rebuild it from the
  `.c` next to it if the default changed; it maps the raw region read-only) and save
  `/sys/kernel/debug/rog5_ramdump`; the wrapper's `postmortem snapshot
  bytes=N` line gives the dead boot's console length.

Then
`modprobe -r qcom_iris && modprobe -d /run/rog5-modules qcom_iris experimental_encoder=1 markers=1`,
the firmware, and one encode with NV12 input:
`timeout 60 ffmpeg -hide_banner -f lavfi -i testsrc2=size=1280x720:rate=30:duration=5 -vf format=nv12 -pix_fmt nv12 -c:v h264_v4l2m2m -b:v 4M -an -y /var/tmp/enc.h264`.
The last `mark:` line before the hang names the step (marked: core init
steps, runtime suspend/resume, power off, and every command before and
after its doorbell: session init, each property, SET_BUFFERS, LOAD, START,
the first six ETB/FTB of a session).

## k117 trials

Kernel k117 = k116 + patches 0169-0171, DTB d15 unchanged. Wrappers
(`boot-ram-128m.img` in `~/.local/state/rog5-production-boot-20260923/package-<bundle>/`,
descriptor in `trial-<bundle>/`):

| Bundle | Use | Wrapper SHA-256 |
|---|---|---|
| `main-k117-d15-261002a` | F1 regression + safe reload | `e2473675149c47b118d00224daf1c692968ab80e9014ddc2555d9550dda62de9` |
| `main-k117-d15-261002b` | F2 VP9 | `1ab51f9ce20da67ef97bfd132a01cd757442fb6de90cdc2409436bc89cf4078a` |
| `main-k117-d15-261002c` | F3 staged encoder | `5049507c06cb287948c81f3be6d1f1c01dbeaba032d0256996a4a5472a4747c6` |
| `main-k117-d15-261002d` | spare | `f2de01c615e1f215c398879848af3942c401d81bea852051ed9bf1042c89ced0` |

What changed:

- 0169, safety (GPT-6.1-Sol audit 16): the video nodes were registered
  before their driver data was set, and runtime PM after them; udev's
  `v4l_id` opens a new node at once and `iris_open()` dereferenced a NULL
  core. This can oops at boot and is the leading candidate for the k116
  reload reset (not proven: nothing was logged). Now the data, DMA mask and
  runtime PM come first and the nodes last. While authenticated firmware
  runs the module is pinned (`modprobe -r` refused) until TrustZone
  confirms its shutdown; the new `firmware_unload` attribute shuts an idle
  core down. Runtime suspend is refused while a fatal error is latched but
  not yet contained. Clock/bandwidth scaling holds a runtime PM reference
  across both updates; decoder QBUF fails on a failed vote.
- 0170, VP9 (SM8350 only): the VP9 firmware rejected every reference
  buffer (`vDec_FillThisBuffer: Buffer validation failed`, all stream-0 FTBs
  of 0x302000 bytes). Stream 0 for the DPBs is right (split mode, as
  stock). The leading hypothesis (credible, not established; the firmware's
  criterion is not visible) is their size: stock sizes a DPB with
  VENUS_BUFFER_SIZE(NV12_UBWC), which up to 1920x1920 / 8160 MBs reserves
  two interlaced fields, 0x312000 at 1920x1088. DPBs now use the stock size;
  luma alignment 512 (the packetizer now sends the caller's constraints);
  input buffers +25 % for VP9/HEVC. The stock buffer counts (OUTPUT = DPB
  count, OUTPUT2 = the client's CAPTURE minimum and allocation) are in but
  off (`stock_buf_counts=0`), so that a VP9 result can be attributed.
  H.264/HEVC get the same DPB sizes, so F1 re-checks them.
- 0171, bring-up knobs (all off by default, writable at run time):
  `marker_delay_ms` (quiet after each marker so the line leaves the
  phone), `enc_stop_before` (encoder sessions refuse the first command of
  that HFI type: one boot can walk the start up step by step; a stop before
  START releases what LOAD_RESOURCES took) and `dpb_pad_kib` (extra KiB per
  DPB, if VP9 still rejects them; change it only between sessions).
- `install-rog5-video-firmware --check` reports the copy the kernel loads
  first (the `firmware_class.path` directory included) and exits 1 unless
  it is the pinned image; a persistent install refuses a differing copy
  earlier in that path.

Never reload `qcom_iris` in these trials; options go into
`/etc/modprobe.d/rog5-video-trial.conf` before the boot and are removed
afterwards.

### F1: regression and reload (wrapper a, no options)

1. E1 again with the k117 wrapper: H.264, HEVC, H.264 300/300 identical,
   v4l2-compliance 48/48, power off `handshakes done: 0`. New: the counts
   line (`markers=1`): `mark: counts: DPB n, CAPTURE min m actual k`.
2. Reload safety, after the decodes: `modprobe -r -d /run/rog5-modules
   qcom_iris` must fail with "in use" (firmware running). Then
   `echo 1 > /sys/bus/platform/devices/aa00000.video-codec/firmware_unload`
   (expect `mark: firmware unload`, power off done), then
   `modprobe -r -d /run/rog5-modules qcom_iris` and
   `modprobe -d /run/rog5-modules qcom_iris markers=1` with `ssh ... dmesg -w`
   running; expect `mark: probe done` and one more H.264 decode identical. A reset here means the
   cause was not (only) the probe race: the `dmesg -w` capture is the
   evidence.

### F2: VP9 (wrapper b)

`options qcom_iris experimental_vp9=1 markers=1` in `/etc/modprobe.d`
before the boot. H.264 control decode, then the 300-frame 1080p VP9 clip
(`decode_check` from the VP9 deep dive, or `ffmpeg -c:v vp9_v4l2m2m ...
-f framemd5` against software). Watch for `Buffer validation failed` and
`session error`; the trace shows the DPB FTBs as `0000002c 00211005 <session>
00000000 00000000 00312000` (stream 0, offset 0, alloc 0x312000). If they are still rejected,
retry in the same boot, one change at a time and between sessions:
`echo 1 > /sys/module/qcom_iris/parameters/stock_buf_counts`, then
`echo 1024 > .../dpb_pad_kib`, then 4096 (the trace and `mark: counts:`
show what went out). Also 720p and 4K clips.

### F3: encoder, staged (wrapper c, dedicated fresh boot; d spare)

`options qcom_iris experimental_encoder=1` in `/etc/modprobe.d` before the
boot; firmware installed; no decode before. Host: `socat -u UDP-RECV:6666 -
| tee enc-netconsole.log` and `ssh root@PHONE 'dmesg -w' > enc-kmsg.log`.
Phone:
`ssh root@PHONE sh -s -- --netconsole <ncm-if> --unbind-uart <scripts/device/rog5-video-encoder-trial`.
It sets ignore_loglevel and console loglevel 8, markers=1 with
`marker_delay_ms=50`, pads the log past 160 KiB for the ramoops console,
and encodes 2 s of 1280x720 NV12 with `enc_stop_before` at SET_BUFFERS
(0x11002), LOAD_RESOURCES (0x211001), START (0x211002), first ETB
(0x211004; deferred raw input goes out before capture buffers), first FTB
(0x211005), then no stop (expects 60 frames, `done: PASS`). A stage counts
only if the driver logged its stop and ffmpeg ended on its own; the script
stops at the first one that does not. Progress in
`/var/tmp/rog5-enc-trial/progress`. If the phone resets, the last
`rog5-enc: stage ...` line and the last `mark:` line name the step. After
the reset it runs the installed default (k116 today): copy
`~/.local/state/rog5-encoder-trial/rog5_ramdump-k116.ko` over, `insmod` it,
save `/sys/kernel/debug/rog5_ramdump` (the raw ramoops region; the
wrapper's `postmortem snapshot bytes=N` line gives the dead boot's console
length), and fetch `/var/tmp/rog5-enc-trial/` if it was synced.

What k117 does not change for the encoder: stock puts the encoder's
INTERNAL_PERSIST buffer in the secure non-pixel pool (msm_smem.c:376,
stream 0x2104, VMID 0xb) even for a non-secure session. Linux owns only
stream 0x2100 here (the secure context banks stay with the hypervisor), so
it cannot do that; if the hang is at LOAD_RESOURCES or START right after
the PERSIST SET_BUFFERS, that is the first suspect, and the encoder may need
the hypervisor-owned bank. The 0166 packet sizing fix is in since k116.

### Deferred from the deep dives (not in k116)

Each is a separate experiment or larger change; ordered by expected value.

- Encoder: translate V4L2 profile/level enums to HFI ones (stock
  msm_vidc_common.c:360; now sent untranslated, zero falls back to H.264
  High/1); stock allocates encoder PERSIST in the secure non-pixel pool
  (msm_smem.c:376, stream 0x2104, VMID 0xb) even for non-secure sessions,
  which Linux cannot do while the hypervisor owns the secure banks: the
  top-ranked hang candidate; one configuration transaction after both
  ports are ready; the stock baseline properties; a printk-independent
  persistent breadcrumb journal.
- Power: hand MVS0 to hardware right after the PAS load / SCM resume and
  before the HFI boot (stock order); drop the VERSION_INFO (+0xa0058) write
  at boot; pulse only the AXI0 reset (stock DT lists no MVS0C reset);
  `hw_clk_ctrl` on the MVS0 RCG (stock sets CFG bit 20); scale the
  controller clock too; hold resources instead of collapsing after a
  failed handshake (stock logs and continues, k116 too).
- VP9 beyond SECURE_SESSION: decoder init properties (profile/level with
  stock mapping, output order, thumbnail off, realtime, conceal colours);
  25% input headroom and 16-line alignment for gen1 VP9 line buffers; VP9
  admission limits; DPB retirement on resolution change; 10-bit/profile 2.
- Robustness/performance: OUTPUT/OUTPUT2 minimum/actual buffer counts
  from the real allocations (now 32/32 and DPB count for OUTPUT2); one
  effective frame rate for clock and bandwidth (bandwidth uses 30 fps,
  clocks a submission count, 1080p30 lands in the 60 fps row); COMV sized
  for the real reference count (32 now: 66 MB for HEVC 1080p); requeue
  driver-owned DPBs after a flush (seek); bounded sequence-change parsing;
  decoder QBUF ignoring power-vote errors; session admission (the 17th
  open is silently not listed); Lahaina core limits and clock model; DCVS.

## k120 trials

k120 uses d15 unchanged. Package root is
`~/.local/state/rog5-production-boot-20260923/package-<bundle>/`; the wrapper
is `boot-ram-128m.img`, the signed bundle is `bundles/<bundle>/`, and the
one-use descriptor is under the sibling `trial-<bundle>/descriptor`.
The wrapper hashes will be recorded here after the clean build and packaging.

This is a plan for a later admitted operator session. No phone commands were
run during host preparation. Use the existing production RAM-trial controller
and its identity/power/thermal/fallback/one-use checks; one fresh wrapper per
boot. Do not flash, change slots, install k120, or recursively unload dependencies.
Stop at the first kernel/SMMU fault, firmware session/system error, or lost
transport; do not perform repeated VP9 failures on a latched core. Keep live
logs on the host. A hard hang needs the [manual rescue](../development.md#manual-rescue-hard-hang-no-usb-dark-screen),
then lands on the installed default. A timeout does not authorize replaying
the same wrapper.

### Shared preparation and boot

1. Before each boot, stage only that boot's load options in
   `/etc/modprobe.d/rog5-video-trial.conf` through the admitted connection.
   Remove that file after landing back on the installed system. These are
   temporary persistent options, so verify they are removed even after rescue.
   Do not reload Iris to select VP9/encoder/probe options.
2. On the host, create a fresh evidence directory and start
   `socat -u UDP-RECV:6666 - > <evidence>/netconsole.log` before hazardous work.
   Use the controller's stage receiver for the boot. The boot commands from
   the repository are:

   ```sh
   python3 scripts/host/production-ram-trial.py to-fastboot
   python3 scripts/host/production-ram-trial.py boot \
     --wrapper "$PACKAGE/boot-ram-128m.img" --wrapper-sha256 "$WRAPPER_SHA256" \
     --evidence "$NEW_BOOT_EVIDENCE" --stage-receiver
   ```

   Substitute the exact package and hash from the table. Never reuse an
   evidence directory or consumed descriptor. After boot require
   `uname -r = 7.2.7-rog5-k120`, correct d15/video binding, no SID 0x2100
   route refusal, no warnings/faults, and expected module parameters.
3. On the host, start a live capture **before firmware/teardown**:
   `ssh root@PHONE 'dmesg -w' > <evidence>/live-dmesg-w.txt`. In parallel retain
   a timestamped host heartbeat through the admitted observer. USB NCM and
   ACM are useful redundant channels but share USB hardware. Discover the
   phone NCM interface; load netconsole with
   `modprobe -d /run/rog5-modules netconsole "netconsole=@/IF,6666@169.254.77.1/"`
   and set `dmesg -n 8`. All `PHONE` commands below are future phone commands.
4. For decoder/encoder boots, run the pinned firmware installer `--runtime`,
   then `--check`; require its effective-image SHA/size match. Use
   `scripts/device/install-rog5-video-firmware` via the admitted connection.
   Firmware on the installed default can be persistent; verify the effective
   copy rather than assuming it is absent before this step.

### G1: locate removal (wrapper a)

Boot options: `options qcom_iris markers=1 remove_quiesce=0`.
Keep `marker_delay_ms=0` during decode. Repeat F1 H.264/HEVC 1080p30 software
framemd5 comparisons (300 identical frames each), decoder compliance 48/48,
clean power-off markers and five-minute idle/decode. Identify `/dev/videoN`
from its `qcom-iris-decoder` name. Close every video client; require `fuser`
shows none. The module is pinned while firmware is resident.

With live dmesg/UDP capture already armed, execute on the phone in order:

```sh
echo 1 > /sys/bus/platform/devices/aa00000.video-codec/firmware_unload
# Require success and clean PAS/power-off; stop if it fails.
cat /sys/module/qcom_iris/refcnt
echo 200 > /sys/module/qcom_iris/parameters/marker_delay_ms
echo 1 > /sys/module/qcom_iris/parameters/markers
printf 'rog5-G1: remove once\n' > /dev/kmsg
rmmod qcom_iris
printf 'rog5-G1: rmmod returned\n' > /dev/kmsg
```

Require refcnt zero before removal. Remove **only Iris** once. Do not chain
reprobe after it. Expected progress: lock/cancel/deinit/IRQ/node/unregister,
`callback done`, IOMMU group ownership, each devres release/action, domain
work/GDSC provider markers, driver links/uevent, `module exit done`, then
`rmmod returned`. After success retain another ten seconds of logs for late
work and heartbeat, save dmesg, and end the trial through the ordinary accepted
return path. If responsive during a stall, use the admitted observer to obtain
SysRq blocked-task/all-CPU stacks; do not create a second device coordinator.

Wrapper d is a fresh G1 discriminator selected **after reviewing a's last
marker**, not an automatic retry:

- If a stops in redundant deinit or PM disable, repeat the powered F1/unload
  preparation with `remove_quiesce=1`; compare the last boundary and expected
  `skipping deinit` plus early `runtime disable action` markers. This changes
  only the optional correction, with the same decode/firmware history.
- If a points elsewhere, use `options qcom_iris probe_no_video=1 markers=1
  remove_quiesce=0` for a never-powered resource-control boot. Require no Iris
  video nodes and no firmware-auth marker; do not run any video tool or install
  firmware. Set delay 200 and remove Iris once under the same live capture.
  This distinguishes generic cleanup from a firmware-used core.

If the failing boundary needs a different provider fix, preserve d unused and
prepare a reviewed successor; the current code does not guess GDSC/SMMU changes.

### G2: VP9 extradata (wrapper b)

Boot options: `options qcom_iris experimental_vp9=1 vp9_dpb_extra=1 markers=1
trace_config=1`. Require `stock_buf_counts=0`, `dpb_pad_kib=0`, `ubwc_config=0`,
`remove_quiesce=0`, `probe_no_video=0`; `marker_delay_ms=0` throughout decoding.
After firmware check, one H.264 control decode must match software and power
off cleanly. Prepare the 10-second 1920x1080/30 VP9 profile-0 clip with
`libvpx-vp9 -deadline realtime -cpu-used 8 -pix_fmt yuv420p` and its software
framemd5 before the hardware decode. Run exactly one hardware attempt:

```sh
timeout 60 ffmpeg -hide_banner -nostdin -c:v vp9_v4l2m2m \
  -i /var/tmp/t1080.webm -pix_fmt yuv420p -f framemd5 -y /var/tmp/vp9-hw.md5
```

Require 300 identical frame rows versus the software reference, no 0x1003,
`Buffer validation failed`, system error, watchdog or SMMU fault, and clean
idle power-off. DPB markers must show stream 0, size 0x312000, and the **same**
nonzero, in-window extradata address/0x4000 on every DPB; CAPTURE stays stream
1. Keep setup packets (`hfi config t`) and complete live logs, raw files, module
parameters and exit status. If it fails, stop the boot without changing counts,
padding or UBWC settings and without module reload. Further variants require
fresh wrappers, preserving causal separation from the F2r baseline.

### G3: staged encoder (wrapper c)

Boot options: `options qcom_iris experimental_encoder=1`; VP9 and its extradata
switch stay off. Fresh boot with **no decoder session** before the encoder.
After firmware `--check`, require an encoder node and no video openers. Arm
live dmesg and UDP first, then stream the checked-in helper through the admitted
connection:

```sh
ssh root@PHONE sh -s -- --netconsole IF --unbind-uart --delay 50 \
  < scripts/device/rog5-video-encoder-trial
```

The helper pads ramoops, then visits stops 0x11002, 0x211001, 0x211002,
0x211004, 0x211005 and full encode (0). Each stopped stage needs that
invocation's driver stop marker and natural ffmpeg exit; any timeout,
firmware error or kernel/SMMU fault ends the run. Full encode requires 60
software-decodable frames and `done: PASS`. Save `/var/tmp/rog5-enc-trial/`
(including raw dmesg and stage-local kmsg) and the external capture. After a
hang, read raw ramoops only through the existing read-only ramdump module
built for the **actual installed landing kernel**, never the k120 module
on a different release. Confirm its vermagic before use. No encoder hardware
fix or performance qualification is claimed by this host work.
