// VM-only close observation; default read-only. Explicit close_ptrace builds
// add one intrusive snapshot. Records never prove successful shutdown.
#[cfg(close_ptrace)]
#[path = "app-close-ptrace.rs"]
mod ptrace;
use std::{fs::{self, OpenOptions}, io::{self, Read, Write}, os::unix::{fs::{MetadataExt, OpenOptionsExt}, ffi::OsStrExt}, path::Path, time::{Duration, Instant}};
#[repr(C)]
struct Timespec { seconds: i64, nanos: i64 }
unsafe extern "C" { fn getuid() -> u32; fn geteuid() -> u32; fn clock_gettime(clock: i32, value: *mut Timespec) -> i32; fn sysconf(name: i32) -> std::ffi::c_long; }
// Exact Linux7.1.4 UAPI: ARM64 asm/fcntl.h overrides asm-generic.
#[cfg(target_arch = "aarch64")]
const NOFOLLOW: i32 = 0o100000;
#[cfg(target_arch = "x86_64")]
const NOFOLLOW: i32 = 0o400000;
#[cfg(not(any(target_arch = "aarch64", target_arch = "x86_64")))]
compile_error!("unsupported proc fixture architecture");
const NONBLOCK: i32 = 0o4000;
const MAX_BYTES: usize = 8192;
const MAX_RECORDS: usize = 64;

fn read(path: &Path, limit: usize) -> Result<Vec<u8>, String> {
    let file = OpenOptions::new().read(true).custom_flags(NOFOLLOW | NONBLOCK)
        .open(path).map_err(|e| format!("open:{:?}", e.kind()))?;
    if !file.metadata().map_err(|e| e.to_string())?.is_file() { return Err("not-regular".into()); }
    let mut data = Vec::new();
    file.take((limit + 1) as u64).read_to_end(&mut data).map_err(|e| format!("read:{:?}", e.kind()))?;
    if data.len() > limit { return Err("read-limit".into()); }
    Ok(data)
}
fn escaped(bytes: &[u8]) -> String { bytes.iter().flat_map(|b| std::ascii::escape_default(*b)).map(char::from).collect() }
#[derive(Debug, PartialEq)]
struct Identity { pid: u32, ppid: u32, start: u64, state: String, comm: String }
fn identity(bytes: &[u8]) -> Result<Identity, String> {
    let s = std::str::from_utf8(bytes).map_err(|_| "stat-utf8")?;
    let (head, tail) = s.rsplit_once(") ").ok_or("stat-close")?;
    let (pid, comm) = head.split_once(" (").ok_or("stat-open")?;
    let f: Vec<_> = tail.split_whitespace().collect();
    if f.len() < 20 { return Err("stat-short".into()); }
    Ok(Identity { pid: pid.parse().map_err(|_| "stat-pid")?, comm: comm.into(), state: f[0].into(),
        ppid: f[1].parse().map_err(|_| "stat-ppid")?, start: f[19].parse().map_err(|_| "stat-start")? })
}
#[derive(Clone, Copy)]
struct Target { pid: u32, start: u64 }
fn cpu_ticks(bytes: &[u8], target: Target) -> Result<(u64,u64), String> {
    let id=identity(bytes)?;
    if id.pid!=target.pid || id.start!=target.start { return Err("identity-reused".into()); }
    let s=std::str::from_utf8(bytes).map_err(|_| "stat-utf8")?;
    let fields:Vec<_>=s.rsplit_once(") ").ok_or("stat-close")?.1.split_whitespace().collect();
    // Tail starts at stat field3: utime/stime are fields14/15; not child times.
    Ok((fields[11].parse().map_err(|_| "utime-parse")?,fields[12].parse().map_err(|_| "stime-parse")?))
}
fn context_switches(bytes: &[u8]) -> Result<(u64,u64), String> {
    let status=std::str::from_utf8(bytes).map_err(|_| "status-utf8")?;
    let counter=|key:&str| -> Result<u64,String> {
        let fields:Vec<_>=status.lines().filter_map(|line|line.strip_prefix(key)).collect();
        if fields.len()!=1 { return Err(format!("missing-or-duplicate:{key}")); }
        fields[0].trim().parse().map_err(|_|format!("invalid:{key}"))
    };
    Ok((counter("voluntary_ctxt_switches:")?,counter("nonvoluntary_ctxt_switches:")?))
}
fn check(root: &Path, target: Target, uid: u32, parent: Option<u32>, comm: Option<&str>) -> Result<Identity, String> {
    let dir = root.join(target.pid.to_string());
    let id = identity(&read(&dir.join("stat"), 4096)?)?;
    if id.pid != target.pid || id.start != target.start { return Err("identity-reused".into()); }
    if matches!(id.state.as_str(), "Z" | "X" | "x") { return Err("exited".into()); }
    if parent.is_some_and(|p| p != id.ppid) || comm.is_some_and(|c| c != id.comm) { return Err("identity-mismatch".into()); }
    let status = read(&dir.join("status"), 8192)?;
    let status = std::str::from_utf8(&status).map_err(|_| "status-utf8")?;
    let fields: Vec<_> = status.lines().filter_map(|s| s.strip_prefix("Uid:")).collect();
    if fields.len() != 1 || fields[0].split_whitespace().map(|v| v.parse::<u32>()).collect::<Result<Vec<_>, _>>().map_err(|_| "uid-parse")? != [uid; 4] { return Err("uid-mismatch".into()); }
    Ok(id)
}
struct Records<W: Write> { writer: W, bytes: usize, count: usize, truncated: bool, reserved: usize, invalidated: bool }
impl<W: Write> Records<W> {
    fn new(writer: W) -> Self { Self { writer, bytes: 0, count: 0, truncated: false, reserved: 0, invalidated: false } }
    fn add(&mut self, kind: &str, round: usize, pid: u32, value: &[u8]) -> io::Result<()> {
        let mut text = String::new();
        let mut consumed = 0;
        for byte in value {
            let escaped = escaped(&[*byte]);
            if text.len() + escaped.len() > 768 { break; }
            text.push_str(&escaped); consumed += 1;
        }
        let clipped = consumed != value.len();
        let line = format!("APP_CLOSE_PROBE kind={kind} round={round} pid={pid} clipped={clipped} value=\"{}\"\n", text);
        if self.count >= MAX_RECORDS - 1 || self.bytes + line.len() > MAX_BYTES - 128 - self.reserved { self.truncated = true; return Ok(()); }
        self.truncated |= clipped;
        self.writer.write_all(line.as_bytes())?; self.bytes += line.len(); self.count += 1; Ok(())
    }
    fn finish(&mut self, elapsed: Duration) -> io::Result<()> {
        let line = format!("APP_CLOSE_PROBE kind=footer records={} truncated={} elapsed_ms={} diagnostic_only=true invalidated={}\n", self.count + 1, self.truncated, elapsed.as_millis().min(u64::MAX as u128), self.invalidated);
        self.writer.write_all(line.as_bytes())?; self.writer.flush()
    }
}
fn observation(result: Result<Vec<u8>, String>) -> Vec<u8> { match result { Ok(v) => v, Err(e) => format!("unavailable:{e}").into_bytes() } }
// No whole map dump: retain only the mapping containing the sampled PC.
// A missing/truncated maps file is explicitly unavailable, not guessed.
fn pc_map(root: &Path, pid: u32, syscall: &[u8]) -> Vec<u8> {
    let Some(pc) = std::str::from_utf8(syscall).ok().and_then(|s| {
        let f: Vec<_> = s.split_whitespace().collect();
        if f.len() != 3 && f.len() != 9 { return None; }
        u64::from_str_radix(f.last()?.strip_prefix("0x")?, 16).ok()
    }) else { return b"unavailable:no-sampled-pc".to_vec(); };
    let data = match read(&root.join(format!("{pid}/maps")), 65536) { Ok(v) => v, Err(e) => return format!("unavailable:{e}").into_bytes() };
    for line in data.split(|b| *b == b'\n').take(512) {
        let Some(s) = std::str::from_utf8(line).ok() else { continue; };
        let range = s.split_whitespace().next().and_then(|f| f.split_once('-'));
        let Some((lo, hi)) = range.and_then(|(a,b)| Some((u64::from_str_radix(a,16).ok()?,u64::from_str_radix(b,16).ok()?))) else { continue; };
        if lo <= pc && pc < hi { return line.to_vec(); }
    }
    b"unavailable:no-matching-map-within-bound".to_vec()
}
fn sample<W: Write>(root: &Path, timeout: Target, app: Target, uid: u32, round: usize, out: &mut Records<W>) -> io::Result<bool> {
    // Preserve at least1KiB for clock + main-thread data in every later round.
    // Extra workers/FD/maps may be omitted with an explicit truncation footer.
    out.reserved = 5usize.saturating_sub(round) * 1024;
    // Reserve the requested snapshot before earlier optional worker/FD records
    // consume its space. Released after the round1 proc sample, still within8KiB.
    #[cfg(close_ptrace)]
    if round <= 1 { out.reserved += 1536; }
    let mut time = Timespec { seconds: 0, nanos: 0 };
    // SAFETY: valid writable timespec; CLOCK_MONOTONIC is1 on both Linux ABIs.
    if unsafe { clock_gettime(1, &mut time) } != 0 { return Err(io::Error::last_os_error()); }
    // SAFETY: glibc bits/confname.h on both supported targets defines _SC_CLK_TCK=2.
    let ticks=unsafe { sysconf(2) };
    if ticks<=0 { return Err(io::Error::other("clock tick scale unavailable")); }
    out.add("clock", round, app.pid, format!("CLOCK_MONOTONIC={}.{:09} ticks_per_second={ticks}", time.seconds, time.nanos).as_bytes())?;
    for (target, parent, comm) in [(timeout, None, None), (app, Some(timeout.pid), Some("mousepad"))] {
        if let Err(e) = check(root, target, uid, parent, comm) { out.add("identity-unavailable", round, target.pid, format!("status=NOT_RUN cause={e}").as_bytes())?; return Ok(false); }
    }
    let mut tids = vec![app.pid];
    if let Ok(entries) = fs::read_dir(root.join(format!("{}/task", app.pid))) {
        // Enumeration and work are bounded independently of the output budget.
        let mut extra: Vec<u32> = entries.take(32).filter_map(Result::ok).filter_map(|e| e.file_name().to_str()?.parse().ok()).filter(|p| *p != app.pid).collect();
        extra.sort_unstable();
        if extra.len() > 3 { out.truncated = true; }
        tids.extend(extra.into_iter().take(3));
    }
    let extra = tids.into_iter().skip(1);
    for pid in [app.pid, timeout.pid].into_iter().chain(extra) {
        let dir = if pid == timeout.pid { root.join(pid.to_string()) } else { root.join(format!("{}/task/{pid}", app.pid)) };
        let syscall = observation(read(&dir.join("syscall"), 512));
        let status=read(&dir.join("status"),8192);
        if pid==app.pid {
            // task/PID/stat is per-thread; /proc/PID/stat aggregates its group.
            let cpu=match read(&dir.join("stat"),4096).and_then(|s|cpu_ticks(&s,app)) {
                Ok((u,s))=>format!("utime_ticks={u} stime_ticks={s}"),
                Err(e)=>format!("cpu=unavailable:{e}"),
            };
            let switches=match status.as_ref().map_err(Clone::clone).and_then(|s|context_switches(s)) {
                Ok((v,n))=>format!("voluntary={v} involuntary={n}"),
                Err(e)=>format!("switches=unavailable:{e}"),
            };
            out.add("thread-cpu",round,pid,format!("{cpu} {switches}").as_bytes())?;
        }
        let signals = status.map(|s| String::from_utf8_lossy(&s).lines().filter(|s| ["State:","Tgid:","Pid:","PPid:","SigPnd:","ShdPnd:","SigBlk:","SigIgn:","SigCgt:"].iter().any(|p| s.starts_with(p))).collect::<Vec<_>>().join(";").into_bytes());
        let mut combined = b"syscall=".to_vec();
        combined.extend_from_slice(&syscall); combined.extend_from_slice(b" status="); combined.extend_from_slice(&observation(signals));
        out.add("task", round, pid, &combined)?;
        if pid == app.pid { out.add("pc-map", round, pid, &pc_map(root, app.pid, &syscall))?; }
    }
    if round == 0 {
        let fd_dir = root.join(format!("{}/fd", app.pid));
        match fs::read_dir(&fd_dir) {
            Err(e) => out.add("fd-unavailable", round, app.pid, format!("{:?}", e.kind()).as_bytes())?,
            Ok(entries) => {
                let mut fds: Vec<u32> = entries.take(64).filter_map(Result::ok).filter_map(|e| e.file_name().to_str()?.parse().ok()).collect();
                fds.sort_unstable();
                if fds.len() > 8 { out.truncated = true; }
                for fd in fds.into_iter().take(8) {
                    let value = match fs::read_link(fd_dir.join(fd.to_string())) { Ok(v) => format!("fd={fd} target={}", escaped(v.as_os_str().as_bytes())), Err(e) => format!("fd={fd} unavailable={:?}", e.kind()) };
                    out.add("fd", round, app.pid, value.as_bytes())?;
                }
            }
        }
    }
    // A reused/exited identity invalidates attribution of this entire round.
    for (target, parent, comm) in [(timeout, None, None), (app, Some(timeout.pid), Some("mousepad"))] {
        if let Err(e) = check(root, target, uid, parent, comm) { out.invalidated = true; out.reserved = 0; out.add("round-invalidated", round, target.pid, e.as_bytes())?; return Ok(false); }
    }
    Ok(true)
}
fn markers(bytes: &[u8]) -> bool {
    let Ok(s) = std::str::from_utf8(bytes) else { return false; };
    ["rog5.logind_fixture", "rog5.virtual_drm"].iter().all(|key| {
        let prefix = format!("{key}="); s.split_whitespace().filter(|s| s.starts_with(&prefix)).eq([format!("{key}=1").as_str()])
    })
}
fn valid_stdout(meta: &fs::Metadata, uid: u32) -> bool {
    meta.is_file() && meta.uid() == uid && meta.mode() & 0o7777 == 0o600 && meta.nlink() == 1 && meta.len() == 0
}
#[cfg(close_ptrace)]
fn pc_observation(root: &Path, timeout: Target, app: Target, uid: u32) -> Result<(String, Vec<u8>), String> {
    let owned_root = root.to_owned();
    let validate = move || {
        check(&owned_root, timeout, uid, None, None)?;
        check(&owned_root, app, uid, Some(timeout.pid), Some("mousepad"))?;
        Ok(())
    };
    let shot = ptrace::capture(app.pid as i32, validate)?;
    let mapping = pc_map(root, app.pid, format!("-1 {:#x} {:#x}", shot.sp, shot.pc).as_bytes());
    // Maps are read after detach, not an atomic snapshot. Reject attribution if
    // either identity changed before that bounded read finished.
    check(root, timeout, uid, None, None)?;
    check(root, app, uid, Some(timeout.pid), Some("mousepad"))?;
    let mut now = Timespec { seconds: 0, nanos: 0 };
    // SAFETY: writable timespec, Linux CLOCK_MONOTONIC.
    if unsafe { clock_gettime(1, &mut now) } != 0 { return Err(io::Error::last_os_error().to_string()); }
    Ok((format!("intrusive=true pc={:#x} sp={:#x} fp={:#x} lr={:?} interrupt_to_detach_us={} end_monotonic={}.{:09}",
        shot.pc, shot.sp, shot.frame_pointer, shot.link_register, shot.interrupt_to_detach.as_micros(), now.seconds, now.nanos), mapping))
}
#[cfg(close_ptrace)]
fn before_snapshot_deadline<T>(start: Instant, capture: impl FnOnce() -> Result<T, String>) -> Result<T, String> {
    if start.elapsed() >= Duration::from_millis(1200) { return Err("snapshot-start-deadline".into()); }
    capture()
}
#[cfg(close_ptrace)]
fn publish_pc<W: Write>(out: &mut Records<W>, pid: u32, result: Result<(String, Vec<u8>), String>) -> io::Result<bool> {
    out.reserved -= 1536;
    match result {
        Ok((shot, mapping)) => {
            let before = out.count;
            out.add("ptrace-pc", 1, pid, shot.as_bytes())?;
            out.add("ptrace-map", 1, pid, &mapping)?;
            Ok(out.count == before + 2)
        },
        Err(e) => { out.add("ptrace-unavailable", 1, pid, e.as_bytes())?; Ok(false) }
    }
}
fn run() -> Result<(), String> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 4 || args.iter().any(|s| s.is_empty() || !s.bytes().all(|b| b.is_ascii_digit())) { return Err("four positive identity arguments required".into()); }
    let values = args.iter().map(|s| s.parse::<u64>()).collect::<Result<Vec<_>,_>>().map_err(|_| "identity-range")?;
    if values.contains(&0) || values[0] > i32::MAX as u64 || values[2] > i32::MAX as u64 { return Err("identity-range".into()); }
    // SAFETY: read-only process credential queries.
    if unsafe { getuid() != 1000 || geteuid() != 1000 } || !markers(&read(Path::new("/proc/cmdline"), 8192)?) { return Err("requires non-root isolated VM".into()); }
    // Intentional descriptor metadata lookup, never read its underlying data.
    let meta = fs::metadata("/proc/self/fd/1").map_err(|e| e.to_string())?;
    if !valid_stdout(&meta, 1000) { return Err("stdout must be empty owned0600 single-link regular file".into()); }
    let mut out = Records::new(io::stdout().lock());
    let start = Instant::now();
    let timeout = Target {pid: values[0] as u32, start: values[1]};
    let app = Target {pid: values[2] as u32, start: values[3]};
    #[cfg(close_ptrace)]
    let mut snapshot_done = false;
    for round in 0..6 {
        if round > 0 {
            let next = start + Duration::from_millis(round as u64 * 200);
            if let Some(delay) = next.checked_duration_since(Instant::now()) { std::thread::sleep(delay); }
        }
        if start.elapsed() >= Duration::from_millis(1200) { out.truncated = true; break; }
        if !sample(Path::new("/proc"), timeout, app, 1000, round, &mut out).map_err(|e| e.to_string())? { break; }
        #[cfg(close_ptrace)]
        if round == 1 {
            let result = before_snapshot_deadline(start, || pc_observation(Path::new("/proc"), timeout, app, 1000));
            snapshot_done = publish_pc(&mut out, app.pid, result).map_err(|e| e.to_string())?;
            if !snapshot_done { break; }
        }
    }
    out.finish(start.elapsed()).map_err(|e| e.to_string())?;
    #[cfg(close_ptrace)]
    if !snapshot_done { return Err("requested ptrace snapshot not captured/published".into()); }
    Ok(())
}
fn main() { if let Err(e) = run() { eprintln!("APP_CLOSE_PROBE refused: {e}"); std::process::exit(125); } }

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::symlink;
    #[cfg(close_ptrace)]
    #[test] fn expired_budget_never_starts_snapshot() {
        let mut called=false;
        assert_eq!(before_snapshot_deadline(Instant::now()-Duration::from_secs(2),|| {called=true;Ok(())}),Err("snapshot-start-deadline".into()));
        assert!(!called);
        assert_eq!(before_snapshot_deadline(Instant::now(),||Ok(7)).unwrap(),7);
    }
    #[cfg(close_ptrace)]
    #[test] fn actual_pc_observation_revalidates_parent_uid_and_start() {
        use std::process::{Command, Stdio, Child};
        struct Owned(Child);
        impl Drop for Owned { fn drop(&mut self) { if matches!(self.0.try_wait(),Ok(None)) { let _=self.0.kill(); let _=self.0.wait(); } } }
        let dir=std::env::temp_dir().join(format!("rog5-pc-integration-{}",std::process::id()));
        fs::create_dir(&dir).unwrap();
        struct Scratch(std::path::PathBuf);
        impl Drop for Scratch { fn drop(&mut self) { let _=fs::remove_dir_all(&self.0); } }
        let _scratch=Scratch(dir.clone());
        symlink("/bin/sleep",dir.join("mousepad")).unwrap();
        let child=Owned(Command::new(dir.join("mousepad")).arg("30").stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null()).spawn().unwrap());
        let root=Path::new("/proc"); let start=Instant::now();
        let app=loop {
            let id=identity(&read(&root.join(format!("{}/stat",child.0.id())),4096).unwrap()).unwrap();
            if id.comm=="mousepad" { break Target{pid:id.pid,start:id.start}; }
            assert!(start.elapsed()<Duration::from_secs(1)); std::thread::sleep(Duration::from_millis(1));
        };
        let id=identity(&read(&root.join(format!("{}/stat",std::process::id())),4096).unwrap()).unwrap();
        let timeout=Target{pid:id.pid,start:id.start};
        // SAFETY: read-only current credential query for the owned-child fixture.
        let uid=unsafe{getuid()};
        assert!(pc_observation(root,timeout,Target{start:app.start+1,..app},uid).is_err());
        assert!(pc_observation(root,timeout,app,uid+1).is_err());
        let (shot,map)=pc_observation(root,timeout,app,uid).unwrap();
        assert!(shot.contains("intrusive=true pc=0x") && shot.contains("end_monotonic="));
        assert!(!map.starts_with(b"unavailable:"));
        assert!(String::from_utf8(read(&root.join(format!("{}/status",app.pid)),8192).unwrap()).unwrap().contains("TracerPid:\t0"));
    }
    fn stat(pid: u32, parent: u32, start: u64, comm: &str) -> String { format!("{pid} ({comm}) S {parent} {} {start}\n", vec!["0";17].join(" ")) }
    #[test] fn parses_parentheses_and_rejects_short_stat() { let i=identity(stat(20,10,99,"weird ) comm").as_bytes()).unwrap(); assert_eq!((i.pid,i.ppid,i.start,i.comm),(20,10,99,"weird ) comm".into())); assert!(identity(b"20 (x) S 10").is_err()); }
    #[test] fn cpu_and_switch_counters_reject_missing_invalid_or_reused_data() {
        let target=Target{pid:20,start:99};
        assert_eq!(cpu_ticks(stat(20,10,99,"weird ) comm").as_bytes(),target).unwrap(),(0,0));
        assert!(cpu_ticks(stat(20,10,100,"mousepad").as_bytes(),target).is_err());
        assert!(cpu_ticks(b"20 (mousepad) R 10",target).is_err());
        let mut fields=vec!["0";20];fields[0]="R";fields[1]="10";fields[19]="99";
        for value in ["-1","18446744073709551616","bad"] {
            fields[11]=value;
            assert!(cpu_ticks(format!("20 (mousepad) {}",fields.join(" ")).as_bytes(),target).is_err());
        }
        assert_eq!(context_switches(b"voluntary_ctxt_switches:\t0\nnonvoluntary_ctxt_switches:\t9\n").unwrap(),(0,9));
        for value in [b"".as_slice(),b"voluntary_ctxt_switches: 1\n",
            b"voluntary_ctxt_switches: 1\nvoluntary_ctxt_switches: 2\nnonvoluntary_ctxt_switches: 3\n",
            b"voluntary_ctxt_switches: -1\nnonvoluntary_ctxt_switches: 0\n",
            b"voluntary_ctxt_switches: 1 2\nnonvoluntary_ctxt_switches: 0\n"] {
            assert!(context_switches(value).is_err());
        }
    }
    #[test] fn markers_require_exact_unique_tokens() { assert!(markers(b"rog5.logind_fixture=1 rog5.virtual_drm=1")); assert!(!markers(b"rog5.logind_fixture=1 rog5.virtual_drm=1 rog5.virtual_drm=0")); assert!(!markers(b"rog5.logind_fixture=1 rog5.virtual_drm=11")); }
    #[test] fn output_bounded_and_unforgeable() { let mut out=Records::new(Vec::new()); for n in 0..100 {out.add("test",n,20,b"\nAPP_CLOSE_PROBE forged\x00").unwrap();} out.finish(Duration::ZERO).unwrap(); let s=String::from_utf8(out.writer).unwrap(); assert!(s.len()<=8192); assert!(s.lines().count()<=64); assert!(!s.contains("\nAPP_CLOSE_PROBE forged")); assert!(s.contains("truncated=true")); assert!(s.lines().all(|l|l.len()<1024)); }
    #[test] fn fixture_sampler_identity_fd_and_limits() {
        let dir=std::env::temp_dir().join(format!("app-close-proc-{}",std::process::id())); fs::create_dir(&dir).unwrap();
        struct Cleanup(std::path::PathBuf); impl Drop for Cleanup {fn drop(&mut self){let _=fs::remove_dir_all(&self.0);}} let _cleanup=Cleanup(dir.clone());
        let output=dir.join("output"); let file=OpenOptions::new().write(true).create_new(true).mode(0o600).open(&output).unwrap();
        assert!(valid_stdout(&file.metadata().unwrap(),unsafe{getuid()}));
        assert!(!valid_stdout(&file.metadata().unwrap(),unsafe{getuid()}.wrapping_add(1)));
        fs::hard_link(&output,dir.join("output-link")).unwrap(); assert!(!valid_stdout(&file.metadata().unwrap(),unsafe{getuid()}));
        fs::remove_file(dir.join("output-link")).unwrap(); fs::write(&output,b"nonempty").unwrap(); assert!(!valid_stdout(&file.metadata().unwrap(),unsafe{getuid()}));
        for (pid,parent,comm) in [(10,1,"timeout"),(20,10,"mousepad")] { let p=dir.join(pid.to_string()); fs::create_dir(&p).unwrap(); fs::write(p.join("stat"),stat(pid,parent,99,comm)).unwrap(); fs::write(p.join("status"),"Uid:\t1000\t1000\t1000\t1000\nState:\tS\nSigPnd:\t0\n").unwrap(); fs::write(p.join("syscall"),"98 0x1 0x2\n").unwrap(); }
        fs::create_dir_all(dir.join("20/task/20")).unwrap(); for f in ["stat","status","syscall"] {fs::copy(dir.join("20").join(f),dir.join("20/task/20").join(f)).unwrap();}
        let task_stat = |user: u64| {
            let mut fields=vec!["0".to_string();20];
            fields[0]="R".into(); fields[1]="10".into(); fields[11]=user.to_string();
            fields[12]="7".into(); fields[19]="99".into();
            format!("20 (mousepad) {}\n",fields.join(" "))
        };
        // Process stat remains zero: the counter must come from task/20/stat.
        fs::write(dir.join("20/task/20/stat"),task_stat(42)).unwrap();
        fs::write(dir.join("20/task/20/status"),"State:\tR\nvoluntary_ctxt_switches:\t5\nnonvoluntary_ctxt_switches:\t6\n").unwrap();
        fs::write(dir.join("20/maps"),"00000001-00000010 r-xp 00000000 00:00 0 /fixture.so\n").unwrap();
        assert!(String::from_utf8_lossy(&pc_map(&dir,20,b"98 0x1 0x2")).contains("/fixture.so"));
        assert_eq!(pc_map(&dir,20,b"running"),b"unavailable:no-sampled-pc");
        fs::create_dir(dir.join("20/fd")).unwrap(); for fd in 0..20 { symlink(format!("pipe:[123]{}", "x".repeat(800)),dir.join(format!("20/fd/{fd}"))).unwrap(); }
        let (t,a)=(Target{pid:10,start:99},Target{pid:20,start:99}); let mut out=Records::new(Vec::new()); assert!(sample(&dir,t,a,1000,0,&mut out).unwrap()); assert!(String::from_utf8_lossy(&out.writer).contains("kind=fd"));
        for round in 1..6 {
            fs::write(dir.join("20/task/20/stat"),task_stat(42+round as u64)).unwrap();
            assert!(sample(&dir,t,a,1000,round,&mut out).unwrap());
            #[cfg(close_ptrace)]
            if round==1 { assert!(publish_pc(&mut out,a.pid,Ok(("snapshot".repeat(25),vec![b'x';768]))).unwrap()); }
        }
        out.finish(Duration::from_millis(1000)).unwrap();
        let data=String::from_utf8_lossy(&out.writer); assert!(data.contains("kind=task round=5 pid=20")); assert!(data.contains("truncated=true")); assert!(data.len()<=8192);
        assert!(data.contains("utime_ticks=42 stime_ticks=7"));
        assert!(data.contains("utime_ticks=47 stime_ticks=7"));
        assert!(data.contains("voluntary=5 involuntary=6"));
        assert_eq!(data.matches("kind=thread-cpu").count(),6);
        assert!(data.contains("ticks_per_second="));
        #[cfg(close_ptrace)]
        { assert!(data.contains("kind=ptrace-pc") && data.contains("kind=ptrace-map")); }
        let mut out=Records::new(Vec::new());
        fs::write(dir.join("20/stat"),stat(20,10,99,"wrong")).unwrap(); assert!(check(&dir,a,1000,Some(10),Some("mousepad")).is_err());
        fs::write(dir.join("20/stat"),stat(20,10,99,"mousepad").replace(") S ",") Z ")).unwrap(); assert_eq!(check(&dir,a,1000,Some(10),Some("mousepad")).unwrap_err(),"exited");
        fs::write(dir.join("20/stat"),stat(20,10,100,"mousepad")).unwrap(); assert!(!sample(&dir,t,a,1000,1,&mut out).unwrap());
        fs::write(dir.join("20/stat"),stat(20,11,99,"mousepad")).unwrap(); assert!(check(&dir,a,1000,Some(10),Some("mousepad")).is_err());
        fs::write(dir.join("20/stat"),stat(20,10,99,"mousepad")).unwrap(); fs::write(dir.join("20/status"),"Uid: 1001 1001 1001 1001\n").unwrap(); assert!(check(&dir,a,1000,Some(10),None).is_err());
        symlink("status",dir.join("20/link")).unwrap(); assert!(read(&dir.join("20/link"),8192).is_err()); assert!(read(&dir.join("20/status"),3).is_err());
    }
    #[test] fn real_owned_child_metadata() {
        struct ChildGuard(std::process::Child); impl Drop for ChildGuard { fn drop(&mut self) { let _=self.0.kill(); let _=self.0.wait(); } }
        let mut owned=ChildGuard(std::process::Command::new("sleep").arg("3").spawn().unwrap());
        let child=&mut owned.0;
        let p=Path::new("/proc").join(child.id().to_string()); let id=identity(&read(&p.join("stat"),4096).unwrap()).unwrap(); assert_eq!(id.ppid,std::process::id());
        let target=Target{pid:child.id(),start:id.start}; assert!(check(Path::new("/proc"),target,unsafe{getuid()},Some(std::process::id()),None).is_ok());
        let result=read(&p.join("syscall"),512); eprintln!("real-owned-child syscall={}",String::from_utf8_lossy(&observation(result)));
        // Only the test owns and cleans this child; production never signals.
        child.kill().unwrap(); child.wait().unwrap(); assert!(check(Path::new("/proc"),target,unsafe{getuid()},None,None).is_err());
    }
}
