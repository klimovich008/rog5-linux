//! Bounded ELF loader/symbol probe. Run only in an isolated test root.
//! Loading/resolution may execute constructors, IFUNC resolvers and destructors.
//! No requested entry-point body is called.
use std::ffi::{CStr, CString, c_char, c_int, c_void};
use std::io::{self, Write};
use std::ptr::NonNull;

#[link(name = "dl")]
unsafe extern "C" {
    fn dlopen(path: *const c_char, flags: c_int) -> *mut c_void;
    fn dlsym(handle: *mut c_void, symbol: *const c_char) -> *mut c_void;
    fn dlerror() -> *const c_char;
    fn dlclose(handle: *mut c_void) -> c_int;
    fn dl_iterate_phdr(
        callback: unsafe extern "C" fn(*mut PhdrPrefix, usize, *mut c_void) -> c_int,
        data: *mut c_void,
    ) -> c_int;
}

// Only the ABI's first two fields are read; the callback checks its size.
#[repr(C)]
struct PhdrPrefix {
    address: usize,
    name: *const c_char,
}

fn token(value: &str, path: bool) -> bool {
    !value.is_empty()
        && value.len() <= if path { 4096 } else { 256 }
        && value.bytes().all(|b| {
            b.is_ascii_alphanumeric() || b"_-.+".contains(&b) || (path && b == b'/')
        })
}

fn loader_error() -> String {
    // SAFETY: the current thread owns the loader error until another dl call.
    let raw = unsafe { dlerror() };
    if raw.is_null() {
        "loader returned no diagnostic".into()
    } else {
        // SAFETY: dlerror returns a NUL-terminated loader-owned string.
        unsafe { CStr::from_ptr(raw) }.to_string_lossy().into_owned()
    }
}

struct Library(Option<NonNull<c_void>>);
impl Library {
    fn open(path: &CStr) -> Result<Self, String> {
        // SAFETY: path is terminated. RTLD_NOW=2 checks relocations now;
        // RTLD_LOCAL=0 prevents this load from exporting a new global scope.
        NonNull::new(unsafe { dlopen(path.as_ptr(), 2) })
            .map(|handle| Self(Some(handle)))
            .ok_or_else(loader_error)
    }

    fn require_symbol(&self, symbol: &CStr) -> Result<(), String> {
        let handle = self.0.ok_or("library already closed")?;
        // SAFETY: the handle is live and the symbol name is terminated. Clear
        // the previous loader error so a null symbol is not misclassified.
        unsafe { dlerror() };
        let pointer = unsafe { dlsym(handle.as_ptr(), symbol.as_ptr()) };
        let error = unsafe { dlerror() };
        if !error.is_null() {
            // SAFETY: read before another loader call or closing the handle.
            return Err(unsafe { CStr::from_ptr(error) }.to_string_lossy().into_owned());
        }
        if pointer.is_null() {
            return Err("required entry point has a null address".into());
        }
        Ok(())
    }

    fn close(mut self) -> Result<(), String> {
        if let Some(handle) = self.0.take() {
            // SAFETY: exactly one close for the owned successful dlopen.
            if unsafe { dlclose(handle.as_ptr()) } != 0 {
                return Err(loader_error());
            }
        }
        Ok(())
    }
}
impl Drop for Library {
    fn drop(&mut self) {
        if let Some(handle) = self.0.take() {
            // SAFETY: error-path cleanup owns this still-live handle.
            unsafe { dlclose(handle.as_ptr()) };
        }
    }
}

#[derive(Default)]
struct Objects {
    names: Vec<String>,
    invalid: bool,
}
unsafe extern "C" fn collect(info: *mut PhdrPrefix, size: usize, data: *mut c_void) -> c_int {
    // SAFETY: objects is passed by the synchronous dl_iterate_phdr caller.
    let objects = unsafe { &mut *data.cast::<Objects>() };
    if info.is_null() || size < std::mem::size_of::<PhdrPrefix>() || objects.names.len() >= 128 {
        objects.invalid = true;
        return 1;
    }
    // SAFETY: the loader provides at least the checked prefix and a terminated name.
    let name = unsafe { (*info).name };
    if name.is_null() {
        objects.invalid = true;
        return 1;
    }
    let bytes = unsafe { CStr::from_ptr(name) }.to_bytes();
    if bytes.is_empty() {
        return 0; // Main executable has no dlpi_name; the runner binds it separately.
    }
    match std::str::from_utf8(bytes) {
        Ok(name) if token(name, true) => objects.names.push(name.to_owned()),
        _ => {
            objects.invalid = true;
            return 1;
        }
    }
    0
}

fn probe(args: &[String], out: &mut impl Write) -> Result<(), String> {
    if !(2..=17).contains(&args.len()) || !args[0].starts_with('/')
        || !token(&args[0], true) || args[1..].iter().any(|s| !token(s, false)) {
        return Err("usage: probe /absolute/library.so symbol [symbol ...] (maximum16)".into());
    }
    let path = CString::new(args[0].as_str()).map_err(|e| e.to_string())?;
    let library = Library::open(&path)?;
    for symbol in &args[1..] {
        library.require_symbol(&CString::new(symbol.as_str()).map_err(|e| e.to_string())?)?;
    }
    let mut objects = Objects::default();
    // SAFETY: callback receives a live Objects pointer for this synchronous call.
    let status = unsafe { dl_iterate_phdr(collect, (&mut objects as *mut Objects).cast()) };
    if status != 0 || objects.invalid {
        return Err("loaded object inventory exceeds bounds or contains an invalid name".into());
    }
    objects.names.sort();
    objects.names.dedup();
    // Complete cleanup before emitting the success receipt. Constructors and
    // destructors may themselves print; only this bounded receipt is authoritative.
    library.close()?;
    writeln!(out, "LIBRARY {}", args[0]).map_err(|e| e.to_string())?;
    for symbol in &args[1..] {
        writeln!(out, "SYMBOL {symbol}").map_err(|e| e.to_string())?;
    }
    for name in objects.names {
        writeln!(out, "OBJECT {name}").map_err(|e| e.to_string())?;
    }
    writeln!(out, "RESULT PASS_LINKAGE_ONLY").map_err(|e| e.to_string())
}

fn main() -> std::process::ExitCode {
    let args: Vec<String> = std::env::args().skip(1).take(18).collect();
    match probe(&args, &mut io::stdout().lock()) {
        Ok(()) => std::process::ExitCode::SUCCESS,
        Err(error) => {
            let _ = writeln!(io::stderr().lock(), "FAIL_LINKAGE: {error}");
            std::process::ExitCode::FAILURE
        }
    }
}
