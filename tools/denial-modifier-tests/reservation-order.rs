// The caller appends this to the actual-method broker fixture. These desired
// properties currently FAIL: the API identifies only a view, not queued work.
#[cfg(test)]
mod reservation_order {
    use super::*;

    fn expire_and_replace(b: &mut OutputBufferBroker) {
        let start = b.pools[0].authorized_request.unwrap().authorized_at;
        assert_eq!(b.expire_authorizations(start + Duration::from_millis(32)), 1);
        let next = Request {
            tick: Tick { interval: Duration::from_millis(16), output: 1 },
            dirty_serial: 10,
        };
        assert_eq!(b.authorize(next, start + Duration::from_millis(33)), Some(1));
    }

    #[test]
    fn delayed_acquire_must_not_consume_a_replacement_reservation() {
        let mut b = broker();
        // A queued backing-store request captures the only identity accepted
        // by acquire today. Run it after its original reservation has expired.
        let queued_view = b.pools[0].render_view_id.get();
        let queued_size = b.pools[0].size;
        expire_and_replace(&mut b);
        let result = b.acquire(queued_view, queued_size);
        assert!(result.is_err(), "stale queued work acquired the replacement: {result:?}");
        assert_eq!(b.pools[0].authorized_request.unwrap().request.dirty_serial, 10);
    }

    #[test]
    fn delayed_cancel_must_not_remove_a_replacement_reservation() {
        let mut b = broker();
        let queued_view = b.pools[0].render_view_id.get();
        expire_and_replace(&mut b);
        // A prospective asynchronous completion cannot safely use the current
        // cancellation API. This is NOT evidence of such a callback in the VM.
        b.cancel_authorizations(&[queued_view]);
        assert_eq!(b.pools[0].authorized_request.map(|a| a.request.dirty_serial),
                   Some(10), "old completion canceled unrelated new work");
    }

    #[test]
    fn expired_acquire_without_replacement_is_refused() {
        let mut b = broker();
        let start = b.pools[0].authorized_request.unwrap().authorized_at;
        assert_eq!(b.expire_authorizations(start + Duration::from_millis(32)), 1);
        assert_eq!(format!("{:?}", b.acquire(1, size()).unwrap_err()), "MissingAuthorization");
    }

    #[test]
    fn current_acquire_consumes_exactly_once() {
        let mut b = broker();
        assert_eq!(b.acquire(1, size()).unwrap(), 23);
        assert_eq!(b.pools[0].slots[0].request.unwrap().dirty_serial, 9);
        assert_eq!(format!("{:?}", b.acquire(1, size()).unwrap_err()), "MissingAuthorization");
    }
}
