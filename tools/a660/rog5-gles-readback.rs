//! One offscreen GLES 3.2/3.0 shader/readback. Optional same-context DMA-BUF roundtrip; no KMS or admission.
//! Run only under an external deadline: synchronous driver calls can block.
use std::ffi::{c_char, c_int, c_uint, c_void, CStr};
use std::ptr;
use std::os::unix::fs::FileTypeExt;
use std::os::fd::{AsRawFd, FromRawFd, IntoRawFd, OwnedFd};
use std::time::{Duration, Instant};

type Handle = *mut c_void;
type Result<T> = std::result::Result<T, String>;

#[link(name = "dl")]
extern "C" {
    fn dlopen(name: *const c_char, flags: c_int) -> Handle;
    fn dlsym(handle: Handle, name: *const c_char) -> Handle;
    fn dlclose(handle: Handle) -> c_int;
    fn fcntl(fd: c_int, command: c_int, ...) -> c_int;
    fn poll(fds: *mut PollFd, count: usize, timeout: c_int) -> c_int;
    fn ioctl(fd: c_int, request: std::ffi::c_ulong, ...) -> c_int;
}

#[repr(C)]
struct PollFd { fd: c_int, events: i16, revents: i16 }
#[repr(C)]
#[derive(Default)]
struct SyncFileInfo {
    name: [u8; 32], status: i32, flags: u32, num_fences: u32,
    pad: u32, sync_fence_info: u64,
}

fn wait_native_fd(fd: &OwnedFd) -> Result<()> {
    let deadline = Instant::now() + Duration::from_secs(1);
    loop {
        let remaining = deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() { return Err("native fence wait timeout".into()); }
        let timeout = remaining.as_millis().clamp(1, 1000) as c_int;
        let mut entry = PollFd { fd: fd.as_raw_fd(), events: 1, revents: 0 };
        // Poll borrows the live descriptor; all waits share one deadline.
        let result = unsafe { poll(&mut entry, 1, timeout) };
        if result < 0 {
            let error = std::io::Error::last_os_error();
            if error.kind() == std::io::ErrorKind::Interrupted { continue; }
            return Err(format!("native fence poll: {error}"));
        }
        if result == 0 { continue; }
        if entry.revents != 1 { return Err(format!("native fence poll events=0x{:x}", entry.revents)); }
        let mut info = SyncFileInfo::default();
        // Linux _IOWR('>', 4, struct sync_file_info), verified on x86_64/aarch64.
        let request = (3 << 30) | (std::mem::size_of::<SyncFileInfo>() << 16) | (62 << 8) | 4;
        // num_fences=0 requests only the fixed header; no user array is supplied.
        if unsafe { ioctl(fd.as_raw_fd(), request as std::ffi::c_ulong, &mut info) } != 0 {
            return Err(format!("native sync_file info: {}", std::io::Error::last_os_error()));
        }
        if info.status != 1 { return Err(format!("native sync_file status={}", info.status)); }
        return Ok(());
    }
}

struct Library(Handle);
impl Library {
    fn open(name: &'static [u8]) -> Result<Self> {
        // Static library names are NUL terminated; RTLD_NOW | RTLD_LOCAL.
        let handle = unsafe { dlopen(name.as_ptr().cast(), 2) };
        if handle.is_null() { return Err(format!("load {} failed", String::from_utf8_lossy(name))); }
        Ok(Self(handle))
    }
    fn symbol(&self, name: &'static [u8]) -> Result<Handle> {
        // The handle lives until all loaded function pointers are discarded.
        let symbol = unsafe { dlsym(self.0, name.as_ptr().cast()) };
        if symbol.is_null() { return Err(format!("missing symbol {}", String::from_utf8_lossy(name))); }
        Ok(symbol)
    }
}
impl Drop for Library {
    fn drop(&mut self) { unsafe { dlclose(self.0); } }
}

macro_rules! gbm_api {
    ($($name:ident($($arg:ty),*) -> $ret:ty;)+) => {
        #[allow(non_snake_case)]
        struct GbmApi { $($name: unsafe extern "C" fn($($arg),*) -> $ret,)+ _library: Library }
        impl GbmApi {
            fn load() -> Result<Self> {
                let library = Library::open(b"libgbm.so.1\0")?;
                Ok(Self { $($name: unsafe { std::mem::transmute::<Handle, unsafe extern "C" fn($($arg),*) -> $ret>(library.symbol(concat!(stringify!($name), "\0").as_bytes())?) },)+ _library: library })
            }
        }
    }
}
gbm_api! {
    gbm_create_device(c_int) -> Handle;
    gbm_device_destroy(Handle) -> ();
    gbm_bo_create_with_modifiers2(Handle, u32, u32, u32, *const u64, u32, u32) -> Handle;
    gbm_bo_get_format(Handle) -> u32;
    gbm_bo_get_modifier(Handle) -> u64;
    gbm_bo_get_plane_count(Handle) -> c_int;
    gbm_bo_get_stride_for_plane(Handle, c_int) -> u32;
    gbm_bo_get_offset(Handle, c_int) -> u32;
    gbm_bo_get_fd_for_plane(Handle, c_int) -> c_int;
    gbm_bo_destroy(Handle) -> ();
}
struct Gbm { api: GbmApi, device: Handle, bo: Handle, _fd: std::fs::File }
impl Gbm {
    fn open(raw: c_int) -> Result<Self> {
        // Duplicate an explicitly inherited FD; no path discovery/open and no
        // ownership change to the caller's FD. F_DUPFD_CLOEXEC is Linux 1030.
        let cloned = unsafe { fcntl(raw, 1030, 3) };
        if cloned < 0 { return Err(format!("GBM descriptor duplication: {}", std::io::Error::last_os_error())); }
        let file = std::fs::File::from(unsafe { OwnedFd::from_raw_fd(cloned) });
        if !file.metadata().map_err(|e| format!("GBM descriptor metadata: {e}"))?.file_type().is_char_device() {
            return Err("GBM descriptor must be a character device".into());
        }
        // This type check is not device admission. The coordinator must bind
        // the exact render node/device/module identity before any physical run.
        let api = GbmApi::load()?;
        let device = unsafe { (api.gbm_create_device)(file.as_raw_fd()) };
        if device.is_null() { return Err("GBM device creation failed".into()); }
        Ok(Self { api, device, bo: ptr::null_mut(), _fd: file })
    }
    fn allocate(&mut self) -> Result<(OwnedFd, c_int, c_int, c_int)> {
        let a = &self.api;
        let linear = [0u64];
        // ABGR8888, 4x4, explicit LINEAR, GBM_BO_USE_RENDERING. No fallback
        // allocation or scanout request. Keep BO alive through EGL teardown.
        unsafe {
            self.bo = (a.gbm_bo_create_with_modifiers2)(self.device, 4, 4, 0x34324241, linear.as_ptr(), 1, 4);
            if self.bo.is_null() { return Err("GBM explicit linear allocation failed".into()); }
            let format = (a.gbm_bo_get_format)(self.bo);
            if format != 0x34324241 || (a.gbm_bo_get_plane_count)(self.bo) != 1 || (a.gbm_bo_get_modifier)(self.bo) != 0 {
                return Err("GBM allocation layout mismatch".into());
            }
            let stride = (a.gbm_bo_get_stride_for_plane)(self.bo, 0);
            let offset = (a.gbm_bo_get_offset)(self.bo, 0);
            if stride < 16 || stride > c_int::MAX as u32 || offset > c_int::MAX as u32 { return Err("GBM stride/offset out of EGL range".into()); }
            let raw = (a.gbm_bo_get_fd_for_plane)(self.bo, 0);
            if raw < 0 { return Err("GBM DMA-BUF export failed".into()); }
            Ok((OwnedFd::from_raw_fd(raw), format as c_int, stride as c_int, offset as c_int))
        }
    }
}
impl Drop for Gbm {
    fn drop(&mut self) {
        unsafe {
            if !self.bo.is_null() { (self.api.gbm_bo_destroy)(self.bo); }
            (self.api.gbm_device_destroy)(self.device);
        }
    }
}

// Signatures match EGL 1.5 / GLES 3.0. Keeping libraries in Api owns their lifetime.
macro_rules! api {
    ($($name:ident($($arg:ty),*) -> $ret:ty;)+) => {
        #[allow(non_snake_case)]
        struct Api { $($name: unsafe extern "C" fn($($arg),*) -> $ret,)+ _egl: Library, _gl: Library }
        impl Api {
            fn load() -> Result<Self> {
                let egl = Library::open(b"libEGL.so.1\0")?;
                let gl = Library::open(b"libGLESv2.so.2\0")?;
                Ok(Self {
                    $($name: {
                        let lib = if stringify!($name).starts_with("egl") { &egl } else { &gl };
                        let raw = lib.symbol(concat!(stringify!($name), "\0").as_bytes())?;
                        // POSIX dlsym function pointers have the declared C ABI.
                        unsafe { std::mem::transmute::<Handle, unsafe extern "C" fn($($arg),*) -> $ret>(raw) }
                    },)+ _egl: egl, _gl: gl,
                })
            }
        }
    }
}
api! {
    eglGetError() -> c_uint;
    eglGetProcAddress(*const c_char) -> Handle;
    eglCreateSync(Handle, c_uint, *const isize) -> Handle;
    eglDestroySync(Handle, Handle) -> c_uint;
    eglWaitSync(Handle, Handle, c_int) -> c_uint;
    eglQueryString(Handle, c_int) -> *const c_char;
    eglGetPlatformDisplay(c_uint, Handle, *const isize) -> Handle;
    eglInitialize(Handle, *mut c_int, *mut c_int) -> c_uint;
    eglBindAPI(c_uint) -> c_uint;
    eglChooseConfig(Handle, *const c_int, *mut Handle, c_int, *mut c_int) -> c_uint;
    eglCreatePbufferSurface(Handle, Handle, *const c_int) -> Handle;
    eglCreateContext(Handle, Handle, Handle, *const c_int) -> Handle;
    eglMakeCurrent(Handle, Handle, Handle, Handle) -> c_uint;
    eglDestroyContext(Handle, Handle) -> c_uint;
    eglDestroySurface(Handle, Handle) -> c_uint;
    eglTerminate(Handle) -> c_uint;
    glGetString(c_uint) -> *const c_char;
    glGetError() -> c_uint;
    glFlush() -> ();
    glFinish() -> ();
    eglCreateImage(Handle, Handle, c_uint, Handle, *const isize) -> Handle;
    eglDestroyImage(Handle, Handle) -> c_uint;
    glGenTextures(c_int, *mut c_uint) -> ();
    glBindTexture(c_uint, c_uint) -> ();
    glTexParameteri(c_uint, c_uint, c_int) -> ();
    glTexImage2D(c_uint, c_int, c_int, c_int, c_int, c_int, c_uint, c_uint, *const c_void) -> ();
    glDeleteTextures(c_int, *const c_uint) -> ();
    glGenFramebuffers(c_int, *mut c_uint) -> ();
    glBindFramebuffer(c_uint, c_uint) -> ();
    glFramebufferTexture2D(c_uint, c_uint, c_uint, c_uint, c_int) -> ();
    glCheckFramebufferStatus(c_uint) -> c_uint;
    glDeleteFramebuffers(c_int, *const c_uint) -> ();
    glGetIntegerv(c_uint, *mut c_int) -> ();
    glCreateShader(c_uint) -> c_uint;
    glShaderSource(c_uint, c_int, *const *const c_char, *const c_int) -> ();
    glCompileShader(c_uint) -> ();
    glGetShaderiv(c_uint, c_uint, *mut c_int) -> ();
    glDeleteShader(c_uint) -> ();
    glCreateProgram() -> c_uint;
    glAttachShader(c_uint, c_uint) -> ();
    glBindAttribLocation(c_uint, c_uint, *const c_char) -> ();
    glLinkProgram(c_uint) -> ();
    glGetProgramiv(c_uint, c_uint, *mut c_int) -> ();
    glUseProgram(c_uint) -> ();
    glDeleteProgram(c_uint) -> ();
    glViewport(c_int, c_int, c_int, c_int) -> ();
    glDisable(c_uint) -> ();
    glClearColor(f32, f32, f32, f32) -> ();
    glClear(c_uint) -> ();
    glVertexAttribPointer(c_uint, c_int, c_uint, u8, c_int, *const c_void) -> ();
    glEnableVertexAttribArray(c_uint) -> ();
    glDrawArrays(c_uint, c_int, c_int) -> ();
    glReadPixels(c_int, c_int, c_int, c_int, c_uint, c_uint, *mut c_void) -> ();
}

#[derive(Clone, Copy, Debug, PartialEq)]
enum Mode { A660, Software }
impl Mode {
    fn parse(args: &[String]) -> Result<Self> {
        match args {
            [mode] if mode == "--require-a660" => Ok(Self::A660),
            [mode] if mode == "--software-fixture" => Ok(Self::Software),
            _ => Err("usage: rog5-gles-readback --require-a660 | --software-fixture [--native-fence | --native-fence-import | --dma-buf | --gbm-fd=N] (external deadline required)".into()),
        }
    }
    fn scope(self) -> &'static str {
        match self { Self::A660 => "a660-offscreen-renderer-only", Self::Software => "software-fixture-only" }
    }
    fn check(self, renderer: &str) -> Result<()> {
        let accepted = match self {
            Self::A660 => matches!(renderer, "FD660" | "Adreno (TM) 660" | "Adreno 660"),
            Self::Software => (renderer.starts_with("llvmpipe (") && renderer.ends_with(')')) || renderer == "softpipe",
        };
        if accepted { Ok(()) } else { Err(format!("renderer refused for {}: {renderer}", self.scope())) }
    }
}

fn pixels_match(pixels: &[u8; 64]) -> Result<()> {
    for y in 0..4 {
        for x in 0..4 {
            // gl_FragCoord is at pixel centres; readback starts at the lower left.
            let expected = [((2 * x + 1) * 255 + 4) / 8, ((2 * y + 1) * 255 + 4) / 8, 64, 255];
            for channel in 0..4 {
                let actual = pixels[(y * 4 + x) * 4 + channel] as i32;
                if (actual - expected[channel] as i32).abs() > 1 {
                    return Err(format!("pixel mismatch x={x} y={y} channel={channel} actual={actual} expected={}", expected[channel]));
                }
            }
        }
    }
    Ok(())
}

fn string_value(raw: *const c_char, label: &str) -> Result<String> {
    if raw.is_null() { return Err(format!("{label} unavailable")); }
    // EGL/GL own these NUL terminated strings for the life of the current display.
    let value = unsafe { CStr::from_ptr(raw) }.to_str().map_err(|_| format!("{label} is not UTF-8"))?;
    if value.len() > 4096 || value.chars().any(char::is_control) { return Err(format!("invalid {label}")); }
    Ok(value.to_owned())
}
fn check(ok: c_uint, stage: &str) -> Result<()> {
    if ok != 0 { Ok(()) } else { Err(format!("{stage} failed")) }
}

fn combine(result: Result<()>, cleanup: Result<()>) -> Result<()> {
    match (result, cleanup) {
        (Ok(()), Ok(())) => Ok(()),
        (Err(e), Ok(())) | (Ok(()), Err(e)) => Err(e),
        (Err(e), Err(cleanup)) => Err(format!("{e}; {cleanup}")),
    }
}

struct Session<'a> {
    api: &'a Api,
    display: Handle,
    initialized: bool,
    producer_current: bool,
    surface: Handle,
    context: Handle,
    shaders: Vec<c_uint>,
    program: c_uint,
    textures: Vec<c_uint>,
    framebuffers: Vec<c_uint>,
    images: Vec<Handle>,
    gbm: Option<Gbm>,
    dma_metadata: Option<(c_int, c_int, c_int)>,
    requested_minor: c_int,
    actual_version: (c_int, c_int),
    preferred_error: c_uint,
}
impl<'a> Session<'a> {
    fn new(api: &'a Api) -> Self {
        Self { api, display: ptr::null_mut(), initialized: false, producer_current: false, surface: ptr::null_mut(), context: ptr::null_mut(), shaders: Vec::new(), program: 0, textures: Vec::new(), framebuffers: Vec::new(), images: Vec::new(), gbm: None, dma_metadata: None, requested_minor: 0, actual_version: (0, 0), preferred_error: 0 }
    }
    fn gl_check(&self, stage: &str) -> Result<()> {
        let error = unsafe { (self.api.glGetError)() };
        if error == 0 { Ok(()) } else { Err(format!("{stage}: GL error 0x{error:x}")) }
    }
    fn render(&mut self, mode: Mode, native_fence: bool, fence_import: bool, dma_buf: bool, gbm_fd: Option<c_int>) -> Result<(String, String, String)> {
        let a = self.api;
        // All pointer arguments below reference live arrays/handles of the exact
        // API types and lengths. GL calls follow a successful eglMakeCurrent.
        unsafe {
            let extensions = string_value((a.eglQueryString)(ptr::null_mut(), 0x3055), "EGL client extensions")?;
            if let Some(fd) = gbm_fd {
                if !extensions.split_ascii_whitespace().any(|e| matches!(e, "EGL_KHR_platform_gbm" | "EGL_MESA_platform_gbm")) { return Err("EGL GBM platform unavailable".into()); }
                let gbm = Gbm::open(fd)?;
                self.display = (a.eglGetPlatformDisplay)(0x31d7, gbm.device, ptr::null());
                self.gbm = Some(gbm);
            } else {
                if !extensions.split_ascii_whitespace().any(|e| e == "EGL_MESA_platform_surfaceless") { return Err("EGL_MESA_platform_surfaceless unavailable".into()); }
                self.display = (a.eglGetPlatformDisplay)(0x31dd, ptr::null_mut(), ptr::null());
            }
            if self.display.is_null() { return Err("eglGetPlatformDisplay failed".into()); }
            let (mut major, mut minor) = (0, 0);
            check((a.eglInitialize)(self.display, &mut major, &mut minor), "eglInitialize")?;
            self.initialized = true;
            if (major, minor) < (1, 5) { return Err("EGL 1.5 required".into()); }
            if gbm_fd.is_some() {
                let extensions = string_value((a.eglQueryString)(self.display, 0x3055), "EGL display extensions")?;
                if !extensions.split_ascii_whitespace().any(|e| e == "EGL_KHR_surfaceless_context") { return Err("GBM requires EGL_KHR_surfaceless_context".into()); }
            }
            check((a.eglBindAPI)(0x30a0), "eglBindAPI")?; // OPENGL_ES_API
            // PBUFFER_BIT, OPENGL_ES3_BIT, RGBA sizes and no depth/stencil requirement.
            let attributes = [0x3033, if gbm_fd.is_some() { 0 } else { 1 }, 0x3040, 0x40, 0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3021, 8, 0x3038];
            let (mut config, mut count) = (ptr::null_mut(), 0);
            check((a.eglChooseConfig)(self.display, attributes.as_ptr(), &mut config, 1, &mut count), "eglChooseConfig")?;
            if count != 1 || config.is_null() { return Err("no RGBA8 ES3 config".into()); }
            let size = [0x3057, 4, 0x3056, 4, 0x3038];
            if gbm_fd.is_none() {
            self.surface = (a.eglCreatePbufferSurface)(self.display, config, size.as_ptr());
            if self.surface.is_null() { return Err("eglCreatePbufferSurface failed".into()); }
            }
            // Match pinned Denial's preferred GLES 3.2 and fallback GLES 3.0.
            // EGL 1.5 defines both major and minor context attributes.
            for minor in [2, 0] {
                let attributes = [0x3098, 3, 0x30fb, minor, 0x3038];
                self.context = (a.eglCreateContext)(self.display, config, ptr::null_mut(), attributes.as_ptr());
                if !self.context.is_null() {
                    self.requested_minor = minor;
                    break;
                }
                let error = (a.eglGetError)();
                if minor == 2 {
                    self.preferred_error = error;
                } else {
                    return Err(format!("eglCreateContext failed: GLES 3.2 error=0x{:x}; GLES 3.0 error=0x{error:x}", self.preferred_error));
                }
            }
            check((a.eglMakeCurrent)(self.display, self.surface, self.surface, self.context), "eglMakeCurrent")?;
            self.producer_current = true;
            let renderer = string_value((a.glGetString)(0x1f01), "renderer")?;
            mode.check(&renderer)?;
            let vendor = string_value((a.glGetString)(0x1f00), "vendor")?;
            let version = string_value((a.glGetString)(0x1f02), "version")?;
            self.gl_check("identity")?;
            (a.glGetIntegerv)(0x821b, &mut self.actual_version.0);
            (a.glGetIntegerv)(0x821c, &mut self.actual_version.1);
            self.gl_check("GLES version query")?;
            if self.actual_version.1 < 0 || self.actual_version < (3, self.requested_minor) {
                return Err(format!("GLES context version {}.{} is below requested 3.{}", self.actual_version.0, self.actual_version.1, self.requested_minor));
            }
            let gbm_buffer = if let Some(gbm) = &mut self.gbm { Some(gbm.allocate()?) } else { None };
            if let Some((fd, fourcc, stride, offset)) = &gbm_buffer {
                self.dma_extensions(false)?;
                self.import_dma(fd, *fourcc, *stride, *offset)?;
            } else if dma_buf {
                self.dma_extensions(true)?;
                let texture = self.create_texture(true)?;
                self.attach_framebuffer(texture)?;
            }
            for (kind, source) in [
                (0x8b31, b"attribute vec2 position; void main() { gl_Position=vec4(position,0.,1.); }\0".as_slice()),
                (0x8b30, b"precision mediump float; void main() { gl_FragColor=vec4(gl_FragCoord.xy/4.,0.25,1.); }\0".as_slice()),
            ] {
                let shader = (a.glCreateShader)(kind);
                if shader == 0 { return Err("glCreateShader failed".into()); }
                self.shaders.push(shader);
                let source_ptr = source.as_ptr().cast();
                (a.glShaderSource)(shader, 1, &source_ptr, ptr::null());
                (a.glCompileShader)(shader);
                let mut compiled = 0;
                (a.glGetShaderiv)(shader, 0x8b81, &mut compiled);
                if compiled != 1 { return Err(format!("shader compile failed kind=0x{kind:x}")); }
            }
            self.program = (a.glCreateProgram)();
            if self.program == 0 { return Err("glCreateProgram failed".into()); }
            for shader in &self.shaders { (a.glAttachShader)(self.program, *shader); }
            (a.glBindAttribLocation)(self.program, 0, b"position\0".as_ptr().cast());
            (a.glLinkProgram)(self.program);
            let mut linked = 0;
            (a.glGetProgramiv)(self.program, 0x8b82, &mut linked);
            if linked != 1 { return Err("program link failed".into()); }
            (a.glUseProgram)(self.program);
            (a.glViewport)(0, 0, 4, 4);
            (a.glDisable)(0x0bd0); // DITHER: allow only quantization tolerance.
            (a.glClearColor)(0., 0., 0., 0.);
            (a.glClear)(0x4000);
            let vertices: [f32; 6] = [-1., -1., 3., -1., -1., 3.];
            (a.glVertexAttribPointer)(0, 2, 0x1406, 0, 0, vertices.as_ptr().cast());
            (a.glEnableVertexAttribArray)(0);
            (a.glDrawArrays)(0x0004, 0, 3);
            self.gl_check("draw")?;
            if native_fence { self.native_fence(fence_import, config)?; }
            if let Some((fd, fourcc, stride, offset)) = &gbm_buffer {
                (a.glFinish)();
                self.gl_check("GBM producer completion")?;
                self.import_dma(fd, *fourcc, *stride, *offset)?;
            } else if dma_buf { self.dma_roundtrip()?; }
            let mut pixels = [0u8; 64];
            (a.glReadPixels)(0, 0, 4, 4, 0x1908, 0x1401, pixels.as_mut_ptr().cast());
            self.gl_check("readback")?;
            pixels_match(&pixels)?;
            Ok((renderer, vendor, version))
        }
    }
    fn native_fence(&mut self, import: bool, config: Handle) -> Result<()> {
        let a = self.api;
        // The display and current GLES context are owned by this session.
        unsafe {
            let extensions = string_value((a.eglQueryString)(self.display, 0x3055), "EGL display extensions")?;
            for required in ["EGL_ANDROID_native_fence_sync", "EGL_KHR_fence_sync"] {
                if !extensions.split_ascii_whitespace().any(|value| value == required) {
                    return Err(format!("native fence unavailable: {required}"));
                }
            }
            let symbol = (a.eglGetProcAddress)(b"eglDupNativeFenceFDANDROID\0".as_ptr().cast());
            if symbol.is_null() { return Err("native fence export symbol unavailable".into()); }
            let export: unsafe extern "C" fn(Handle, Handle) -> c_int = std::mem::transmute(symbol);
            let sync = (a.eglCreateSync)(self.display, 0x3144, ptr::null());
            if sync.is_null() { return Err("native fence creation failed".into()); }
            let result = (|| {
                // Match Denial: fence after drawing, explicit flush before export.
                (a.glFlush)();
                self.gl_check("native fence flush")?;
                let raw = export(self.display, sync);
                if raw < 0 { return Err("native fence export failed".into()); }
                // Export transfers ownership of a new descriptor to the caller.
                let fd = OwnedFd::from_raw_fd(raw);
                if import { self.consume_native_fence(&fd, config)?; }
                wait_native_fd(&fd)
            })();
            // fd has closed on every path before destroying the producer sync.
            let destroyed = check((a.eglDestroySync)(self.display, sync), "native fence destruction");
            combine(result, destroyed)
        }
    }
    fn consume_native_fence(&mut self, fd: &OwnedFd, config: Handle) -> Result<()> {
        let a = self.api;
        // A separate unshared context and pbuffer isolate the consumer command
        // stream. No pixel/buffer sharing is claimed by this fence-only check.
        unsafe {
            let attributes = [0x3098, 3, 0x30fb, self.requested_minor, 0x3038];
            let context = (a.eglCreateContext)(self.display, config, ptr::null_mut(), attributes.as_ptr());
            if context.is_null() { return Err("consumer context creation failed".into()); }
            let size = [0x3057, 4, 0x3056, 4, 0x3038];
            let surface = (a.eglCreatePbufferSurface)(self.display, config, size.as_ptr());
            let mut switched = false;
            let result = (|| {
                if surface.is_null() { return Err("consumer surface creation failed".into()); }
                check((a.eglMakeCurrent)(self.display, surface, surface, context), "consumer make-current")?;
                switched = true;
                self.producer_current = false;
                let imported_fd = fd.try_clone().map_err(|e| format!("native fence duplicate: {e}"))?;
                let attributes = [0x3145, imported_fd.as_raw_fd() as isize, 0x3038];
                let imported = (a.eglCreateSync)(self.display, 0x3144, attributes.as_ptr());
                if imported.is_null() { return Err("native fence import failed".into()); }
                // Successful creation transfers the duplicate to EGL. On error
                // OwnedFd closes it, matching the pinned Smithay import path.
                let _ = imported_fd.into_raw_fd();
                let waited = (|| {
                    check((a.eglWaitSync)(self.display, imported, 0), "native fence server wait")?;
                    // A second native fence follows the server wait. Its export,
                    // bounded wait and Linux status prove consumer completion.
                    // import=false prevents recursion and keeps this context current.
                    self.native_fence(false, config)
                })();
                let destroyed = check((a.eglDestroySync)(self.display, imported), "imported fence destruction");
                combine(waited, destroyed)
            })();
            let restored = if switched {
                let result = check((a.eglMakeCurrent)(self.display, self.surface, self.surface, self.context), "producer context restoration");
                self.producer_current = result.is_ok();
                result
            } else { Ok(()) };
            // Destroy all independent resources even when restoration fails.
            // Final cleanup then avoids producer GL calls in the wrong context.
            let destroyed = check((a.eglDestroyContext)(self.display, context), "consumer context destruction");
            let surface_destroyed = if surface.is_null() { Ok(()) } else {
                check((a.eglDestroySurface)(self.display, surface), "consumer surface destruction")
            };
            combine(combine(combine(result, restored), destroyed), surface_destroyed)
        }
    }
    fn dma_extensions(&self, export: bool) -> Result<()> {
        let extensions = string_value(unsafe { (self.api.eglQueryString)(self.display, 0x3055) }, "EGL display extensions")?;
        for name in ["EGL_MESA_image_dma_buf_export", "EGL_EXT_image_dma_buf_import", "EGL_EXT_image_dma_buf_import_modifiers"] {
            if !export && name == "EGL_MESA_image_dma_buf_export" { continue; }
            if !extensions.split_ascii_whitespace().any(|value| value == name) {
                return Err(format!("DMA-BUF unavailable: {name}"));
            }
        }
        Ok(())
    }
    fn create_texture(&mut self, allocate: bool) -> Result<c_uint> {
        let a = self.api;
        // All objects stay session-owned, including partial setup failures.
        unsafe {
            let mut texture = 0;
            (a.glGenTextures)(1, &mut texture);
            if texture == 0 { return Err("texture creation failed".into()); }
            self.textures.push(texture);
            (a.glBindTexture)(0x0de1, texture);
            for (name, value) in [(0x2801, 0x2600), (0x2800, 0x2600), (0x2802, 0x812f), (0x2803, 0x812f)] {
                (a.glTexParameteri)(0x0de1, name, value);
            }
            if allocate { (a.glTexImage2D)(0x0de1, 0, 0x8058, 4, 4, 0, 0x1908, 0x1401, ptr::null()); }
            self.gl_check("texture setup")?;
            Ok(texture)
        }
    }
    fn attach_framebuffer(&mut self, texture: c_uint) -> Result<()> {
        let a = self.api;
        unsafe {
            let mut framebuffer = 0;
            (a.glGenFramebuffers)(1, &mut framebuffer);
            if framebuffer == 0 { return Err("framebuffer creation failed".into()); }
            self.framebuffers.push(framebuffer);
            (a.glBindFramebuffer)(0x8d40, framebuffer);
            (a.glFramebufferTexture2D)(0x8d40, 0x8ce0, 0x0de1, texture, 0);
            if (a.glCheckFramebufferStatus)(0x8d40) != 0x8cd5 { return Err("framebuffer incomplete".into()); }
            self.gl_check("framebuffer setup")
        }
    }
    fn dma_roundtrip(&mut self) -> Result<()> {
        let a = self.api;
        // This deliberately uses CPU completion, separating pixel sharing from
        // native-fence qualification. The external deadline covers glFinish.
        unsafe {
            (a.glFinish)();
            self.gl_check("DMA-BUF producer completion")?;
            let attributes = [0x30bc, 0, 0x30d2, 1, 0x3038]; // level 0, PRESERVED
            let image = (a.eglCreateImage)(self.display, self.context, 0x30b1, self.textures[0] as usize as Handle, attributes.as_ptr());
            if image.is_null() { return Err("DMA-BUF source image creation failed".into()); }
            self.images.push(image);
            let query = (a.eglGetProcAddress)(b"eglExportDMABUFImageQueryMESA\0".as_ptr().cast());
            let export = (a.eglGetProcAddress)(b"eglExportDMABUFImageMESA\0".as_ptr().cast());
            if query.is_null() || export.is_null() { return Err("DMA-BUF symbols unavailable".into()); }
            let query: unsafe extern "C" fn(Handle, Handle, *mut c_int, *mut c_int, *mut u64) -> c_uint = std::mem::transmute(query);
            let export: unsafe extern "C" fn(Handle, Handle, *mut c_int, *mut c_int, *mut c_int) -> c_uint = std::mem::transmute(export);
            let (mut fourcc, mut planes) = (0, 0);
            // MESA specifies at most four planes; query writes one modifier per
            // plane, even when this probe will subsequently refuse multi-plane.
            let mut modifiers = [u64::MAX; 4];
            check(query(self.display, image, &mut fourcc, &mut planes, modifiers.as_mut_ptr()), "DMA-BUF query")?;
            if planes != 1 || !matches!(fourcc, 0x34325241 | 0x34324241) || modifiers[0] != 0 {
                return Err(format!("DMA-BUF layout unsupported: fourcc=0x{fourcc:x} planes={planes} modifier=0x{:x}", modifiers[0]));
            }
            let (mut raw, mut stride, mut offset) = (-1, 0, -1);
            let exported = export(self.display, image, &mut raw, &mut stride, &mut offset);
            // The exporter can leave an FD on a failed partial operation. Own
            // any returned descriptor before checking the status or metadata.
            let fd = if raw >= 0 { Some(OwnedFd::from_raw_fd(raw)) } else { None };
            check(exported, "DMA-BUF export")?;
            let fd = fd.ok_or("DMA-BUF export returned no FD")?;
            if stride < 16 || offset < 0 { return Err("DMA-BUF invalid stride/offset".into()); }
            self.import_dma(&fd, fourcc, stride, offset)
        }
    }
    fn import_dma(&mut self, fd: &OwnedFd, fourcc: c_int, stride: c_int, offset: c_int) -> Result<()> {
        let a = self.api;
        unsafe {
            let attributes = [0x3057, 4, 0x3056, 4, 0x3271, fourcc as isize,
                0x3272, fd.as_raw_fd() as isize, 0x3273, offset as isize,
                0x3274, stride as isize, 0x3443, 0, 0x3444, 0, 0x3038];
            let imported = (a.eglCreateImage)(self.display, ptr::null_mut(), 0x3270, ptr::null_mut(), attributes.as_ptr());
            if imported.is_null() { return Err("DMA-BUF import failed".into()); }
            self.images.push(imported);
            // EGL borrows the DMA-BUF FD; unlike native-fence import, ownership
            // stays here. The image holds its own backing reference after close.
            let symbol = (a.eglGetProcAddress)(b"glEGLImageTargetTexture2DOES\0".as_ptr().cast());
            if symbol.is_null() { return Err("DMA-BUF image target unavailable".into()); }
            let target: unsafe extern "C" fn(c_uint, Handle) = std::mem::transmute(symbol);
            let texture = self.create_texture(false)?;
            target(0x0de1, imported);
            self.gl_check("DMA-BUF texture import")?;
            self.attach_framebuffer(texture)?;
            self.dma_metadata = Some((fourcc, stride, offset));
            Ok(())
        }
    }
    fn cleanup(&mut self) -> Result<()> {
        if !self.initialized { drop(self.gbm.take()); return Ok(()); }
        let a = self.api;
        let mut errors = Vec::new();
        // Attempt each independent EGL teardown even after failure; no retry or
        // subsequent rendering. Context destruction reclaims all GL objects.
        unsafe {
            let had_objects = !self.shaders.is_empty() || self.program != 0;
            if self.producer_current {
                for shader in self.shaders.drain(..) { (a.glDeleteShader)(shader); }
                if self.program != 0 { (a.glDeleteProgram)(self.program); self.program = 0; }
                if had_objects {
                    if let Err(e) = self.gl_check("GL object cleanup") { errors.push(e); }
                }
            }
            if self.producer_current {
                for framebuffer in self.framebuffers.drain(..) { (a.glDeleteFramebuffers)(1, &framebuffer); }
                if let Err(e) = self.gl_check("framebuffer cleanup") { errors.push(e); }
                for texture in self.textures.drain(..) { (a.glDeleteTextures)(1, &texture); }
                if let Err(e) = self.gl_check("texture cleanup") { errors.push(e); }
            }
            for image in self.images.drain(..).rev() {
                if let Err(e) = check((a.eglDestroyImage)(self.display, image), "EGL image cleanup") { errors.push(e); }
            }
            // Context teardown also reclaims objects when restoration failed.
            if !self.context.is_null() {
                if let Err(e) = check((a.eglMakeCurrent)(self.display, ptr::null_mut(), ptr::null_mut(), ptr::null_mut()), "unbind") { errors.push(e); }
                if let Err(e) = check((a.eglDestroyContext)(self.display, self.context), "eglDestroyContext") { errors.push(e); }
                self.context = ptr::null_mut();
            }
            if !self.surface.is_null() {
                if let Err(e) = check((a.eglDestroySurface)(self.display, self.surface), "eglDestroySurface") { errors.push(e); }
                self.surface = ptr::null_mut();
            }
            if let Err(e) = check((a.eglTerminate)(self.display), "eglTerminate") { errors.push(e); }
            self.initialized = false;
        }
        drop(self.gbm.take());
        if errors.is_empty() { Ok(()) } else { Err(errors.join("; ")) }
    }
}

fn run(mode: Mode, native_fence: bool, fence_import: bool, dma_buf: bool, gbm_fd: Option<c_int>) -> Result<()> {
    let api = Api::load()?;
    let mut session = Session::new(&api);
    let rendered = session.render(mode, native_fence, fence_import, dma_buf, gbm_fd);
    let cleanup = session.cleanup();
    let (renderer, vendor, version) = match (rendered, cleanup) {
        (Ok(identity), Ok(())) => identity,
        (Err(e), Ok(())) | (Ok(_), Err(e)) => return Err(e),
        (Err(e), Err(cleanup)) => return Err(format!("{e}; cleanup: {cleanup}")),
    };
    println!("format=rog5-gles-readback-v1\nscope={}\nrenderer={renderer}\nvendor={vendor}\nversion={version}\ngles_requested=3.{}\ngles_actual={}.{}\ngles32_error=0x{:x}\npixels=16\nchannels_checked=64\nrender_readback=PASS\ncleanup=PASS\nnative_fence={}\nnative_fence_import={}\nscanout=NOT RUN\ndma_buf={}\nbuffer_sharing={}\nphysical_acceptance=NOT RUN", mode.scope(), session.requested_minor, session.actual_version.0, session.actual_version.1, session.preferred_error, if native_fence { "PASS" } else { "NOT RUN" }, if fence_import { "PASS" } else { "NOT RUN" }, if dma_buf { "PASS" } else { "NOT RUN" }, if dma_buf { "PASS: same-context linear DMA-BUF" } else { "NOT RUN" });
    if let Some((fourcc, stride, offset)) = session.dma_metadata { println!("dma_fourcc=0x{fourcc:x}\ndma_modifier=0x0\ndma_stride={stride}\ndma_offset={offset}\ndma_allocation={}\ndma_sync=glFinish", if gbm_fd.is_some() { "GBM explicit linear" } else { "GLES texture" }); }
    Ok(())
}
fn main() {
    let mut args: Vec<String> = std::env::args().skip(1).collect();
    let gbm_fd = if args.len() == 2 {
        args[1].strip_prefix("--gbm-fd=").filter(|v| !v.is_empty() && v.bytes().all(|b| b.is_ascii_digit())).and_then(|v| v.parse::<c_int>().ok())
    } else { None };
    let dma_buf = gbm_fd.is_some() || (args.len() == 2 && args[1] == "--dma-buf");
    let fence_import = args.len() == 2 && args[1] == "--native-fence-import";
    let native_fence = fence_import || (args.len() == 2 && args[1] == "--native-fence");
    if native_fence || dma_buf { args.pop(); }
    let mode = match Mode::parse(&args) {
        Ok(mode) => mode,
        Err(error) => { eprintln!("{error}"); std::process::exit(2); }
    };
    if let Err(error) = run(mode, native_fence, fence_import, dma_buf, gbm_fd) { eprintln!("FAIL {error}"); std::process::exit(1); }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn gbm_rejects_invalid_and_regular_descriptors_before_loading() {
        assert!(matches!(Gbm::open(-1), Err(e) if e.contains("descriptor duplication")));
        let regular = std::fs::File::open(std::env::current_exe().unwrap()).unwrap();
        assert!(matches!(Gbm::open(regular.as_raw_fd()), Err(e) if e.contains("character device")));
        assert!(regular.metadata().is_ok()); // caller retains its descriptor
    }
    #[test]
    fn explicit_mode_only() {
        for args in [vec![], vec!["--require-a660", "--software-fixture"], vec!["--unknown"]] {
            assert!(Mode::parse(&args.into_iter().map(String::from).collect::<Vec<_>>()).is_err());
        }
    }
    #[test]
    fn renderer_is_exact_and_software_is_explicit() {
        for name in ["FD660", "Adreno (TM) 660", "Adreno 660"] { assert!(Mode::A660.check(name).is_ok()); }
        for name in ["FD660 llvmpipe", "FD6600", "llvmpipe (LLVM)", "softpipe", "AMD Radeon", ""] { assert!(Mode::A660.check(name).is_err()); }
        assert!(Mode::Software.check("llvmpipe (LLVM)").is_ok());
        assert!(Mode::Software.check("FD660").is_err());
        assert!(Mode::Software.check("softpipeevil").is_err());
    }
    #[test]
    fn every_channel_is_checked_with_one_unit_tolerance() {
        let mut pixels = [0u8; 64];
        for y in 0..4 { for x in 0..4 { pixels[(y * 4 + x) * 4..(y * 4 + x + 1) * 4].copy_from_slice(&[32 + x as u8 * 64 - (x / 2) as u8, 32 + y as u8 * 64 - (y / 2) as u8, 64, 255]); } }
        assert!(pixels_match(&pixels).is_ok());
        for i in 0..64 {
            let mut corrupt = pixels;
            corrupt[i] = if corrupt[i] > 2 { corrupt[i] - 3 } else { corrupt[i] + 3 };
            assert!(pixels_match(&corrupt).is_err(), "unchecked channel {i}");
        }
        assert!(pixels_match(&[0; 64]).is_err());
    }
}
