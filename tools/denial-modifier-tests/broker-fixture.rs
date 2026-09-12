// Data adapters for actual extracted broker methods; no engine, GBM or KMS I/O.
#![allow(dead_code)]
use std::time::{Duration,Instant};
#[derive(Clone,Copy,Debug,PartialEq,Eq)] struct PixelSize { width:u32,height:u32 }
#[derive(Clone,Copy)] struct View(i64);
impl View {fn get(self)->i64 {self.0}}
#[derive(Clone,Copy)] struct Tick {interval:Duration,output:u64}
#[derive(Clone,Copy)] struct Request {tick:Tick,dirty_serial:u64}
#[derive(Clone,Copy)] struct Authorization {request:Request,authorized_at:Instant}
struct Slot {
 framebuffer:u32,state:BufferState,output_refs:usize,fence:Option<u64>,
 ready_damage:Option<u64>,rendered_at:Option<Instant>,screenshot_request_id:Option<u64>,
 ready_transaction:u64,request:Option<Request>,
}
struct Pool {output_id:u64,render_view_id:View,size:PixelSize,authorized_request:Option<Authorization>,slots:Vec<Slot>}
struct OutputBufferBroker {pools:Vec<Pool>,next_screenshot:Option<(u64,u64)>}
type OutputBufferPool = Pool;
type OutputBufferSlot = Slot;
type AuthorizedOutputRequest = Authorization;
type OutputFrameRequest = Request;
type OutputId = u64;
fn render_audit_enabled()->bool {true}
macro_rules! info { ($($tokens:tt)*) => {{}} }
// @TRACE_HELPERS@
// @ENUMS@
impl OutputBufferBroker {
// @METHODS@
}
fn broker()->OutputBufferBroker {
 OutputBufferBroker {pools:vec![Pool {output_id:1,render_view_id:View(1),size:PixelSize{width:640,height:480},
 authorized_request:Some(Authorization {request:Request{tick:Tick{interval:Duration::from_millis(16),output:1},dirty_serial:9},authorized_at:Instant::now()}),
 slots:vec![Slot {framebuffer:23,state:BufferState::Free,output_refs:0,fence:Some(42),ready_damage:Some(1),rendered_at:Some(Instant::now()),screenshot_request_id:None,ready_transaction:8,request:None}]}],next_screenshot:Some((1,81))}
}
fn size()->PixelSize {PixelSize{width:640,height:480}}
fn refusal(b:&mut OutputBufferBroker,view:i64,s:PixelSize)->String {format!("{:?}",b.acquire(view,s).unwrap_err())}
#[test] fn missing_view_and_size_have_a_distinct_reason() {
 let mut b=broker();assert_eq!(refusal(&mut b,2,size()),"MissingPool");
 assert_eq!(refusal(&mut b,1,PixelSize{width:1,height:1}),"MissingPool");
 assert!(b.pools[0].authorized_request.is_some());assert_eq!(b.pools[0].slots[0].state,BufferState::Free);
}
#[test] fn absent_authorization_has_a_distinct_reason() {
 let mut b=broker();b.pools[0].authorized_request=None;
 assert_eq!(refusal(&mut b,1,size()),"MissingAuthorization");assert_eq!(b.pools[0].slots[0].state,BufferState::Free);
}
#[test] fn no_free_slot_is_distinct_and_preserves_authorization() {
 let mut b=broker();b.pools[0].slots[0].output_refs=1;
 assert_eq!(refusal(&mut b,1,size()),"NoFreeSlot");assert!(b.pools[0].authorized_request.is_some());
 b.pools[0].slots[0].output_refs=0;b.pools[0].slots[0].state=BufferState::Rendering;
 assert_eq!(refusal(&mut b,1,size()),"NoFreeSlot");
}
#[test] fn ready_handoff_still_refuses() {
 let mut b=broker();b.pools[0].slots[0].state=BufferState::Ready;
 assert_eq!(refusal(&mut b,1,size()),"ReadyHandoff");assert!(b.pools[0].authorized_request.is_some());
}
#[test] fn successful_acquire_consumes_once_and_preserves_handoff_fields() {
 let mut b=broker();assert_eq!(b.acquire(1,size()).unwrap(),23);
 assert!(b.pools[0].authorized_request.is_none());let s=&b.pools[0].slots[0];
 assert_eq!(s.state,BufferState::Rendering);assert_eq!(s.screenshot_request_id,Some(81));
 assert_eq!(s.request.unwrap().dirty_serial,9);assert!(s.fence.is_none());assert!(s.ready_damage.is_none());assert!(s.rendered_at.is_none());assert_eq!(s.ready_transaction,0);
}
#[test] fn authorization_expiry_boundary_is_unchanged() {
 let mut b=broker();let now=b.pools[0].authorized_request.unwrap().authorized_at;
 assert_eq!(b.expire_authorizations(now+Duration::from_millis(31)),0);
 assert_eq!(b.expire_authorizations(now+Duration::from_millis(32)),1);
 assert!(b.pools[0].authorized_request.is_none());assert_eq!(b.pools[0].slots[0].state,BufferState::Free);
}

#[derive(Default)] struct RenderDamageAudit {
 target_blocked_ready:u64,target_blocked_exhausted:u64,target_blocked_missing_pool:u64,
 target_blocked_no_authorization:u64,target_blocked_no_free_slot:u64,
}
impl RenderDamageAudit {
// @AUDIT_METHOD@
}
#[test] fn detailed_audit_preserves_the_old_aggregate() {
 let mut b=broker();let mut audit=RenderDamageAudit::default();
 audit.record_target_blocked(b.acquire(2,size()).unwrap_err());
 b.pools[0].slots[0].output_refs=1;
 audit.record_target_blocked(b.acquire(1,size()).unwrap_err());
 b.pools[0].authorized_request=None;
 audit.record_target_blocked(b.acquire(1,size()).unwrap_err());
 assert_eq!(audit.target_blocked_exhausted,3);assert_eq!(audit.target_blocked_ready,0);
 assert_eq!(audit.target_blocked_missing_pool,1);assert_eq!(audit.target_blocked_no_authorization,1);assert_eq!(audit.target_blocked_no_free_slot,1);
}

#[test] fn expired_permission_refuses_until_next_explicit_grant() {
 let mut b=broker();let start=b.pools[0].authorized_request.unwrap().authorized_at;
 assert_eq!(b.expire_authorizations(start+Duration::from_millis(33)),1);
 assert!(b.acquire(1,size()).is_err());
 let request=Request{tick:Tick{interval:Duration::from_millis(16),output:1},dirty_serial:10};
 assert_eq!(b.authorize(request,start+Duration::from_millis(34)),Some(1));
 assert_eq!(b.acquire(1,size()).unwrap(),23);assert_eq!(b.pools[0].slots[0].request.unwrap().dirty_serial,10);
}
#[cfg(authorization_trace)]
#[test] fn trace_sequence_is_bounded_and_unique_under_contention() {
 use std::sync::{Arc,atomic::{AtomicUsize,Ordering}};
 let counter=Arc::new(AtomicUsize::new(0));let mut threads=vec![];
 for _ in 0..8 {let c=counter.clone();threads.push(std::thread::spawn(move || {
  (0..1024).filter_map(|_|next_authorization_trace_sequence(&c)).collect::<Vec<_>>()
 }));}
 let mut values=threads.into_iter().flat_map(|t|t.join().unwrap()).collect::<Vec<_>>();values.sort_unstable();
 assert_eq!(values,(0..512).collect::<Vec<_>>());assert_eq!(counter.load(Ordering::Relaxed),512);
 assert_eq!(next_authorization_trace_sequence(&counter),None);
}
