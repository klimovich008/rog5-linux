//! Bounded frame-pointer candidates for a stopped, identity-validated VM task.
//! Not wired into the VM sampler yet. Call only within capture_inspect(). Other
//! threads remain runnable, so maps and frame records are not an atomic snapshot.
use std::{ffi::c_void, fs::File, io::{self, Read}, time::{Duration, Instant}};

const MAX_MAPS: usize = 65536;
const MAX_FRAMES: usize = 4;
const MAX_DISTANCE: u64 = 65536;
const BUDGET: Duration = Duration::from_millis(15);

#[derive(Clone, Debug, PartialEq)]
pub struct Mapping {
    pub start: u64,
    pub end: u64,
    pub offset: u64,
    pub path: String,
    readable: bool,
    writable: bool,
    executable: bool,
}

#[derive(Debug, PartialEq)]
pub struct Frame {
    pub address: u64,
    /// Raw saved return address. PAC bits are never silently stripped.
    pub return_address: u64,
    pub executable_mapping: Option<Mapping>,
}

#[derive(Debug, PartialEq)]
pub enum Stop { End, Limit, Deadline, InvalidFrame, NonIncreasing, ReadFailed, ShortRead }

#[derive(Debug, PartialEq)]
pub struct Trace {
    pub frames: Vec<Frame>,
    pub stop: Stop,
}

fn maps(text: &str) -> Result<Vec<Mapping>, String> {
    if text.len() > MAX_MAPS { return Err("maps-byte-limit".into()); }
    text.lines().map(|line| {
        let mut fields = line.split_whitespace();
        let (start, end) = fields.next().and_then(|s| s.split_once('-')).ok_or("maps-range")?;
        let hex = |s| u64::from_str_radix(s,16).map_err(|_| "maps-hex".to_string());
        let (start,end)=(hex(start)?,hex(end)?);
        let permissions=fields.next().ok_or("maps-permissions")?.as_bytes();
        if start>=end || permissions.len()!=4 { return Err("maps-shape".into()); }
        let offset=hex(fields.next().ok_or("maps-offset")?)?;
        fields.next().ok_or("maps-device")?;
        fields.next().ok_or("maps-inode")?;
        let path=fields.collect::<Vec<_>>().join(" ");
        if path.len()>512 { return Err("maps-path-limit".into()); }
        Ok(Mapping {start,end,offset,path,readable:permissions[0]==b'r',writable:permissions[1]==b'w',executable:permissions[2]==b'x'})
    }).collect()
}

fn stack_map(mappings: &[Mapping], sp: u64) -> Result<&Mapping, String> {
    let mut matches=mappings.iter().filter(|m| m.path=="[stack]" && m.readable && m.writable && m.start<=sp && sp<m.end);
    let selected=matches.next().ok_or("unsupported-stack-mapping")?;
    if matches.next().is_some() { return Err("ambiguous-stack-mapping".into()); }
    Ok(selected)
}

// The same traversal is used by actual reads and fault-injection fixtures.
fn walk(mappings: &[Mapping], sp: u64, mut fp: u64,
        mut read: impl FnMut(u64, &mut [u8;16]) -> io::Result<usize>,
        mut expired: impl FnMut() -> bool) -> Result<Trace,String> {
    let stack=stack_map(mappings,sp)?;
    let mut frames=Vec::with_capacity(MAX_FRAMES);
    let stop=loop {
        if fp==0 { break Stop::End; }
        if frames.len()==MAX_FRAMES { break Stop::Limit; }
        if expired() { break Stop::Deadline; }
        if fp%16!=0 || fp<stack.start || fp.checked_add(16).is_none_or(|end| end>stack.end)
            || fp.checked_sub(sp).is_none_or(|distance| distance>MAX_DISTANCE) {
            break Stop::InvalidFrame;
        }
        let mut bytes=[0u8;16];
        match read(fp,&mut bytes) {
            Ok(16)=>{}, Ok(_)=>break Stop::ShortRead, Err(_)=>break Stop::ReadFailed,
        }
        // Deadlines include reads: never publish a late frame as on-time data.
        if expired() { break Stop::Deadline; }
        let next=u64::from_ne_bytes(bytes[..8].try_into().map_err(|_| "frame-size")?);
        let ret=u64::from_ne_bytes(bytes[8..].try_into().map_err(|_| "frame-size")?);
        let executable_mapping=mappings.iter().find(|m| m.executable && m.start<=ret && ret<m.end).cloned();
        frames.push(Frame {address:fp,return_address:ret,executable_mapping});
        if next!=0 && next<=fp { break Stop::NonIncreasing; }
        fp=next;
    };
    Ok(Trace {frames,stop})
}

#[repr(C)]
struct Iovec { base: *mut c_void, length: usize }
unsafe extern "C" {
    fn process_vm_readv(pid: i32, local: *const Iovec, local_count: usize,
        remote: *const Iovec, remote_count: usize, flags: usize) -> isize;
}

fn read_frame(pid: i32, address: u64, bytes: &mut [u8;16]) -> io::Result<usize> {
    let address=usize::try_from(address).map_err(|_| io::Error::from(io::ErrorKind::InvalidInput))?;
    let local=Iovec {base:bytes.as_mut_ptr().cast(),length:bytes.len()};
    let remote=Iovec {base:address as *mut c_void,length:bytes.len()};
    // SAFETY: kernel copies at most16 bytes into the live local array. Remote
    // memory is only read, and this function never dereferences a remote pointer.
    let result=unsafe {process_vm_readv(pid,&local,1,&remote,1,0)};
    if result<0 {Err(io::Error::last_os_error())} else {Ok(result as usize)}
}

/// Read up to four conventional 16-byte FP records. This is not DWARF unwinding
/// or a complete backtrace; optimized code and signal frames can break the chain.
/// Caller must stop/revalidate the exact process and keep an outer watchdog.
pub fn capture(pid: i32, sp: u64, fp: u64) -> Result<Trace,String> {
    if pid<=1 || pid as u32==std::process::id() {return Err("invalid-target-pid".into());}
    let started=Instant::now();
    let mut text=String::new();
    File::open(format!("/proc/{pid}/maps")).map_err(|e| format!("maps-open:{e}"))?
        .take((MAX_MAPS+1) as u64).read_to_string(&mut text).map_err(|e| format!("maps-read:{e}"))?;
    let mappings=maps(&text)?;
    walk(&mappings,sp,fp,|address,bytes| read_frame(pid,address,bytes),|| started.elapsed()>=BUDGET)
}

#[cfg(test)]
#[path="app-close-ptrace.rs"]
mod ptrace;

#[cfg(test)]
mod tests {
    use super::*;
    fn mapping() -> Vec<Mapping> {maps("1000-20000 rw-p 00000000 00:00 0 [stack]\n40000-41000 r-xp 00001000 00:00 1 /test.so\n").unwrap()}
    fn record(bytes:&mut [u8;16],next:u64,ret:u64) {bytes[..8].copy_from_slice(&next.to_ne_bytes());bytes[8..].copy_from_slice(&ret.to_ne_bytes());}
    #[test] fn bounded_chain_retains_raw_pac_and_mapping() {
        let t=walk(&mapping(),0x1000,0x1010,|fp,b| {record(b,if fp==0x1010 {0x1020}else{0},if fp==0x1010{0x40008}else{0xff0040008});Ok(16)},||false).unwrap();
        assert_eq!(t.stop,Stop::End);assert_eq!(t.frames.len(),2);
        assert_eq!(t.frames[0].executable_mapping.as_ref().unwrap().offset,0x1000);
        assert_eq!(t.frames[1].return_address,0xff0040008);assert!(t.frames[1].executable_mapping.is_none());
    }
    #[test] fn invalid_bounds_never_read() {
        for fp in [0x1001,0xff0,0x1fff8,u64::MAX-15,0x11010] {
            let t=walk(&mapping(),0x1000,fp,|_,_|panic!("invalid read"),||false).unwrap();
            assert_eq!(t.stop,Stop::InvalidFrame);assert!(t.frames.is_empty());
        }
        assert_eq!(walk(&mapping(),0x1000,0,|_,_|panic!(),||false).unwrap().stop,Stop::End);
    }
    #[test] fn partial_error_and_cycle_preserve_only_completed_frames() {
        for failure in [0,1,2] {
            let t=walk(&mapping(),0x1000,0x1010,|fp,b| {
                if fp==0x1010 {record(b,0x1020,0x40008);Ok(16)}
                else if failure==0 {Ok(8)} else if failure==1 {Err(io::ErrorKind::NotFound.into())}
                else {record(b,0x1010,0x40010);Ok(16)}
            },||false).unwrap();
            assert_eq!(t.stop,match failure {0=>Stop::ShortRead,1=>Stop::ReadFailed,_=>Stop::NonIncreasing});
            assert_eq!(t.frames.len(),if failure==2{2}else{1});
        }
    }
    #[test] fn deadline_before_and_after_read_and_frame_limit() {
        let t=walk(&mapping(),0x1000,0x1010,|_,_|panic!(),||true).unwrap();assert_eq!(t.stop,Stop::Deadline);
        let mut checks=0;
        let t=walk(&mapping(),0x1000,0x1010,|_,b| {record(b,0,0x40008);Ok(16)},|| {checks+=1;checks>1}).unwrap();
        assert_eq!(t.stop,Stop::Deadline);assert!(t.frames.is_empty());
        let mut reads=0;
        let t=walk(&mapping(),0x1000,0x1010,|fp,b| {reads+=1;record(b,fp+16,0x40008);Ok(16)},||false).unwrap();
        assert_eq!(t.stop,Stop::Limit);assert_eq!(reads,4);
    }
    #[test] fn maps_limits_permissions_and_ambiguity_refuse() {
        assert!(maps(&"x".repeat(MAX_MAPS+1)).is_err());
        assert!(maps("2000-1000 rw-p 0 00:00 0 [stack]").is_err());
        let mut m=mapping();m[0].writable=false;assert!(stack_map(&m,0x1000).is_err());
        m=mapping();m.push(m[0].clone());assert!(stack_map(&m,0x1000).is_err());
        assert!(stack_map(&mapping(),0x20000).is_err());
    }
    #[test] fn actual_owned_child_stack_and_partial_syscall() {
        use std::{io::{BufRead,BufReader},process::{Command,Stdio}};
        struct Owned(std::process::Child);
        impl Drop for Owned {fn drop(&mut self) {if matches!(self.0.try_wait(),Ok(None)) {let _=self.0.kill();let _=self.0.wait();}}}
        let mut child=Owned(Command::new(std::env::var("ROG5_STACK_FIXTURE").unwrap()).stdout(Stdio::piped()).spawn().unwrap());
        let mut line=String::new();BufReader::new(child.0.stdout.take().unwrap()).read_line(&mut line).unwrap();
        let values:Vec<u64>=line.split_whitespace().map(|s|u64::from_str_radix(s,16).unwrap()).collect();assert_eq!(values.len(),2);
        let pid=child.0.id() as i32;let fp=values[0];let boundary=values[1];
        let (_,trace)=ptrace::capture_inspect(pid,||Ok(()),move|shot| capture(pid,shot.sp,fp)).unwrap();
        assert_eq!(trace.stop,Stop::End);assert_eq!(trace.frames.len(),2);
        assert_eq!(trace.frames[0].return_address,0x12345678);assert_eq!(trace.frames[1].return_address,0x87654321);
        let (_,partial)=ptrace::capture_inspect(pid,||Ok(()),move|_| {
            let mut bytes=[0u8;16];read_frame(pid,boundary,&mut bytes).map_err(|e|e.to_string())
        }).unwrap();assert_eq!(partial,8);
        let status=std::fs::read_to_string(format!("/proc/{pid}/status")).unwrap();assert!(status.contains("TracerPid:\t0"));
        assert!(child.0.try_wait().unwrap().is_none());
    }
}
