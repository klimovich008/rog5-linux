// Isolated VM test fixture for actual packaged login PAM session registration.
// The fixed password is public test data and is never used for a real account.
use std::{ffi::{c_char,c_int,c_void,CStr},ptr,process::Command};
use libloading::{Library,Symbol};
#[repr(C)] struct Message { style:c_int, text:*const c_char }
#[repr(C)] struct Response { text:*mut c_char, code:c_int }
#[repr(C)] struct Conversation {
    callback:unsafe extern "C" fn(c_int,*mut *const Message,*mut *mut Response,*mut c_void)->c_int,
    data:*mut c_void,
}
unsafe extern "C" fn converse(n:c_int,msg:*mut *const Message,out:*mut *mut Response,_:*mut c_void)->c_int {
    if !(1..=16).contains(&n) || msg.is_null() || out.is_null() { return 19; }
    // SAFETY: PAM passes n message pointers and an output slot. calloc initializes
    // all response pointers; ownership transfers only after every item succeeds.
    unsafe {
        let responses=libc::calloc(n as usize,std::mem::size_of::<Response>()).cast::<Response>();
        if responses.is_null() { return 19; }
        for i in 0..n as usize {
            let m=*msg.add(i);
            let data=if m.is_null() {None} else {match (*m).style {
                1=>Some(c"rog5-logind-fixture-password"),2=>Some(c"mobile"),
                3|4=>Some(c""),_=>None,
            }};
            let p=data.map_or(ptr::null_mut(),|s|libc::strdup(s.as_ptr()));
            if p.is_null() {
                for j in 0..i { libc::free((*responses.add(j)).text.cast()); }
                libc::free(responses.cast());return 19;
            }
            (*responses.add(i)).text=p;
        }
        *out=responses;
    }
    0
}
type Step=unsafe extern "C" fn(*mut c_void,c_int)->c_int;
fn checked(code:c_int,stage:&str)->Result<(),String>{
    println!("OBSERVE PAM {stage} code={code}");
    if code==0 {Ok(())} else {Err(format!("PAM {stage} failed: {code}"))}
}
fn run()->Result<(),Box<dyn std::error::Error>> {
    if std::env::args().len()!=1 || !std::fs::read_to_string("/proc/cmdline")?.split_whitespace().filter(|s|s.starts_with("rog5.logind_fixture=")).eq(["rog5.logind_fixture=1"])
       || !std::path::Path::new("/sys/bus/virtio/devices").is_dir()
       || std::fs::read_to_string("/proc/1/comm")?.trim()!="systemd" {
        return Err("requires isolated systemd VM".into());
    }
    // SAFETY: read-only identity/tty queries; CStr used only on non-null pointer.
    unsafe {
        let tty=libc::ttyname(0);
        if libc::getuid()!=0 || libc::geteuid()!=0 || libc::tcgetsid(0)!=libc::getsid(0) || tty.is_null() || CStr::from_ptr(tty).to_bytes()!=b"/dev/tty1" {
            return Err("requires root controlling tty1 fixture".into());
        }
    }
    for key in ["XDG_SESSION_ID","XDG_SESSION_TYPE","XDG_SESSION_CLASS","XDG_SEAT","XDG_VTNR","XDG_RUNTIME_DIR","DBUS_SESSION_BUS_ADDRESS"] {
        if std::env::var_os(key).is_some() { return Err("inherited session metadata is forbidden".into()); }
    }
    // SAFETY: this is a standalone single-threaded process; deadline termination
    // is failure, not PAM cleanup proof. The VM coordinator verifies scope removal.
    unsafe {
        if libc::signal(libc::SIGALRM,libc::SIG_DFL)==libc::SIG_ERR {return Err("cannot arm fixture deadline".into());}
        // Full child190s +35s authentication/PAM cleanup; the outer shell
        // owns230s, leaving5s beyond this last-resort process alarm.
        // Startup-only and basic retain their original140s/40s alarms.
        libc::alarm(if cfg!(denial_session) { if cfg!(startup_only) { 140 } else { 225 } } else { 40 });
    }
    // SAFETY: fixed authenticated guest library, signatures from pam_appl.h.
    // Library and conversation stay live until pam_end has released the handle.
    unsafe {
        let library=Library::new("libpam.so.0")?;
        let start:Symbol<unsafe extern "C" fn(*const c_char,*const c_char,*const Conversation,*mut *mut c_void)->c_int>=library.get(b"pam_start\0")?;
        let set:Symbol<unsafe extern "C" fn(*mut c_void,c_int,*const c_void)->c_int>=library.get(b"pam_set_item\0")?;
        let auth:Symbol<Step>=library.get(b"pam_authenticate\0")?;
        let account:Symbol<Step>=library.get(b"pam_acct_mgmt\0")?;
        let cred:Symbol<Step>=library.get(b"pam_setcred\0")?;
        let open:Symbol<Step>=library.get(b"pam_open_session\0")?;
        let close:Symbol<Step>=library.get(b"pam_close_session\0")?;
        let end:Symbol<Step>=library.get(b"pam_end\0")?;
        let getenv:Symbol<unsafe extern "C" fn(*mut c_void,*const c_char)->*const c_char>=library.get(b"pam_getenv\0")?;
        let conv=Conversation{callback:converse,data:ptr::null_mut()};
        let mut handle=ptr::null_mut();
        checked(start(c"login".as_ptr(),c"mobile".as_ptr(),&conv,&mut handle),"start")?;
        let mut credential=false;let mut opened=false;
        let outcome=(||->Result<(),Box<dyn std::error::Error>> {
            checked(set(handle,3,c"tty1".as_ptr().cast()),"tty")?;
            checked(auth(handle,0),"authenticate")?;
            checked(account(handle,0),"account")?;
            checked(cred(handle,2),"establish credentials")?;credential=true;
            opened=true;checked(open(handle,0),"open session")?;
            let mut child=Command::new("/usr/bin/timeout");
            // Full session includes preparation, portals, app flow and cleanup.
            // Preserve the smaller basic and startup-only fixture limits.
            child.args(["-k","1",if cfg!(denial_session) {if cfg!(startup_only) {"120"} else {"190"}} else {"20"},"/usr/bin/setpriv","--reuid=1000","--regid=1000","--clear-groups","--bounding-set=-all","--inh-caps=-all","--ambient-caps=-all","/usr/bin/bash","/run/logind-user.sh"])
                 .env_clear().env("PATH","/usr/bin").env("HOME","/run/mobile-home")
                 .env("USER","mobile").env("LOGNAME","mobile").env("LANG","C.UTF-8");
            for key in [c"XDG_SESSION_ID",c"XDG_RUNTIME_DIR",c"XDG_SESSION_TYPE",c"XDG_SEAT",c"XDG_VTNR",c"DBUS_SESSION_BUS_ADDRESS"] {
                let value=getenv(handle,key.as_ptr());
                if !value.is_null() { child.env(key.to_str()?,CStr::from_ptr(value).to_str()?); }
            }
            let status=child.status()?;
            if !status.success(){return Err(format!("session child failed: {status}").into());}
            Ok(())
        })();
        let mut cleanup=Ok(());
        if opened { cleanup=checked(close(handle,0),"close session"); }
        if credential {
            let r=checked(cred(handle,4),"delete credentials");
            if cleanup.is_ok(){cleanup=r;}
        }
        let r=checked(end(handle,if outcome.is_ok(){0}else{4}),"end");
        let errors:Vec<String>=[outcome.err().map(|e|e.to_string()),cleanup.err(),r.err()].into_iter().flatten().collect();
        if !errors.is_empty(){return Err(errors.join("; ").into());}
    }
    unsafe { libc::alarm(0); }
    println!("PASS authenticated PAM local session and child execution");
    Ok(())
}
fn main()->std::process::ExitCode {
    match run(){Ok(())=>std::process::ExitCode::SUCCESS,Err(e)=>{
        eprintln!("FAIL local PAM fixture: {e}");std::process::ExitCode::FAILURE
    }}
}
