//! Offline ARM64 VM probe of real libseat/logind device mediation.
//! No rendering, input reading, device writes or phone qualification occurs.

use std::cell::Cell;
use std::ffi::{c_char, c_int, c_void, CStr};
use std::fs::{self, File};
use std::io::{self, Write};
use std::os::fd::FromRawFd;
use std::os::unix::fs::{FileTypeExt, MetadataExt};
use std::ptr;
use std::time::{Duration, Instant};

type Seat = c_void;
type SeatCall = unsafe extern "C" fn(*mut Seat) -> c_int;
type OpenDevice = unsafe extern "C" fn(*mut Seat, *const c_char, *mut c_int) -> c_int;
type CloseDevice = unsafe extern "C" fn(*mut Seat, c_int) -> c_int;
type Dispatch = unsafe extern "C" fn(*mut Seat, c_int) -> c_int;
type Error = Box<dyn std::error::Error>;

#[repr(C)]
struct Listener {
    enable: unsafe extern "C" fn(*mut Seat, *mut c_void),
    disable: unsafe extern "C" fn(*mut Seat, *mut c_void),
}

struct Events {
    enabled: Cell<bool>,
    revoked: Cell<bool>,
    disable_errno: Cell<Option<i32>>,
    disable: SeatCall,
}

unsafe extern "C" fn enabled(_seat: *mut Seat, data: *mut c_void) {
    // SAFETY: Session retains this boxed Events until close_seat returns. libseat
    // dispatches callbacks synchronously on this one thread; Cell avoids aliases
    // to mutable references when C re-enters a callback.
    unsafe { &*data.cast::<Events>() }.enabled.set(true);
}

unsafe extern "C" fn disabled(seat: *mut Seat, data: *mut c_void) {
    // SAFETY: same stable callback storage as enabled; seat is provided by libseat.
    let events = unsafe { &*data.cast::<Events>() };
    events.enabled.set(false);
    events.revoked.set(true);
    // Acknowledge promptly; this callback never accesses any device fd.
    if unsafe { (events.disable)(seat) } != 0 {
        events.disable_errno.set(Some(io::Error::last_os_error().raw_os_error().unwrap_or(0)));
    }
}

static LISTENER: Listener = Listener { enable: enabled, disable: disabled };

struct Api {
    open: unsafe extern "C" fn(*const Listener, *mut c_void) -> *mut Seat,
    close: SeatCall,
    disable: SeatCall,
    name: unsafe extern "C" fn(*mut Seat) -> *const c_char,
    open_device: OpenDevice,
    close_device: CloseDevice,
    dispatch: Dispatch,
    // Keep code and ABI symbols alive through every seat/device cleanup call.
    _library: libloading::Library,
}

impl Api {
    fn load() -> Result<Self, Error> {
        // SAFETY: these ABI signatures match the authenticated runtime's
        // usr/include/libseat.h. No symbols outlive their owning Library.
        unsafe {
            let library = libloading::Library::new("libseat.so.1")?;
            Ok(Self {
                open: *library.get(b"libseat_open_seat\0")?,
                close: *library.get(b"libseat_close_seat\0")?,
                disable: *library.get(b"libseat_disable_seat\0")?,
                name: *library.get(b"libseat_seat_name\0")?,
                open_device: *library.get(b"libseat_open_device\0")?,
                close_device: *library.get(b"libseat_close_device\0")?,
                dispatch: *library.get(b"libseat_dispatch\0")?,
                _library: library,
            })
        }
    }
}

struct Session<'a> {
    api: &'a Api,
    seat: *mut Seat,
    events: Box<Events>,
    devices: Vec<(c_int, File)>,
}

impl<'a> Session<'a> {
    fn open(api: &'a Api) -> Result<Self, Error> {
        let events = Box::new(Events {
            enabled: Cell::new(false), revoked: Cell::new(false),
            disable_errno: Cell::new(None), disable: api.disable,
        });
        let data = ptr::from_ref(events.as_ref()).cast_mut().cast::<c_void>();
        // SAFETY: listener is static and boxed callback storage does not move.
        let seat = unsafe { (api.open)(&LISTENER, data) };
        if seat.is_null() { return Err(format!("open_seat: {}", io::Error::last_os_error()).into()); }
        Ok(Self { api, seat, events, devices: Vec::with_capacity(2) })
    }

    fn check_events(&self) -> Result<(), Error> {
        if let Some(errno) = self.events.disable_errno.get() {
            return Err(format!("disable_seat callback failed errno={errno}").into());
        }
        if self.events.revoked.get() { return Err("seat disabled during probe".into()); }
        Ok(())
    }

    fn exercise(&mut self) -> Result<(), Error> {
        let deadline = Instant::now() + Duration::from_secs(5);
        while !self.events.enabled.get() {
            self.check_events()?;
            let remaining = deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() { return Err("seat enable deadline exceeded (5s)".into()); }
            let wait_ms = remaining.as_millis().min(100) as c_int;
            // SAFETY: live seat and nonnegative bounded dispatch timeout.
            if unsafe { (self.api.dispatch)(self.seat, wait_ms) } < 0 {
                return Err(format!("dispatch: {}", io::Error::last_os_error()).into());
            }
        }
        self.check_events()?;
        // SAFETY: libseat owns the NUL-terminated seat name until close_seat.
        let name = unsafe { (self.api.name)(self.seat) };
        if name.is_null() { return Err("seat_name returned null".into()); }
        let name = unsafe { CStr::from_ptr(name) }.to_str()?;
        if name.is_empty() { return Err("seat_name returned empty name".into()); }
        println!("LOGIND_SEAT backend=logind name={name} enabled=true uid=1000");

        for path in [c"/dev/dri/card0", c"/dev/input/event0"] {
            self.check_events()?;
            let path_text = path.to_str()?;
            let expected = fs::symlink_metadata(path_text)?;
            if !expected.file_type().is_char_device() {
                return Err(format!("expected direct character device: {path_text}").into());
            }
            let mut fd = -1;
            // SAFETY: live seat, fixed NUL-terminated path, valid out pointer.
            let id = unsafe { (self.api.open_device)(self.seat, path.as_ptr(), &mut fd) };
            if id < 0 {
                return Err(format!("open_device {path_text}: {}", io::Error::last_os_error()).into());
            }
            if fd < 0 {
                // A successful device ID still needs a release attempt if the
                // library violates its output-fd contract.
                let released = unsafe { (self.api.close_device)(self.seat, id) };
                let release_error = io::Error::last_os_error();
                return Err(format!("open_device {path_text}: invalid returned fd; release={released} errno={release_error}").into());
            }
            // SAFETY: logind backend returns an owned duplicate of the D-Bus fd.
            // ReleaseDevice uses it for fstat, so close the File only afterward.
            let file = unsafe { File::from_raw_fd(fd) };
            self.devices.push((id, file));
            let observed = self.devices.last().ok_or("missing owned device")?.1.metadata()?;
            if !observed.file_type().is_char_device() || observed.rdev() != expected.rdev() {
                return Err(format!("returned device identity mismatch: {path_text}").into());
            }
            println!("LOGIND_DEVICE path={path_text} id={id} fd={fd} rdev={} matched=true", observed.rdev());
        }
        // Process any queued revocation before making the terminal claim.
        if unsafe { (self.api.dispatch)(self.seat, 0) } < 0 {
            return Err(format!("final dispatch: {}", io::Error::last_os_error()).into());
        }
        self.check_events()
    }

    fn cleanup(&mut self) -> Result<(), Error> {
        let mut errors = Vec::new();
        while let Some((id, file)) = self.devices.pop() {
            // SAFETY: live seat and device registered by open_device; File still open.
            if unsafe { (self.api.close_device)(self.seat, id) } != 0 {
                errors.push(format!("close_device id={id}: {}", io::Error::last_os_error()));
            }
            drop(file);
        }
        if !self.seat.is_null() {
            // Never retry a destructor after a reported failure: it may have freed
            // the object. Callback storage and library remain live for this call.
            let seat = std::mem::replace(&mut self.seat, ptr::null_mut());
            if unsafe { (self.api.close)(seat) } != 0 {
                errors.push(format!("close_seat: {}", io::Error::last_os_error()));
            }
        }
        if errors.is_empty() { Ok(()) } else { Err(errors.join("; ").into()) }
    }
}

impl Drop for Session<'_> {
    fn drop(&mut self) {
        if let Err(error) = self.cleanup() {
            let _ = writeln!(io::stderr(), "LOGIND_CLEANUP error={error}");
        }
    }
}

fn run() -> Result<(), Error> {
    if std::env::args_os().len() != 1 { return Err("arguments are not supported".into()); }
    let cmdline = fs::read_to_string("/proc/cmdline")?;
    if cmdline.split_whitespace().filter(|v| v.starts_with("rog5.logind_fixture=")).collect::<Vec<_>>() != ["rog5.logind_fixture=1"]
        || !std::path::Path::new("/sys/bus/virtio/devices").is_dir()
    { return Err("not the isolated logind VM fixture".into()); }
    if std::env::var("LIBSEAT_BACKEND").as_deref() != Ok("logind") {
        return Err("LIBSEAT_BACKEND must be exactly logind".into());
    }
    // SAFETY: identity queries have no pointer arguments or side effects.
    if unsafe { libc::getuid() } != 1000 || unsafe { libc::geteuid() } != 1000 {
        return Err("probe requires real/effective UID1000".into());
    }
    // Bound synchronous D-Bus calls too, not only our dispatch loop. SIGALRM
    // terminates this disposable process on a wedged library call; kernel fd
    // closure releases its D-Bus control. This is a failed run, never cleanup PASS.
    // SAFETY: standalone single-threaded process, reserved SIGALRM default action.
    if unsafe { libc::signal(libc::SIGALRM, libc::SIG_DFL) } == libc::SIG_ERR {
        return Err(format!("arm deadline signal: {}", io::Error::last_os_error()).into());
    }
    unsafe { libc::alarm(15); }
    let api = Api::load()?;
    let mut session = Session::open(&api)?;
    let result = session.exercise();
    let cleanup = session.cleanup();
    if let Err(error) = cleanup {
        if let Err(primary) = result { return Err(format!("{primary}; cleanup: {error}").into()); }
        return Err(error);
    }
    result?;
    println!("LOGIND_SEAT_PROBE PASS devices=2 released=true seat_closed=true physical=NOT_RUN");
    unsafe { libc::alarm(0); }
    Ok(())
}

fn main() -> std::process::ExitCode {
    match run() {
        Ok(()) => std::process::ExitCode::SUCCESS,
        Err(error) => {
            let _ = writeln!(io::stderr(), "LOGIND_SEAT_PROBE FAIL {error}");
            std::process::ExitCode::FAILURE
        }
    }
}
