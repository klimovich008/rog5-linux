"""Reference model for the ROG5 stable recovery control protocol."""

from .reference import (
    EMPTY_BODY_SHA256,
    ZERO_ID,
    FrameParser,
    HostIntentLedger,
    InjectedCrash,
    ProtocolViolation,
    RecoveryModel,
    RecoveryState,
    Request,
    Response,
    TargetDeparted,
    decode_request,
    decode_response,
    encode_frame,
    encode_request,
    encode_response,
)

__all__ = [
    "EMPTY_BODY_SHA256",
    "ZERO_ID",
    "FrameParser",
    "HostIntentLedger",
    "InjectedCrash",
    "ProtocolViolation",
    "RecoveryModel",
    "RecoveryState",
    "Request",
    "Response",
    "TargetDeparted",
    "decode_request",
    "decode_response",
    "encode_frame",
    "encode_request",
    "encode_response",
]
