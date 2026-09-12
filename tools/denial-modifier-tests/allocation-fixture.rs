// Test boundary adapters. The runner inserts the actual upstream struct and
// allocate_gbm method; allocation, export and DRM registration alone are faked.
#![allow(dead_code)]
use std::{cell::{Cell, RefCell}, error::Error, marker::PhantomData, rc::Rc};
#[derive(Clone,Copy,Debug,PartialEq,Eq)] enum Fourcc { Xrgb8888, Argb8888 }
#[derive(Clone,Copy,Debug,PartialEq,Eq)] enum Modifier { Linear, Invalid, Tiled }
#[derive(Clone,Copy,Debug,PartialEq,Eq)] struct Format { code:Fourcc, modifier:Modifier }
#[derive(Clone,Copy)] struct PixelSize { width:u32, height:u32 }
mod smithay { pub mod backend { pub mod allocator {
    pub trait Buffer { fn format(&self) -> crate::Format; }
}}}
#[derive(Clone,Default)] struct State {
    live:Rc<Cell<usize>>, registered:Rc<Cell<usize>>, drops:Rc<RefCell<Vec<&'static str>>>,
}
struct DrmDeviceFd(State);
struct GbmAllocator<T> { stored:Format, exported:Format, fail_export:bool, state:State, _type:PhantomData<T> }
struct GbmBuffer { stored:Format, exported:Format, fail_export:bool, state:State }
struct Dmabuf { format:Format, state:State }
struct LinearRenderBuffer;
struct Fb(State);
enum AtlasFramebuffer { Gbm(Fb), Prime(Fb) }
impl Drop for Fb { fn drop(&mut self) { self.0.drops.borrow_mut().push("framebuffer"); } }
impl Drop for GbmBuffer { fn drop(&mut self) {
    self.state.live.set(self.state.live.get()-1); self.state.drops.borrow_mut().push("buffer");
}}
impl smithay::backend::allocator::Buffer for GbmBuffer { fn format(&self)->Format {self.stored} }
impl smithay::backend::allocator::Buffer for Dmabuf { fn format(&self)->Format {self.format} }
impl GbmBuffer { fn export(&self)->Result<Dmabuf,Box<dyn Error>> {
    if self.fail_export {return Err("injected export failure".into());}
    Ok(Dmabuf {format:self.exported,state:self.state.clone()})
}}
impl<T> GbmAllocator<T> {
    fn create_buffer(&mut self,_w:u32,_h:u32,_f:Fourcc,_m:&[Modifier])->Result<GbmBuffer,Box<dyn Error>> {
        self.state.live.set(self.state.live.get()+1);
        Ok(GbmBuffer {stored:self.stored,exported:self.exported,fail_export:self.fail_export,state:self.state.clone()})
    }
}
fn framebuffer_from_bo(fd:&DrmDeviceFd,_b:&GbmBuffer,_opaque:bool)->Result<Fb,Box<dyn Error>> {
    fd.0.registered.set(fd.0.registered.get()+1); Ok(Fb(fd.0.clone()))
}
fn framebuffer_from_prime_dmabuf(fd:&DrmDeviceFd,_b:&Dmabuf)->Result<Fb,Box<dyn Error>> {
    fd.0.registered.set(fd.0.registered.get()+1); Ok(Fb(fd.0.clone()))
}
// @ACTUAL_STRUCT@
impl ScanoutBuffer {
// @ACTUAL_ALLOCATE_GBM@
}
fn format(modifier:Modifier)->Format { Format {code:Fourcc::Xrgb8888,modifier} }
fn allocate(request:&[Modifier],stored:Format,exported:Format,fail_export:bool,cross:bool)->(Result<ScanoutBuffer,Box<dyn Error>>,State) {
    let state=State::default();let fd=DrmDeviceFd(state.clone());
    let mut allocator=GbmAllocator {stored,exported,fail_export,state:state.clone(),_type:PhantomData};
    let result=ScanoutBuffer::allocate_gbm(&mut allocator,&fd,cross,PixelSize{width:640,height:480},request);
    (result,state)
}
fn rejects_before_registration(request:&[Modifier],stored:Format,exported:Format) {
    for cross in [false,true] {
        let (result,state)=allocate(request,stored,exported,false,cross);
        let error=match result {Err(e)=>e,Ok(_)=>panic!("unexpected descriptor admitted")};
        assert!(error.to_string().contains("allocation contract"));
        assert_eq!(state.registered.get(),0);assert_eq!(state.live.get(),0);
    }
}
#[test] fn valid_modes_preserve_framebuffer_before_buffer_drop() {
    for modifier in [Modifier::Invalid,Modifier::Linear,Modifier::Tiled] {
        for cross in [false,true] {
            let (result,state)=allocate(&[modifier],format(modifier),format(modifier),false,cross);
            let buffer=result.expect("matching format");assert_eq!(state.registered.get(),1);
            drop(buffer);assert_eq!(state.live.get(),0);
            assert_eq!(*state.drops.borrow(),vec!["framebuffer","buffer"]);
        }
    }
}
#[test] fn implicit_request_rejects_explicit_result() {
    rejects_before_registration(&[Modifier::Invalid],format(Modifier::Linear),format(Modifier::Linear));
}
#[test] fn explicit_request_rejects_implicit_result() {
    rejects_before_registration(&[Modifier::Linear],format(Modifier::Invalid),format(Modifier::Invalid));
}
#[test] fn export_must_match_stored_descriptor() {
    rejects_before_registration(&[Modifier::Linear],format(Modifier::Linear),format(Modifier::Tiled));
}
#[test] fn wrong_fourcc_and_empty_request_are_rejected() {
    let wrong=Format {code:Fourcc::Argb8888,modifier:Modifier::Linear};
    rejects_before_registration(&[Modifier::Linear],wrong,wrong);
    rejects_before_registration(&[],format(Modifier::Linear),format(Modifier::Linear));
}
#[test] fn export_error_is_preserved_and_buffer_released() {
    let (result,state)=allocate(&[Modifier::Invalid],format(Modifier::Invalid),format(Modifier::Invalid),true,false);
    let error=match result {Err(e)=>e,Ok(_)=>panic!("export error discarded")};
    assert_eq!(error.to_string(),"injected export failure");
    assert_eq!(state.registered.get(),0);assert_eq!(state.live.get(),0);
}
