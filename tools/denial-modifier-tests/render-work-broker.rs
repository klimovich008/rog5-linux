// Types and boundary effects only. The runner inserts production broker,
// handler and FFI methods; this file does not implement their algorithms.
#![allow(dead_code, unused_variables)]
use std::{ffi::c_void, mem, panic::{catch_unwind, AssertUnwindSafe},
    sync::{Arc, Mutex, MutexGuard, atomic::{AtomicU64, Ordering}},
    thread::ThreadId, time::{Duration, Instant}};
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct PixelSize { width: u32, height: u32 }
impl PixelSize { fn new(width: u32, height: u32) -> Self { Self { width, height } } }
#[derive(Clone, Copy, Debug)] struct View(i64);
impl View { fn get(self) -> i64 { self.0 } }
#[derive(Clone, Copy, Debug)] struct Tick { interval: Duration, output: u64 }
#[derive(Clone, Copy, Debug)] struct OutputFrameRequest { tick: Tick, dirty_serial: u64 }
type OutputId = u64;
// @DECLARATIONS@
struct Slot {
    framebuffer: u32, state: BufferState, output_refs: usize, fence: Option<u64>,
    ready_damage: Option<u64>, rendered_at: Option<Instant>, screenshot_request_id: Option<u64>,
    ready_transaction: u64, request: Option<OutputFrameRequest>,
}
struct OutputBufferPool {
    output_id: u64, render_view_id: View, size: PixelSize,
    authorized_request: Option<AuthorizedOutputRequest>, slots: Vec<Slot>,
}
struct OutputBufferBroker { pools: Vec<OutputBufferPool>, next_screenshot: Option<(u64, u64)> }
fn render_audit_enabled() -> bool { true }
macro_rules! info { ($($tokens:tt)*) => {{}} }
// @TRACE_HELPERS@
impl OutputBufferBroker {
// @BROKER_METHODS@
}
fn size() -> PixelSize { PixelSize::new(640, 480) }
fn request(output: u64, serial: u64) -> OutputFrameRequest {
    OutputFrameRequest { tick: Tick { interval: Duration::from_millis(16), output }, dirty_serial: serial }
}
fn pool(view: i64) -> OutputBufferPool {
    OutputBufferPool { output_id: view as u64, render_view_id: View(view), size: size(),
        authorized_request: None, slots: (0..3).map(|i| Slot {
            framebuffer: 23 + i + 10 * (view as u32 - 1), state: BufferState::Free,
            output_refs: usize::from(i == 2), fence: Some(42), ready_damage: Some(1),
            rendered_at: Some(Instant::now()), screenshot_request_id: None,
            ready_transaction: 8, request: None,
        }).collect() }
}
fn broker() -> OutputBufferBroker {
    OutputBufferBroker { pools: vec![pool(1), pool(2)], next_screenshot: Some((1, 81)) }
}
fn grant(b: &mut OutputBufferBroker, work: u64, now: Instant) {
    assert_eq!(b.authorize(request(1, work), now, work), Some(1));
}
fn admitted(b: &mut OutputBufferBroker, work: u64, now: Instant) {
    grant(b, work, now);
    assert_eq!(b.admit(1, size(), work, now), Ok(true));
}
fn replacement(b: &mut OutputBufferBroker, now: Instant) {
    grant(b, 1, now);
    assert_eq!(b.expire_authorizations(now + Duration::from_millis(32)), 1);
    grant(b, 2, now + Duration::from_millis(33));
}
fn work(b: &OutputBufferBroker, index: usize) -> Option<u64> {
    b.pools[index].authorized_request.map(|a| a.work_id)
}

#[test] fn delayed_acquire_must_not_consume_a_replacement_reservation() {
    let mut b = broker(); let now = Instant::now(); replacement(&mut b, now);
    assert_eq!(b.admit(1, size(), 1, now + Duration::from_millis(34)), Ok(false));
    assert_eq!(b.acquire(1, size(), 1), Err(RenderTargetBlocked::MissingAuthorization));
    assert_eq!(work(&b, 0), Some(2));
    assert_eq!(b.admit(1, size(), 2, now + Duration::from_millis(34)), Ok(true));
    assert_eq!(b.acquire(1, size(), 1), Err(RenderTargetBlocked::MissingAuthorization));
    assert_eq!(b.acquire(1, size(), 2), Ok(23));
    assert_eq!(b.pools[0].slots[0].request.unwrap().dirty_serial, 2);
}
#[test] fn delayed_cancel_must_not_remove_a_replacement_reservation() {
    let mut b = broker(); replacement(&mut b, Instant::now());
    b.cancel_work(1); assert_eq!(work(&b, 0), Some(2));
}
#[test] fn acquire_requires_admitted_matching_nonzero_work() {
    let mut b = broker(); let now = Instant::now(); grant(&mut b, 1, now);
    for id in [0, 1, 2] { assert_eq!(b.acquire(1, size(), id), Err(RenderTargetBlocked::MissingAuthorization)); }
    assert_eq!(work(&b, 0), Some(1));
    assert_eq!(b.admit(1, size(), 1, now), Ok(true));
    for id in [0, 2] { assert_eq!(b.acquire(1, size(), id), Err(RenderTargetBlocked::MissingAuthorization)); }
    assert_eq!(b.acquire(1, size(), 1), Ok(23));
}
#[test] fn expiry_before_admission_refuses_at_exact_boundary() {
    for (millis, expected) in [(31, true), (32, false), (33, false)] {
        let mut b = broker(); let now = Instant::now(); grant(&mut b, 1, now);
        assert_eq!(b.admit(1, size(), 1, now + Duration::from_millis(millis)), Ok(expected));
        assert_eq!(work(&b, 0), expected.then_some(1));
    }
}
#[test] fn expiry_after_admission_preserves_permission_and_blocks_regrant() {
    let mut b = broker(); let now = Instant::now(); admitted(&mut b, 1, now);
    assert_eq!(b.expire_authorizations(now + Duration::from_secs(30)), 0);
    assert!(!b.target_available(1));
    assert_eq!(b.authorize(request(1, 2), now + Duration::from_secs(30), 2), None);
    assert_eq!(b.acquire(1, size(), 1), Ok(23));
}
#[test] fn unused_end_releases_only_admitted_permission() {
    let mut b = broker(); let now = Instant::now(); grant(&mut b, 1, now);
    b.end_admission(1, 1); assert_eq!(work(&b, 0), Some(1));
    assert_eq!(b.admit(1, size(), 1, now), Ok(true));
    b.end_admission(1, 1); assert_eq!(work(&b, 0), None); assert!(b.target_available(1));
    b.end_admission(1, 1); assert!(b.target_available(1));
}
#[test] fn late_old_end_preserves_replacement() {
    let mut b = broker(); let now = Instant::now(); admitted(&mut b, 1, now);
    b.end_admission(1, 1); admitted(&mut b, 2, now);
    b.end_admission(1, 1); assert_eq!(work(&b, 0), Some(2));
    assert_eq!(b.acquire(1, size(), 2), Ok(23));
}
#[test] fn completion_before_admit_is_terminal_and_idempotent() {
    let mut b = broker(); let now = Instant::now(); grant(&mut b, 1, now);
    b.cancel_work(1); b.cancel_work(1);
    assert_eq!(b.admit(1, size(), 1, now), Ok(false));
    assert_eq!(b.acquire(1, size(), 1), Err(RenderTargetBlocked::MissingAuthorization));
    assert!(b.target_available(1));
}
#[test] fn missing_view_and_wrong_size_remain_real_errors() {
    let mut b = broker(); let now = Instant::now(); admitted(&mut b, 1, now);
    for (view, dimensions) in [(3, size()), (1, PixelSize::new(1, 1))] {
        assert_eq!(b.admit(view, dimensions, 1, now), Err(RenderTargetBlocked::MissingPool));
        assert_eq!(b.acquire(view, dimensions, 1), Err(RenderTargetBlocked::MissingPool));
    }
    assert_eq!(work(&b, 0), Some(1));
}
#[test] fn duplicate_admission_is_a_real_busy_error() {
    let mut b = broker(); let now = Instant::now(); admitted(&mut b, 1, now);
    assert_eq!(b.admit(1, size(), 1, now), Err(RenderTargetBlocked::NoFreeSlot));
    assert_eq!(b.acquire(1, size(), 1), Ok(23));
}
#[test] fn ready_and_busy_slots_refuse_before_allocation() {
    for (state, expected) in [(BufferState::Ready, RenderTargetBlocked::ReadyHandoff),
                             (BufferState::Rendering, RenderTargetBlocked::NoFreeSlot),
                             (BufferState::Pending, RenderTargetBlocked::NoFreeSlot)] {
        let mut b = broker(); let now = Instant::now(); grant(&mut b, 1, now);
        b.pools[0].slots[0].state = state;
        assert_eq!(b.admit(1, size(), 1, now), Err(expected));
        assert!(!b.pools[0].authorized_request.unwrap().admitted);
        assert_eq!(work(&b, 0), Some(1));
    }
}
#[test] fn fully_referenced_pool_cannot_admit() {
    let mut b = broker(); let now = Instant::now(); grant(&mut b, 1, now);
    for slot in &mut b.pools[0].slots { slot.output_refs = 1; }
    assert_eq!(b.admit(1, size(), 1, now), Err(RenderTargetBlocked::NoFreeSlot));
}
#[test] fn zero_work_and_zero_dirty_serial_never_grant() {
    let mut b = broker(); let now = Instant::now();
    assert_eq!(b.authorize(request(1, 1), now, 0), None);
    assert_eq!(b.authorize(request(1, 0), now, 1), None);
    grant(&mut b, 1, now);
    assert_eq!(b.admit(1, size(), 0, now), Ok(false));
    b.cancel_work(0); b.end_admission(1, 0); assert_eq!(work(&b, 0), Some(1));
}
#[test] fn counter_exhaustion_never_wraps_or_reissues_an_id() {
    let counter = AtomicU64::new(u64::MAX - 1);
    assert_eq!(OutputBufferBroker::next_work_id(&counter), Some(u64::MAX));
    for _ in 0..4 { assert_eq!(OutputBufferBroker::next_work_id(&counter), None); }
    assert_eq!(counter.load(Ordering::Relaxed), u64::MAX);
}
#[test] fn counter_is_unique_under_concurrent_submission() {
    let counter = Arc::new(AtomicU64::new(0)); let mut threads = vec![];
    for _ in 0..4 { let counter = counter.clone(); threads.push(std::thread::spawn(move || {
        (0..256).map(|_| OutputBufferBroker::next_work_id(&counter).unwrap()).collect::<Vec<_>>()
    })); }
    let mut ids = threads.into_iter().flat_map(|t| t.join().unwrap()).collect::<Vec<_>>(); ids.sort_unstable();
    assert_eq!(ids, (1..=1024).collect::<Vec<_>>());
}
#[test] fn view_scoped_end_does_not_cancel_other_output_in_batch() {
    let mut b = broker(); let now = Instant::now(); admitted(&mut b, 1, now);
    assert_eq!(b.authorize(request(2, 1), now, 1), Some(2));
    assert_eq!(b.admit(2, size(), 1, now), Ok(true));
    b.end_admission(1, 1); assert_eq!(work(&b, 0), None); assert_eq!(work(&b, 1), Some(1));
    assert_eq!(b.acquire(2, size(), 1), Ok(33));
}
#[test] fn completion_cancels_all_unused_outputs_of_exact_batch() {
    let mut b = broker(); let now = Instant::now(); grant(&mut b, 1, now);
    assert_eq!(b.authorize(request(2, 1), now, 1), Some(2));
    b.cancel_work(1); assert!(b.target_available(1)); assert!(b.target_available(2));
}
#[test] fn done_cannot_free_consumed_rendering_slot() {
    let mut b = broker(); let now = Instant::now(); admitted(&mut b, 1, now);
    assert_eq!(b.acquire(1, size(), 1), Ok(23));
    b.end_admission(1, 1); b.cancel_work(1); b.cancel_work(1);
    assert_eq!(b.pools[0].slots[0].state, BufferState::Rendering);
    assert!(!b.target_available(1));
    assert_eq!(b.authorize(request(1, 2), now, 2), None);
}
#[test] fn current_acquire_consumes_once_and_preserves_handoff_fields() {
    let mut b = broker(); admitted(&mut b, 1, Instant::now());
    assert_eq!(b.acquire(1, size(), 1), Ok(23));
    assert_eq!(b.acquire(1, size(), 1), Err(RenderTargetBlocked::MissingAuthorization));
    let slot = &b.pools[0].slots[0];
    assert_eq!(slot.request.unwrap().dirty_serial, 1);
    assert_eq!(slot.screenshot_request_id, Some(81)); assert_eq!(slot.ready_transaction, 0);
    assert!(slot.fence.is_none()); assert!(slot.ready_damage.is_none()); assert!(slot.rendered_at.is_none());
}

fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> { mutex.lock().unwrap() }
#[derive(Default)] struct Audit { errors: Vec<RenderTargetBlocked> }
impl Audit { fn record_target_blocked(&mut self, error: RenderTargetBlocked) { self.errors.push(error); } }
trait OpenGlHandler: Send + Sync {
    fn begin_render_work(&self, view: i64, work: u64, width: u32, height: u32) -> i32;
    fn end_render_work(&self, view: i64, work: u64);
    fn render_work_done(&self, work: u64);
    fn create_backing_store(&self, _: BackingStoreRequest) -> Option<CompositorBackingStore> { None }
}
struct FlutterGlHandler {
    broker: Mutex<OutputBufferBroker>, active_render_work: Mutex<Option<(i64, u64, ThreadId)>>,
    render_audit: Option<Mutex<Audit>>, gl: Gl, gpu_timing: Option<Mutex<GpuTiming>>,
}
impl FlutterGlHandler {
// @CANCEL_METHOD@
}
impl OpenGlHandler for FlutterGlHandler {
// @HANDLER_METHODS@
}
fn handler() -> FlutterGlHandler {
    let mut b = broker();
    // Wide interval avoids wall-clock dependence in callback/thread fixtures;
    // broker deadline cases above use exact virtual Instant arithmetic.
    let mut req = request(1, 1); req.tick.interval = Duration::from_secs(60);
    assert_eq!(b.authorize(req, Instant::now(), 1), Some(1));
    FlutterGlHandler { broker: Mutex::new(b), active_render_work: Mutex::new(None), render_audit: Some(Mutex::new(Audit::default())), gl: Gl { bind_framebuffer, viewport }, gpu_timing: None }
}
#[test] fn handler_begin_end_are_bound_to_raster_thread_view_and_work() {
    let h = Arc::new(handler()); assert_eq!(h.begin_render_work(1, 1, 640, 480), 1);
    assert_eq!(h.begin_render_work(1, 1, 640, 480), -1);
    let other = h.clone(); std::thread::spawn(move || other.end_render_work(1, 1)).join().unwrap();
    h.end_render_work(2, 1); h.end_render_work(1, 2);
    assert!(lock(&h.active_render_work).is_some()); assert_eq!(work(&lock(&h.broker), 0), Some(1));
    h.end_render_work(1, 1); assert!(lock(&h.active_render_work).is_none());
    assert!(lock(&h.broker).target_available(1));
}
#[test] fn handler_stale_and_real_failure_have_distinct_outcomes() {
    let h = handler(); assert_eq!(h.begin_render_work(1, 2, 640, 480), 0);
    assert_eq!(h.begin_render_work(1, 1, 1, 1), -1);
    assert_eq!(lock(h.render_audit.as_ref().unwrap()).errors, vec![RenderTargetBlocked::MissingPool]);
    assert!(lock(&h.active_render_work).is_none());
}
struct CallbackState { handler: Box<dyn OpenGlHandler> }
// @FFI_METHODS@
struct PanicHandler;
impl OpenGlHandler for PanicHandler {
    fn begin_render_work(&self, _: i64, _: u64, _: u32, _: u32) -> i32 { panic!("injected begin panic") }
    fn end_render_work(&self, _: i64, _: u64) { panic!("injected end panic") }
    fn render_work_done(&self, _: u64) { panic!("injected done panic") }
}
#[test] fn ffi_null_userdata_is_refused_without_dereference() {
    unsafe { assert_eq!(begin_render_work(std::ptr::null_mut(), 1, 1, 640, 480), -1);
        end_render_work(std::ptr::null_mut(), 1, 1); render_work_done(std::ptr::null_mut(), 1); }
}
#[test] fn ffi_panic_is_contained_for_each_reservation_callback() {
    let mut state = CallbackState { handler: Box::new(PanicHandler) };
    let ptr = (&mut state as *mut CallbackState).cast();
    unsafe { assert_eq!(begin_render_work(ptr, 1, 1, 640, 480), -1);
        end_render_work(ptr, 1, 1); render_work_done(ptr, 1); }
    // Actual valid handler still serves another callback after caught panics.
    let mut valid = CallbackState { handler: Box::new(handler()) };
    let ptr = (&mut valid as *mut CallbackState).cast();
    unsafe { assert_eq!(begin_render_work(ptr, 1, 1, 640, 480), 1); end_render_work(ptr, 1, 1); }
}

// GL and timing boundary effects are counters only; the complete production
// create_backing_store method above decides whether these may be reached.
struct BackingStoreRequest { view_id: i64, width: usize, height: usize }
#[derive(Debug, PartialEq, Eq)]
struct CompositorBackingStore { framebuffer: u32, format: u32, user_data: usize }
struct Gl { bind_framebuffer: unsafe fn(u32, u32), viewport: unsafe fn(i32, i32, i32, i32) }
mod gl { pub const FRAMEBUFFER: u32 = 0x8d40; pub const RGBA8: u32 = 0x8058; }
static GL_CALLS: AtomicU64 = AtomicU64::new(0);
unsafe fn bind_framebuffer(target: u32, framebuffer: u32) {
    assert_eq!(target, gl::FRAMEBUFFER); assert_ne!(framebuffer, 0);
    GL_CALLS.fetch_add(1, Ordering::Relaxed);
}
unsafe fn viewport(x: i32, y: i32, width: i32, height: i32) {
    assert_eq!((x, y, width, height), (0, 0, 640, 480));
    GL_CALLS.fetch_add(1, Ordering::Relaxed);
}
struct GpuTiming;
impl GpuTiming { fn begin(&mut self, _: u32) {} }
struct RenderAuditCallbackTimer;
enum RenderAuditStage { BackingStore }
impl RenderAuditCallbackTimer { fn new(_: Option<&Mutex<Audit>>, _: RenderAuditStage) -> Self { Self } }
fn backing_request(view_id: i64) -> BackingStoreRequest { BackingStoreRequest { view_id, width: 640, height: 480 } }
#[test] fn actual_backing_store_callback_requires_active_thread_and_view() {
    let h = Arc::new(handler());
    assert_eq!(h.create_backing_store(backing_request(1)), None);
    assert_eq!(h.begin_render_work(1, 1, 640, 480), 1);
    let other = h.clone();
    assert_eq!(std::thread::spawn(move || other.create_backing_store(backing_request(1))).join().unwrap(), None);
    assert_eq!(h.create_backing_store(backing_request(2)), None);
    assert_eq!(GL_CALLS.load(Ordering::Relaxed), 0);
    assert_eq!(work(&lock(&h.broker), 0), Some(1));
    assert_eq!(h.create_backing_store(backing_request(1)), Some(CompositorBackingStore {
        framebuffer: 23, format: gl::RGBA8, user_data: 23,
    }));
    assert_eq!(GL_CALLS.load(Ordering::Relaxed), 2);
    assert_eq!(h.create_backing_store(backing_request(1)), None);
    assert_eq!(GL_CALLS.load(Ordering::Relaxed), 2);
    h.end_render_work(1, 1); h.render_work_done(1);
    assert_eq!(lock(&h.broker).pools[0].slots[0].state, BufferState::Rendering);
}
#[test] fn actual_backing_store_size_failure_is_preserved_without_gl_calls() {
    let h = handler(); assert_eq!(h.begin_render_work(1, 1, 640, 480), 1);
    assert_eq!(h.create_backing_store(BackingStoreRequest { view_id: 1, width: 1, height: 1 }), None);
    assert_eq!(GL_CALLS.load(Ordering::Relaxed), 0);
    assert_eq!(lock(h.render_audit.as_ref().unwrap()).errors, vec![RenderTargetBlocked::MissingPool]);
    assert_eq!(work(&lock(&h.broker), 0), Some(1));
    h.end_render_work(1, 1); assert!(lock(&h.broker).target_available(1));
}
#[test] fn completion_during_admitted_span_cannot_revoke_active_allocation() {
    let mut b = broker(); admitted(&mut b, 1, Instant::now());
    // A submit-error cleanup or terminal callback may race on another thread.
    // Admission owns this grant through acquisition/end, independently of TTL.
    b.cancel_work(1);
    assert_eq!(work(&b, 0), Some(1), "completion revoked admitted allocation");
    assert!(!b.target_available(1));
    assert_eq!(b.acquire(1, size(), 1), Ok(23));
    b.end_admission(1, 1); b.cancel_work(1);
    assert_eq!(b.pools[0].slots[0].state, BufferState::Rendering);
}
#[test] fn completion_during_unused_admission_still_releases_on_end() {
    let mut b = broker(); admitted(&mut b, 1, Instant::now());
    b.cancel_work(1); assert_eq!(work(&b, 0), Some(1));
    b.end_admission(1, 1); assert!(b.target_available(1));
}
