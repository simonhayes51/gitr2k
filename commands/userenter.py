"""
commands/userenter.py
-----------------------
Handler for the USERENTER token (and related USERLEAVE, confirmed to
exist in gitr2k.exe).

Confidence: token existence = CONFIRMED (disassembly). Direction and
payload are UNKNOWN.

STRONG INFERENCE: given the name and the presence of a paired USERLEAVE
token, this is very likely a server->client presence broadcast (telling
already-connected clients that a user joined/left), rather than something
the client sends about itself - but this has not been confirmed by
runtime capture, and the actual login/identification sequence that would
precede it (see docs/protocol.md "Login handler" - still UNKNOWN) hasn't
been found either.

TODO(runtime):
    - Confirm direction and trigger (does it fire on meta-server login,
      or on entering a specific arena/channel?).
    - Confirm payload: username only, or username + additional presence
      metadata (away status - AWAYSTAT token also confirmed to exist)?
"""


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note="Candidate USERENTER token detected. No response sent - payload/direction UNKNOWN, see TODO in this file.",
    )
    # TODO(runtime): once confirmed, implement real presence broadcast here.
    return None
