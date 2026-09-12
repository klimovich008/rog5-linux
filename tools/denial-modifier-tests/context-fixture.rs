// Actual ContextBinding methods are extracted by the runner. Only EGL effects
// and tracing output are adapters; the separate virtual probe tests real EGL.
#![allow(dead_code, unused_variables)]
use std::cell::Cell;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::thread::{self, ThreadId};
static AUDIT: AtomicBool = AtomicBool::new(true);
static LOGS: AtomicUsize = AtomicUsize::new(0);
static QUERIES: AtomicUsize = AtomicUsize::new(0);
macro_rules! error { ($($token:tt)*) => {} }
macro_rules! info { ($($token:tt)*) => {{ LOGS.fetch_add(1, Ordering::Relaxed); }} }
fn render_audit_enabled() -> bool { AUDIT.load(Ordering::Relaxed) }
mod egl_ffi { pub mod egl {
    #[allow(non_snake_case)]
    pub unsafe fn GetCurrentContext() -> *const () {
        super::super::QUERIES.fetch_add(1, super::super::Ordering::Relaxed);
        std::ptr::null()
    }
}}
#[derive(Default)]
struct Egl {
    fail_bind: bool, fail_unbind: bool, current: Cell<bool>,
    binds: Cell<usize>, unbinds: Cell<usize>,
}
impl Egl {
    unsafe fn make_current(&self) -> Result<(), &'static str> {
        self.binds.set(self.binds.get()+1);
        if self.fail_bind { return Err("bind fault"); }
        self.current.set(true); Ok(())
    }
    fn unbind(&self) -> Result<(), &'static str> {
        self.unbinds.set(self.unbinds.get()+1);
        if self.fail_unbind { return Err("unbind fault"); }
        self.current.set(false); Ok(())
    }
}
#[derive(Default)]
struct ContextBinding { context: Egl, owner: Option<ThreadId> }
impl ContextBinding {
// @METHODS@
}
#[test]
fn bind_and_release_update_owner_only_after_success() {
    let mut binding = ContextBinding::default();
    assert!(binding.make_current());
    assert_eq!(binding.owner, Some(thread::current().id()));
    assert!(binding.clear_current());
    assert_eq!(binding.owner, None);
    assert_eq!((binding.context.binds.get(), binding.context.unbinds.get()), (1,1));
}
#[test]
fn wrong_thread_never_calls_egl() {
    let other = thread::spawn(|| thread::current().id()).join().unwrap();
    let mut binding = ContextBinding { owner: Some(other), ..Default::default() };
    assert!(!binding.make_current()); assert!(!binding.clear_current());
    assert_eq!(binding.owner, Some(other));
    assert_eq!((binding.context.binds.get(), binding.context.unbinds.get()), (0,0));
}
#[test]
fn bind_failure_does_not_create_owner() {
    let mut binding = ContextBinding::default(); binding.context.fail_bind=true;
    assert!(!binding.make_current()); assert_eq!(binding.owner,None);
}
#[test]
fn unbind_failure_preserves_owner() {
    let mut binding = ContextBinding::default(); assert!(binding.make_current());
    binding.context.fail_unbind=true;
    assert!(!binding.clear_current());
    assert_eq!(binding.owner,Some(thread::current().id()));
    assert!(binding.context.current.get());
}
#[cfg(egl_trace)]
#[test]
fn trace_bounds() {
    // Run this test alone in a fresh process so the function-local static is new.
    let binding = ContextBinding::default();
    AUDIT.store(false,Ordering::Relaxed);
    binding.trace_binding("disabled",true);
    assert_eq!(QUERIES.load(Ordering::Relaxed),0);
    AUDIT.store(true,Ordering::Relaxed);
    for _ in 0..2100 { binding.trace_binding("regular",false); }
    assert_eq!(LOGS.load(Ordering::Relaxed),2048);
    assert_eq!(QUERIES.load(Ordering::Relaxed),2048);
    binding.trace_binding("cleanup-enter",true);
    binding.trace_binding("cleanup-bind-failed",true);
    assert_eq!(LOGS.load(Ordering::Relaxed),2050);
    assert_eq!(binding.owner,None);
    assert_eq!((binding.context.binds.get(),binding.context.unbinds.get()),(0,0));
}
