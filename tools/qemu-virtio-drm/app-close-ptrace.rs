//! Single main-thread PC snapshot for a future, explicitly intrusive VM probe.
//! Not a CLI or enabled by the current read-only sampler. The caller must gate
//! VM/UID/owner identity and supply a revalidation closure. Numeric-PID seize is
//! not atomic with that check; stopped revalidation prevents false attribution.
use std::{ffi::c_void, io, thread, time::{Duration, Instant}};

const SEIZE: u32 = 0x4206;
const INTERRUPT: u32 = 0x4207;
const GETREGSET: u32 = 0x4204;
const DETACH: u32 = 17;
const WALL_NOHANG: i32 = 0x40000001;
const EVENT_STOP: i32 = 128;
const SIGTRAP: i32 = 5;
const WAIT_BUDGET: Duration = Duration::from_millis(75);

unsafe extern "C" {
    fn ptrace(request: u32, pid: i32, address: *mut c_void, data: *mut c_void) -> isize;
    fn waitpid(pid: i32, status: *mut i32, options: i32) -> i32;
}
#[repr(C)]
struct Iovec { base: *mut c_void, length: usize }

#[derive(Debug, PartialEq)]
pub struct Snapshot {
    pub pc: u64,
    pub sp: u64,
    pub frame_pointer: u64,
    pub link_register: Option<u64>,
    /// INTERRUPT through successful DETACH, including scheduling/wait overhead.
    /// Not a hard pause bound: the external process watchdog is still required.
    pub interrupt_to_detach: Duration,
}

fn request(operation: u32, pid: i32, address: usize, data: usize) -> Result<(), String> {
    // SAFETY: integer operands are ptrace ABI values; GETREGSET callers provide
    // a live writable iovec and register buffer for the duration of this call.
    if unsafe { ptrace(operation, pid, address as *mut c_void, data as *mut c_void) } == -1 {
        Err(format!("ptrace-{operation:#x}:{}", io::Error::last_os_error()))
    } else { Ok(()) }
}

#[cfg(target_arch = "aarch64")]
const REGISTER_WORDS: usize = 34;
#[cfg(target_arch = "x86_64")]
const REGISTER_WORDS: usize = 27;
#[cfg(not(any(target_arch = "aarch64", target_arch = "x86_64")))]
compile_error!("unsupported ptrace ABI");

fn decode(registers: &[u64], length: usize) -> Result<Snapshot, String> {
    if registers.len() != REGISTER_WORDS || length != REGISTER_WORDS * 8 {
        return Err("unexpected-NT_PRSTATUS-size".into());
    }
    // Exact Linux user_pt_regs / user_regs_struct; never dump the whole set.
    #[cfg(target_arch = "aarch64")]
    let (pc, sp, fp, lr) = (registers[32], registers[31], registers[29], Some(registers[30]));
    #[cfg(target_arch = "x86_64")]
    let (pc, sp, fp, lr) = (registers[16], registers[19], registers[4], None);
    Ok(Snapshot { pc, sp, frame_pointer: fp, link_register: lr, interrupt_to_detach: Duration::ZERO })
}

#[derive(Clone, Copy, PartialEq)]
enum Stage { Seized, Interrupted, Stopped }

fn run(pid: i32, validate: impl Fn() -> Result<(), String>,
       hook: impl Fn(Stage) -> Result<(), String>) -> Result<Snapshot, String> {
    validate()?;
    // Options=0: especially NO EXITKILL, signal injection, syscall tracing,
    // clone following or persistent relationship outside this one snapshot.
    request(SEIZE, pid, 0, 0)?;
    hook(Stage::Seized)?;
    let started = Instant::now();
    request(INTERRUPT, pid, 0, 0)?;
    hook(Stage::Interrupted)?;
    let status = loop {
        if started.elapsed() >= WAIT_BUDGET { return Err("interrupt-wait-deadline".into()); }
        let mut status = 0;
        // SAFETY: exact positive PID, writable status, Linux __WALL|WNOHANG.
        let result = unsafe { waitpid(pid, &mut status, WALL_NOHANG) };
        if result == pid { break status; }
        if result == -1 {
            let error = io::Error::last_os_error();
            if error.kind() == io::ErrorKind::Interrupted { continue; }
            return Err(format!("wait:{error}"));
        }
        thread::sleep(Duration::from_millis(1));
    };
    if status & 0xff != 0x7f { return Err(format!("target-exited:status={status:#x}")); }
    let event = status >> 16;
    let signal = (status >> 8) & 0xff;
    // INTERRUPT may encounter a real pending signal first. Suppressing it with
    // DETACH(0) would alter application behavior. No register capture then.
    if event == 0 {
        if !(1..=64).contains(&signal) { return Err("invalid-stop-signal".into()); }
        request(DETACH, pid, 0, signal as usize)?;
        return Err(format!("signal-delivery-stop:{signal}"));
    }
    if event != EVENT_STOP || signal != SIGTRAP {
        // Existing group-stop state is preserved by kernel detach. Never send
        // SIGCONT or inject a second stop signal to try to make capture work.
        request(DETACH, pid, 0, 0)?;
        return Err(format!("non-snapshot-stop:event={event}:signal={signal}"));
    }
    hook(Stage::Stopped)?;
    let observed = (|| {
        validate()?;
        let mut registers = [0u64; REGISTER_WORDS];
        let mut iovec = Iovec { base: registers.as_mut_ptr().cast(), length: std::mem::size_of_val(&registers) };
        request(GETREGSET, pid, 1, &mut iovec as *mut Iovec as usize)?; // NT_PRSTATUS
        decode(&registers, iovec.length)
    })();
    // Detach even when identity or register reading failed. Errors before this
    // point use tracer-thread exit cleanup; no captured value escapes failure.
    request(DETACH, pid, 0, 0)?;
    let mut snapshot = observed?;
    snapshot.interrupt_to_detach = started.elapsed();
    validate()?;
    Ok(snapshot)
}

fn capture_with(pid: i32, validate: impl Fn() -> Result<(), String> + Send + 'static,
                hook: impl Fn(Stage) -> Result<(), String> + Send + 'static) -> Result<Snapshot, String> {
    if pid <= 1 || pid as u32 == std::process::id() { return Err("invalid-target-pid".into()); }
    // The relationship belongs to this Linux task, not the whole process.
    // join waits for task exit: kernel exit_ptrace detaches on every error or
    // panic, including a deadline before the interrupt stop can be reaped.
    thread::Builder::new().name("vm-pc-snapshot".into()).spawn(move || run(pid, validate, hook))
        .map_err(|e| format!("tracer-thread:{e}"))?.join().map_err(|_| "tracer-panicked".to_string())?
}

pub fn capture(pid: i32, validate: impl Fn() -> Result<(), String> + Send + 'static) -> Result<Snapshot, String> {
    capture_with(pid, validate, |_| Ok(()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{fs, process::{Child, Command, Stdio}, sync::{Arc, atomic::{AtomicUsize, Ordering}}};
    unsafe extern "C" { fn kill(pid: i32, signal: i32) -> i32; }
    struct Owned(Child);
    impl Drop for Owned {
        fn drop(&mut self) {
            // A tracer wait can already have consumed exit status. Never send
            // a numeric-PID kill after ECHILD or a recorded/reaped exit.
            if matches!(self.0.try_wait(), Ok(None)) { let _ = self.0.kill(); let _ = self.0.wait(); }
        }
    }
    fn child() -> Owned {
        Owned(Command::new("/bin/sh").args(["-c", "while :; do :; done"])
            .stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null()).spawn().unwrap())
    }
    fn status(pid: i32) -> String { fs::read_to_string(format!("/proc/{pid}/status")).unwrap() }
    fn signal(pid: i32, value: i32) {
        // SAFETY: only an unreaped child owned by this test is signalled.
        assert_eq!(unsafe { kill(pid, value) }, 0);
    }
    fn wait_until(mut predicate: impl FnMut() -> bool) {
        let end = Instant::now() + Duration::from_secs(2);
        while !predicate() { assert!(Instant::now() < end, "fixture deadline"); thread::sleep(Duration::from_millis(2)); }
    }
    fn detached(pid: i32) { wait_until(|| status(pid).lines().any(|l| l == "TracerPid:\t0")); }
    fn running(pid: i32) {
        detached(pid);
        let state = status(pid);
        assert!(state.contains("State:\tR") || state.contains("State:\tS"), "tracee not alive/runnable: {state}");
        let ticks = || {
            let data = fs::read_to_string(format!("/proc/{pid}/stat")).unwrap();
            data.rsplit_once(") ").unwrap().1.split_whitespace().nth(11).unwrap().parse::<u64>().unwrap()
        };
        let before = ticks();
        wait_until(|| ticks() > before);
    }

    #[test] fn actual_snapshot_detaches_and_revalidates() {
        let child = child(); let pid = child.0.id() as i32;
        let checks = Arc::new(AtomicUsize::new(0)); let observed = checks.clone();
        let shot = capture(pid, move || { observed.fetch_add(1, Ordering::SeqCst); Ok(()) }).unwrap();
        assert!(shot.pc != 0 && shot.sp != 0);
        assert_eq!(checks.load(Ordering::SeqCst), 3);
        running(pid);
    }
    #[test] fn identity_refusal_never_publishes_registers() {
        let child = child(); let pid = child.0.id() as i32;
        assert_eq!(capture(pid, || Err("pre-identity".into())).unwrap_err(), "pre-identity");
        running(pid);
        let calls = AtomicUsize::new(0);
        assert_eq!(capture(pid, move || if calls.fetch_add(1, Ordering::SeqCst) == 0 { Ok(()) } else { Err("stopped-identity".into()) }).unwrap_err(), "stopped-identity");
        running(pid);
    }
    #[test] fn thread_exit_and_panic_release_real_tracee() {
        for stage in [Stage::Seized, Stage::Interrupted, Stage::Stopped] {
            let child = child(); let pid = child.0.id() as i32;
            assert_eq!(capture_with(pid, || Ok(()), move |s| if s == stage { Err("injected".into()) } else { Ok(()) }).unwrap_err(), "injected");
            running(pid);
        }
        let child = child(); let pid = child.0.id() as i32;
        assert_eq!(capture_with(pid, || Ok(()), |s| { if s == Stage::Stopped { panic!("injected"); } Ok(()) }).unwrap_err(), "tracer-panicked");
        running(pid);
    }
    #[test] fn pending_term_is_forwarded_not_suppressed() {
        let mut child = child(); let pid = child.0.id() as i32;
        let result = capture_with(pid, || Ok(()), move |s| {
            if s == Stage::Seized {
                signal(pid, 15);
                wait_until(|| status(pid).contains("State:\tt"));
            }
            Ok(())
        });
        assert_eq!(result.unwrap_err(), "signal-delivery-stop:15");
        wait_until(|| child.0.try_wait().unwrap().is_some());
        use std::os::unix::process::ExitStatusExt;
        assert_eq!(child.0.wait().unwrap().signal(), Some(15));
    }
    #[test] fn handled_signal_is_delivered_exactly_once() {
        use std::os::unix::fs::DirBuilderExt;
        let root = std::env::temp_dir().join(format!("rog5-ptrace-signal-{}", std::process::id()));
        fs::DirBuilder::new().mode(0o700).create(&root).unwrap();
        struct Scratch(std::path::PathBuf);
        impl Drop for Scratch { fn drop(&mut self) { let _ = fs::remove_dir_all(&self.0); } }
        let _scratch = Scratch(root.clone());
        let log = root.join("events"); let ready = root.join("ready");
        let child = Owned(Command::new("/bin/sh").args(["-c", "trap 'printf x >> \"$1\"' USR1; : > \"$2\"; while :; do :; done", "owned-signal-fixture"])
            .arg(&log).arg(&ready).stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null()).spawn().unwrap());
        let pid = child.0.id() as i32;
        wait_until(|| ready.exists());
        let result = capture_with(pid, || Ok(()), move |s| {
            if s == Stage::Seized { signal(pid, 10); wait_until(|| status(pid).contains("State:\tt")); }
            Ok(())
        });
        assert_eq!(result.unwrap_err(), "signal-delivery-stop:10");
        wait_until(|| fs::read(&log).is_ok_and(|data| !data.is_empty()));
        running(pid);
        // Kill/reap before checking final output so later duplicate delivery
        // cannot be hidden by inspecting the log too early.
        drop(child);
        assert_eq!(fs::read(&log).unwrap(), b"x");
    }
    #[test] fn real_wait_deadline_releases_tracee() {
        let child = child(); let pid = child.0.id() as i32;
        let result = capture_with(pid, || Ok(()), |s| {
            if s == Stage::Interrupted { thread::sleep(WAIT_BUDGET + Duration::from_millis(1)); }
            Ok(())
        });
        assert_eq!(result.unwrap_err(), "interrupt-wait-deadline");
        running(pid);
    }
    #[test] fn group_stop_survives_detach_and_tracer_exit() {
        for fail in [false, true] {
            let child = child(); let pid = child.0.id() as i32;
            signal(pid, 19);
            wait_until(|| status(pid).contains("State:\tT"));
            let result = capture_with(pid, || Ok(()), move |s| if fail && s == Stage::Seized { Err("injected".into()) } else { Ok(()) });
            assert!(result.is_err()); detached(pid);
            wait_until(|| status(pid).contains("State:\tT"));
            // Only the fixture restores its own pre-existing group stop.
            signal(pid, 18); wait_until(|| !status(pid).contains("State:\tT")); running(pid);
        }
    }
    #[test] fn target_kill_never_becomes_a_snapshot() {
        let child = child(); let pid = child.0.id() as i32;
        let result = capture_with(pid, || Ok(()), move |s| { if s == Stage::Seized { signal(pid, 9); } Ok(()) });
        assert!(result.is_err());
    }
    #[test] fn abi_size_and_fields_are_explicit() {
        let registers: Vec<_> = (0..REGISTER_WORDS as u64).collect();
        assert!(decode(&registers, REGISTER_WORDS * 8 - 8).is_err());
        assert!(decode(&registers[..REGISTER_WORDS-1], REGISTER_WORDS * 8).is_err());
        let value = decode(&registers, REGISTER_WORDS * 8).unwrap();
        #[cfg(target_arch = "aarch64")]
        assert_eq!((value.pc, value.sp, value.frame_pointer, value.link_register), (32,31,29,Some(30)));
        #[cfg(target_arch = "x86_64")]
        assert_eq!((value.pc, value.sp, value.frame_pointer, value.link_register), (16,19,4,None));
    }
}
