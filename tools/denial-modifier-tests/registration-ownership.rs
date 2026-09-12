// The runner inserts the exact startup ownership tail, engine/host shutdown
// methods and Drop implementations. Engine callbacks and configuration values
// below are boundary adapters; no engine library or worker is launched.
#![allow(dead_code, unused_variables, non_snake_case, unused_unsafe)]
use std::{ffi::c_void, mem, ptr, sync::{Arc, Mutex, atomic::{AtomicUsize, Ordering}}};
static EVENTS: Mutex<Vec<&'static str>> = Mutex::new(Vec::new());
static FAIL_REGISTRATION: AtomicUsize = AtomicUsize::new(0);
static FAIL_SHUTDOWN: AtomicUsize = AtomicUsize::new(0);
fn event(name: &'static str) { EVENTS.lock().unwrap().push(name); }
#[derive(Debug, PartialEq, Eq)] enum EngineError { RegistrationOne, RegistrationTwo, Shutdown }
type HostError = EngineError;
struct Track(&'static str);
impl Drop for Track { fn drop(&mut self) { event(self.0); } }
struct CallbackState { engine_handle: AtomicUsize }
impl Drop for CallbackState { fn drop(&mut self) { event("callback-drop"); } }
struct EngineLibrary { table: ProcTable }
struct ProcTable { Shutdown: Option<unsafe fn(*mut c_void) -> i32> }
unsafe fn shutdown_boundary(_: *mut c_void) -> i32 {
    event("shutdown"); if FAIL_SHUTDOWN.load(Ordering::Relaxed) != 0 { 1 } else { 0 }
}
fn check_result(_: &str, result: i32) -> Result<(), EngineError> {
    if result == 0 { Ok(()) } else { Err(EngineError::Shutdown) }
}
impl EngineLibrary {
    unsafe fn run(self: &Arc<Self>, _: &Track, _: &Track, _: *mut c_void, aot: Option<Track>) -> Result<RunningEngine, EngineError> {
        event("run"); Ok(RunningEngine { handle: ptr::without_provenance_mut(1), library: self.clone(), aot_data: aot })
    }
}
struct RunningEngine { handle: *mut c_void, library: Arc<EngineLibrary>, aot_data: Option<Track> }
impl RunningEngine {
    fn raw_handle(&self) -> *mut c_void { self.handle }
    unsafe fn set_external_texture_gl_state_callback(&self, _: Option<fn()>, _: *mut c_void) -> Result<(), EngineError> {
        event("register-one");
        if FAIL_REGISTRATION.load(Ordering::Relaxed) == 1 { Err(EngineError::RegistrationOne) } else { Ok(()) }
    }
    unsafe fn set_render_work_callbacks(&self, _: fn(), _: fn(), _: fn(), _: *mut c_void) -> Result<(), EngineError> {
        event("register-two");
        if FAIL_REGISTRATION.load(Ordering::Relaxed) == 2 { Err(EngineError::RegistrationTwo) } else { Ok(()) }
    }
// @ENGINE_SHUTDOWN@
}
impl Drop for RunningEngine {
// @ENGINE_DROP@
}
struct EngineHostState {
    engine: Option<RunningEngine>, _library: Arc<EngineLibrary>, _callback_state: Box<CallbackState>,
    _renderer: Track, _platform_runner: Track, _custom_runners: Track, _compositor: Track,
    _project_args: Track, _assets: Track, _icu_data: Track, _argv: Track, _argv_pointers: Track,
}
struct EngineHost { state: Option<Box<EngineHostState>> }
fn external_texture_callback_may_modify_gl() {}
fn begin_render_work() {}
fn end_render_work() {}
fn render_work_done() {}
fn publish_engine_handle(callback: &CallbackState, handle: usize, _: *mut c_void) {
    event("publish"); callback.engine_handle.store(handle, Ordering::Release);
}
impl EngineHost {
    fn start_fixture() -> Result<Self, HostError> {
        let library = Arc::new(EngineLibrary { table: ProcTable { Shutdown: Some(shutdown_boundary) } });
        let mut callback_state = Box::new(CallbackState { engine_handle: AtomicUsize::new(0) });
        let state = (&mut *callback_state as *mut CallbackState).cast::<c_void>();
        let renderer=Track("renderer-drop"); let platform_runner=Track("runner-drop");
        let custom_runners=Track("custom-runners-drop"); let compositor=Track("compositor-drop");
        let project_args=Track("args-drop"); let assets=Track("assets-drop");
        let icu_data=Track("icu-drop"); let argv=Track("argv-drop");
        let argv_pointers=Track("argv-pointers-drop"); let aot_data=Some(Track("aot-drop"));
// @STARTUP_TAIL@
// @ENGINE_ACCESSOR@
// @HOST_SHUTDOWN@
}
impl Drop for EngineHost {
// @HOST_DROP@
}
// @RELEASE_OR_LEAK@

fn registration_failure(registration: usize, shutdown_fails: bool) {
    FAIL_REGISTRATION.store(registration, Ordering::Relaxed);
    FAIL_SHUTDOWN.store(usize::from(shutdown_fails), Ordering::Relaxed);
    let result = EngineHost::start_fixture();
    assert!(matches!((&result, registration), (Err(EngineError::RegistrationOne),1) | (Err(EngineError::RegistrationTwo),2)),
            "original registration error must survive failed cleanup");
    let events=EVENTS.lock().unwrap();
    assert_eq!(events.iter().filter(|e| **e == "shutdown").count(), 1);
    assert!(!events.contains(&"publish"));
    if shutdown_fails {
        assert!(!events.iter().any(|e| e.ends_with("-drop")), "failed shutdown freed engine-reachable graph: {events:?}");
    } else {
        assert_eq!(events.iter().filter(|e| **e == "callback-drop").count(),1);
        assert_eq!(events.iter().filter(|e| e.ends_with("-drop")).count(),11);
        assert!(events.iter().position(|e| *e == "shutdown").unwrap() < events.iter().position(|e| *e == "callback-drop").unwrap());
    }
}
#[test] fn first_registration_failure_with_successful_shutdown_releases_graph() { registration_failure(1, false); }
#[test] fn second_registration_failure_with_successful_shutdown_releases_graph() { registration_failure(2, false); }
#[test] fn first_registration_failure_with_failed_shutdown_retains_graph() { registration_failure(1, true); }
#[test] fn second_registration_failure_with_failed_shutdown_retains_graph() { registration_failure(2, true); }
#[test] fn normal_registration_publishes_after_both_callbacks_and_drops_once() {
    let host=EngineHost::start_fixture().unwrap();
    assert_eq!(*EVENTS.lock().unwrap(),vec!["run","register-one","register-two","publish"]);
    drop(host);
    let events=EVENTS.lock().unwrap();
    assert_eq!(events.iter().filter(|e| **e == "shutdown").count(),1);
    assert_eq!(events.iter().filter(|e| **e == "callback-drop").count(),1);
}
#[test] fn successful_registration_then_failed_shutdown_retains_graph() {
    let host=EngineHost::start_fixture().unwrap();
    FAIL_SHUTDOWN.store(1,Ordering::Relaxed); drop(host);
    let events=EVENTS.lock().unwrap();
    assert_eq!(events.iter().filter(|e| **e == "shutdown").count(),1);
    assert!(!events.iter().any(|e| e.ends_with("-drop")));
}
