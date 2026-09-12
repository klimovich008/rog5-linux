//! One offscreen GLES 3.2/3.0 shader/readback. No KMS, window, DMA-BUF or admission.
//! Run only under an external deadline: synchronous driver calls can block.
use std::ffi::{c_char, c_int, c_uint, c_void, CStr};
use std::ptr;
use std::os::fd::{AsRawFd, FromRawFd, OwnedFd};
use std::time::{Duration, Instant};

type Handle = *mut c_void;
type Result<T> = std::result::Result<T, String>;

#[link(name = "dl")]
extern "C" {
    fn dlopen(name: *const c_char, flags: c_int) -> Handle;
    fn dlsym(handle: Handle, name: *const c_char) -> Handle;
    fn dlclose(handle: Handle) -> c_int;
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
            _ => Err("usage: rog5-gles-readback --require-a660 | --software-fixture [--native-fence] (external deadline required)".into()),
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

struct Session<'a> {
    api: &'a Api,
    display: Handle,
    initialized: bool,
    surface: Handle,
    context: Handle,
    shaders: Vec<c_uint>,
    program: c_uint,
    requested_minor: c_int,
    actual_version: (c_int, c_int),
    preferred_error: c_uint,
}
impl<'a> Session<'a> {
    fn new(api: &'a Api) -> Self {
        Self { api, display: ptr::null_mut(), initialized: false, surface: ptr::null_mut(), context: ptr::null_mut(), shaders: Vec::new(), program: 0, requested_minor: 0, actual_version: (0, 0), preferred_error: 0 }
    }
    fn gl_check(&self, stage: &str) -> Result<()> {
        let error = unsafe { (self.api.glGetError)() };
        if error == 0 { Ok(()) } else { Err(format!("{stage}: GL error 0x{error:x}")) }
    }
    fn render(&mut self, mode: Mode, native_fence: bool) -> Result<(String, String, String)> {
        let a = self.api;
        // All pointer arguments below reference live arrays/handles of the exact
        // API types and lengths. GL calls follow a successful eglMakeCurrent.
        unsafe {
            let extensions = string_value((a.eglQueryString)(ptr::null_mut(), 0x3055), "EGL client extensions")?;
            if !extensions.split_ascii_whitespace().any(|e| e == "EGL_MESA_platform_surfaceless") {
                return Err("EGL_MESA_platform_surfaceless unavailable".into());
            }
            self.display = (a.eglGetPlatformDisplay)(0x31dd, ptr::null_mut(), ptr::null());
            if self.display.is_null() { return Err("eglGetPlatformDisplay failed".into()); }
            let (mut major, mut minor) = (0, 0);
            check((a.eglInitialize)(self.display, &mut major, &mut minor), "eglInitialize")?;
            self.initialized = true;
            if (major, minor) < (1, 5) { return Err("EGL 1.5 required".into()); }
            check((a.eglBindAPI)(0x30a0), "eglBindAPI")?; // OPENGL_ES_API
            // PBUFFER_BIT, OPENGL_ES3_BIT, RGBA sizes and no depth/stencil requirement.
            let attributes = [0x3033, 1, 0x3040, 0x40, 0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3021, 8, 0x3038];
            let (mut config, mut count) = (ptr::null_mut(), 0);
            check((a.eglChooseConfig)(self.display, attributes.as_ptr(), &mut config, 1, &mut count), "eglChooseConfig")?;
            if count != 1 || config.is_null() { return Err("no RGBA8 ES3 pbuffer config".into()); }
            let size = [0x3057, 4, 0x3056, 4, 0x3038];
            self.surface = (a.eglCreatePbufferSurface)(self.display, config, size.as_ptr());
            if self.surface.is_null() { return Err("eglCreatePbufferSurface failed".into()); }
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
            if native_fence { self.native_fence()?; }
            let mut pixels = [0u8; 64];
            (a.glReadPixels)(0, 0, 4, 4, 0x1908, 0x1401, pixels.as_mut_ptr().cast());
            self.gl_check("readback")?;
            pixels_match(&pixels)?;
            Ok((renderer, vendor, version))
        }
    }
    fn native_fence(&self) -> Result<()> {
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
                wait_native_fd(&fd)
            })();
            // fd has closed on every path before destroying the producer sync.
            let destroyed = check((a.eglDestroySync)(self.display, sync), "native fence destruction");
            match (result, destroyed) {
                (Ok(()), Ok(())) => Ok(()),
                (Err(e), Ok(())) | (Ok(()), Err(e)) => Err(e),
                (Err(e), Err(cleanup)) => Err(format!("{e}; {cleanup}")),
            }
        }
    }
    fn cleanup(&mut self) -> Result<()> {
        if !self.initialized { return Ok(()); }
        let a = self.api;
        let mut errors = Vec::new();
        // Attempt each independent EGL teardown even after failure; no retry or
        // subsequent rendering. Context destruction reclaims all GL objects.
        unsafe {
            let had_objects = !self.shaders.is_empty() || self.program != 0;
            for shader in self.shaders.drain(..) { (a.glDeleteShader)(shader); }
            if self.program != 0 { (a.glDeleteProgram)(self.program); self.program = 0; }
            if had_objects {
                if let Err(e) = self.gl_check("GL object cleanup") { errors.push(e); }
            }
            // No GL calls when make-current failed: no objects then exist.
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
        if errors.is_empty() { Ok(()) } else { Err(errors.join("; ")) }
    }
}

fn run(mode: Mode, native_fence: bool) -> Result<()> {
    let api = Api::load()?;
    let mut session = Session::new(&api);
    let rendered = session.render(mode, native_fence);
    let cleanup = session.cleanup();
    let (renderer, vendor, version) = match (rendered, cleanup) {
        (Ok(identity), Ok(())) => identity,
        (Err(e), Ok(())) | (Ok(_), Err(e)) => return Err(e),
        (Err(e), Err(cleanup)) => return Err(format!("{e}; cleanup: {cleanup}")),
    };
    println!("format=rog5-gles-readback-v1\nscope={}\nrenderer={renderer}\nvendor={vendor}\nversion={version}\ngles_requested=3.{}\ngles_actual={}.{}\ngles32_error=0x{:x}\npixels=16\nchannels_checked=64\nrender_readback=PASS\ncleanup=PASS\nnative_fence={}\nscanout=NOT RUN\nbuffer_sharing=NOT RUN\nphysical_acceptance=NOT RUN", mode.scope(), session.requested_minor, session.actual_version.0, session.actual_version.1, session.preferred_error, if native_fence { "PASS" } else { "NOT RUN" });
    Ok(())
}
fn main() {
    let mut args: Vec<String> = std::env::args().skip(1).collect();
    let native_fence = args.len() == 2 && args[1] == "--native-fence";
    if native_fence { args.pop(); }
    let mode = match Mode::parse(&args) {
        Ok(mode) => mode,
        Err(error) => { eprintln!("{error}"); std::process::exit(2); }
    };
    if let Err(error) = run(mode, native_fence) { eprintln!("FAIL {error}"); std::process::exit(1); }
}

#[cfg(test)]
mod tests {
    use super::*;
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
