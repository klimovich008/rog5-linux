# Codex era (2026-07-30 to 2026-09-22): what the user asked for

Source: 770 distinct user-turn messages sent to the previous agent (OpenAI Codex). About 340 of them
are machine-written reviewer or sub-agent prompts ("Standards/Spec review… NO_BLOCKERS", "Bounded
implementation task…"). They show how Codex worked, not what the user said, and this draft uses them
only where they quote the user. Dates are UTC. "Main chat" means the long-running Codex development
session. The user often asked other Codex chats about it.

## 1. Project timeline (inferred from messages)

- **07-30: moved to the Steam Deck host.** The user asked to "transfer this project to my steamdeck" and do "most of the things via ssh".
- **07-31 to 08-01: headless network-root server and hardening.** The work covered a USB/NFS network root, SSH over USB ACM, and then
  USB-NCM fallback. The user's request: "Fast boot is ready, but can we do something to eliminate this bottleneck with the SSH USB
  connection?" Codex also added QEMU early-target diagnostics, GitHub CI, and many rounds of dual reviewers. On 08-01 the user asked
  for a written rule that routine actions need no repeated authorization ("you can use any authorization that you want").
- **08-03 to 08-10: slow, guard-heavy phase.** The user kept asking about MVP distance and percentages, and asked why the project used
  a custom recovery rather than TWRP. On 08-10 they wanted the main chat to "drop most of the guards so the development itself gonna be faster".
- **08-12 to 08-14: scope clarified to Linux only.** "I don't care about android tbh. I want to use this phone only for Linux." Topics
  were the mainline-style kernel versus the ASUS 5.4 source, storage (the 16 GB image versus using all 256 GB), and server uses such as AI
  with an online model, cloud storage, Hermes with Telegram, and remote access.
- **08-15 to 08-19: charging crisis.** The phone would not charge. It flashed a charging icon and then rebooted into fastboot, even
  after a stock restore that the user authorized ("even if phone dies this is ok"). On 08-19 the user said "I believe it started to charge".
  Follow-up problems: charging stalled at about 43–47%, and the user wanted charging and data on the side port as under Android.
- **08-20 to 08-23: working on dev-loop speed.** A mistakes and lessons guide became docs/development-lessons.md (R1–R10 failure
  classes, one canonical manifest). Other changes: a non-fatal power observer, an early initramfs charging probe, and trying to "flash a
  kernel with charging capabilities and test every change as a patch".
- **08-22 to 08-25: storage and persistent install.** The user confirmed formatting userdata (partition 23). They then confirmed shrinking
  userdata and creating GPT partition 24, and authorized Stage 2: clone the Arch image to arch_root_a, run native-root boot tests, then
  flash the Linux boot bundle to slot B and make it active, "Preserve ASUS slot A and all firmware, identity, calibration, security and modem partitions".
- **08-26 to 08-29: persistent boot.** Blockers were rebooting into the slot-A stock recovery and fastboot hangs ("fastboot logo, yet it
  was unresponsive until force reboot"). On 08-29 the user said "I authorize you to do any changes to GitHub."
- **08-29 to 09-01: Wi-Fi and status screen.** Codex built native Wi-Fi (board-data/BDF selection) with Tailscale. On 09-01 the user asked
  for an initial screen that the power button toggles and that shows the time, Wi-Fi and battery.
- **09-04 to 09-05: new model (GPT-6 "Astra") and consolidation.** Codex cleaned sessions and the repository and fixed flaws. The user asked to
  check the kernel and Arch image code for problems before making more changes ("Black screen" after a build). Acceptance/test-first work
  began (release-acceptance manifest, E01/E02). The user also said: "If you believe debian is easier to implement and use - do it."
- **09-07 to 09-08: thermals and a fresh session.** Topics were the CPU cap, undervolting and maximum temperature. Codex handed off to a
  fresh session ("ROG5 server qualification") so that "only one session controls the phone". The user asked how the kernel compares with
  mainline, raised a grub-like multi-distro boot, and suggested Rust for new modules.
- **09-09 to 09-10: first live human-assisted hardware test and new goals.** The user pointed to a Denial reference (Arch on a OnePlus 12R:
  "I want to have smth like this at the end. I don't need cellular module only"). On 09-10 they set a long-term goal of running Denial
  Wayland, then corrected the priority: "building fully working kernel is the first right step before running denial".
- **09-11 to 09-13: display, GPU and disk.** Topics were OLED at 144 Hz, Adreno/GPU (the user was told the problem was ordering rather than
  the driver), and Pro-model reviews. The user asked "Why we dropped GPU kernel work" and "When are we going to test things on the phone
  itself?", and asked for disk cleanup because the project used about 600 GB.
- **09-19 to 09-22: looking for reuse, then handoff.** The user pointed to r/mobilelinux and the mu-qcom guide for reusable work and set up
  Oracle MCP as a Pro adviser (since dropped). On 09-21: "Allow trial preparation and read-only phone checks". On 09-22 they asked for a
  handoff document for the model that will work on the Steam Deck.

## 2. Standing preferences still likely relevant

**Goals and scope**
- Linux only. Android does not matter (08-12). Still keep ASUS slot A and all firmware, identity, calibration, security and modem
  partitions (08-25).
- End state: a stable Arch ARM server (Wi-Fi, charging, storage, remote access), then a full phone like the Denial reference, without
  cellular (09-09). Priority is **kernel and non-cellular hardware first, Denial/UI later** (09-10).
- Wants the full 256 GB usable (08-13, 08-25).
- For server AI, prefers online models to small local ones ("small models are dumb tbh", 08-13).
- Wants a design that can later boot other distros (Fedora or Debian, grub-like) and patches that could go upstream (08-14, 09-08).
- Is open to new modules in Rust, per-module unit-test harnesses on the device, and tests written first as goals (09-05, 09-08, 09-09).
- Asked about a charge limit, and wants charging to stop at 100% at least (08-25). Also asked about power-bypass mode (08-13) and CPU
  undervolting with a frequency cap (09-07).

**How work should be done**
- Speed with stability. "I want to have a stable server, but want the process it be faster" (09-07). "make changes fast with little
  to no over engineering" (08-19).
- The agent may improve code without asking. "If you suspect that any code including kernel code is unstable or need to be improved you
  can and actually a want you to do it" (09-05). "If you think anything can be improved in a way our kernel, arch image or GitHub
  repository works - do it" (09-08).
- Reuse existing work before inventing: ASUS kernel source, Qualcomm SoC patches, LineageOS, r/mobilelinux, mu-qcom, other SM8350 projects (08-12, 08-15, 09-06, 09-09, 09-19, 09-20).
- Self-improvement after each run: spot repeated errors and slow stages, then fix the process (09-10, also 08-20). This is now in CLAUDE.md.
- Hardware tests that involve the user must be "prepared in advance and be able to start immediately when I'm ready" (09-10). This is now in CLAUDE.md.
- Pick your own approach to CI: "ci/CD GitHub calls can slow us down so you can decide" (09-04). The user asked whether CI can run locally (09-07).
- Keep disk use down. Delete builds that are no longer needed (08-11 /var, 09-08, 09-09 "500 gb", 09-13 "600gb").
- Only one session should control the phone at a time. Handoffs should be concise and checked (09-08).

**Authorization posture**
- Broad standing authorization. 08-01: routine signing, sudo/pkexec, GitHub, reboots, preflights and admitted boots need no repeated
  consent. 08-29: "any changes to GitHub". 09-08: "Full access granted".
- Destructive partition or boot operations were still explicitly confirmed each time: userdata format (08-22), shrink and partition 24
  (08-25), boot_b flashes (08-18), boot-B replacement (09-06). Inference: keep asking for a short explicit confirmation for irreversible
  partition changes.
- The user asked whether sudo can be reused or the password stored (09-11). Never store credentials in the repository or in notes.

**Communication**
- The user asks often for a status, percentage, ETA and main blocker ("How far are we", "Give eta pls"). Give short, concrete, honest numbers.
- Asks for "compact" updates and "short and structured" roadmaps (09-08, 09-10). The user writes informally with typos, and replies are
  often one or two words ("Up", "News", "Go", "Continue.").
- Asks plain conceptual questions (why ext4 rather than btrfs, C versus Rust, USB speed, Snapdragon 888 performance). Answer them directly.

## 3. Recurring frustrations (avoid)

- **Slowness**, the dominant theme. "I feel like we are doing it pretty slow" (08-21). "why we are moving this slow" (08-23). "What takes
  most of the time" (09-07, 09-11). "main chat can move faster but legacy stops us" (09-06).
- **Too many guards and too much process.** The user wanted most guards dropped (08-10). Codex's heavy review-loop and identity/pinning
  machinery (hundreds of reviewer prompts) is exactly what the user saw as slowing things down.
- **Repeating the same mistakes** (08-20). This led to the lessons guide.
- **Stuck in loops without progress on the phone.** Examples: the phone rebooting into stock recovery (08-23, 08-26), "Why we are not yet
  flashing new kernel" (08-25), "When are we going to test things on the phone itself?" (09-13), and dropping GPU work without saying why (09-13).
- **Estimates that keep slipping.** The user asks for ETAs over and over. Inference: past estimates were not reliable, so give ranges and what they depend on.
- **Disk bloat** (hundreds of GB) and **context or session pollution** from long sessions and plugins (08-19, 09-08).
- **Hard to type on the Steam Deck** during hardware tests: "Write ready pls, it's hard on the steamdeck to write", "Enter doesn't work",
  "I can't type anything into the field" (09-09, 09-10).
- **Failed scripts during a live session** ("Script failed", 09-09). This is why tests must be prepared and validated before the user is involved.
- Logic mistakes the user caught themselves: "w33 is for ROG 7 but I have ROG phone 5" (08-19). Before the charging fix, the user
  suspected "we have some logical problems" and asked to rethink from first principles (08-17).

## 4. Obsolete instructions (do not revive)

- Anything about the Codex app, Codex Linux desktop updates or restarts, "uncap context window", "reapply context limits", pinning to the taskbar, and remote-session instability.
- Model and effort choices: "sol"/"sol-wm", GPT-5.6, GPT-6 "Astra" migration, "ultra reasoning", "fast mode", "use opus if it's stuck" (08-10).
- ChatGPT Pro / "astra pro" adviser flows: Oracle MCP `consult` with a gpt-6-pro browser engine (09-20), review branches and prompts for
  Pro, webhooks that wake the agent when Pro finishes, turning a ChatGPT subscription into an API (FreeQwenApi-style), and scheduled
  tasks that check whether a review branch was published.
- Delegating to other tools: opencode CLI with the "OX Alpha" model (08-21), and "give this context to Claude" from inside Codex (08-19).
- Codex skills management (installing a "systematic debugging" skill, pruning skills) and requests to write prompts to paste into the main chat.
- Phase constraints that are gone: "temporary-boot-only / no-flash" (superseded by the 08-25 flashing authorization), the consumed
  r2/v3/v7 candidate pins, and "drop most of the guards" (08-10). The last is tempered by 09-07 "stable server… faster" and CLAUDE.md
  "Do not weaken safety checks".
- Denial/Flutter UI as the top priority (09-10 first ask). The user reprioritized the same day to kernel first.
- "If … debian is easier … do it" (09-05). There is no sign in the messages that a switch happened. Inference: Arch remains the base unless the user revisits this.

## 5. Physical and operator protocol (how phone interaction worked)

- The host is the Steam Deck. The phone connects over USB, either the **bottom port** or the **side port**, with one cable during most
  tests (08-18 "I have only 1 cable connected"). Charging and data behaviour differed by port. A host USB hub sits in the path; a host hub
  disconnect once ended a capture (09-05, agent prompt).
- The user reports physical state in short replies: "fastboot ready.", "A believe fastboot Is ready now", "reconnected", "Phone
  Reconnected", "I connected bottom port", "Unplugged", "Pressed, I see it started to boot", "It rebooted into fastboot", "Black screen",
  "ready to press".
- The user does button presses on request: the power button, and power-off and boot-mode selection from the fastboot or recovery menus
  (08-18, 08-19, 09-09). The phone often has **no visual indication** under Linux ("not sure how to confirm if it's powered off", 09-09),
  so the agent must detect state over USB or the network and say what the user should expect to see.
- 09-09 session pattern: the user asked the agent to check the phone first, then to "assist me on every step, so I would type here on
  every step". Because typing is hard on the Deck, prompts must accept a minimal reply such as "Ready" and give one short action at a time.
- Readiness etiquette (from 09-10, codified in CLAUDE.md): prepare and validate everything first. Ask for "Ready" only when the session
  is armed. Start any response countdown only after a fresh reply. On Ready, give the first physical prompt immediately. If something
  fails, release the user, fix it, and ask again later. Never reuse an old "ready".
- Destructive steps got an explicit quoted confirmation sentence from the user (e.g. "I confirm formatting only userdata partition 23 as
  described…"). Inference: present the exact action and let the user confirm in one line.
- The user suggested human-free tests by power-cycling or disconnecting the phone at the USB-hub level (09-09). This is not yet confirmed as implemented.

## Archive

Codex was retired on 2026-09-23 and its session store deleted. A private,
non-Git archive at `~/.local/state/rog5-codex-archive-20260923/` keeps every user
message (`user-messages.md`) and every user/assistant/final-summary message
(`codex-conversations.jsonl.gz`, from 318 sessions). Tool outputs were not kept;
the evidence they produced is in `test-results/` and `~/.local/state/rog5-*`.
