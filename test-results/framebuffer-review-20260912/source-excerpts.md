# Exact source excerpts for framebuffer review

These are unmodified excerpts, with original line numbers in the headings.
Full-file SHA-256 values bind each excerpt. Diagnostics are in the separate patch.
Denial base: 85b2303e2f09ae7b7b993641f90061a200f03d53.
Smithay base: 812bd33259ff58810dadef6086d8385eeac1ca55.
Upstream licenses and copyright remain those of the pinned source projects;
these excerpts do not establish a new project-wide license.

## Denial: `compositor/src/bin/deniald/startup.rs:285–396`

Full-file SHA-256: `2093bc8e7e9f8381ed74310af1a0e3cd9251bd797a0953383d99c60f75317e43`

```rust
            .find(|planned| planned.id == output.id)
            .ok_or("output missing from atlas plan")?
            .source_rect;

        kms.scanouts.push(Scanout {
            output,
            surface,
            plane_properties,
            source_rect,
            original_mode,
            powered: true,
        });
    }

    let cross_device_rendering = render_device != options.device;
    let gbm = GbmDevice::new(render_fd.clone()).map_err(|error| {
        format!(
            "could not create GBM device for {}: {error}",
            render_device.display()
        )
    })?;
    let gbm_flags = GbmBufferFlags::RENDERING | GbmBufferFlags::SCANOUT;
    let mut allocator = GbmAllocator::new(gbm.clone(), gbm_flags);
    let mut scanout_allocator = ScanoutAllocator::gbm(
        GbmAllocator::new(gbm.clone(), scanout_gbm_flags(cross_device_rendering)),
        drm_fd.clone(),
        cross_device_rendering,
    );
    // SAFETY: the GBM device outlives the EGL display, context, renderer and
    // every imported dmabuf created below. All of them are dropped in this
    // function before `gbm`, `render_fd`, and `drm_fd`.
    let egl_display = unsafe { EGLDisplay::new(gbm.clone()) }.map_err(|error| {
        format!(
            "could not create EGL display for {}: {error}",
            render_device.display()
        )
    })?;
    let mut swapchains = if options.flutter_bundle.is_some() {
        #[cfg(feature = "flutter")]
        {
            let render_outputs = atlas
                .render_outputs(&snapshot)
                .ok_or("initial Flutter output plans do not match topology")?;
            RenderSwapchains::Outputs {
                desktop_size: atlas.pixel_size,
                swapchains: OutputSwapchains::allocate(
                    &mut scanout_allocator,
                    &render_outputs,
                    &kms.scanouts,
                    egl_display.dmabuf_render_formats(),
                    options.flutter_offscreen_blit,
                )?,
            }
        }
        #[cfg(not(feature = "flutter"))]
        return Err("Flutter feature was checked before allocating scanout buffers".into());
    } else {
        let atlas_modifiers =
            shared_atlas_modifiers(&kms.scanouts, egl_display.dmabuf_render_formats())?;
        let atlas_swapchain = AtlasSwapchain::allocate(
            &mut scanout_allocator,
            atlas.pixel_size,
            &atlas_modifiers,
        )
        .map_err(|error| {
            format!(
                "could not allocate diagnostic atlas on render device {} for KMS device {}: {error}",
                render_device.display(),
                options.device.display()
            )
        })?;
        RenderSwapchains::Atlas(atlas_swapchain)
    };
    let egl_context = egl_context::create_render_context(&egl_display)?;
    // SAFETY: `egl_context` is current only through this renderer and remains
    // alive for the renderer's entire lifetime.
    let mut renderer = unsafe { GlesRenderer::new(egl_context)? };
    if let Some(frontend) = wayland.as_mut() {
        frontend.init_renderer(&mut renderer)?;
    }
    if options.flutter_bundle.is_some() {
        #[cfg(feature = "flutter")]
        for pool in &mut swapchains
            .outputs_mut()
            .ok_or("Flutter output pools were not allocated")?
            .outputs
        {
            render_blank_target(
                &mut renderer,
                &mut pool.buffers[pool.current].dmabuf,
                pool.size,
            )?;
        }
    } else {
        let atlas_swapchain = swapchains
            .atlas_mut()
            .ok_or("diagnostic rendering has no atlas swapchain")?;
        render_diagnostic_atlas(
            &mut renderer,
            &mut atlas_swapchain.buffers[atlas_swapchain.current].dmabuf,
            atlas_swapchain.size,
            &kms.scanouts,
            0,
        )?;
    }

    let fb = swapchains.representative_framebuffer();

    info!(
        device = %options.device.display(),
        render_device = %render_device.display(),
        outputs = kms.scanouts.len(),
```

## Denial: `compositor/src/bin/deniald/kms_state.rs:480–522`

Full-file SHA-256: `530af227560a43667e5d62933dfb2faa0cb9e0953060d8aae92eef2db31e7ff0`

```rust
    render_target: Option<LinearRenderBuffer>,
    _buffer: GbmBuffer,
}

impl ScanoutBuffer {
    fn allocate_gbm(
        allocator: &mut GbmAllocator<DrmDeviceFd>,
        drm_fd: &DrmDeviceFd,
        cross_device: bool,
        size: PixelSize,
        modifiers: &[Modifier],
    ) -> Result<Self, Box<dyn Error>> {
        let buffer =
            allocator.create_buffer(size.width, size.height, Fourcc::Xrgb8888, modifiers)?;
        let format = smithay::backend::allocator::Buffer::format(&buffer);
        let dmabuf = buffer.export()?;
        let framebuffer = if cross_device {
            AtlasFramebuffer::Prime(framebuffer_from_prime_dmabuf(drm_fd, &dmabuf)?)
        } else {
            AtlasFramebuffer::Gbm(framebuffer_from_bo(drm_fd, &buffer, true)?)
        };
        Ok(Self {
            framebuffer,
            dmabuf,
            format,
            render_target: None,
            _buffer: buffer,
        })
    }

    pub(super) fn framebuffer(&self) -> framebuffer::Handle {
        self.framebuffer.handle()
    }

    pub(super) fn format(&self) -> Format {
        self.format
    }

    #[cfg(feature = "flutter")]
    pub(super) fn flutter_target_dmabufs(&self) -> (&Dmabuf, Option<&Dmabuf>) {
        (
            &self.dmabuf,
            self.render_target.as_ref().map(|target| &target.dmabuf),
```

## Denial: `compositor/src/bin/deniald/kms_state.rs:1177–1245`

Full-file SHA-256: `530af227560a43667e5d62933dfb2faa0cb9e0953060d8aae92eef2db31e7ff0`

```rust
        return Err(
            "The prepared JIT Flutter engine changed after this Denial session loaded its native development runtime. Restart the Denial session before enabling live UI development."
                .into(),
        );
    }
    Ok(())
}

fn common_xrgb8888_modifiers<'a>(
    format_sets: impl IntoIterator<Item = &'a FormatSet>,
) -> Vec<Modifier> {
    let mut format_sets = format_sets.into_iter();
    let Some(first) = format_sets.next() else {
        return Vec::new();
    };
    let remaining = format_sets.collect::<Vec<_>>();
    first
        .iter()
        .filter(|format| format.code == Fourcc::Xrgb8888 && format.modifier != Modifier::Invalid)
        .filter(|format| remaining.iter().all(|formats| formats.contains(format)))
        .map(|format| format.modifier)
        .collect()
}

fn compatible_xrgb8888_modifiers<'a>(
    plane_formats: impl IntoIterator<Item = &'a FormatSet>,
    render_formats: &FormatSet,
) -> Vec<Modifier> {
    let plane_formats = plane_formats.into_iter().collect::<Vec<_>>();
    let mut modifiers = common_xrgb8888_modifiers(plane_formats.iter().copied());
    let renderer_has_explicit_modifiers = render_formats
        .iter()
        .any(|format| format.code == Fourcc::Xrgb8888 && format.modifier != Modifier::Invalid);
    if renderer_has_explicit_modifiers {
        modifiers.retain(|modifier| {
            render_formats.contains(&Format {
                code: Fourcc::Xrgb8888,
                modifier: *modifier,
            })
        });
    } else {
        modifiers.retain(|modifier| *modifier == Modifier::Linear);
    }

    let implicit_xrgb8888 = Format {
        code: Fourcc::Xrgb8888,
        modifier: Modifier::Invalid,
    };
    if modifiers.is_empty()
        && !plane_formats.is_empty()
        && plane_formats
            .iter()
            .all(|formats| formats.contains(&implicit_xrgb8888))
        && render_formats.contains(&implicit_xrgb8888)
    {
        // GBM may satisfy this through an explicit LINEAR allocation or its
        // legacy implicit allocation path. Both are safe when every consumer
        // advertises implicit XR24, unlike guessing a vendor modifier.
        modifiers.push(Modifier::Linear);
    }

    modifiers
}

/// Return XR24 modifiers that every primary plane can scan out and EGL can
/// render into. Plane order is retained: DRM exposes the driver's preferred
/// tiled/compressed layouts first and LINEAR last on hardware that supports
/// both. If there is no explicit intersection but every consumer advertises
/// legacy implicit XR24, fall back to a LINEAR allocation request rather than
```

## Denial: `compositor/src/bin/deniald/kms_render.rs:55–78`

Full-file SHA-256: `8c5af738293b3c18d7009c2e6da77f5836b2df05095ded33ca3418af29e13db2`

```rust

pub(super) fn render_blank_target(
    renderer: &mut GlesRenderer,
    dmabuf: &mut Dmabuf,
    target_size: PixelSize,
) -> Result<(), Box<dyn Error>> {
    let render_size = (
        i32::try_from(target_size.width)?,
        i32::try_from(target_size.height)?,
    )
        .into();
    let mut framebuffer = renderer.bind(dmabuf)?;
    let mut frame = renderer.render(&mut framebuffer, render_size, Transform::Normal)?;
    frame.clear(
        Color32F::new(0.0, 0.0, 0.0, 1.0),
        &[Rectangle::from_size(render_size)],
    )?;
    frame.finish()?.wait()?;
    Ok(())
}

#[cfg(feature = "flutter")]
pub(super) fn render_blank_output_swapchains(
    renderer: &mut GlesRenderer,
```

## Smithay: `src/backend/allocator/gbm.rs:99–130`

Full-file SHA-256: `cf510131d2a0e283df87b3e7d1e677cf9c2d1325475abd56ddc1f547196143a7`

```rust
    ///
    /// `implicit` forces the object to assume the modifier is `Invalid` for cases,
    /// where the buffer was allocated with an older api, that doesn't support modifiers.
    ///
    /// Gbm might otherwise give us the underlying or a non-sensical modifier,
    /// which can fail in various other apis.
    pub fn from_bo_with_node(bo: BufferObject<()>, implicit: bool, drm_node: Option<DrmNode>) -> Self {
        let size = (bo.width() as i32, bo.height() as i32).into();
        let format = Format {
            code: bo.format(),
            modifier: if implicit {
                Modifier::Invalid
            } else {
                bo.modifier()
            },
        };
        Self {
            drm_node,
            bo,
            size,
            format,
        }
    }

    /// Get the [`DrmNode`] of the device the buffer was allocated when available
    pub fn device_node(&self) -> Option<DrmNode> {
        self.drm_node
    }
}

impl std::ops::Deref for GbmBuffer {
    type Target = BufferObject<()>;
```

## Smithay: `src/backend/allocator/gbm.rs:187–238`

Full-file SHA-256: `cf510131d2a0e283df87b3e7d1e677cf9c2d1325475abd56ddc1f547196143a7`

```rust
    /// a different set of usage flags.
    #[instrument(level = "trace", skip(self), fields(self.device = ?self.device, err))]
    #[profiling::function]
    pub fn create_buffer_with_flags(
        &mut self,
        width: u32,
        height: u32,
        fourcc: Fourcc,
        modifiers: &[Modifier],
        flags: GbmBufferFlags,
    ) -> Result<GbmBuffer, std::io::Error> {
        #[cfg(feature = "backend_gbm_has_create_with_modifiers2")]
        let result = self
            .device
            .create_buffer_object_with_modifiers2(width, height, fourcc, modifiers.iter().copied(), flags)
            .map(|bo| GbmBuffer::from_bo_with_node(bo, false, self.drm_node));

        #[cfg(not(feature = "backend_gbm_has_create_with_modifiers2"))]
        let result = if (flags & !(GbmBufferFlags::SCANOUT | GbmBufferFlags::RENDERING)).is_empty() {
            self.device
                .create_buffer_object_with_modifiers(width, height, fourcc, modifiers.iter().copied())
                .map(|bo| GbmBuffer::from_bo_with_node(bo, false, self.drm_node))
        } else if modifiers.contains(&Modifier::Invalid) || modifiers.contains(&Modifier::Linear) {
            return self
                .device
                .create_buffer_object(width, height, fourcc, flags)
                .map(|bo| GbmBuffer::from_bo_with_node(bo, true, self.drm_node));
        } else {
            return Err(std::io::Error::new(
                std::io::ErrorKind::Other,
                "unsupported combination of flags and modifiers",
            ));
        };

        match result {
            Ok(bo) => Ok(bo),
            Err(err) => {
                if modifiers.contains(&Modifier::Invalid) || modifiers.contains(&Modifier::Linear) {
                    self.device
                        .create_buffer_object(width, height, fourcc, flags)
                        .map(|bo| GbmBuffer::from_bo_with_node(bo, true, self.drm_node))
                } else {
                    Err(err)
                }
            }
        }
    }
}

impl<A: AsFd + 'static> Allocator for GbmAllocator<A> {
    type Buffer = GbmBuffer;
    type Error = std::io::Error;
```

## Smithay: `src/backend/renderer/gles/mod.rs:710–750`

Full-file SHA-256: `4ce214ebc65cc26042e806d7272d9fcb9921388c09db03df53f45cd7bbb86edd`

```rust
        unsafe {
            self.egl.make_current()?;
        }

        let bind = || {
            let mut sync_lock = texture.0.sync.write().unwrap();
            let mut fbo = 0;
            unsafe {
                sync_lock.wait_for_all(&self.gl);
                self.gl.GenFramebuffers(1, &mut fbo as *mut _);
                self.gl.BindFramebuffer(ffi::FRAMEBUFFER, fbo);
                self.gl.FramebufferTexture2D(
                    ffi::FRAMEBUFFER,
                    ffi::COLOR_ATTACHMENT0,
                    ffi::TEXTURE_2D,
                    texture.0.texture,
                    0,
                );
                let status = self.gl.CheckFramebufferStatus(ffi::FRAMEBUFFER);
                self.gl.BindFramebuffer(ffi::FRAMEBUFFER, 0);

                if status != ffi::FRAMEBUFFER_COMPLETE {
                    self.gl.DeleteFramebuffers(1, &mut fbo as *mut _);
                    return Err(GlesError::FramebufferBindingError);
                }
            }

            Ok(GlesTarget(GlesTargetInternal::Texture {
                texture: texture.clone(),
                sync_lock,
                destruction_callback_sender: self.gles_cleanup().sender.clone(),
                fbo,
            }))
        };

        bind().inspect_err(|_| {
            if let Err(err) = self.unbind() {
                self.span.in_scope(|| warn!(?err, "Failed to unbind on err"));
            }
        })
    }
```

## Smithay: `src/backend/renderer/gles/mod.rs:1202–1253`

Full-file SHA-256: `4ce214ebc65cc26042e806d7272d9fcb9921388c09db03df53f45cd7bbb86edd`

```rust
impl ImportDma for GlesRenderer {
    #[instrument(level = "trace", parent = &self.span, skip(self))]
    #[profiling::function]
    fn import_dmabuf(
        &mut self,
        buffer: &Dmabuf,
        _damage: Option<&[Rectangle<i32, BufferCoord>]>,
    ) -> Result<GlesTexture, GlesError> {
        use crate::backend::allocator::Buffer;
        if !self.extensions.iter().any(|ext| ext == "GL_OES_EGL_image") {
            return Err(GlesError::GLExtensionNotSupported(&["GL_OES_EGL_image"]));
        }

        self.existing_dmabuf_texture(buffer)?.map(Ok).unwrap_or_else(|| {
            let is_external = !self.egl.dmabuf_render_formats().contains(&buffer.format());
            let image = self
                .egl
                .display()
                .create_image_from_dmabuf(buffer)
                .map_err(GlesError::BindBufferEGLError)?;

            let tex = match self.import_egl_image(image, is_external, None) {
                Ok(tex) => tex,
                Err(err) => {
                    unsafe {
                        ffi_egl::DestroyImageKHR(**self.egl.display().get_display_handle(), image);
                    }
                    return Err(err);
                }
            };
            let format = fourcc_to_gl_formats(buffer.format().code)
                .map(|(internal, _, _)| internal)
                .unwrap_or(ffi::RGBA8);
            let has_alpha = has_alpha(buffer.format().code);
            let texture = GlesTexture(Arc::new(GlesTextureInternal {
                texture: tex,
                sync: RwLock::default(),
                format: Some(format),
                has_alpha,
                is_external,
                y_inverted: buffer.y_inverted(),
                size: buffer.size(),
                egl_images: Some(vec![image]),
                destruction_callback_sender: self.gles_cleanup().sender.clone(),
            }));
            self.dmabuf_cache.insert(buffer.weak(), texture.clone());
            Ok(texture)
        })
    }

    fn dmabuf_formats(&self) -> FormatSet {
        self.egl.dmabuf_texture_formats().clone()
```

## Smithay: `src/backend/renderer/gles/mod.rs:1486–1511`

Full-file SHA-256: `4ce214ebc65cc26042e806d7272d9fcb9921388c09db03df53f45cd7bbb86edd`

```rust

impl Bind<Dmabuf> for GlesRenderer {
    fn bind<'a>(&mut self, dmabuf: &'a mut Dmabuf) -> Result<GlesTarget<'a>, GlesError> {
        let mut bind = |dmabuf: &'a mut Dmabuf| {
            let texture = self.import_dmabuf(dmabuf, None)?;
            if texture.0.is_external {
                return Err(GlesError::FramebufferBindingError);
            }
            self.bind_texture(&texture)
                // SAFETY: The lifetime of the target only depends on the dmabuf,
                // as the GlesTexture is cloned internally.
                .map(|tex| unsafe { std::mem::transmute::<GlesTarget<'_>, GlesTarget<'a>>(tex) })
        };

        bind(dmabuf).inspect_err(|_| {
            if let Err(err) = self.unbind() {
                self.span.in_scope(|| warn!(?err, "Failed to unbind on err"));
            }
        })
    }

    fn supported_formats(&self) -> Option<FormatSet> {
        Some(self.egl.display().dmabuf_render_formats().clone())
    }
}

```

## Smithay: `src/backend/egl/display.rs:921–1007`

Full-file SHA-256: `a4e862ea7225984a826393a85c894026be03be4dc35ff0600cf896cbd4ee6368`

```rust
        }
    };

    let mut texture_formats = IndexSet::new();
    let mut render_formats = IndexSet::new();

    for fourcc in formats {
        let mut num = 0i32;
        // Some drivers return EGL_BAD_PARAMETER here for formats
        // they themselves returned for the query above.. *sigh*
        //
        // - NVIDIA proprietary since 520
        //
        // So lets ignore any errors of this call on purpose(!),
        // which will let `num` stay at `0` and handle the format
        // as unsupported by explicit modifiers.
        // Which is probably what the error is suppose to indicate
        // although the spec doesn't seem to demand it...
        match wrap_egl_call_bool(|| unsafe {
            ffi::egl::QueryDmaBufModifiersEXT(
                *display,
                fourcc as i32,
                0,
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                &mut num as *mut _,
            )
        }) {
            Ok(_) => {}
            Err(EGLError::BadParameter) => {
                debug!(
                    "eglQueryDmaBufModifiersEXT returned BadParameter for {:?}",
                    fourcc
                );
                num = 0;
            }
            Err(x) => {
                return Err(x);
            }
        };

        if num != 0 {
            let mut mods: Vec<u64> = Vec::with_capacity(num as usize);
            let mut external: Vec<ffi::egl::types::EGLBoolean> = Vec::with_capacity(num as usize);

            wrap_egl_call_bool(|| unsafe {
                ffi::egl::QueryDmaBufModifiersEXT(
                    *display,
                    fourcc as i32,
                    num,
                    mods.as_mut_ptr(),
                    external.as_mut_ptr(),
                    &mut num as *mut _,
                )
            })?;

            unsafe {
                mods.set_len(num as usize);
                external.set_len(num as usize);
            }

            for (modifier, external_only) in mods.into_iter().zip(external) {
                let format = DrmFormat {
                    code: fourcc,
                    modifier: Modifier::from(modifier),
                };
                texture_formats.insert(format);
                if external_only == 0 {
                    render_formats.insert(format);
                }
            }
        }

        texture_formats.insert(DrmFormat {
            code: fourcc,
            modifier: Modifier::Invalid,
        });
        render_formats.insert(DrmFormat {
            code: fourcc,
            modifier: Modifier::Invalid,
        });
    }

    trace!("Supported dmabuf import formats: {:?}", texture_formats);
    trace!("Supported dmabuf render formats: {:?}", render_formats);

    Ok((
```
