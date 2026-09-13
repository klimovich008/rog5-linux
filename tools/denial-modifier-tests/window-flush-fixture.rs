// Extension of window-dispatch-fixture.rs. Rust/Wayland routing is extracted;
// this bounded byte transport adapter is not the Wayland protocol/backend.
use std::io::{self, Read, Write};
use std::os::unix::net::UnixStream;
struct Frontend { display_handle: BufferedDisplay }
struct BufferedDisplay {
    socket: UnixStream, pending: Vec<u8>, attempts: usize, would_blocks: usize, fail: bool,
}
impl BufferedDisplay {
    fn flush_clients(&mut self) -> io::Result<()> {
        self.attempts += 1;
        if self.fail { return Err(io::Error::other("injected flush API failure")); }
        while !self.pending.is_empty() {
            match self.socket.write(&self.pending) {
                Ok(0) => return Err(io::ErrorKind::WriteZero.into()),
                Ok(count) => { self.pending.drain(..count); }
                Err(e) if e.kind() == io::ErrorKind::WouldBlock => {
                    // Pinned Rust backend flush(None) suppresses this error,
                    // while BufferedSocket retains the unsent bytes.
                    self.would_blocks += 1; return Ok(());
                }
                Err(e) => return Err(e),
            }
        }
        Ok(())
    }
    fn queue(&mut self, commands: &[wire::WindowCommand]) {
        assert!(self.pending.len() + commands.len() * 9 <= 8192);
        for command in commands {
            self.pending.push(match command {
                wire::WindowCommand::Focus { .. } => b'F',
                wire::WindowCommand::Close { .. } => b'C',
                wire::WindowCommand::Configure { .. } => b'G',
            });
            self.pending.extend_from_slice(&command.window_id().unwrap().to_le_bytes());
        }
    }
}
mod focus_trace { pub fn log(_: &str, _: u64, _: Option<u64>, _: Option<bool>, _: Option<bool>) {} }
fn transport() -> (flutter_runtime::FlutterRuntime, RuntimeState, UnixStream) {
    let (socket, client) = UnixStream::pair().unwrap();
    socket.set_nonblocking(true).unwrap(); client.set_nonblocking(true).unwrap();
    let frontend = Frontend { display_handle: BufferedDisplay {
        socket, pending: Vec::new(), attempts: 0, would_blocks: 0, fail: false,
    }};
    (Default::default(), RuntimeState { boundary_applied: true, wayland: Some(frontend), ..Default::default() }, client)
}
fn receive(client: &mut UnixStream) -> Vec<u8> {
    let mut received = Vec::new(); let mut chunk = [0; 4096];
    loop { match client.read(&mut chunk) {
        Ok(0) => break,
        Ok(count) => { received.extend_from_slice(&chunk[..count]); assert!(received.len() <= 1048576); }
        Err(e) if e.kind() == io::ErrorKind::WouldBlock => break,
        Err(e) => panic!("socket receive failed: {e}"),
    }}
    received
}
fn attempt(r: &mut flutter_runtime::FlutterRuntime, e: &mut RuntimeState) -> Result<(), Box<dyn Error>> {
    #[cfg(before)] { dispatch_flutter_window_commands(r, e); Ok(()) }
    #[cfg(not(before))] { dispatch_flutter_window_commands(r, e) }
}
fn expected(op: u8, id: u64) -> Vec<u8> { let mut bytes=vec![op]; bytes.extend_from_slice(&id.to_le_bytes()); bytes }
fn idle_command(command: wire::WindowCommand, op: u8) {
    let (mut r, mut e, mut client) = transport();
    r.wire.pending_window_commands.push_back(command);
    attempt(&mut r, &mut e).unwrap();
    assert_eq!(receive(&mut client), expected(op, 7), "idle client must receive without new input/presentation");
    assert_eq!(e.wayland.unwrap().display_handle.attempts, 1);
}
#[test] fn idle_focus_delivery() { idle_command(focus(7), b'F'); }
#[test] fn idle_close_delivery() { idle_command(wire::WindowCommand::Close { window_id: 7 }, b'C'); }
#[test] fn idle_configure_delivery() { idle_command(wire::WindowCommand::Configure { window_id: 7 }, b'G'); }
#[test] fn empty_iteration_retries_real_socket_backpressure() {
    let (mut r, mut e, mut client) = transport();
    let display = &mut e.wayland.as_mut().unwrap().display_handle;
    let mut filled = 0;
    loop {
        match display.socket.write(&[b'A'; 8192]) {
            Ok(count) => { filled += count; assert!(filled <= 1048576); }
            Err(error) if error.kind() == io::ErrorKind::WouldBlock => break,
            other => panic!("unexpected socket saturation result: {other:?}"),
        }
    }
    r.wire.pending_window_commands.push_back(focus(7));
    attempt(&mut r, &mut e).unwrap();
    let display = &e.wayland.as_ref().unwrap().display_handle;
    assert_eq!(display.would_blocks, 1, "first flush must attempt blocked socket");
    assert_eq!(display.pending, expected(b'F', 7));
    assert_eq!(receive(&mut client), vec![b'A'; filled]);
    assert!(r.wire.pending_window_commands.is_empty());
    attempt(&mut r, &mut e).unwrap();
    assert_eq!(receive(&mut client), expected(b'F', 7));
    assert!(e.wayland.unwrap().display_handle.pending.is_empty());
}
#[test] fn locked_iteration_discards_commands_but_flushes_auth_output() {
    let (mut r, mut e, mut client) = transport(); e.locked = true;
    // Represents protocol output queued by the earlier authentication boundary.
    e.wayland.as_mut().unwrap().display_handle.pending = vec![b'L'];
    r.wire.pending_window_commands.push_back(focus(7));
    attempt(&mut r, &mut e).unwrap();
    assert!(r.wire.pending_window_commands.is_empty()); assert!(e.applied.is_empty());
    assert_eq!(receive(&mut client), b"L");
}
#[test] fn api_flush_failure_propagates_from_early_dispatch() {
    let (mut r, mut e, _) = transport(); e.wayland.as_mut().unwrap().display_handle.fail = true;
    r.wire.pending_window_commands.push_back(focus(7));
    assert!(attempt(&mut r, &mut e).is_err());
}
#[test] fn api_flush_failure_propagates_from_final_drain() {
    let (mut r, mut e, _) = transport(); e.wayland.as_mut().unwrap().display_handle.fail = true;
    r.wire.pending_window_commands.push_back(focus(7));
    assert!(synchronize_flutter_window_management(&mut r, &mut e).is_err());
}
#[test] fn final_drain_flushes_all_commands_once() {
    let (mut r, mut e, mut client) = transport();
    r.wire.pending_window_commands = (1..=67).map(focus).collect();
    synchronize_flutter_window_management(&mut r, &mut e).unwrap();
    assert!(r.wire.pending_window_commands.is_empty());
    assert_eq!(receive(&mut client), (1..=67).flat_map(|id| expected(b'F', id)).collect::<Vec<_>>());
    assert_eq!(e.wayland.unwrap().display_handle.attempts, 1);
}
#[test] fn empty_and_absent_frontend_preserve_success() {
    let mut r = Default::default();
    let mut e = RuntimeState { boundary_applied: true, ..Default::default() };
    attempt(&mut r, &mut e).unwrap();
    assert!(e.applied.is_empty());
    r.wire.pending_window_commands.push_back(focus(7));
    attempt(&mut r, &mut e).unwrap();
    assert_eq!(e.applied, [focus(7)]);
}
