// Production callback and ContextBinding methods with thread-local EGL effects.
#![allow(dead_code, unused_variables)]
use std::cell::Cell;
use std::sync::{Mutex, MutexGuard};
use std::thread::{self, ThreadId};
macro_rules! error { ($($token:tt)*) => {} }
thread_local! { static CURRENT: Cell<usize> = const { Cell::new(0) }; }
fn lock<T>(value: &Mutex<T>) -> MutexGuard<'_, T> { value.lock().unwrap() }
struct Egl { id: usize, fail: bool, calls: Cell<usize> }
impl Egl {
    fn is_current(&self) -> bool { CURRENT.with(|c| c.get() == self.id) }
    fn unbind(&self) -> Result<(), ()> {
        self.calls.set(self.calls.get() + 1);
        if self.fail { return Err(()); }
        // Smithay leaves an unrelated current context alone.
        if self.is_current() { CURRENT.with(|c| c.set(0)); }
        Ok(())
    }
}
struct ContextBinding { context: Egl, owner: Option<ThreadId> }
impl ContextBinding {
    fn trace_binding(&self, _: &'static str, _: bool) {}
    // @BINDING@
}
struct FlutterGlHandler {
    render_context: Mutex<ContextBinding>,
    resource_context: Mutex<ContextBinding>,
}
impl FlutterGlHandler {
    // @CALLBACK@
}
fn binding(id: usize, owner: Option<ThreadId>) -> Mutex<ContextBinding> {
    Mutex::new(ContextBinding { context: Egl {id, fail: false, calls: Cell::new(0)}, owner })
}
fn main() {
    let mode = std::env::args().nth(1).unwrap();
    let other = thread::spawn(|| thread::current().id()).join().unwrap();
    let here = thread::current().id();
    let handler = FlutterGlHandler {
        render_context: binding(1, Some(other)),
        resource_context: binding(2, Some(here)),
    };
    CURRENT.with(|c| c.set(2));
    if mode == "resource-failure" { lock(&handler.resource_context).context.fail = true; }
    if mode == "wrong-owner" { lock(&handler.resource_context).owner = Some(other); }
    if mode == "render" {
        CURRENT.with(|c| c.set(1));
        lock(&handler.render_context).owner = Some(here);
        lock(&handler.resource_context).owner = Some(other);
    }
    let result = handler.clear_current();
    let render = lock(&handler.render_context);
    let resource = lock(&handler.resource_context);
    let pass = match mode.as_str() {
        "resource" => result && CURRENT.with(|c| c.get() == 0) &&
            resource.owner.is_none() && resource.context.calls.get() == 1 &&
            render.owner == Some(other) && render.context.calls.get() == 0,
        "resource-failure" => !result && CURRENT.with(|c| c.get() == 2) &&
            resource.owner == Some(here) && resource.context.calls.get() == 1 &&
            render.context.calls.get() == 0,
        "wrong-owner" => !result && CURRENT.with(|c| c.get() == 2) &&
            resource.owner == Some(other) && resource.context.calls.get() == 0 &&
            render.context.calls.get() == 0,
        "render" => result && CURRENT.with(|c| c.get() == 0) &&
            render.owner.is_none() && render.context.calls.get() == 1 &&
            resource.owner == Some(other) && resource.context.calls.get() == 0,
        _ => false,
    };
    println!("{mode}: {}", if pass { "PASS" } else { "FAIL" });
    std::process::exit(if pass { 0 } else { 1 });
}
