# r105 pre-install review (0125-0127, 0136-0139): install

No P0 found. The harness blocked writing `review-r105/report.md` (subagents may not write report files), so the full report is below and the review-r105 folder is empty. Nothing was modified and the phone was not touched.

Scope: repo at `955c6afe` (branch HEAD is now `6b3369cd`, a steam-arm64 commit on top), checked against the patched tree `/home/deck/.local/state/rog5-kernel-7.2.7-build-r105/source`; line numbers refer to that tree. The second Sol pass (`fix/dp4/sol-review2.log`) never ran because it hit the usage limit, so this review stands in for it.

### What I verified
- **Boot with the MSI monitor on the side port:** none of the new code paths can hang, panic or leak.
  - Early `bridge_detect` inits and exits the PHY in the USB3DP default.
  - pmic_glink then sets orientation, then the mux (DP_ONLY applied while `init_count` is 0, bus width 4), then HPD.
  - The capability read gives 4 lanes, and 0138 caps the rate at HBR2.
- **Quick monitor <-> hub swap:** covered by applying the pending pin mode at the next first PHY init (combo.c:3702). DP is the only user of the combo PHY, and every msm path that brings a link back up drops `init_count` to 0 first:
  - `display_disable` with sink_count != 0 (ctrl_off + phy_exit)
  - `off_link_stream`, which does exit/init (dp_ctrl.c:2709)
  - `deinitialize_mainlink`, which does exit/init (dp_ctrl.c:2105)
  - `atomic_enable`, via `host_phy_init` (dp_display.c:1488)
- **No USB3 user on the side port:** the composed DTB gives the side dwc3 only the USB2 PHY and uses the UTMI clock as pipe clock. So `usb_consumer` stays false and forced PHY restarts don't disturb USB2.
- **Counts stay balanced:**
  - A failed forced init no longer decrements `init_count` (combo.c:3803).
  - The mux restart returns before touching registers if the init fails (combo.c:4606).
  - A failed `power_on` leaves `dp_powered_on` false and the core power count unchanged.
  - The 0137 power wrappers match the PHY core's own counting.
- **No new lock-order problem:** `phy->mutex` is still taken before `phy_mutex`, and `phy_set_bus_width()` takes no lock.
- **0137 error path:** after a failed re-enable, `on_link` only writes DPCD and then deinitializes. `mainlink_disable` is now guarded. The display-level disable paths bail out when the link is not on.
- **0138:** the HBR3 cap sits after the LTTPR limit and skips eDP. With `dp_hbr3=1`, HBR3 still passes the sink-caps check (`max_bw_code` is 8.1).
- **0139:** the default `full` behaves exactly like 0114. There are no duplicate msm module parameter names.
- **Hub path (pin D):**
  - Pin D equals the probe default mode (USB3DP), so there is no PHY restart and the bus width is 2.
  - The new data-lanes `<0 1 2 3>` gives the same lane map as the old `<0 1>`.
  - The 0110 converter cap still runs after the DPCD read (dp_panel.c:420).
- **Sol's first review:** findings 1, 2, 4, 5, 6 (set_vx_px part) and 7 are fixed. Finding 3 (forced restart under a live AUX channel) no longer applies to power_on.
- **Audio:**
  - The V4 block is 28 bytes and matches the stock layout (`fmt_blk_size` 24). `FORMAT_LINEAR_PCM_V4` (0x10000) can't collide with the compress codec IDs. The 24-bit msbits constraint only applies to 32-bit samples.
  - **S16_LE playback and capture are unchanged.** Playback sends the same open and V2 format block. Capture only changes by queueing read buffers after the encoder configuration succeeds.
  - The second `q6routing_stream_close` from `close()` after the 0126 error path is harmless: the first close set the session ID to -1, so the lookup finds nothing.
  - The machine driver doesn't merge front-end and back-end formats, and WirePlumber pins both nodes to S16LE.

### P0
None.

### P1
None that block the install or first boot.

### P2
1. **0137 exposes partially rebuilt `link_info` to concurrent readers.** The memset is at dp_panel.c:132, and the 0110 converter cap is re-applied only at dp_panel.c:420, after two AUX reads.
   - Every pmic_glink notification, including hpd_irq ones, calls `hpd_notify`. That reruns `plug_handle` and the capability read while the stream is up.
   - `atomic_enable` (where `on_link` reads `link_info.rate`) and `mode_valid` don't take `plugged_lock`.
   - Scenario: the hub sends an IRQ_HPD just as the compositor's modeset starts. `on_link` reads the uncapped 540000 in the millisecond window and trains the converter at HBR2, which is the known dark-HDMI case. `mode_valid` can also briefly see 0 lanes and prune modes.
   - The old stale rate masked this. The window is narrow and a replug recovers.
   - Fix: build the values in a local struct, apply the converter cap to it, then copy it over in one step.
2. **0136 left the orientation path alone.** `typec_switch_set` still ignores a failed forced init and then calls `usb_power_on` / `dp_aux_init` with clocks off (combo.c:4519-4523). That is an unclocked access. It is inherited and needs a clock or regulator failure. The 0136 description only covers the mux path.
3. **0136: a failed forced restart leaves resources off with `init_count` ≥ 1.** A later `dp_exit` then disables clocks and regulators twice, which triggers WARNs. A `power_on` in between would write unclocked registers. Same rare trigger as item 2; a "common block enabled" flag checked before register access would close it.
4. **0136: the lane check accepts 0 lanes** (`qmp_combo_dp_lanes_ok`, combo.c:3630). msm can pass 0 during the window in item 1. Accept only 1, 2 or 4.
5. **UCSI now drives the combo PHY mux too.** With `mode-switch` on the combo PHY, UCSI's `typec_set_mode` calls (ucsi.c:1318/1362) reach it alongside pmic_glink.
   - If UCSI's USB state lands after the DP state and before the modeset, the PHY switches to USB3-only and `power_on` returns -ENODEV (combo.c:3876).
   - The external screen stays black until the next DP notification and a new modeset.
   - gpio-sbu-mux already disables AUX on the same UCSI call, so this is the existing failure domain, not a new one.
6. **Stream-enable failure after a good `on_link` (inherited).** dp_display.c:1510 only logs the failure, so `power_on` stays false and teardown is skipped. The PHY stays powered and a pending pin change isn't applied. The next attempt skips `phy_power_on`, and the new lane checks make training fail once. The exit/init in `deinitialize` then applies the mode, so it self-heals after one extra failed modeset.
7. **4-lane test item.** On clock-recovery failure msm lowers the rate before the lane count (dp_ctrl.c:2443) and doesn't revalidate the mode. A bad upper lane pair can end at 4 x RBR with a mode that needs more bandwidth, giving a black external screen; the internal display is unaffected. With 4 lanes, modes at 400–438 MHz (for example 3840x1080 at 75–90 Hz) become admissible, and the DPU has never run at that pixel clock, so watch for underruns. Fallback: `msm.dp_max_lanes=2`, either on the command line or via sysfs followed by a replug.
8. **Audio test item: the PCM_V4 / Q23 path is unverified on this ADSP.** The S16 default doesn't use it.
   - If the firmware rejects V4, prepare now fails cleanly because of 0126.
   - If it ignores the mode field, S24 plays quiet, as before.
   - If it doesn't sign-extend and a producer leaves the top byte zero, negative samples would saturate. PipeWire sign-extends, but aplay or sox with S24_LE may not.
   - Test S24_LE at low volume first. Capture S24_LE is gone; nothing in configs, scripts or tests asks for it.

### Inherited and dormant on ROG5
- **Link maintenance with link clocks off:** after a failed training, link maintenance can write `REG_DP_STATE_CTRL` with the link clocks off (dp_ctrl.c:392 via :2338). It is only reachable through msm's own IRQ_HPD pulse detection (dp_display.c:1685). ROG5 gets HPD through pmic_glink instead, so this path is dead here. Since 0137 adds more ways to end with link clocks off, `if (!ctrl->link_clks_on) return;` at the top of `msm_dp_ctrl_handle_sink_request` would be cheap insurance.
- **Runtime-PM reference leak:** repeated connected notifications each take a runtime-PM reference in `plug_handle`. That matters for standby, not for this install.

### Install notes
- Install r105 only together with its composed DTB (`mode-switch`, data-lanes 0–3). The fallback bundles carry their own DTBs, so that pairing is fine.
- First-use order:
  1. Hub on pin D: expect a 2-lane mode line and working HDMI, same as today.
  2. MSI monitor: expect a 4-lane HBR2 mode line.
  3. Swap monitor and hub with the output on: expect `applying deferred qmpphy mode` in the log once.
  4. Suspend and resume with the monitor attached.
- Keep `msm.dp_max_lanes=2` ready.

### Key files
- /home/deck/.local/state/rog5-kernel-7.2.7-build-r105/source/drivers/phy/qualcomm/phy-qcom-qmp-combo.c
- /home/deck/.local/state/rog5-kernel-7.2.7-build-r105/source/drivers/gpu/drm/msm/dp/dp_ctrl.c
- /home/deck/.local/state/rog5-kernel-7.2.7-build-r105/source/drivers/gpu/drm/msm/dp/dp_panel.c
- /home/deck/.local/state/rog5-kernel-7.2.7-build-r105/source/drivers/gpu/drm/msm/dp/dp_display.c
- /home/deck/.local/state/rog5-kernel-7.2.7-build-r105/source/sound/soc/qcom/qdsp6/q6asm-dai.c
- /home/deck/.local/state/rog5-prod-boot-20260923/dts/qcom/sm8350-asus-rog-phone5-displayport-side.dtso","handback":true},"promptSource":"system","turnOrigin":"peer","queueSkipAttachments":true,"userType":"external","entrypoint":"cli","cwd":"/home/deck/Projects/rog-phone-linux-migration","sessionId":"2cc1c994-1a4f-4a0b-aca7-41804577680f","version":"2.1.280","gitBranch":"HEAD","slug":"declarative-baking-pearl"}
{"parentUuid":"aa447c91-6c22-4742-9f9e-cb723c489bb1","isSidechain":false,"message":{"model":"claude-opus-5-5","id":"msg_011CfZbn1hsde2ZybKwjE5o3","type":"message","role":"assistant","content":[{"type":"thinking","thinking":"","signature":"CAQSmAgKEAgSGAI4AUIIdGhpbmtpbmcSDIN+98T/arI4h8jPbhoMKEBVGCRYfnPqRGWRIjBl/9RGFdQOBSYPvhlZWyxRWM2srrp26MI1x4c+zf1XzMA5E+epBdUP09SHggkTHHEqtQcShYxyiqydsXFMY4vjfk8GEduteMjzAEYleQw8l/DF8eWm53SQSe9cfO8bSAMjnoSpWaZiZG/rcO0kh8s1zunLNeWF8BP+Ff4HrHuiR39v+acQ4Ahz3T9WRAoBNqPenbhVIRh70iYfFjQMp+3v5YwCKDDjryXXezc6xcUDm7unckh7C4bgD69Jy6YcdDyNzXTW2RQEqYHvknQGv3gEDflVhWnLKhEIyCxZZVPYN7hGVU4de5kgF8uXyY0aTojao/wkJQ7sjTYi8tsiljk3zTEehiz8AvbtawTof+HQa7Rgb/E3x4nEmxzfHDRGg8nZiWnFT/Ih0QSx4ZcOdQfYpBs3z/5RPFy4tO+/ocqK2owQvOcQ2HcbXlBuR70TZP2VH/nRxyHYr4YLbe7GW63Fo4Mq+2nCYdf9VXRkkUAoLm7hVrhxOx3YjAYdQh1uMxEB4JO1Ber5CI9+TUiSDKvcBIW2cGjiVc5M1CZjySx8awSe0dzuOj75SJ9bSoWZir0x/IlhjE+5bNfZ/TPjK0bmazQJHkjwIXBJjzMShXxkiZtNiE5zNzX+biSqT+kvx6svFcLBhSXExRKm4RhZNGL0WiyI3zLChsZ1M4kfUQxxmsXYioEZ+cv0RQMyhFGxfDw9dRWfn+3QS3NWBjTu3psuc4hy2dBdELKeeQpeGJnKM6emrLhYZQuc64pMFAU/ftXC4sLb0n2RYiiea61Ybm5aZ42v/Zlsq7DZmYy6KXqjXgZ1oH0zKhlWaCH+/mHH9hlJg4KdPJl0Kdm41dF0R9qhplJA3p9xaI514BXQxPYSHIH1B7yFSohr7+UZftuONvcZCVSwyPTQfk2OOr55k8NJItVEPxX4lA8E5qBVyMtFId1v+H984oMo3/G9broUyujBrCUTEuRmMayh9xkzEpDHAqPiB1FmnH93q2hfqmXgoKt/O9duelOHYKhVZk/JkgYae84GBrGQpSMCcMRrSldVNRh3aWeEtGuo8Y6YWDcZcmUbg2Q7phSD1O2hk4hCbjOjsKSkSS47uyooNXzTkS2+5MJlvaRdNWIwFNkpYITW7DVY4KhDsfF6Z/B3CXEHDQLLetoAjVKvgNvLwSIRgPJvUWkHMucRkojE5OtDPm8mkReyf41AvipooZV5lAvwLAOoVqfKVeUHrpJb+6NTpoBGcVA24sC/tWp1CZGQ8cwXS7Na3RW2UIeAbfn7GGFmzgE0Hw3YopS92tDbz8QqP1Tzg+6XdHTRk1z4k0Ims9FOdqxcD4qsJmvpGAE="}],"container":null,"stop_reason":"tool_use","stop_sequence":null,"stop_details":null,"usage":{"input_tokens":4,"cache_creation_input_tokens":4681,"cache_read_input_tokens":274506,"output_tokens":860,"output_tokens_details":{"thinking_tokens":102},"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":4681,"ephemeral_5m_input_tokens":0},"inference_geo":"not_available","iterations":[{"input_tokens":4,"output_tokens":860,"cache_read_input_tokens":274506,"cache_creation_input_tokens":4681,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":4681},"type":"message"}],"speed":"standard"},"input_transformations":[{"type":"thinking_dropped","path":"messages.2.content.0","reason":"prefix_binding_mismatch"}],"diagnostics":null,"context_management":null},"serverClassifierRequest":"0852562a-46d1-43f3-8be3-85943784b30b","apiBlockIndex":0,"requestId":"req_011CfZbmzgMeg79srDtqJHNs","type":"assistant","uuid":"a7c5bfd2-c9c4-41e3-bfd3-3948f7494f84","timestamp":"2026-09-30T12:10:32.196Z","advisorModel":"claude-opus-5-5","effort":"high","perTurnEffort":"high","session_id":"560e7b12-79fb-4ec8-a2be-b44d4c93807d","userType":"external","entrypoint":"cli","cwd":"/home/deck/Projects/rog-phone-linux-migration","sessionId":"2cc1c994-1a4f-4a0b-aca7-41804577680f","version":"2.1.280","gitBranch":"HEAD","slug":"declarative-baking-pearl"}
{"parentUuid":"a7c5bfd2-c9c4-41e3-bfd3-3948f7494f84","isSidechain":false,"message":{"model":"claude-opus-5-5","id":"msg_011CfZbn1hsde2ZybKwjE5o3","type":"message","role":"assistant","content":[{"type":"tool_use","id":"toolu_01Uc4myVkqVjFB1CmpdUPNmM","name":"SendMessage","input":{"to":"a5bab3f00706c960f","summary":"Review of r105 DP patches: P2 follow-ups","message":"FYI from main: an independent read-only review of r105 (0136-0139) found no P0/P1. P2 items worth folding into your next revision after the current diagnosis (line numbers in the r105 source tree):
1) 0137: link_info memset at dp_panel.c:132 is visible to concurrent readers until the 0110 converter cap is re-applied at dp_panel.c:420; hpd_irq notifications rerun plug_handle/capability read while the stream is up, and atomic_enable/mode_valid don't take plugged_lock -> on_link can read the uncapped 540000 (HDMI hub dark at HBR2) or mode_valid can see 0 lanes. Fix: fill a local struct, apply the cap, then copy in one step.
2) 0136 left typec_switch_set (combo.c:4519-4523) ignoring a failed forced init before usb_power_on/dp_aux_init (unclocked access; inherited).
3) 0136: a failed forced restart leaves resources off with init_count >= 1 -> later dp_exit double-disables (WARNs), power_on in between writes unclocked regs; a "common block enabled" flag would close it.
4) 0136: qmp_combo_dp_lanes_ok (combo.c:3630) accepts 0 lanes; accept only 1/2/4.
5) UCSI typec_set_mode (ucsi.c:1318/1362) now also reaches the combo mux; a late USB state can switch the PHY to USB3-only and power_on returns -ENODEV until the next DP notification (same failure domain as gpio-sbu-mux).
Also cheap insurance: `if (!ctrl->link_clks_on) return;` at the top of msm_dp_ctrl_handle_sink_request. The user is doing the flipped-orientation step now; I've relayed your two questions (what was in the side port at boot, and whether the MSI input was on USB-C at the first plug).","type":"message","recipient":"a5bab3f00706c960f","content":"FYI from main: an independent read-only review of…"},"caller":{"type":"direct"}}],"container":null,"stop_reason":"tool_use","stop_sequence":null,"stop_details":null,"usage":{"input_tokens":4,"cache_creation_input_tokens":4681,"cache_read_input_tokens":274506,"output_tokens":860,"output_tokens_details":{"thinking_tokens":102},"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":4681,"ephemeral_5m_input_tokens":0},"inference_geo":"not_available","iterations":[{"input_tokens":4,"output_tokens":860,"cache_read_input_tokens":274506,"cache_creation_input_tokens":4681,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":4681},"type":"message"}],"speed":"standard"},"input_transformations":[{"type":"thinking_dropped","path":"messages.2.content.0","reason":"prefix_binding_mismatch"}],"diagnostics":null,"context_management":null},"wireToolInputs":{"toolu_01Uc4myVkqVjFB1CmpdUPNmM":{"to":"a5bab3f00706c960f","summary":"Review of r105 DP patches: P2 follow-ups","message":"FYI from main: an independent read-only review of r105 (0136-0139) found no P0/P1. P2 items worth folding into your next revision after the current diagnosis (line numbers in the r105 source tree):
1) 0137: link_info memset at dp_panel.c:132 is visible to concurrent readers until the 0110 converter cap is re-applied at dp_panel.c:420; hpd_irq notifications rerun plug_handle/capability read while the stream is up, and atomic_enable/mode_valid don't take plugged_lock -> on_link can read the uncapped 540000 (HDMI hub dark at HBR2) or mode_valid can see 0 lanes. Fix: fill a local struct, apply the cap, then copy in one step.
2) 0136 left typec_switch_set (combo.c:4519-4523) ignoring a failed forced init before usb_power_on/dp_aux_init (unclocked access; inherited).
3) 0136: a failed forced restart leaves resources off with init_count >= 1 -> later dp_exit double-disables (WARNs), power_on in between writes unclocked regs; a "common block enabled" flag would close it.
4) 0136: qmp_combo_dp_lanes_ok (combo.c:3630) accepts 0 lanes; accept only 1/2/4.
5) UCSI typec_set_mode (ucsi.c:1318/1362) now also reaches the combo mux; a late USB state can switch the PHY to USB3-only and power_on returns -ENODEV until the next DP notification (same failure domain as gpio-sbu-mux).
Also cheap insurance: `if (!ctrl->link_clks_on) return;` at the top of msm_dp_ctrl_handle_sink_request. The user is doing the flipped-orientation step now; I've relayed your two questions (what was in the side port at boot, and whether the MSI input was on USB-C at the first plug)."}},"serverClassifierRequest":"0852562a-46d1-43f3-8be3-85943784b30b","apiBlockIndex":1,"requestId":"req_011CfZbmzgMeg79srDtqJHNs","type":"assistant","uuid":"ff3c405c-69b7-4570-a981-a4c49fcbed6e","timestamp":"2026-09-30T12:10:37.656Z","advisorModel":"claude-opus-5-5","effort":"high","perTurnEffort":"high","session_id":"560e7b12-79fb-4ec8-a2be-b44d4c93807d","userType":"external","entrypoint":"cli","cwd":"/home/deck/Projects/rog-phone-linux-migration","sessionId":"2cc1c994-1a4f-4a0b-aca7-41804577680f","version":"2.1.280","gitBranch":"HEAD","slug":"declarative-baking-pearl"}
{"parentUuid":"ff3c405c-69b7-4570-a981-a4c49fcbed6e","isSidechain":false,"promptId":"fd6a331c-4fe3-4696-b2d7-560e6c107339","type":"user","message":{"role":"user","content":[{"tool_use_id":"toolu_01Uc4myVkqVjFB1CmpdUPNmM","type":"tool_result","content":[{"type":"text","text":"{"success":true,"message":"Message queued for delivery to a5bab3f00706c960f at its next tool round.","pin":{"id":"a5bab3f00706c960f","name":"a5bab3f00706c960f","ref":"6557bc"}}"}]}]},"uuid":"fc916846-ea33-4f43-ba77-1c8222ff4944","timestamp":"2026-09-30T12:10:38.706Z","toolUseResult":{"success":true,"message":"Message queued for delivery to a5bab3f00706c960f at its next tool round.","pin":{"id":"a5bab3f00706c960f","name":"a5bab3f00706c960f","ref":"6557bc"}},"serverClassifierContext":{"request":"0852562a-46d1-43f3-8be3-85943784b30b","context":{"git_state":{"cwd":"/home/deck/Projects/rog-phone-linux-migration","root":null,"branch":null,"default_branch":null,"status":null,"visibility":{"origin":null,"push_remote":null,"remotes":[],"visibility_cache":[]},"error":"not_a_repo"},"live_cwd":"/home/deck/Projects/rog-phone-linux-migration","platform":"linux"}},"sourceToolAssistantUUID":"ff3c405c-69b7-4570-a981-a4c49fcbed6e","session_id":"560e7b12-79fb-4ec8-a2be-b44d4c93807d","userType":"external","entrypoint":"cli","cwd":"/home/deck/Projects/rog-phone-linux-migration","sessionId":"2cc1c994-1a4f-4a0b-aca7-41804577680f","version":"2.1.280","gitBranch":"HEAD","slug":"declarative-baking-pearl"}
{"type":"queue-operation","operation":"enqueue","timestamp":"2026-09-30T12:10:40.195Z","sessionId":"2cc1c994-1a4f-4a0b-aca7-41804577680f","content":"<task-notification>
<task-id>aea204b5bdaf06282</task-id>
<tool-use-id>toolu_01B1yiwiYNzKw43KJkaaHK6x</tool-use-id>
<output-file>/tmp/claude-1000/-home-deck-Projects-rog-phone-linux-migration/2cc1c994-1a4f-4a0b-aca7-41804577680f/tasks/aea204b5bdaf06282.output</output-file>
<status>completed</status>
<summary>Agent "Review r105 DP and audio patches" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>This agent's report was delivered to you as a message from "aea204b5bdaf06282" (its SubagentHandback call). Read it there; it is not repeated here.
</result>
<usage><subagent_tokens>273691</subagent_tokens><tool_uses>67</tool_uses><duration_ms>1087288</duration_ms></usage>
</task-notification>"}
{"parentUuid":"fc916846-ea33-4f43-ba77-1c8222ff4944","isSidechain":false,"attachment":{"type":"total_tokens_reminder","text":"<total_tokens>14989389 tokens left</total_tokens>"},"type":"attachment","uuid":"71f085a7-1640-4092-8da8-1d0085f7491d","timestamp":"2026-09-30T12:10:38.804Z","rendered":[{"content":"<system-reminder>
<total_tokens>14989389 tokens left</total_tokens>
</system-reminder>"}],"session_id":"560e7b12-79fb-4ec8-a2be-b44d4c93807d","userType":"external","entrypoint":"cli","cwd":"/home/deck/Projects/rog-phone-linux-migration","sessionId":"2cc1c994-1a4f-4a0b-aca7-41804577680f","version":"2.1.280","gitBranch":"HEAD","slug":"declarative-baking-pearl"}
{"type":"last-prompt","lastPrompt":"I was not able to test speakers. Can you run the same test we had at 80% loudness.","leafUuid":"71f085a7-1640-4092-8da8-1d0085f7491d","sessionId":"2cc1c994-1a4f-4a0b-aca7-41804577680f"}
{"type":"ai-title","aiTitle":"STEAMDECK-ROG5 handoff verification","sessionId":"2cc1c994-1a4f-4a0b-aca7-41804577680f"}
{"type":"mode","mode":"normal","sessionId":"2cc1c994-1a4f-4a0b-aca7-41804577680f"}
{"type":"permission-mode","permissionMode":"auto","sessionId":"2cc1c994-1a4f-4a0b-aca7-41804577680f"}
{"type":"atis-latch","atis":"","sessionId":"2cc1c994-1a4f-4a0b-aca7-41804577680f"}
{"type":"bridge-session","sessionId":"2cc1c994-1a4f-4a0b-aca7-41804577680f","bridgeSessionId":"cse_01CKnPrDyMnYfFaSuLEbMQAJ","lastSequenceNum":53874,"ownerAccountUuid":"0afda5a0-c45a-4d7c-9d12-e1636991c94f","ownerOrganizationUuid":"0273d556-7f83-4d49-8a97-c8e65d890cbe"}
