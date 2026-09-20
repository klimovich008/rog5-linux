//! Bounded observation of the VM diagnostic DSO's append-only lifecycle log.
//! This is an observation gate, not authentication of a cooperative log writer.
//! Process identity must separately be checked by the owning capture helper.
use std::{fs::{self, File, Metadata, OpenOptions}, os::unix::{fs::{FileExt, MetadataExt, OpenOptionsExt}}, path::{Path, PathBuf}, sync::Mutex};

#[derive(Debug, Eq, PartialEq)]
pub enum State { Waiting, Ready, Complete }

// Linux ARM64 overrides the asm-generic O_NOFOLLOW value for AArch32
// compatibility (arch/arm64/include/uapi/asm/fcntl.h in the pinned source).
// Reject other targets rather than silently applying another ABI's flags.
#[cfg(not(all(target_os = "linux", any(target_arch = "x86_64", target_arch = "aarch64"))))]
compile_error!("stage reader requires Linux x86-64 or aarch64 open flags");
#[cfg(target_arch = "aarch64")]
const NOFOLLOW: i32 = 0o100000;
#[cfg(target_arch = "x86_64")]
const NOFOLLOW: i32 = 0o400000;
const NONBLOCK: i32 = 0o4000;
const MAX_BYTES: usize = 1536;

pub struct Gate {
    path: PathBuf,
    file: File,
    pid: u32,
    uid: u32,
    device: u64,
    inode: u64,
    prefix: Mutex<Vec<u8>>,
}
impl Gate {
    pub fn open(path: &Path, pid: u32, uid: u32) -> Result<Self,String> {
        if pid == 0 { return Err("stage-invalid-pid".into()); }
        let file=OpenOptions::new().read(true).custom_flags(NOFOLLOW | NONBLOCK)
            .open(path).map_err(|e| format!("stage-open: {e}"))?;
        let m=file.metadata().map_err(|e| format!("stage-stat: {e}"))?;
        let gate=Self { path:path.into(),file,pid,uid,device:m.dev(),inode:m.ino(),prefix:Mutex::new(Vec::new()) };
        // Pin existing bytes now, before the first caller poll. Completed logs
        // remain Complete; opening one must never turn a stale END into Ready.
        gate.state()?;
        Ok(gate)
    }
    fn metadata(&self) -> Result<Metadata,String> {
        let descriptor=self.file.metadata().map_err(|e| format!("stage-stat: {e}"))?;
        let path=fs::symlink_metadata(&self.path).map_err(|e| format!("stage-path: {e}"))?;
        for m in [&descriptor,&path] {
            if !m.is_file() || m.uid()!=self.uid || m.mode() & 0o7777 != 0o600 || m.nlink()!=1
                || m.len()>MAX_BYTES as u64 || m.dev()!=self.device || m.ino()!=self.inode {
                return Err("stage-file-identity".into());
            }
        }
        Ok(descriptor)
    }
    pub fn state(&self) -> Result<State,String> {
        // Never wait for another polling caller inside the capture deadline.
        let mut prefix=self.prefix.try_lock().map_err(|_| "stage-reader-busy")?;
        let before=self.metadata()?;
        let mut bytes=vec![0;before.len() as usize];
        let count=self.file.read_at(&mut bytes,0).map_err(|e| format!("stage-read: {e}"))?;
        let after=self.metadata()?;
        if count!=bytes.len() || !bytes.starts_with(&prefix) {
            return Err("stage-log-shrunk-or-rewritten".into());
        }
        let state=parse(&bytes,self.pid)?;
        *prefix=bytes;
        // An append can advance through the target phase while read_at runs.
        // Retry on the next bounded poll; never publish a stale Ready snapshot.
        if before.len()!=after.len() || before.mtime()!=after.mtime()
            || before.mtime_nsec()!=after.mtime_nsec() || before.ctime()!=after.ctime()
            || before.ctime_nsec()!=after.ctime_nsec() {
            return Ok(State::Waiting);
        }
        Ok(state)
    }
}

fn parse(bytes: &[u8], pid: u32) -> Result<State,String> {
    if bytes.len()>MAX_BYTES || !bytes.is_ascii() { return Err("stage-log-encoding-or-limit".into()); }
    let text=std::str::from_utf8(bytes).map_err(|_| "stage-log-encoding")?;
    let complete=text.rfind('\n').map_or(0,|i|i+1);
    let tail=&text[complete..];
    if tail.len()>=127 || tail.bytes().any(|b| b<32 || b==127) { return Err("stage-line-limit-or-control".into()); }
    let stages=["loaded resolved=true","APP_RUN_BEGIN","SHUTDOWN_BEFORE","BEGIN","END",
        "SHUTDOWN_AFTER","APP_RUN_END","APP_DISCONNECT_ONE_END","APP_OBSERVERS_REMOVED",
        "APP_UNREF_BEGIN","APP_UNREF_END","DSO_FINI"];
    let mut step=0;
    let mut previous=None;
    for line in text[..complete].split_terminator('\n') {
        if line.len()+1>=128 || step>=stages.len() { return Err("stage-record-limit".into()); }
        let (phase,rest)=line.strip_prefix("ROG5_SETTINGS_SYNC phase=")
            .and_then(|s|s.split_once(" pid=")).ok_or("stage-record-shape")?;
        let (found_pid,time)=rest.split_once(" clock=CLOCK_MONOTONIC seconds=").ok_or("stage-clock-shape")?;
        if found_pid!=pid.to_string() { return Err("stage-pid-mismatch".into()); }
        let (seconds,nanos)=time.split_once('.').ok_or("stage-time-shape")?;
        if seconds.is_empty() || seconds.len()>19 || !seconds.bytes().all(|b|b.is_ascii_digit())
            || (seconds.len()>1 && seconds.starts_with('0')) || nanos.len()!=9
            || !nanos.bytes().all(|b|b.is_ascii_digit()) { return Err("stage-time-shape".into()); }
        let now=(seconds.parse::<u64>().map_err(|_| "stage-time-range")?,nanos.parse::<u32>().map_err(|_| "stage-time-range")?);
        if previous.is_some_and(|old|now<old) { return Err("stage-time-reversed".into()); }
        previous=Some(now);
        // The explicitly built no-unref control omits these two records.
        if step==9 && phase=="DSO_FINI" { step=11; }
        if phase!=stages[step] { return Err("stage-order-or-unknown-phase".into()); }
        step+=1;
    }
    if !tail.is_empty() { return Ok(State::Waiting); }
    Ok(if step<5 { State::Waiting } else if step==5 { State::Ready } else { State::Complete })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{io::Write, os::unix::fs::{PermissionsExt, symlink}, sync::atomic::{AtomicU32, Ordering}};
    static NEXT: AtomicU32 = AtomicU32::new(0);
    const PID: u32 = 123;
    struct Fixture { dir: PathBuf, path: PathBuf, writer: File, uid: u32 }
    impl Fixture {
        fn new() -> Self {
            let dir = std::env::temp_dir().join(format!("rog5-stage-{}-{}",std::process::id(),NEXT.fetch_add(1,Ordering::Relaxed)));
            fs::create_dir(&dir).unwrap();
            let path=dir.join("stage.log");
            let writer=OpenOptions::new().write(true).create_new(true).mode(0o600).open(&path).unwrap();
            let uid=writer.metadata().unwrap().uid();
            Self {dir,path,writer,uid}
        }
        fn open(&self) -> Gate { Gate::open(&self.path,PID,self.uid).unwrap() }
        fn append(&mut self, bytes: &[u8]) { self.writer.write_all(bytes).unwrap(); }
        fn stage(&mut self, phase: &str, tick: u32) { self.append(line(phase,tick).as_bytes()); }
        fn ready(&mut self) { for (i,p) in ["loaded resolved=true","APP_RUN_BEGIN","SHUTDOWN_BEFORE","BEGIN","END"].iter().enumerate() { self.stage(p,i as u32); } }
    }
    impl Drop for Fixture { fn drop(&mut self) { fs::remove_dir_all(&self.dir).unwrap(); } }
    fn line(phase: &str,tick: u32) -> String { format!("ROG5_SETTINGS_SYNC phase={phase} pid={PID} clock=CLOCK_MONOTONIC seconds=1.{tick:09}\n") }
    #[test]
    fn real_append_waits_until_end_then_completes() {
        let mut f=Fixture::new(); let g=f.open();
        assert_eq!(g.state().unwrap(),State::Waiting);
        for (i,p) in ["loaded resolved=true","APP_RUN_BEGIN","SHUTDOWN_BEFORE","BEGIN"].iter().enumerate() { f.stage(p,i as u32); assert_eq!(g.state().unwrap(),State::Waiting); }
        f.stage("END",4); assert_eq!(g.state().unwrap(),State::Ready);
        f.stage("SHUTDOWN_AFTER",5); assert_eq!(g.state().unwrap(),State::Complete);
    }
    #[test]
    fn partial_tail_never_yields_ready() {
        let mut f=Fixture::new(); f.ready(); let g=f.open();
        let end=line("SHUTDOWN_AFTER",5); f.append(&end.as_bytes()[..20]);
        assert_eq!(g.state().unwrap(),State::Waiting);
        f.append(&end.as_bytes()[20..]); assert_eq!(g.state().unwrap(),State::Complete);
    }
    #[test]
    fn completed_snapshots_support_both_dso_variants() {
        for unref in [false,true] { let mut f=Fixture::new(); f.ready();
            let mut phases=vec!["SHUTDOWN_AFTER","APP_RUN_END","APP_DISCONNECT_ONE_END","APP_OBSERVERS_REMOVED"];
            if unref { phases.extend(["APP_UNREF_BEGIN","APP_UNREF_END"]); }
            phases.push("DSO_FINI");
            for (i,p) in phases.iter().enumerate() { f.stage(p,5+i as u32); }
            assert_eq!(f.open().state().unwrap(),State::Complete);
        }
    }
    #[test]
    fn rejects_wrong_pid_order_time_duplicates_and_grammar() {
        for bad in [line("APP_RUN_BEGIN",1),line("loaded",0),line("loaded resolved=true",0).replace("pid=123","pid=124"),line("loaded resolved=true",0).replace("seconds=1.","seconds=+1."),line("loaded resolved=true",0).replace("CLOCK_MONOTONIC","CLOCK_REALTIME")] {
            let mut f=Fixture::new(); let g=f.open(); f.append(bad.as_bytes()); assert!(g.state().is_err(),"{bad}");
        }
        for phase in ["END","UNKNOWN","loaded resolved=true"] { let mut f=Fixture::new(); let g=f.open(); f.ready(); f.stage(phase,8); assert!(g.state().is_err()); }
        let mut f=Fixture::new(); let g=f.open(); f.stage("loaded resolved=true",3); f.stage("APP_RUN_BEGIN",2); assert!(g.state().is_err());
    }
    #[test]
    fn rejects_links_modes_ownership_and_nonregular() {
        let f=Fixture::new(); let link=f.dir.join("link"); symlink(&f.path,&link).unwrap();
        assert!(Gate::open(&link,PID,f.uid).is_err());
        assert!(Gate::open(&f.path,PID,f.uid+1).is_err());
        assert!(Gate::open(&f.dir,PID,f.uid).is_err());
        fs::hard_link(&f.path,f.dir.join("hard")).unwrap(); assert!(Gate::open(&f.path,PID,f.uid).is_err());
        fs::remove_file(f.dir.join("hard")).unwrap(); fs::set_permissions(&f.path,fs::Permissions::from_mode(0o640)).unwrap(); assert!(Gate::open(&f.path,PID,f.uid).is_err());
    }
    #[test]
    fn refuses_replacement_truncate_rewrite_and_oversize() {
        for change in ["replace","truncate","rewrite","oversize","mode","link"] {
            let mut f=Fixture::new(); f.ready(); let g=f.open(); assert_eq!(g.state().unwrap(),State::Ready);
            match change {
                "replace" => { fs::rename(&f.path,f.dir.join("old")).unwrap(); File::create(&f.path).unwrap(); }
                "truncate" => f.writer.set_len(0).unwrap(),
                "rewrite" => { f.writer.write_at(b"X",0).unwrap(); }
                "oversize" => f.writer.set_len(1537).unwrap(),
                "mode" => fs::set_permissions(&f.path,fs::Permissions::from_mode(0o644)).unwrap(),
                "link" => fs::hard_link(&f.path,f.dir.join("hard")).unwrap(),
                _ => unreachable!()
            }
            assert!(g.state().is_err(),"{change}");
        }
    }
    #[test]
    fn target_open_flags_reject_symlink_before_metadata_validation() {
        #[cfg(target_arch = "aarch64")]
        assert_eq!(NOFOLLOW,0o100000);
        #[cfg(target_arch = "x86_64")]
        assert_eq!(NOFOLLOW,0o400000);
        let f=Fixture::new(); let link=f.dir.join("link");
        symlink(&f.path,&link).unwrap();
        // Test the kernel open semantics directly: Gate's later symlink metadata
        // rejection would otherwise hide a wrong O_NOFOLLOW ABI constant.
        let error=OpenOptions::new().read(true).custom_flags(NOFOLLOW | NONBLOCK)
            .open(&link).unwrap_err();
        assert_eq!(error.raw_os_error(),Some(40)); // ELOOP on both supported ABIs.
    }
    #[test]
    fn fifo_open_does_not_block_and_is_refused() {
        use std::{ffi::CString, os::unix::ffi::OsStrExt};
        unsafe extern "C" { fn mkfifo(path: *const std::ffi::c_char, mode: u32) -> i32; }
        let f=Fixture::new(); let path=f.dir.join("fifo");
        let name=CString::new(path.as_os_str().as_bytes()).unwrap();
        // Owned fixture path, NUL-terminated bytes, no writer: without NONBLOCK
        // open would stall, so the enclosing test runner deadline is essential.
        assert_eq!(unsafe { mkfifo(name.as_ptr(),0o600) },0);
        assert!(Gate::open(&path,PID,f.uid).is_err());
    }
    #[test]
    fn rejects_encoding_record_limits_and_incomplete_oversized_lines() {
        for bytes in [vec![255],vec![b'x';128],vec![b'x';1537],b"\n".to_vec()] {
            assert!(parse(&bytes,PID).is_err());
        }
        let mut f=Fixture::new(); f.ready();
        for (i,p) in ["SHUTDOWN_AFTER","APP_RUN_END","APP_DISCONNECT_ONE_END","APP_OBSERVERS_REMOVED","APP_UNREF_BEGIN","APP_UNREF_END","DSO_FINI"].iter().enumerate() { f.stage(p,i as u32+5); }
        let g=f.open(); f.stage("DSO_FINI",20); assert!(g.state().is_err());
    }
    #[test]
    fn append_to_a_partial_target_line_only_readies_after_newline() {
        let mut f=Fixture::new();
        for (i,p) in ["loaded resolved=true","APP_RUN_BEGIN","SHUTDOWN_BEFORE","BEGIN"].iter().enumerate() { f.stage(p,i as u32); }
        let end=line("END",4); f.append(&end.as_bytes()[..end.len()-1]);
        let g=f.open(); assert_eq!(g.state().unwrap(),State::Waiting);
        f.append(b"\n"); assert_eq!(g.state().unwrap(),State::Ready);
    }
    #[test]
    fn opened_prefix_is_retained_before_first_poll() {
        let mut f=Fixture::new(); f.ready(); let g=f.open();
        f.writer.set_len(0).unwrap(); assert!(g.state().is_err());
    }
}
