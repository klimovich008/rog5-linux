#!/usr/bin/env python3
"""Fault-injection tests for the stable recovery protocol reference model."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing
from pathlib import Path
import stat
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.recovery_control import (  # noqa: E402
    EMPTY_BODY_SHA256,
    ZERO_ID,
    FrameParser,
    HostIntentLedger,
    InjectedCrash,
    ProtocolViolation,
    RecoveryModel,
    RecoveryState,
    Response,
    TargetDeparted,
    decode_request,
    decode_response,
    encode_frame,
    encode_request,
    encode_response,
)


SESSION = "1" * 32
NEW_SESSION = "2" * 32
MANIFEST = "a" * 64
OTHER_MANIFEST = "b" * 64


def request_id(number: int) -> str:
    if number < 1:
        raise ValueError("request IDs are nonzero")
    return f"{number:032x}"


def make_request(
    verb: str,
    number: int,
    *,
    session: str = SESSION,
    body: dict[str, str] | None = None,
):
    if verb == "HELLO":
        session = ZERO_ID
    return decode_request(
        encode_request(
            session=session,
            request=request_id(number),
            verb=verb,
            body=body,
        )
    )


def prepare_request(number: int = 10, bundle: str = "arch-v1"):
    return make_request(
        "PREPARE",
        number,
        body={
            "bundle": bundle,
            "manifest_sha256": MANIFEST,
        },
    )


def commit_request(number: int = 11, prepare_number: int = 10):
    return make_request(
        "COMMIT_EXEC",
        number,
        body={
            "prepare_request": request_id(prepare_number),
            "manifest_sha256": MANIFEST,
        },
    )


def arm_in_process(root: str, number: int) -> str:
    ledger = HostIntentLedger(Path(root))
    try:
        ledger.arm(
            session=SESSION,
            request=request_id(number),
            manifest_sha256=MANIFEST,
            target="arch-v1",
        )
    except FileExistsError:
        return "refused"
    finally:
        ledger.close()
    return "armed"


class FrameParserTest(unittest.TestCase):
    def setUp(self):
        self.payload = encode_request(
            session=SESSION,
            request=request_id(1),
            verb="STATUS",
        )
        self.frame = encode_frame(self.payload)

    def test_every_split_point_reassembles_one_frame(self):
        for split in range(len(self.frame) + 1):
            with self.subTest(split=split):
                parser = FrameParser()
                first = parser.feed(self.frame[:split])
                second = parser.feed(self.frame[split:])
                self.assertEqual(first + second, [self.payload])

    def test_byte_at_a_time_and_coalesced_frames(self):
        parser = FrameParser()
        output = []
        for byte in self.frame:
            output.extend(parser.feed(bytes([byte])))
        self.assertEqual(output, [self.payload])

        hello = encode_request(
            session=ZERO_ID,
            request=request_id(2),
            verb="HELLO",
        )
        parser = FrameParser()
        self.assertEqual(
            parser.feed(self.frame + encode_frame(hello)),
            [self.payload, hello],
        )

    def test_incomplete_frame_waits_without_guessing(self):
        parser = FrameParser()
        self.assertEqual(parser.feed(b"11:short"), [])
        self.assertEqual(parser.feed(b" value,"), [b"short value"])
        parser.finalize()

        parser = FrameParser()
        parser.feed(b"11:short")
        with self.assertRaisesRegex(ProtocolViolation, "TRUNCATED_FRAME"):
            parser.finalize()

    def test_exact_maximum_is_accepted_and_larger_is_rejected(self):
        payload = b"x" * 4096
        self.assertEqual(FrameParser().feed(encode_frame(payload)), [payload])
        with self.assertRaisesRegex(ProtocolViolation, "FRAME_TOO_LARGE"):
            encode_frame(payload + b"x")

    def test_malformed_frame_fails_terminally(self):
        malformed = {
            b":,": "BAD_LENGTH",
            b"01:a,": "BAD_LENGTH",
            b"x:a,": "BAD_LENGTH",
            b"4097:": "FRAME_TOO_LARGE",
            b"12345": "BAD_LENGTH",
            b"1:a;": "BAD_TERMINATOR",
        }
        for data, code in malformed.items():
            with self.subTest(data=data):
                parser = FrameParser()
                with self.assertRaisesRegex(ProtocolViolation, code):
                    parser.feed(data)
                with self.assertRaisesRegex(
                    ProtocolViolation,
                    "PARSER_FAILED",
                ):
                    parser.feed(self.frame)

    def test_feed_and_frame_count_are_bounded(self):
        parser = FrameParser()
        with self.assertRaisesRegex(ProtocolViolation, "READ_TOO_LARGE"):
            parser.feed(b"x" * 8193)

        parser = FrameParser()
        with self.assertRaisesRegex(ProtocolViolation, "TOO_MANY_FRAMES"):
            parser.feed(b"".join(encode_frame(b"") for _ in range(33)))


class RecordCodecTest(unittest.TestCase):
    def test_all_request_verbs_round_trip(self):
        requests = [
            make_request("HELLO", 1),
            make_request("STATUS", 2),
            prepare_request(3),
            make_request(
                "COMMIT_EXEC",
                4,
                body={
                    "prepare_request": request_id(3),
                    "manifest_sha256": MANIFEST,
                },
            ),
        ]
        for request in requests:
            with self.subTest(verb=request.verb):
                frame = encode_frame(request.wire)
                payload = FrameParser().feed(frame)[0]
                self.assertEqual(decode_request(payload), request)

    def test_response_round_trip_preserves_correlation(self):
        response = Response(
            session=SESSION,
            request=request_id(1),
            verb="HELLO",
            result="OK",
            state="IDLE",
        )
        decoded = decode_response(encode_response(response))
        self.assertEqual(decoded, response)
        self.assertEqual(
            decode_response(encode_response(decoded)).request,
            request_id(1),
        )

        detailed = Response(
            session=SESSION,
            request=request_id(2),
            verb="STATUS",
            result="OK",
            state="CLAIMED",
            prepared_bundle="arch-v1",
            manifest_sha256=MANIFEST,
            prepare_request=request_id(10),
            commit_request=request_id(11),
            commit_fingerprint=OTHER_MANIFEST,
            execution_started="NO",
            watchdog="ARMED",
            last_error="NONE",
        )
        self.assertEqual(decode_response(encode_response(detailed)), detailed)

    def test_record_rejects_noncanonical_and_unknown_input(self):
        valid = make_request("STATUS", 1).wire
        mutations = {
            valid[:-1]: "NON_CANONICAL",
            valid.replace(b"version=1\n", b"version=1\nversion=1\n"):
                "DUPLICATE_FIELD",
            valid.replace(b"verb=STATUS", b"verb=UNKNOWN"): "UNKNOWN_VERB",
            valid.replace(
                f"body_sha256={EMPTY_BODY_SHA256}".encode(),
                b"body_sha256=" + b"0" * 64,
            ): "BAD_BODY_HASH",
            valid.replace(b"kind=request", b"kind=request\x00"): "NON_CANONICAL",
            valid.replace(b"kind=request", b"kind=reque\xff"): "NON_ASCII",
        }
        for payload, code in mutations.items():
            with self.subTest(code=code):
                with self.assertRaisesRegex(ProtocolViolation, code):
                    decode_request(payload)

    def test_field_order_is_part_of_canonical_identity(self):
        valid = make_request("STATUS", 1).wire
        lines = valid.splitlines(keepends=True)
        lines[0], lines[1] = lines[1], lines[0]
        with self.assertRaisesRegex(ProtocolViolation, "BAD_FIELDS"):
            decode_request(b"".join(lines))

    def test_session_and_request_ids_are_strict(self):
        with self.assertRaisesRegex(ProtocolViolation, "BAD_SESSION"):
            encode_request(
                session=SESSION,
                request=request_id(1),
                verb="HELLO",
            )
        with self.assertRaisesRegex(ProtocolViolation, "BAD_SESSION"):
            encode_request(
                session=ZERO_ID,
                request=request_id(1),
                verb="STATUS",
            )
        with self.assertRaisesRegex(ProtocolViolation, "BAD_REQUEST_ID"):
            encode_request(
                session=SESSION,
                request=ZERO_ID,
                verb="STATUS",
            )

    def test_bundle_identifier_cannot_escape_fixed_path(self):
        rejected = (
            ".hidden",
            "a..b",
            "Upper",
            "a/b",
            "a" * 65,
            "none",
        )
        for bundle in rejected:
            with self.subTest(bundle=bundle):
                with self.assertRaisesRegex(
                    ProtocolViolation,
                    "BAD_BUNDLE",
                ):
                    make_request(
                        "PREPARE",
                        1,
                        body={
                            "bundle": bundle,
                            "manifest_sha256": MANIFEST,
                        },
                    )

    def test_zero_manifest_sentinel_is_rejected(self):
        for verb, body in (
            (
                "PREPARE",
                {
                    "bundle": "arch-v1",
                    "manifest_sha256": "0" * 64,
                },
            ),
            (
                "COMMIT_EXEC",
                {
                    "prepare_request": request_id(1),
                    "manifest_sha256": "0" * 64,
                },
            ),
        ):
            with self.subTest(verb=verb):
                with self.assertRaisesRegex(
                    ProtocolViolation,
                    "BAD_MANIFEST_HASH",
                ):
                    make_request(verb, 2, body=body)

    def test_body_field_order_and_response_tokens_are_strict(self):
        with self.assertRaisesRegex(ProtocolViolation, "BAD_FIELDS"):
            encode_request(
                session=SESSION,
                request=request_id(1),
                verb="PREPARE",
                body={
                    "manifest_sha256": MANIFEST,
                    "bundle": "arch-v1",
                },
            )
        with self.assertRaisesRegex(ProtocolViolation, "BAD_RESPONSE"):
            encode_response(
                Response(
                    session=SESSION,
                    request=request_id(1),
                    verb="STATUS",
                    result="not-fixed",
                    state="IDLE",
                )
            )
        with self.assertRaisesRegex(ProtocolViolation, "BAD_RESPONSE"):
            encode_response(
                Response(
                    session=SESSION,
                    request=request_id(1),
                    verb="STATUS",
                    result="CLAIMED",
                    state="IDLE",
                )
            )
        with self.assertRaisesRegex(ProtocolViolation, "BAD_RESPONSE"):
            encode_response(
                Response(
                    session=SESSION,
                    request=request_id(1),
                    verb="STATUS",
                    result="OK",
                    state="EXEC_FAILED",
                    prepared_bundle="arch-v1",
                    manifest_sha256=MANIFEST,
                    prepare_request=request_id(10),
                    commit_request=request_id(11),
                    commit_fingerprint=OTHER_MANIFEST,
                )
            )
        with self.assertRaisesRegex(ProtocolViolation, "BAD_RESPONSE"):
            encode_response(
                Response(
                    session=SESSION,
                    request=request_id(1),
                    verb="STATUS",
                    result="UNKNOWN_RESULT",
                    state="IDLE",
                )
            )


class RecoveryStateModelTest(unittest.TestCase):
    def setUp(self):
        self.state = RecoveryState(session=SESSION)
        self.model = RecoveryModel(self.state, maximum_ledger_entries=32)

    def prepare(self):
        response = self.model.handle(prepare_request())
        self.assertEqual(response.result, "PREPARED")
        return response

    def test_hello_returns_device_session_and_status_tracks_state(self):
        hello = self.model.handle(make_request("HELLO", 1))
        self.assertEqual(hello.session, SESSION)
        self.assertEqual(hello.request, request_id(1))
        self.assertEqual(hello.result, "OK")
        self.assertEqual(hello.state, "IDLE")
        self.assertEqual(len(self.state.ledger), 0)

        self.prepare()
        status_response = self.model.handle(make_request("STATUS", 2))
        self.assertEqual(status_response.state, "PREPARED")
        self.assertEqual(len(self.state.ledger), 1)

    def test_stale_session_is_rejected_without_entering_ledger(self):
        stale = make_request("STATUS", 1, session=NEW_SESSION)
        response = self.model.handle(stale)
        self.assertEqual(response.result, "STALE_SESSION")
        self.assertNotIn(stale.request, self.state.ledger)

    def test_same_request_replays_and_changed_body_conflicts(self):
        first = prepare_request()
        response = self.model.handle(first)
        self.assertEqual(self.model.handle(first), response)
        changed = make_request(
            "PREPARE",
            10,
            body={
                "bundle": "arch-v2",
                "manifest_sha256": MANIFEST,
            },
        )
        self.assertEqual(
            self.model.handle(changed).result,
            "REQUEST_CONFLICT",
        )
        self.assertEqual(self.state.prepare_calls, 1)

    def test_new_prepare_id_is_rejected_and_original_can_commit(self):
        self.prepare()
        same_bundle = prepare_request(12)
        response = self.model.handle(same_bundle)
        self.assertEqual(response.result, "PREPARE_ID_CONFLICT")
        self.assertEqual(self.state.prepare_calls, 1)
        wrong_commit = make_request(
            "COMMIT_EXEC",
            13,
            body={
                "prepare_request": request_id(12),
                "manifest_sha256": MANIFEST,
            },
        )
        self.assertEqual(
            self.model.handle(wrong_commit).result,
            "PREPARE_MISMATCH",
        )
        self.assertEqual(self.model.handle(commit_request(14)).result, "CLAIMED")

    def test_second_bundle_and_failed_verification_are_fail_closed(self):
        self.prepare()
        other = make_request(
            "PREPARE",
            12,
            body={
                "bundle": "arch-v2",
                "manifest_sha256": MANIFEST,
            },
        )
        self.assertEqual(self.model.handle(other).result, "BUNDLE_CONFLICT")
        self.assertEqual(self.state.prepared_bundle, "arch-v1")

        rejected_state = RecoveryState(session=SESSION)
        rejected = RecoveryModel(
            rejected_state,
            verifier=lambda _bundle, _manifest: False,
        )
        self.assertEqual(
            rejected.handle(prepare_request()).result,
            "VERIFY_FAILED",
        )
        self.assertEqual(rejected_state.phase, "IDLE")
        self.assertIsNone(rejected_state.prepared_bundle)

    def test_commit_requires_exact_prepared_transaction(self):
        self.assertEqual(
            self.model.handle(commit_request()).result,
            "PREPARE_REQUIRED",
        )
        self.prepare()
        wrong_prepare = make_request(
            "COMMIT_EXEC",
            12,
            body={
                "prepare_request": request_id(99),
                "manifest_sha256": MANIFEST,
            },
        )
        self.assertEqual(
            self.model.handle(wrong_prepare).result,
            "PREPARE_MISMATCH",
        )

        wrong_manifest = make_request(
            "COMMIT_EXEC",
            13,
            body={
                "prepare_request": request_id(10),
                "manifest_sha256": OTHER_MANIFEST,
            },
        )
        self.assertEqual(
            self.model.handle(wrong_manifest).result,
            "PREPARE_MISMATCH",
        )
        self.assertEqual(self.state.phase, "PREPARED")

    def test_claim_and_execute_are_at_most_once(self):
        self.prepare()
        commit = commit_request()
        claimed = self.model.handle(commit)
        self.assertEqual(claimed.result, "CLAIMED")
        self.assertEqual(self.model.handle(commit), claimed)
        self.assertEqual(self.state.execute_claims, 1)

        calls = []

        def departed():
            calls.append("execute")
            raise TargetDeparted()

        self.assertEqual(self.model.execute_claimed(departed), "CLAIMED")
        self.assertEqual(self.model.execute_claimed(departed), "CLAIMED")
        self.assertEqual(calls, ["execute"])
        self.assertEqual(self.state.execute_calls, 1)

    def test_kexec_return_or_exception_permanently_fails_session(self):
        self.prepare()
        self.model.handle(commit_request())
        self.assertEqual(self.model.execute_claimed(lambda: None), "EXEC_FAILED")
        self.assertEqual(self.state.last_error, "EXEC_RETURNED")
        self.assertEqual(
            self.model.handle(make_request("STATUS", 20)).state,
            "EXEC_FAILED",
        )

        state = RecoveryState(session=SESSION)
        model = RecoveryModel(state)
        model.handle(prepare_request())
        model.handle(commit_request())

        def failed():
            raise OSError("synthetic kexec failure")

        self.assertEqual(model.execute_claimed(failed), "EXEC_FAILED")
        self.assertEqual(state.last_error, "EXEC_FAILED")

    def test_crash_before_claim_leaves_prepared_state(self):
        self.prepare()
        with self.assertRaisesRegex(InjectedCrash, "before_claim"):
            self.model.handle(commit_request(), inject="before_claim")
        self.assertEqual(self.state.phase, "PREPARED")
        self.assertEqual(self.state.execute_claims, 0)
        self.assertNotIn(request_id(11), self.state.ledger)

    def test_crash_after_prepare_reconstructs_authoritative_request(self):
        prepare = prepare_request()
        with self.assertRaisesRegex(InjectedCrash, "after_prepare"):
            self.model.handle(prepare, inject="after_prepare")
        self.assertEqual(self.state.phase, "PREPARED")
        self.assertEqual(
            self.state.prepare_fingerprint,
            prepare.fingerprint,
        )
        self.assertNotIn(request_id(10), self.state.ledger)

        persisted = RecoveryState.from_snapshot(self.state.snapshot())
        restarted = RecoveryModel(persisted)
        replay = restarted.handle(prepare)
        self.assertEqual(replay.result, "PREPARED")
        self.assertNotIn(request_id(10), persisted.ledger)

        commit = restarted.handle(commit_request())
        self.assertEqual(commit.result, "CLAIMED")
        self.assertEqual(
            restarted.handle(prepare).result,
            "PREPARED",
        )

    def test_crash_after_claim_cannot_execute_after_responder_restart(self):
        self.prepare()
        commit = commit_request()
        with self.assertRaisesRegex(InjectedCrash, "after_claim"):
            self.model.handle(commit, inject="after_claim")
        self.assertEqual(self.state.phase, "CLAIMED")
        self.assertEqual(self.state.execute_claims, 1)

        persisted = RecoveryState.from_snapshot(self.state.snapshot())
        restarted = RecoveryModel(persisted)
        self.assertEqual(restarted.handle(commit).result, "CLAIMED")
        calls = []
        self.assertEqual(
            restarted.execute_claimed(lambda: calls.append("execute")),
            "CLAIMED",
        )
        self.assertEqual(calls, [])
        self.assertEqual(persisted.execute_calls, 0)

        changed = make_request(
            "COMMIT_EXEC",
            11,
            body={
                "prepare_request": request_id(99),
                "manifest_sha256": MANIFEST,
            },
        )
        self.assertEqual(restarted.handle(changed).result, "REQUEST_CONFLICT")

    def test_crash_after_response_replays_claim_but_not_execution(self):
        self.prepare()
        commit = commit_request()
        with self.assertRaisesRegex(InjectedCrash, "after_response"):
            self.model.handle(commit, inject="after_response")
        persisted = RecoveryState.from_snapshot(self.state.snapshot())
        restarted = RecoveryModel(persisted)
        replay = restarted.handle(commit)
        self.assertEqual(replay.result, "CLAIMED")
        calls = []
        restarted.execute_claimed(lambda: calls.append("execute"))
        self.assertEqual(calls, [])

    def test_full_ledger_fails_closed_without_eviction(self):
        verifications = []

        def verify(bundle, manifest):
            verifications.append((bundle, manifest))
            return True

        self.model = RecoveryModel(
            self.state,
            maximum_ledger_entries=4,
            verifier=verify,
        )
        for number in range(20, 22):
            response = self.model.handle(
                commit_request(number, prepare_number=10)
            )
            self.assertEqual(response.result, "PREPARE_REQUIRED")
        self.assertEqual(len(self.state.ledger), 2)
        self.assertEqual(
            self.model.handle(make_request("STATUS", 23)).result,
            "OK",
        )
        response = self.model.handle(
            commit_request(22, prepare_number=10)
        )
        self.assertEqual(response.result, "LEDGER_FULL")
        self.assertEqual(len(self.state.ledger), 2)
        self.assertEqual(self.state.phase, "IDLE")
        self.assertEqual(
            self.model.handle(prepare_request()).result,
            "PREPARED",
        )
        self.assertEqual(verifications, [("arch-v1", MANIFEST)])
        self.assertEqual(
            self.model.handle(commit_request()).result,
            "CLAIMED",
        )
        self.assertEqual(len(self.state.ledger), 4)

    def test_rejected_commit_cannot_change_meaning_after_later_prepare(self):
        state = RecoveryState(session=SESSION)
        model = RecoveryModel(state, maximum_ledger_entries=5)
        commit = commit_request()
        rejected = model.handle(commit)
        self.assertEqual(rejected.result, "PREPARE_REQUIRED")
        model.handle(commit_request(20))
        model.handle(commit_request(21))
        self.assertEqual(model.handle(prepare_request()).result, "PREPARED")
        replay = model.handle(commit)
        self.assertEqual(replay.result, "PREPARE_REQUIRED")
        self.assertEqual(state.phase, "PREPARED")
        self.assertEqual(state.execute_claims, 0)

    def test_status_correlates_the_claim_and_watchdog(self):
        self.prepare()
        commit = commit_request()
        self.model.handle(commit)
        response = self.model.handle(make_request("STATUS", 20))
        self.assertEqual(response.state, "CLAIMED")
        self.assertEqual(response.prepared_bundle, "arch-v1")
        self.assertEqual(response.manifest_sha256, MANIFEST)
        self.assertEqual(response.prepare_request, request_id(10))
        self.assertEqual(response.commit_request, request_id(11))
        self.assertEqual(response.commit_fingerprint, commit.fingerprint)
        self.assertEqual(response.execution_started, "NO")
        self.assertEqual(response.watchdog, "ARMED")

    def test_snapshot_round_trip_rejects_partial_or_duplicate_state(self):
        self.prepare()
        commit = commit_request()
        self.model.handle(commit)
        snapshot = self.state.snapshot()
        restored = RecoveryState.from_snapshot(snapshot)
        self.assertEqual(restored.session, SESSION)
        self.assertEqual(restored.phase, "CLAIMED")
        self.assertEqual(restored.commit_fingerprint, commit.fingerprint)
        self.assertIsNone(restored.claim_owner)
        self.assertEqual(tuple(restored.ledger), tuple(self.state.ledger))

        duplicate = snapshot.replace(
            b'"phase":"CLAIMED"',
            b'"phase":"CLAIMED","phase":"CLAIMED"',
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            RecoveryState.from_snapshot(duplicate)

        partial = snapshot.replace(
            f'"commit_fingerprint":"{commit.fingerprint}"'.encode(),
            b'"commit_fingerprint":null',
            1,
        )
        with self.assertRaisesRegex(ValueError, "partial"):
            RecoveryState.from_snapshot(partial)

        wrong_session = snapshot.replace(
            f'"session":"{SESSION}"'.encode(),
            f'"session":"{NEW_SESSION}"'.encode(),
            1,
        )
        with self.assertRaisesRegex(ValueError, "ledger entry"):
            RecoveryState.from_snapshot(wrong_session)

        terminal_without_marker = snapshot.replace(
            b'"phase":"CLAIMED"',
            b'"phase":"EXEC_FAILED"',
        )
        with self.assertRaisesRegex(ValueError, "execution marker"):
            RecoveryState.from_snapshot(terminal_without_marker)

    def test_crash_after_execution_marker_never_reexecutes(self):
        self.prepare()
        self.model.handle(commit_request())
        with self.assertRaisesRegex(InjectedCrash, "after_execute_start"):
            self.model.execute_claimed(
                lambda: self.fail("executor must not run before injection"),
                inject="after_execute_start",
            )
        persisted = RecoveryState.from_snapshot(self.state.snapshot())
        restarted = RecoveryModel(persisted)
        calls = []
        self.assertEqual(
            restarted.execute_claimed(lambda: calls.append("execute")),
            "CLAIMED",
        )
        self.assertEqual(calls, [])
        self.assertTrue(persisted.execution_started)
        self.assertEqual(persisted.execute_calls, 1)

    def test_new_recovery_session_rejects_old_requests(self):
        old = make_request("STATUS", 1)
        fresh = RecoveryModel(RecoveryState(session=NEW_SESSION))
        self.assertEqual(fresh.handle(old).result, "STALE_SESSION")


class HostIntentLedgerTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "ledger"
        self.ledger = HostIntentLedger(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def arm(
        self,
        *,
        inject: str | None = None,
        session: str = SESSION,
        number: int = 11,
    ):
        return self.ledger.arm(
            session=session,
            request=request_id(number),
            manifest_sha256=MANIFEST,
            target="arch-v1",
            inject=inject,
        )

    def test_intent_is_durable_private_and_duplicate_is_refused(self):
        record = self.arm()
        self.assertEqual(record.state, "TRANSMITTED")
        self.assertEqual(record.outcome, "UNKNOWN")
        self.assertGreater(record.created_unix_ns, 0)
        self.assertEqual(self.ledger.read(SESSION), record)
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o700)
        path = self.root / f"{SESSION}.json"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        with self.assertRaises(FileExistsError):
            self.arm()
        with self.assertRaises(FileExistsError):
            self.arm(number=12)

    def test_resolution_is_durable_and_immutable(self):
        self.arm()
        resolved = self.ledger.resolve(
            session=SESSION,
            request=request_id(11),
            outcome="TARGET_ACCEPTED",
        )
        self.assertEqual(resolved.state, "RESOLVED")
        self.assertEqual(resolved.outcome, "TARGET_ACCEPTED")
        self.assertEqual(
            self.ledger.resolve(
                session=SESSION,
                request=request_id(11),
                outcome="TARGET_ACCEPTED",
            ),
            resolved,
        )
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.ledger.resolve(
                session=SESSION,
                request=request_id(11),
                outcome="FALLBACK_RETURNED",
            )

    def test_resolution_requires_the_original_request(self):
        self.arm()
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.ledger.resolve(
                session=SESSION,
                request=request_id(12),
                outcome="TARGET_ACCEPTED",
            )

    def test_concurrent_resolution_cannot_change_outcome(self):
        self.arm()

        def resolve(outcome):
            ledger = HostIntentLedger(self.root)
            try:
                return ledger.resolve(
                    session=SESSION,
                    request=request_id(11),
                    outcome=outcome,
                ).outcome
            except ValueError:
                return "REFUSED"

        outcomes = ("TARGET_ACCEPTED", "FALLBACK_RETURNED")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(resolve, outcomes))
        self.assertIn("REFUSED", results)
        final = self.ledger.read(SESSION)
        self.assertIn(final.outcome, outcomes)
        self.assertEqual(results.count(final.outcome), 1)

    def test_crash_before_rename_does_not_arm_transmission(self):
        with self.assertRaisesRegex(InjectedCrash, "after_file_fsync"):
            self.arm(inject="after_file_fsync")
        self.assertIsNone(self.ledger.read(SESSION))
        self.assertEqual(len(list(self.root.glob("*.json"))), 0)
        self.assertEqual(len(list(self.root.glob(".*.tmp"))), 1)

    def test_crash_after_replace_is_conservatively_transmitted(self):
        with self.assertRaisesRegex(InjectedCrash, "after_replace"):
            self.arm(inject="after_replace")
        record = self.ledger.read(SESSION)
        self.assertIsNotNone(record)
        self.assertEqual(record.state, "TRANSMITTED")
        with self.assertRaises(FileExistsError):
            self.arm()

    def test_new_device_session_gets_a_distinct_intent(self):
        self.arm()
        second = self.arm(session=NEW_SESSION)
        self.assertEqual(second.session, NEW_SESSION)
        self.assertEqual(len(list(self.root.glob("*.json"))), 2)

    def test_concurrent_session_intents_have_one_winner(self):
        def contender(number):
            ledger = HostIntentLedger(self.root)
            try:
                ledger.arm(
                    session=SESSION,
                    request=request_id(number),
                    manifest_sha256=MANIFEST,
                    target="arch-v1",
                )
            except FileExistsError:
                return "refused"
            return "armed"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(contender, (11, 12)))
        self.assertEqual(sorted(outcomes), ["armed", "refused"])
        self.assertIn(
            self.ledger.read(SESSION).request,
            {request_id(11), request_id(12)},
        )

    def test_multiprocess_session_intents_have_one_winner(self):
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=2,
            mp_context=context,
        ) as pool:
            futures = [
                pool.submit(arm_in_process, str(self.root), number)
                for number in (11, 12)
            ]
            outcomes = [future.result(timeout=10) for future in futures]
        self.assertEqual(sorted(outcomes), ["armed", "refused"])

    def test_invalid_names_and_symlinks_are_rejected(self):
        with self.assertRaises(ValueError):
            self.ledger.arm(
                session=ZERO_ID,
                request=request_id(11),
                manifest_sha256=MANIFEST,
                target="arch-v1",
            )
        with self.assertRaises(ValueError):
            self.ledger.arm(
                session=SESSION,
                request=request_id(11),
                manifest_sha256="bad",
                target="arch-v1",
            )
        with self.assertRaises(ValueError):
            self.ledger.arm(
                session=SESSION,
                request=request_id(11),
                manifest_sha256="0" * 64,
                target="arch-v1",
            )
        with self.assertRaises(ValueError):
            self.ledger.arm(
                session=SESSION,
                request=request_id(11),
                manifest_sha256=MANIFEST,
                target="../escape",
            )

        real = Path(self.temporary.name) / "real"
        real.mkdir()
        linked = Path(self.temporary.name) / "linked"
        linked.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "unlinked directory"):
            HostIntentLedger(linked)

    def test_record_symlink_is_never_followed(self):
        outside = Path(self.temporary.name) / "outside"
        outside.write_text("{}\n", encoding="ascii")
        path = self.root / f"{SESSION}.json"
        path.symlink_to(outside)
        with self.assertRaises(OSError):
            self.ledger.read(SESSION)
        self.assertEqual(outside.read_text(encoding="ascii"), "{}\n")

    def test_open_directory_descriptor_survives_path_replacement(self):
        moved = Path(self.temporary.name) / "ledger-original"
        attacker = Path(self.temporary.name) / "attacker"
        self.root.rename(moved)
        attacker.mkdir()
        self.root.symlink_to(attacker, target_is_directory=True)

        record = self.arm()
        self.assertEqual(self.ledger.read(SESSION), record)
        self.assertTrue((moved / f"{SESSION}.json").is_file())
        self.assertFalse((attacker / f"{SESSION}.json").exists())

    def test_tampered_record_is_rejected(self):
        self.arm()
        path = self.root / f"{SESSION}.json"
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "unsafe ledger record"):
            self.ledger.read(SESSION)
        path.chmod(0o600)

        original = path.read_text(encoding="ascii")
        path.write_text(
            original.replace(
                f'"session":"{SESSION}"',
                f'"session":"{NEW_SESSION}"',
            ),
            encoding="ascii",
        )
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.ledger.read(SESSION)

    def test_duplicate_json_field_is_rejected(self):
        self.arm()
        path = self.root / f"{SESSION}.json"
        original = path.read_text(encoding="ascii")
        path.write_text(
            original.replace(
                '"state":"TRANSMITTED"',
                '"state":"TRANSMITTED","state":"TRANSMITTED"',
            ),
            encoding="ascii",
        )
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "duplicate ledger field"):
            self.ledger.read(SESSION)


if __name__ == "__main__":
    unittest.main(verbosity=2)
