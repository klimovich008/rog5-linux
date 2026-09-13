//! Bounded Linux VM evidence framing. Only one collector writes the virtio port.
//! Prefix/record output and forward's fd 3 must be blocking FIFOs. The guest
//! supervisor owns deadlines: after malformed/capped input this helper drains
//! until EOF, so diagnostics cannot SIGPIPE-kill the observed client.
use std::env;
use std::fs::{File, OpenOptions};
use std::io::{self, Read, Write};
use std::os::unix::fs::FileTypeExt;
use std::process::ExitCode;

const RECORD_LIMIT: usize = 4096; // Linux PIPE_BUF, including the newline.
const CLIENT_LIMIT: usize = 1024 * 1024;
const NATIVE_LIMIT: usize = 8 * 1024 * 1024;
const NATIVE_LINE_LIMIT: usize = 16384;
const TERMINAL: &[u8] = b"independently clocked Flutter KMS session complete";

fn invalid(message: &'static str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message)
}

fn descriptor(number: u8, fifo: bool) -> io::Result<File> {
    let file = OpenOptions::new().write(true).open(format!("/proc/self/fd/{number}"))?;
    if fifo && !file.metadata()?.file_type().is_fifo() {
        return Err(invalid("atomic evidence descriptor must be a FIFO"));
    }
    Ok(file)
}

fn atomic_record(output: &mut impl Write, bytes: &[u8]) -> io::Result<()> {
    if bytes.is_empty() || bytes.len() > RECORD_LIMIT || !bytes.ends_with(b"\n") {
        return Err(invalid("invalid atomic record length/termination"));
    }
    // File::write issues one write(2). A blocking Linux FIFO write <= PIPE_BUF
    // is indivisible. Never use write_all here: retrying a short write could
    // interleave a record. Interrupted is retried only when no bytes were sent.
    loop {
        match output.write(bytes) {
            Ok(count) if count == bytes.len() => return Ok(()),
            Ok(_) => return Err(invalid("short atomic evidence write")),
            Err(error) if error.kind() == io::ErrorKind::Interrupted => continue,
            Err(error) => return Err(error),
        }
    }
}

fn lines(input: &mut impl Read, limit: usize, mut accept: impl FnMut(&[u8], bool) -> io::Result<()>) -> io::Result<()> {
    let mut block = [0; 8192];
    let mut line = Vec::with_capacity(limit);
    loop {
        let count = match input.read(&mut block) {
            Err(error) if error.kind() == io::ErrorKind::Interrupted => continue,
            result => result?,
        };
        if count == 0 {
            return if line.is_empty() { Ok(()) } else { accept(&line, false) };
        }
        for &byte in &block[..count] {
            if line.len() == limit {
                return Err(invalid("evidence input line limit"));
            }
            line.push(byte);
            if byte == b'\n' {
                accept(&line, true)?;
                line.clear();
            }
        }
    }
}

fn drain_after(input: &mut impl Read, result: io::Result<()>) -> io::Result<()> {
    if let Err(original) = result {
        // Retain the first failure even if draining also fails.
        let _ = io::copy(input, &mut io::sink());
        return Err(original);
    }
    Ok(())
}

fn prefix(input: &mut impl Read, output: &mut impl Write, name: &str) -> io::Result<()> {
    if !matches!(name, "EDITOR_WAYLAND" | "FOOT_WAYLAND") {
        return Err(invalid("unknown evidence prefix"));
    }
    let mut record = Vec::with_capacity(RECORD_LIMIT);
    let mut emitted = 0;
    let result = lines(input, RECORD_LIMIT - name.len() - 1, |line, complete| {
        if !complete {
            return Err(invalid("unterminated client evidence line"));
        }
        record.clear();
        record.extend_from_slice(name.as_bytes());
        record.push(b' ');
        record.extend_from_slice(line);
        if emitted + record.len() > CLIENT_LIMIT {
            return Err(invalid("launcher client log limit"));
        }
        atomic_record(output, &record)?;
        emitted += record.len();
        Ok(())
    });
    if result.is_err() {
        let _ = atomic_record(output, b"FAIL launcher client evidence rejected\n");
    }
    drain_after(input, result)
}

fn forward(input: &mut impl Read, output: &mut impl Write, evidence: &mut impl Write) -> io::Result<()> {
    let mut total = 0;
    let mut terminal = false;
    let result = lines(input, NATIVE_LINE_LIMIT, |line, complete| {
        total += line.len();
        if total > NATIVE_LIMIT {
            return Err(invalid("native evidence input limit"));
        }
        let occurrences = line.windows(TERMINAL.len()).filter(|part| *part == TERMINAL).count();
        if occurrences > 0 {
            if !complete || terminal || occurrences != 1 {
                return Err(invalid("duplicate or unterminated native terminal marker"));
            }
            // Establish the teardown boundary before releasing this native log
            // line. This marker carries no counters and cannot prove rendering.
            atomic_record(evidence, b"independently clocked Flutter KMS session complete\n")?;
            terminal = true;
        }
        output.write_all(line)
    });
    let result = result.and_then(|()| if terminal { Ok(()) } else { Err(invalid("missing native terminal marker")) });
    if result.is_err() {
        let _ = atomic_record(evidence, b"FAIL launcher native evidence rejected\n");
    }
    drain_after(input, result)
}

fn run() -> io::Result<()> {
    let mut args = env::args().skip(1);
    let mode = args.next().ok_or_else(|| invalid("missing evidence mode"))?;
    let value = args.next();
    if args.next().is_some() {
        return Err(invalid("unexpected evidence arguments"));
    }
    match (mode.as_str(), value) {
        ("prefix", Some(name)) => prefix(&mut io::stdin().lock(), &mut descriptor(1, true)?, &name),
        ("record", Some(text)) => {
            if text.is_empty() || text.len() >= RECORD_LIMIT || text.contains(['\n', '\r', '\0']) {
                return Err(invalid("invalid supervisor evidence record"));
            }
            let mut record = text.into_bytes();
            record.push(b'\n');
            atomic_record(&mut descriptor(1, true)?, &record)
        }
        ("forward", None) => {
            // Open the required inherited descriptor first. Opening stdout
            // first could allocate fd 3 and mask an absent evidence channel.
            let mut evidence = descriptor(3, true)?;
            let mut output = descriptor(1, false)?;
            forward(&mut io::stdin().lock(), &mut output, &mut evidence)
        },
        _ => Err(invalid("usage: evidence-writer prefix NAME | record TEXT | forward")),
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            // stderr may share the aggregate FIFO too; avoid line-buffered
            // eprintln!, whose individual formatting writes can interleave.
            let message = format!("FAIL launcher evidence-writer: {error}\n");
            if let Ok(mut stderr) = descriptor(2, false) {
                let _ = atomic_record(&mut stderr, message.as_bytes());
            }
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Default)]
    struct WriteProbe { calls: Vec<Vec<u8>>, short: bool, interrupt: bool }
    impl Write for WriteProbe {
        fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
            self.calls.push(bytes.to_vec());
            if self.interrupt { self.interrupt = false; return Err(io::ErrorKind::Interrupted.into()); }
            Ok(if self.short { bytes.len() - 1 } else { bytes.len() })
        }
        fn flush(&mut self) -> io::Result<()> { Ok(()) }
    }

    #[test]
    fn atomic_short_write_fails_without_retry() {
        let mut writer = WriteProbe { short: true, ..Default::default() };
        assert!(atomic_record(&mut writer, b"hello\n").is_err());
        assert_eq!(writer.calls, [b"hello\n"]);
    }

    #[test]
    fn atomic_interrupted_write_retries_same_entire_record() {
        let mut writer = WriteProbe { interrupt: true, ..Default::default() };
        atomic_record(&mut writer, b"hello\n").unwrap();
        assert_eq!(writer.calls, [b"hello\n", b"hello\n"]);
    }

    #[test]
    fn atomic_zero_and_oversized_records_do_not_write() {
        let mut writer = WriteProbe::default();
        for data in [Vec::new(), b"no newline".to_vec(), vec![b'\n'; RECORD_LIMIT + 1]] {
            assert!(atomic_record(&mut writer, &data).is_err());
        }
        assert!(writer.calls.is_empty());
    }
}
