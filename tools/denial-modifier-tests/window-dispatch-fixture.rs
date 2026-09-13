// Production event-loop segment and command dispatcher are inserted verbatim.
// Clock, engine, services and native endpoints are adapters; this is not a VM.
#![allow(dead_code, unused_variables)]
use std::{cell::Cell, collections::VecDeque, error::Error, time::Duration};
thread_local! { static ELAPSED: Cell<Duration> = const { Cell::new(Duration::ZERO) }; }
const COMPOSITOR_BACKGROUND_SLICE: Duration = Duration::from_millis(2);
const MAX_FLUTTER_EVENTS_PER_ITERATION: usize = 64;
struct Clock;
impl Clock { fn elapsed(&self) -> Duration { ELAPSED.get() } }
macro_rules! warn { ($($tt:tt)*) => {}; }
mod wire {
    use super::*;
    #[derive(Clone, Debug, PartialEq, Eq)]
    pub enum WindowCommand { Focus { window_id: u64 }, Close { window_id: u64 } }
    impl WindowCommand { pub fn window_id(&self) -> Option<u64> {
        match self { Self::Focus { window_id } | Self::Close { window_id } => Some(*window_id) }
    } }
    #[derive(Default)]
    pub struct Bridge { pub pending_window_commands: VecDeque<WindowCommand> }
    impl Bridge {
        // @WIRE_METHODS@
    }
}
mod flutter_runtime {
    use super::*;
    #[derive(Default)]
    pub struct FlutterRuntime { pub wire: wire::Bridge, pub batch_cost: Duration }
    impl FlutterRuntime {
        pub fn process_input_batch(&mut self, _: &mut Input) -> Result<(), Box<dyn Error>> { Ok(()) }
        pub fn process_events(&mut self, incoming: impl Iterator<Item=wire::WindowCommand>) -> Result<(), Box<dyn Error>> {
            self.wire.pending_window_commands.extend(incoming);
            ELAPSED.set(ELAPSED.get() + self.batch_cost); Ok(())
        }
        // @RUNTIME_METHODS@
    }
}
#[derive(Default)] struct Input;
impl Input { fn has_pending(&self) -> bool { false } }
#[derive(Default)] struct Plugins { applied: Vec<wire::WindowCommand>, clears: usize }
impl Plugins {
    fn owns_window(&self, id: u64) -> bool { id == 99 }
    fn apply_window_command(&mut self, command: &wire::WindowCommand) -> Result<(), Box<dyn Error>> {
        self.applied.push(command.clone()); Ok(())
    }
    fn clear_focus(&mut self) -> Result<(), Box<dyn Error>> { self.clears += 1; Ok(()) }
}
#[derive(Default)] struct RuntimeState {
    flutter_input: Input, flutter_events: VecDeque<wire::WindowCommand>,
    flutter_reload_requested: bool, locked: bool, boundary_applied: bool,
    native_app_plugins: Option<Plugins>, applied: Vec<wire::WindowCommand>,
    service_cost: Duration, yields: usize,
}
impl RuntimeState { fn secure_session_locked(&self) -> bool { self.locked } }
mod wayland_frontend {
    use super::*;
    pub fn apply_window_commands(events: &mut RuntimeState, commands: Vec<wire::WindowCommand>) {
        assert!(events.boundary_applied, "input routing boundary must precede command effects");
        assert!(!events.locked, "locked session cannot focus a client");
        events.applied.extend(commands);
    }
}
struct EventLoop;
impl EventLoop {
    fn dispatch(&mut self, _: Duration, events: &mut RuntimeState) -> Result<(), Box<dyn Error>> {
        events.yields += 1; Ok(())
    }
}
struct Launcher;
impl Launcher { fn synchronize_ui_development(&mut self, _: &mut flutter_runtime::FlutterRuntime) -> Result<bool, Box<dyn Error>> { Ok(false) } }
struct Screenshot;
impl Screenshot {
    fn request_id(&self) -> Option<u64> { None }
    fn topology_epoch(&self) -> Option<u64> { None }
    fn target_output(&self) -> Option<u64> { None }
}
struct Topology;
impl Topology { fn epoch(&self) -> u64 { 0 } }
struct Scheduler;
impl Scheduler { fn framebuffer_index_for_output(&self, _: u64, _: &[()]) -> Option<usize> { None } }
fn synchronize_authentication_boundary(events: &mut RuntimeState) { events.boundary_applied = true; }
fn synchronize_idle_dpms_configuration(_: &mut flutter_runtime::FlutterRuntime, _: &mut RuntimeState) {}
fn synchronize_requested_dpms_off(_: &mut flutter_runtime::FlutterRuntime, _: &[()], _: &mut RuntimeState) {}
fn synchronize_system_bar_configuration(_: &mut flutter_runtime::FlutterRuntime, _: &mut RuntimeState, _: Option<&mut Launcher>) {}
fn cancel_active_screenshot(_: &mut Option<Screenshot>, _: &mut flutter_runtime::FlutterRuntime, _: bool, _: &str) -> Result<(), Box<dyn Error>> { Ok(()) }
macro_rules! service { ($($name:ident),*) => { $(fn $name(_: &mut flutter_runtime::FlutterRuntime, _: &mut RuntimeState) -> Result<(), Box<dyn Error>> { Ok(()) })* }; }
service!(synchronize_clipboard, synchronize_system_control_events, synchronize_notification_events, synchronize_xembed_tray, synchronize_shell_keyboard);
fn synchronize_settings(_: &mut flutter_runtime::FlutterRuntime, events: &mut RuntimeState) -> Result<(), Box<dyn Error>> { ELAPSED.set(ELAPSED.get() + events.service_cost); Ok(()) }
// @DISPATCH@
// The old late dispatch boundary is adapted separately; actual routing is
// extracted for the corrected early dispatcher below.
fn synchronize_flutter_window_management(runtime: &mut flutter_runtime::FlutterRuntime, events: &mut RuntimeState) -> Result<(), Box<dyn Error>> {
    if events.secure_session_locked() {
        runtime.drain_window_commands().for_each(drop);
    } else {
        // @LATE_DISPATCH@
    }
    Ok(())
}
fn run_segment(mut runtime: flutter_runtime::FlutterRuntime, mut events: RuntimeState, background_services_due: bool, iterations: usize) -> (flutter_runtime::FlutterRuntime, RuntimeState) {
    let mut flutter = Some(runtime);
    let mut event_loop = EventLoop;
    let mut launcher = Launcher;
    let flutter_launcher = &mut launcher;
    let mut screenshot_manager: Option<Screenshot> = None;
    let topology = Topology;
    let scheduler = Scheduler;
    let scanouts: &[()] = &[];
    let mut execute = || -> Result<(), Box<dyn Error>> {
        for _ in 0..iterations {
            ELAPSED.set(Duration::ZERO);
            let background_started = Clock;
            // @SEGMENT@
        }
        Ok(())
    };
    execute().unwrap();
    (flutter.unwrap(), events)
}
fn focus(id: u64) -> wire::WindowCommand { wire::WindowCommand::Focus { window_id: id } }
fn initial() -> (flutter_runtime::FlutterRuntime, RuntimeState) {
    (Default::default(), RuntimeState { flutter_events: VecDeque::from([focus(7)]), ..Default::default() })
}
#[test] fn input_batch_over_budget_cannot_starve_focus() {
    let (mut r, e) = initial(); r.batch_cost = Duration::from_millis(3);
    let (_, e) = run_segment(r, e, true, 3); assert_eq!(e.applied, [focus(7)]); assert_eq!(e.yields, 3);
}
#[test] fn slow_settings_cannot_starve_focus() {
    let (r, mut e) = initial(); e.service_cost = Duration::from_millis(3);
    let (_, e) = run_segment(r, e, true, 3); assert_eq!(e.applied, [focus(7)]);
}
#[test] fn focus_does_not_require_background_cadence() {
    let (r, e) = initial(); let (_, e) = run_segment(r, e, false, 1); assert_eq!(e.applied, [focus(7)]);
}
#[test] fn retained_command_runs_without_new_platform_message() {
    let (mut r, mut e) = initial(); r.wire.pending_window_commands = std::mem::take(&mut e.flutter_events);
    let (_, e) = run_segment(r, e, false, 1); assert_eq!(e.applied, [focus(7)]);
}
#[test] fn lock_discards_commands_even_when_input_exhausts_slice() {
    let (mut r, mut e) = initial(); e.locked = true; r.batch_cost = Duration::from_millis(3);
    let (r, e) = run_segment(r, e, false, 1);
    assert!(r.wire.pending_window_commands.is_empty()); assert!(e.applied.is_empty()); assert!(e.boundary_applied);
}
#[test] fn ordinary_focus_is_dispatched_once() {
    let (r, e) = initial(); let (_, e) = run_segment(r, e, true, 3); assert_eq!(e.applied, [focus(7)]);
}
#[test] fn batch_bound_keeps_unprocessed_commands_in_order() {
    let (mut r, mut e) = initial(); e.flutter_events.clear();
    r.wire.pending_window_commands = (1..=67).map(focus).collect();
    let (r, e) = run_segment(r, e, false, 1);
    assert_eq!(e.applied, (1..=64).map(focus).collect::<Vec<_>>());
    assert_eq!(r.wire.pending_window_commands, (65..=67).map(focus).collect::<VecDeque<_>>());
    let (_, e) = run_segment(r, e, false, 1); assert_eq!(e.applied, (1..=67).map(focus).collect::<Vec<_>>());
}
#[cfg(not(before))]
#[test] fn plugin_focus_and_wayland_focus_preserve_routing() {
    let (mut r, mut e) = initial(); e.flutter_events.clear();
    r.wire.pending_window_commands = VecDeque::from([focus(99), focus(7)]);
    e.native_app_plugins = Some(Plugins::default());
    let (_, e) = run_segment(r, e, false, 1);
    assert_eq!(e.applied, [focus(7)]);
    let p = e.native_app_plugins.unwrap(); assert_eq!(p.applied, [focus(99)]); assert_eq!(p.clears, 1);
}

#[test] fn replacement_final_drain_keeps_backlog_and_last_engine_messages() {
    let (mut r, mut e) = initial(); e.boundary_applied = true;
    r.wire.pending_window_commands = (1..=67).map(focus).collect();
    e.flutter_events = VecDeque::from([focus(68), wire::WindowCommand::Close { window_id: 69 }]);
    r.process_events(e.flutter_events.drain(..)).unwrap();
    synchronize_flutter_window_management(&mut r, &mut e).unwrap();
    let mut expected: Vec<_> = (1..=68).map(focus).collect();
    expected.push(wire::WindowCommand::Close { window_id: 69 });
    assert_eq!(e.applied, expected); assert!(r.wire.pending_window_commands.is_empty());
}
