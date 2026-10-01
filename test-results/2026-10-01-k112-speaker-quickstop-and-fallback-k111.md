# k112 speaker quick-stop check and safe-k111 fallback rehearsal (2026-10-01 15:40-15:47)

## Speaker quick-stop (tools/audio_debug/speaker-quick-stop-check.py) on main-k112-d10-261001a
10 quick open/close cycles of hw:0,0 with 10 ms of silence (each ~300 ms with 0151's pause settle), then a 3 s tone at -20 dBFS: RCV and SPK temperature moving and heartbeat advancing during the tone, stop OK, firmware mailbox paused after stop; 0 missed pause/resume lines, 0 slow, 0 reloads -> PASS. Boot of k112 itself: 0 amp mailbox errors (k111 boots logged them at ~57 s).

## Fallback rehearsal: safe-k111-d10-261001a (alpha kernel k111 + d10)
- 15:42 on main-k112-d10-261001a: trial-state reject -> failed, reboot.
- 15:43 loader selected safe-k111-d10-261001a: uname 7.2.7-rog5-k111, system running, no failed units, Wi-Fi up, memx reservation present, sound card + speaker protection running on both amps, qcom-battmgr-usb online=1 through the side hub (the old k69 fallback could not see hub power).
- 15:45 installed main-k112-d10-261001b from the fallback (preflight + stage PASS), reboot; 15:47 k112 committed healthy, selector main-k112-d10-261001b / fallback safe-k111-d10-261001a.
Result: PASS.
