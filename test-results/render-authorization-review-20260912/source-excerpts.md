# Pinned source excerpts

Rust source: Denial 85b2303e plus the three recorded local patches and the earlier initial-format diagnostic. Engine source: Flutter fork d728e61e, unchanged in the inspected files. These excerpts are source evidence, not extra runtime observations.

### compositor/src/bin/deniald/flutter_runtime/output_pipeline.rs: target_available, line 198

Revision: `ca89dcf7 over upstream 85b2303e`. Full file SHA-256 `f34b77805c0c9bf2ceb61a62e9c60fd432c4e52673d02248ea453201709a9c10`.

```rust
fn target_available(&self, output: OutputId) -> bool {
        self.pools
            .iter()
            .find(|pool| pool.output_id == output)
            .is_some_and(|pool| {
                pool.authorized_request.is_none()
                    && !pool
                        .slots
                        .iter()
                        .any(|slot| slot.state != BufferState::Free)
                    && pool
                        .slots
                        .iter()
                        .any(|slot| slot.state == BufferState::Free && slot.output_refs == 0)
            })
    }
```

### compositor/src/bin/deniald/flutter_runtime/output_pipeline.rs: authorize, line 215

Revision: `ca89dcf7 over upstream 85b2303e`. Full file SHA-256 `f34b77805c0c9bf2ceb61a62e9c60fd432c4e52673d02248ea453201709a9c10`.

```rust
fn authorize(&mut self, request: OutputFrameRequest, now: Instant) -> Option<i64> {
        if request.dirty_serial == 0 || !self.target_available(request.tick.output) {
            return None;
        }
        let pool = self
            .pools
            .iter_mut()
            .find(|pool| pool.output_id == request.tick.output)?;
        pool.authorized_request = Some(AuthorizedOutputRequest {
            request,
            authorized_at: now,
        });
        trace_render_authorization("grant", pool, pool.authorized_request, now);
        Some(pool.render_view_id.get())
    }
```

### compositor/src/bin/deniald/flutter_runtime/output_pipeline.rs: cancel_authorizations, line 231

Revision: `ca89dcf7 over upstream 85b2303e`. Full file SHA-256 `f34b77805c0c9bf2ceb61a62e9c60fd432c4e52673d02248ea453201709a9c10`.

```rust
fn cancel_authorizations(&mut self, render_view_ids: &[i64]) {
        for pool in &mut self.pools {
            if render_view_ids.contains(&pool.render_view_id.get()) {
                trace_render_authorization("cancel", pool, pool.authorized_request, Instant::now());
                pool.authorized_request = None;
            }
        }
    }
```

### compositor/src/bin/deniald/flutter_runtime/output_pipeline.rs: expire_authorizations, line 240

Revision: `ca89dcf7 over upstream 85b2303e`. Full file SHA-256 `f34b77805c0c9bf2ceb61a62e9c60fd432c4e52673d02248ea453201709a9c10`.

```rust
fn expire_authorizations(&mut self, now: Instant) -> usize {
        let mut expired = 0;
        for pool in &mut self.pools {
            let should_expire = pool.authorized_request.is_some_and(|authorization| {
                now.saturating_duration_since(authorization.authorized_at)
                    >= authorization.request.tick.interval.saturating_mul(2)
            });
            if should_expire {
                trace_render_authorization("expire", pool, pool.authorized_request, now);
                pool.authorized_request = None;
                expired += 1;
            }
        }
        expired
    }
```

### compositor/src/bin/deniald/flutter_runtime/output_pipeline.rs: acquire, line 256

Revision: `ca89dcf7 over upstream 85b2303e`. Full file SHA-256 `f34b77805c0c9bf2ceb61a62e9c60fd432c4e52673d02248ea453201709a9c10`.

```rust
fn acquire(
        &mut self,
        render_view_id: i64,
        size: PixelSize,
    ) -> Result<u32, RenderTargetBlocked> {
        let Some(pool) = self
            .pools
            .iter_mut()
            .find(|pool| pool.render_view_id.get() == render_view_id && pool.size == size)
        else {
            return Err(RenderTargetBlocked::MissingPool);
        };
        let Some(authorization) = pool.authorized_request else {
            trace_render_authorization("refuse-no-authorization", pool, None, Instant::now());
            return Err(RenderTargetBlocked::MissingAuthorization);
        };
        if pool
            .slots
            .iter()
            .any(|slot| slot.state == BufferState::Ready)
        {
            return Err(RenderTargetBlocked::ReadyHandoff);
        }
        let Some(slot_index) = pool
            .slots
            .iter()
            .position(|slot| slot.state == BufferState::Free && slot.output_refs == 0)
        else {
            return Err(RenderTargetBlocked::NoFreeSlot);
        };
        trace_render_authorization("consume", pool, Some(authorization), Instant::now());
        pool.authorized_request = None;
        let slot = &mut pool.slots[slot_index];
        slot.state = BufferState::Rendering;
        slot.fence = None;
        slot.ready_damage = None;
        slot.rendered_at = None;
        slot.screenshot_request_id = self
            .next_screenshot
            .filter(|(output, _)| *output == pool.output_id)
            .map(|(_, request_id)| request_id);
        slot.ready_transaction = 0;
        slot.request = Some(authorization.request);
        Ok(slot.framebuffer)
    }
```

### compositor/src/bin/deniald/flutter_runtime/output_pipeline.rs: begin_transaction, line 180

Revision: `ca89dcf7 over upstream 85b2303e`. Full file SHA-256 `f34b77805c0c9bf2ceb61a62e9c60fd432c4e52673d02248ea453201709a9c10`.

```rust
fn begin_transaction(&mut self) {
        self.transaction = self.transaction.wrapping_add(1).max(1);
        for pool in &mut self.pools {
            for slot in &mut pool.slots {
                if slot.state == BufferState::Rendering && slot.output_refs == 0 {
                    slot.damage.invalidate();
                    slot.state = BufferState::Free;
                    slot.fence = None;
                    slot.ready_damage = None;
                    slot.rendered_at = None;
                    slot.screenshot_request_id = None;
                    slot.ready_transaction = 0;
                    slot.request = None;
                }
            }
        }
    }
```
### compositor/src/bin/deniald/flutter_runtime/output_runtime.rs: with_frame_readiness, line 305

Revision: `ca89dcf7 over upstream 85b2303e`. Full file SHA-256 `e4a129cd37f4fa84cc3e8d0e76e218dc60f255b7020a938949cb3136237021ee`.

```rust
fn with_frame_readiness<T>(
        &self,
        action: impl FnOnce(PendingFrame, &mut dyn FnMut(OutputId) -> bool) -> T,
    ) -> T {
        // Output authorization is a bounded per-output queue reservation, not
        // a global raster lock. A framework frame can legitimately consume
        // OnVsync without producing a raster task, so expire an unclaimed
        // reservation after two of that output's own intervals.
        let pending = PendingFrame {
            flutter_requested: self.handler.has_pending_vsync(),
        };
        let (result, expired) = self
            .handler
            .with_output_target_availability(Instant::now(), |target_available| {
                action(pending, target_available)
            });
        if expired > 0 {
            if render_audit_enabled() {
                info!(expired, "expired unclaimed output render authorizations");
            }
            debug!(
                expired,
                "released output render authorizations which produced no raster task"
            );
        }
        result
    }
```

### compositor/src/bin/deniald/flutter_runtime/output_runtime.rs: render_authorized_outputs, line 381

Revision: `ca89dcf7 over upstream 85b2303e`. Full file SHA-256 `e4a129cd37f4fa84cc3e8d0e76e218dc60f255b7020a938949cb3136237021ee`.

```rust
fn render_authorized_outputs(
        &mut self,
        requests: &[OutputFrameRequest],
        texture_ids: impl IntoIterator<Item = i64>,
        flutter_output: Option<OutputId>,
    ) -> Result<bool, Box<dyn Error>> {
        if !self.kms_frame_clock_enabled {
            return Err("the KMS Flutter frame clock is not enabled".into());
        }
        if requests.is_empty() {
            return Ok(false);
        }

        self.handler
            .authorize_outputs(requests, &mut self.render_view_scratch);
        if self.render_view_scratch.is_empty() {
            return Ok(false);
        }

        let flutter_tick = flutter_output.and_then(|output_id| {
            let render_view_id = self
                .render_outputs
                .iter()
                .find(|output| output.output_id == output_id)?
                .render_view_id
                .get();
            self.render_view_scratch
                .contains(&render_view_id)
                .then(|| {
                    requests
                        .iter()
                        .find(|request| request.tick.output == output_id)
                        .map(|request| request.tick)
                })
                .flatten()
        });
        self.render_texture_scratch.clear();
        self.render_texture_scratch.extend(texture_ids);
        self.render_texture_scratch.sort_unstable();
        self.render_texture_scratch.dedup();
        self.changed_texture_scratch.clear();
        self.handler.advance_external_texture_sources(
            &self.render_texture_scratch,
            &mut self.changed_texture_scratch,
        );
        self.stage_changed_textures();

        let selected_tick = flutter_tick.unwrap_or_else(|| {
            requests
                .iter()
                .filter(|request| {
                    self.render_outputs
                        .iter()
                        .find(|output| output.output_id == request.tick.output)
                        .is_some_and(|output| {
                            self.render_view_scratch
                                .contains(&output.render_view_id.get())
                        })
                })
                .min_by_key(|request| request.tick.presentation_target)
                .map(|request| request.tick)
                .expect("an authorized render view has an output-timeline request")
        });

        let baton = if flutter_tick.is_some() {
            let (baton, _) = self.handler.take_next_vsync();
            let Some(baton) = baton else {
                self.handler
                    .cancel_output_authorizations(&self.render_view_scratch);
                return Err("a KMS-authorized Flutter frame has no AwaitVSync baton".into());
            };
            Some(baton)
        } else {
            None
        };

        let tagged_screenshot = self.pending_screenshot_frame.and_then(|pending| {
            self.render_outputs
                .iter()
                .find(|output| output.output_id == pending.0)
                .filter(|output| {
                    self.render_view_scratch
                        .contains(&output.render_view_id.get())
                })
                .map(|_| pending)
        });
        if let Some((output, request_id)) = tagged_screenshot {
            if let Err(error) = self
                .handler
                .tag_next_frame_for_screenshot(output, request_id)
            {
                if let Some(baton) = baton {
                    self.handler.restore_vsync(baton);
                }
                self.handler
                    .cancel_output_authorizations(&self.render_view_scratch);
                return Err(error.into());
            }
            self.pending_screenshot_frame = None;
        }

        let engine = self
            .host
            .as_ref()
            .expect("Flutter runtime is shutting down")
            .engine();
        let now_nanos = engine.current_time_nanos();
        let observation_delay =
            Instant::now().saturating_duration_since(selected_tick.render_deadline);
        if let Some(audit) = &self.handler.render_audit {
            lock(audit).record_render_authorization(observation_delay);
        }
        let target_after_deadline = selected_tick
            .presentation_target
            .saturating_duration_since(selected_tick.render_deadline);
        let (frame_start_nanos, frame_target_nanos) =
            timeline_vsync_timestamps(now_nanos, observation_delay, target_after_deadline);

        if let Err(error) = engine.render_outputs(
            &self.render_view_scratch,
            &self.render_texture_scratch,
            flutter_tick.is_some(),
            frame_start_nanos,
            frame_target_nanos,
        ) {
            if let Some(baton) = baton {
                self.handler.restore_vsync(baton);
            }
            if let Some((output, request_id)) = tagged_screenshot {
                self.handler.cancel_screenshot_frame(request_id);
                self.pending_screenshot_frame = Some((output, request_id));
            }
            self.handler
                .cancel_output_authorizations(&self.render_view_scratch);
            return Err(error.into());
        }

        if let Some(baton) = baton
            && let Err(error) = engine.on_vsync(baton, frame_start_nanos, frame_target_nanos)
        {
            self.handler.restore_vsync(baton);
            if let Some((output, request_id)) = tagged_screenshot {
                self.handler.cancel_screenshot_frame(request_id);
                self.pending_screenshot_frame = Some((output, request_id));
            }
            self.handler
                .cancel_output_authorizations(&self.render_view_scratch);
            return Err(error.into());
        }
        Ok(baton.is_some())
    }
```
### compositor/src/bin/deniald/flutter_runtime/renderer/handler/open_gl.rs: make_current, line 34

Revision: `85b2303e`. Full file SHA-256 `927c26d2df1df26f036671451e625d1a5cd030bff389850d096c45ffd3894453`.

```rust
fn make_current(&self) -> bool {
        let _audit_timer = RenderAuditCallbackTimer::new(
            self.render_audit.as_ref(),
            RenderAuditStage::ContextMakeCurrent,
        );
        let current = lock(&self.render_context).make_current();
        if current {
            self.collect_gpu_timings();
        }
        if current && self.begin_raster_frame() {
            if let Some(audit) = &self.render_audit {
                lock(audit).record_raster_start(Instant::now());
            }
            debug_assert!(lock(&self.sampled_buffer_release_fence).is_none());
            lock(&self.broker).begin_transaction();
        }
        current
    }
```

### compositor/src/bin/deniald/flutter_runtime/renderer/handler/open_gl.rs: create_backing_store, line 131

Revision: `85b2303e`. Full file SHA-256 `927c26d2df1df26f036671451e625d1a5cd030bff389850d096c45ffd3894453`.

```rust
fn create_backing_store(&self, request: BackingStoreRequest) -> Option<CompositorBackingStore> {
        let _audit_timer = RenderAuditCallbackTimer::new(
            self.render_audit.as_ref(),
            RenderAuditStage::BackingStore,
        );
        let size = PixelSize::new(
            u32::try_from(request.width).ok()?,
            u32::try_from(request.height).ok()?,
        );
        let framebuffer = match lock(&self.broker).acquire(request.view_id, size) {
            Ok(framebuffer) => framebuffer,
            Err(blocked) => {
                if let Some(audit) = &self.render_audit {
                    lock(audit).record_target_blocked(blocked);
                }
                // Every independently clocked output can temporarily retain a
                // scanning generation, an atomic submission awaiting page flip,
                // and a newer ready generation. Exhaustion remains ordinary
                // producer backpressure if a supported topology reaches its
                // bounded worst case. Flutter accepts FBO 0 as a skipped frame;
                // present() completes that no-op successfully so it returns to
                // AwaitVSync instead of entering a retry storm that could starve
                // the page flip which frees the next target.
                return None;
            }
        };
        // Leave the selected FBO current as required by the embedder OpenGL
        // contract. Denial's versioned engine stack queries the attached
        // level-zero texture and wraps it as borrowed storage; Skia owns the
        // stencil and dynamic-MSAA resources used to render into it.
        // SAFETY: Flutter calls this with the render context current.
        unsafe {
            (self.gl.bind_framebuffer)(gl::FRAMEBUFFER, framebuffer);
            (self.gl.viewport)(0, 0, size.width as i32, size.height as i32);
        }
        if let Some(gpu_timing) = &self.gpu_timing {
            lock(gpu_timing).begin(framebuffer);
        }
        Some(CompositorBackingStore {
            framebuffer,
            format: gl::RGBA8,
            // The pool owns the target. This identity makes a malformed or
            // cross-view present observable without allocating a callback
            // baton for every raster pass.
            user_data: framebuffer as usize,
        })
    }
```

### compositor/src/bin/deniald/flutter_runtime/renderer/handler/open_gl.rs: raster_idle, line 61

Revision: `85b2303e`. Full file SHA-256 `927c26d2df1df26f036671451e625d1a5cd030bff389850d096c45ffd3894453`.

```rust
fn raster_idle(&self) {
        let audit_timer = RenderAuditCallbackTimer::new(
            self.render_audit.as_ref(),
            RenderAuditStage::RasterIdleCallback,
        );
        if let (Some(audit), Some(started_at)) = (&self.render_audit, audit_timer.started_at()) {
            lock(audit).record_raster_idle(started_at);
        }
        // The host posts this sentinel behind Flutter's current render work.
        // If present() already sealed the transaction this is idempotent; if
        // the transaction had no present callback it supplies the missing
        // REQUESTED/RASTERIZING -> IDLE transition.
        let ready = lock(&self.broker).finish_transaction();
        let previous = self.finish_producer_frame();
        if !ready.is_empty() {
            let sampled = self.seal_sampled_buffers();
            if let Some(audit) = &self.render_audit {
                lock(audit).record_sampled_textures(sampled.as_ref());
            }
            let release_fence = lock(&self.sampled_buffer_release_fence).take();
            self.publish_sampled_buffer_release(release_fence, sampled);
            self.publish_ready_frames(ready);
        } else {
            lock(&self.sampled_buffer_release_fence).take();
            if let Some(audit) = &self.render_audit {
                lock(audit).record_empty_transaction();
            }
        }
        if matches!(
            previous,
            FlutterProducerState::Requested | FlutterProducerState::Rasterizing
        ) {
            self.rearm_abandoned_samples();
            let batch = self.seal_sampled_buffers();
            if batch.is_some() {
                // The raster transaction returned without present(), so no
                // exportable fence exists. Match the C++ conservative path.
                // SAFETY: the sentinel runs on Flutter's render thread after
                // the abandoned raster task.
                unsafe { (self.gl.finish)() };
                self.publish_sampled_buffer_release(None, batch);
            }
        }
    }
```
### compositor/flutter-engine/src/host.rs: create_backing_store, line 830

Revision: `85b2303e`. Full file SHA-256 `267eeb287449fb964e5f65d8b6db2fa98dafcf642c92701ccb74ce1bde1bf338`.

```rust
fn create_backing_store(
    config: *const sys::FlutterBackingStoreConfig,
    backing_store_out: *mut sys::FlutterBackingStore,
    data: *mut c_void,
) -> bool {
    if config.is_null() || backing_store_out.is_null() {
        return false;
    }
    dispatch(data, false, |state| {
        // SAFETY: Flutter keeps both full-size structures readable/writable
        // for this synchronous compositor callback.
        let config = unsafe { &*config };
        if config.struct_size < mem::size_of::<sys::FlutterBackingStoreConfig>() {
            return false;
        }
        let Some(width) = compositor_dimension(config.size.width) else {
            return false;
        };
        let Some(height) = compositor_dimension(config.size.height) else {
            return false;
        };
        let request = BackingStoreRequest {
            view_id: config.view_id,
            width,
            height,
        };
        let Some(store) = state.handler.create_backing_store(request) else {
            return false;
        };
        if store.framebuffer == 0 {
            return false;
        }
        let framebuffer = sys::FlutterOpenGLFramebuffer {
            target: store.format,
            name: store.framebuffer,
            user_data: store.user_data as *mut c_void,
            // Both Skia and Impeller require a callable release hook. Native
            // allocation ownership stays with Denial and is returned through
            // collect_backing_store instead of this render-target borrow.
            destruction_callback: Some(backing_store_released),
        };
        let open_gl = sys::FlutterOpenGLBackingStore {
            type_: sys::FlutterOpenGLTargetType_kFlutterOpenGLTargetTypeFramebuffer,
            __bindgen_anon_1: sys::FlutterOpenGLBackingStore__bindgen_ty_1 { framebuffer },
        };
        // SAFETY: Flutter supplied this exclusive out-parameter and consumes
        // the complete value only after the callback returns true.
        unsafe {
            *backing_store_out = sys::FlutterBackingStore {
                struct_size: mem::size_of::<sys::FlutterBackingStore>(),
                user_data: store.user_data as *mut c_void,
                type_: sys::FlutterBackingStoreType_kFlutterBackingStoreTypeOpenGL,
                did_update: true,
                __bindgen_anon_1: sys::FlutterBackingStore__bindgen_ty_1 { open_gl },
            };
        }
        true
    })
}
```
### compositor/flutter-engine/src/lib.rs: render_outputs, line 814

Revision: `85b2303e`. Full file SHA-256 `37b1d24e409eb476865d2daa88a612967739f4ab7535973502d7374d199dd44b`.

```rust
fn render_outputs(
        &self,
        render_view_ids: &[i64],
        texture_ids: &[i64],
        rebuild_scene: bool,
        frame_start_nanos: u64,
        frame_target_nanos: u64,
    ) -> Result<(), EngineError> {
        if render_view_ids.is_empty() {
            return Ok(());
        }
        let function = self.library.render_outputs;
        let texture_ids_ptr = if texture_ids.is_empty() {
            ptr::null()
        } else {
            texture_ids.as_ptr()
        };
        // SAFETY: the engine is live and both slices remain readable while
        // the custom API synchronously copies their contents.
        check_result("RenderOutputs", unsafe {
            function(
                self.handle,
                render_view_ids.as_ptr(),
                render_view_ids.len(),
                texture_ids_ptr,
                texture_ids.len(),
                rebuild_scene,
                frame_start_nanos,
                frame_target_nanos,
            )
        })
    }
```
### engine/src/flutter/shell/common/shell.cc: Shell::RenderOutputs, line 1346

Revision: `d728e61e7d835e02c453c70ae9523a40f6c03215`. Full file SHA-256 `4828e7af91b92b2f91e91ea144cc7c97519ecb58d3b4cca2407ea562a5148016`.

```cpp
Shell::RenderOutputs(std::vector<int64_t> render_view_ids,
                          std::vector<int64_t> texture_identifiers,
                          bool rebuild_scene,
                          uint64_t frame_start_time_nanos,
                          uint64_t frame_target_time_nanos) {
  FML_DCHECK(is_set_up_);
  FML_DCHECK(task_runners_.GetPlatformTaskRunner()->RunsTasksOnCurrentThread());
  FML_DCHECK(!render_view_ids.empty());

  if (rebuild_scene) {
    task_runners_.GetRasterTaskRunner()->PostTask(
        [rasterizer = rasterizer_->GetWeakPtr(),
         render_view_ids = std::move(render_view_ids),
         texture_identifiers = std::move(texture_identifiers)]() mutable {
          if (rasterizer) {
            rasterizer->PrepareDenialRenderOutputs(
                std::move(render_view_ids), std::move(texture_identifiers));
          }
        });
    return;
  }

  const auto frame_start = fml::TimePoint::FromEpochDelta(
      fml::TimeDelta::FromNanoseconds(frame_start_time_nanos));
  const auto frame_target = fml::TimePoint::FromEpochDelta(
      fml::TimeDelta::FromNanoseconds(frame_target_time_nanos));
  task_runners_.GetRasterTaskRunner()->PostTask(
      [rasterizer = rasterizer_->GetWeakPtr(),
       render_view_ids = std::move(render_view_ids),
       texture_identifiers = std::move(texture_identifiers), frame_start,
       frame_target]() mutable {
        if (!rasterizer) {
          return;
        }
        auto recorder = std::make_unique<FrameTimingsRecorder>();
        recorder->RecordVsync(frame_start, frame_target);
        const auto now = fml::TimePoint::Now();
        recorder->RecordBuildStart(now);
        recorder->RecordBuildEnd(now);
        rasterizer->DrawDenialRenderOutputs(std::move(render_view_ids),
                                            std::move(texture_identifiers),
                                            std::move(recorder));
      });
}
```
### engine/src/flutter/shell/common/rasterizer.cc: Rasterizer::PrepareDenialRenderOutputs, line 299

Revision: `d728e61e7d835e02c453c70ae9523a40f6c03215`. Full file SHA-256 `064ca3aec3f7aa89b111dfe2b214aaebb74f6457f12fd5ebfbc3ffa61f65c886`.

```cpp
Rasterizer::PrepareDenialRenderOutputs(
    std::vector<int64_t> render_view_ids,
    std::vector<int64_t> texture_identifiers) {
  denial_selected_render_view_ids_.clear();
  denial_selected_render_view_ids_.insert(render_view_ids.begin(),
                                          render_view_ids.end());
  denial_render_selection_pending_ = true;
  for (int64_t texture_id : texture_identifiers) {
    MarkTextureFrameAvailable(texture_id);
  }
}
```

### engine/src/flutter/shell/common/rasterizer.cc: Rasterizer::DrawDenialRenderOutputs, line 311

Revision: `d728e61e7d835e02c453c70ae9523a40f6c03215`. Full file SHA-256 `064ca3aec3f7aa89b111dfe2b214aaebb74f6457f12fd5ebfbc3ffa61f65c886`.

```cpp
Rasterizer::DrawDenialRenderOutputs(
    std::vector<int64_t> render_view_ids,
    std::vector<int64_t> texture_identifiers,
    std::unique_ptr<FrameTimingsRecorder> frame_timings_recorder) {
  if (!surface_) {
    return;
  }
  for (int64_t texture_id : texture_identifiers) {
    MarkTextureFrameAvailable(texture_id);
  }

  auto dirty_texture_ids = std::move(pending_texture_ids_);
  pending_texture_ids_.clear();
  std::vector<std::unique_ptr<LayerTreeTask>> tasks;
  tasks.reserve(render_view_ids.size());
  for (int64_t view_id : render_view_ids) {
    std::unique_ptr<LayerTreeTask> task;
    auto pending = denial_pending_output_tasks_.find(view_id);
    if (pending != denial_pending_output_tasks_.end()) {
      task = std::move(pending->second);
      denial_pending_output_tasks_.erase(pending);
      const auto* output = FindDenialRenderOutput(view_id);
      if (output) {
        auto reprojected = ReprojectDenialRenderOutputTask(*output, *task);
        if (reprojected) {
          task = std::move(reprojected);
        }
      }
    } else {
      auto view = view_records_.find(view_id);
      if (view == view_records_.end() || !view->second.last_successful_task) {
        continue;
      }
      const auto* output = FindDenialRenderOutput(view_id);
      if (output) {
        task = ReprojectDenialRenderOutputTask(
            *output, *view->second.last_successful_task);
      }
      if (!task) {
        task = std::move(view->second.last_successful_task);
        task->is_reused_layer_tree = true;
      }
    }
    task->dirty_texture_ids = dirty_texture_ids;
    tasks.push_back(std::move(task));
  }
  if (tasks.empty()) {
    pending_texture_ids_ = std::move(dirty_texture_ids);
    return;
  }

  DoDrawResult result =
      DrawToSurfaces(*frame_timings_recorder, std::move(tasks));
  if (external_view_embedder_ && external_view_embedder_->GetUsedThisFrame()) {
    bool should_resubmit_frame = ShouldResubmitFrame(result);
    external_view_embedder_->SetUsedThisFrame(false);
    external_view_embedder_->EndFrame(should_resubmit_frame,
                                      raster_thread_merger_);
  }
}
```

### engine/src/flutter/shell/common/rasterizer.cc: Rasterizer::ExpandDenialRenderOutputTasks, line 438

Revision: `d728e61e7d835e02c453c70ae9523a40f6c03215`. Full file SHA-256 `064ca3aec3f7aa89b111dfe2b214aaebb74f6457f12fd5ebfbc3ffa61f65c886`.

```cpp
Rasterizer::ExpandDenialRenderOutputTasks(
    std::vector<std::unique_ptr<LayerTreeTask>> tasks) {
  if (denial_render_outputs_.empty()) {
    return tasks;
  }

  std::vector<std::unique_ptr<LayerTreeTask>> expanded;
  expanded.reserve(tasks.size() + denial_render_outputs_.size());
  bool expanded_implicit_view = false;
  for (auto& task : tasks) {
    if (task->view_id != kFlutterImplicitViewId) {
      expanded.push_back(std::move(task));
      continue;
    }

    expanded_implicit_view = true;
    const auto source_root = task->layer_tree->root_layer_shared();
    const float source_device_pixel_ratio = task->device_pixel_ratio;
    FML_DCHECK(source_device_pixel_ratio > 0.0f);
    for (const auto& output : denial_render_outputs_) {
      const auto& source = output.source_physical_bounds;
      const DlSize source_logical_size(
          source.GetWidth() / source_device_pixel_ratio,
          source.GetHeight() / source_device_pixel_ratio);
      auto source_clip = std::make_shared<DenialRenderOutputSourceLayer>(
          source, source_logical_size);
      source_clip->Add(source_root);
      auto transform =
          std::make_shared<TransformLayer>(output.source_to_target_transform);
      transform->Add(source_clip);
      auto clip = std::make_shared<ClipRectLayer>(
          DlRect::MakeWH(output.target_size.width, output.target_size.height),
          Clip::kHardEdge);
      clip->Add(transform);

      // These layers are synthesized after SceneBuilder has established the
      // framework layer identities. Link them to the previous projection for
      // this output so damage diffing can reach the actual Flutter scene.
      auto previous_view = view_records_.find(output.render_view_id);
      if (previous_view != view_records_.end() &&
          previous_view->second.last_successful_task &&
          previous_view->second.last_successful_task
                  ->render_output_configuration_generation ==
              output.configuration_generation) {
        Layer* previous_clip = previous_view->second.last_successful_task
                                   ->layer_tree->root_layer();
        const ContainerLayer* previous_clip_container =
            previous_clip->as_container_layer();
        if (previous_clip_container &&
            previous_clip_container->layers().size() == 1u) {
          Layer* previous_transform =
              previous_clip_container->layers().front().get();
          const ContainerLayer* previous_transform_container =
              previous_transform->as_container_layer();
          if (previous_transform_container &&
              previous_transform_container->layers().size() == 1u) {
            clip->AssignOldLayer(previous_clip);
            transform->AssignOldLayer(previous_transform);
            source_clip->AssignOldLayer(
                previous_transform_container->layers().front().get());
          }
        }
      }

      auto output_task = std::make_unique<LayerTreeTask>(
          output.render_view_id,
          std::make_unique<LayerTree>(clip, output.target_size),
          static_cast<float>(output.scale_120) / 120.0f);
      output_task->render_output_configuration_generation =
          output.configuration_generation;
      output_task->dirty_texture_ids = task->dirty_texture_ids;
      const bool selected =
          !denial_render_selection_pending_ ||
          denial_selected_render_view_ids_.contains(output.render_view_id);
      if (selected) {
        denial_pending_output_tasks_.erase(output.render_view_id);
        expanded.push_back(std::move(output_task));
      } else {
        denial_pending_output_tasks_[output.render_view_id] =
            std::move(output_task);
      }
    }
  }
  if (expanded_implicit_view) {
    denial_selected_render_view_ids_.clear();
    denial_render_selection_pending_ = false;
  }
  return expanded;
}
```
