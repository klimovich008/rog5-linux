# HBR2, desktop-mode auto switch and server checks (2026-09-29 night)

## HBR2 through the USB-C HDMI hub (r190: kernel r93 = + 0109 swing floor fix, DTB with link-frequencies 1.62/2.7/5.4 GHz)

- The link trains at 2 lanes x 5.4 Gbit/s; symbol-error counters show a burst in
  the first second after training and 0 at the 5 s and 15 s snapshots
  (counters clear on read). All monitor modes become valid: 3840x1080@60/100,
  2560x1440@60, 1920x1080@120.
- GNOME was switched to 3840x1080@60 (285 MHz, 30 bpp): DPU scanout verified
  (rog5-kms-grab of plane 46: the full-width desktop), no new underruns
  (IRQ [0,24] stayed at 192 over 10 s).
- **The monitor (MSI MPG 491C OLED via the hub's HDMI PCON) showed no picture**,
  also at 8 bpc (285 MHz TMDS, below the 340 MHz HDMI 1.4 limit). The earlier
  "lane-1 errors" reading of HBR2 was probably wrong: the DP side trains; the
  PCON's HDMI output does not come up at HBR2.
- Back at HBR / 1920x1080@60 / 8 bpc the monitor stayed dark too, even with
  the DP controller's test pattern (TPG): the hub's HDMI PCON stayed stuck
  after the HBR2 attempts. After the user reconnected the hub and the phone
  rebooted (a force reboot during r191's first boot sent it to the safe-r7
  fallback, which booted fine on the 16-192 GiB ramdisk; r192 = r191
  content was then reinstalled), the monitor showed GNOME again at
  1920x1080@60 over HBR and the USB keyboard worked (user-confirmed
  2026-09-30 00:0x). HBR stays the production default; HBR2 output needs
  the PCON's HDMI 2.0 (TMDS > 340 MHz / FRL) setup investigated.
- Production default restored to HBR: r191/r192 = kernel r93 + platform-cpucap-dp-sbumux-dtb-r2,
  /etc/tmpfiles.d/rog5-dp.conf dp_max_rate 270000 again.

## Automatic desktop mode

`rog5-desktop-mode` started GNOME 6 s after the phone was unlocked with the
display connected ("display connected, phone unlocked -> GNOME"). GNOME
opened all three input devices of the USB keyboard (Drunkdeer G75) behind
the hub.

## USB after a cable replug

After the user replugged the hub, the USB 2.0 side enumerated full-speed and
failed with `device descriptor read/64, error -71` (xHCI rebind did not help);
after the next reboot the hub came up high-speed with the card reader and the
keyboard. Suspected contact/orientation during the replug.

## Server checks

- Wi-Fi 6, 5540 MHz, 160 MHz, rx 2041 / tx 1730 Mbit/s link rate at -64 dBm.
- TCP from the phone to the Steam Deck host: 1000 MB in 23.4 s = 358 Mbit/s.
- SSH (project unit), Tailscale, nftables firewall (inet rog5_firewall) active.
