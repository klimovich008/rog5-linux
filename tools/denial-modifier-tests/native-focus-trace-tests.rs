#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Arc, Mutex};
    #[test]
    fn only_exact_opt_in_enables() {
        for value in [None, Some(""), Some("0"), Some("true"), Some(" 1"), Some("1\n")] {
            let trace = FocusTrace::new(value);
            trace.emit_with("wire_enqueue", 9, None, None, None, |_| panic!("disabled sink called"));
            assert_eq!(trace.emitted.load(Ordering::Relaxed), 0);
        }
        assert!(FocusTrace::new(Some("1")).enabled);
    }
    #[test]
    fn shared_budget_across_stages_and_ids() {
        let trace = FocusTrace::new(Some("1"));
        let mut seen = Vec::new();
        for id in 1..=100 {
            for stage in ["wire_enqueue", "drain_wayland", "activation"] {
                trace.emit_with(stage, id, Some(id), Some(false), Some(true), |e| seen.push(e));
            }
        }
        assert_eq!(seen.len(), 64);
        assert_eq!(seen[63].sequence, 64);
        assert_eq!(trace.emitted.load(Ordering::Relaxed), 64);
        assert_eq!(seen[0].stage, "wire_enqueue");
        assert_eq!(seen[1].stage, "drain_wayland");
        assert_eq!(seen[2].stage, "activation");
    }
    #[test]
    fn reports_mismatch_and_grab_without_changing_request() {
        let trace = FocusTrace::new(Some("1"));
        trace.emit_with("activation", 11, Some(22), Some(true), Some(true), |e| {
            assert_eq!(e, Event { sequence: 1, stage: "activation", window_id: 11,
                effective_window_id: Some(22), grabbed: Some(true), activated: Some(true) });
        });
    }
    #[test]
    fn absent_focus_and_activation_failure_are_not_success() {
        let trace = FocusTrace::new(Some("1"));
        trace.emit_with("activation", 11, None, Some(false), Some(false), |e| {
            assert_eq!(e.effective_window_id, None);
            assert_eq!(e.activated, Some(false));
        });
    }
    #[test]
    fn concurrent_emitters_cannot_exceed_process_budget() {
        let trace = Arc::new(FocusTrace::new(Some("1")));
        let seen = Arc::new(Mutex::new(Vec::new()));
        let workers: Vec<_> = (0..8).map(|_| {
            let trace = trace.clone(); let seen = seen.clone();
            std::thread::spawn(move || { for _ in 0..1000 {
                trace.emit_with("wire_enqueue", 1, None, None, None, |e| seen.lock().unwrap().push(e.sequence));
            } })
        }).collect();
        for worker in workers { worker.join().unwrap(); }
        let mut sequences = seen.lock().unwrap(); sequences.sort_unstable();
        assert_eq!(*sequences, (1..=64).collect::<Vec<_>>());
    }
    #[test]
    fn exhausted_budget_does_not_invoke_sink() {
        let trace = FocusTrace::new(Some("1"));
        trace.emitted.store(MAX_EVENTS, Ordering::Relaxed);
        trace.emit_with("activation", 1, None, None, None, |_| panic!("exhausted sink called"));
        assert_eq!(trace.emitted.load(Ordering::Relaxed), MAX_EVENTS);
    }
}
