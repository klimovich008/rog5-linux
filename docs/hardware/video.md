# Hardware video decode/encode (Iris v2 on SM8350)

Status 2026-10-01: trial bundle built, **not installed, nothing has run on the
phone**. Kernel k114 (patch 0154, `rog5-video.fragment`), DTB d15 (d13 + the
video overlay), bundle and exact steps in [Trial](#trial) below.

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

## Trial

Not run. Bundle, install, firmware and test steps: [Trial plan](#trial-plan).

## Trial plan

Bundle `main-k114-d15-261001a` (k114 + d15, try-once main; package under
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
