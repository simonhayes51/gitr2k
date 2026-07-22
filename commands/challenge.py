"""
commands/challenge.py
----------------------
Handler for the CHALLENGE token (and related DENYCHALLENGE, confirmed to
exist in gitr2k.exe).

Confidence: token existence = CONFIRMED (disassembly). This almost
certainly relates to the Op1Client/Op2Client ("Operator 1/2") connections
identified during earlier static analysis of gitr2k.exe's main form,
which had Port=0 as a compiled default (STRONG INFERENCE: assigned at
runtime rather than fixed) - consistent with a challenge/matchmaking flow
that hands out a dynamic port for the actual fight connection. This is
still inference, not confirmed wiring.

TODO(runtime):
    - Confirm whether CHALLENGE is client->server (challenging another
      user) or server->client (notifying a user they've been challenged).
    - Confirm the argument(s): target username? arena id? fight type
      (FIGHTTYPE token also confirmed to exist in arena.exe)?
    - Confirm what a challenge acceptance vs DENYCHALLENGE looks like on
      the wire, and how/whether a dynamic port (per the Op1/Op2Client
      inference above) gets communicated to the client.
"""


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note="Candidate CHALLENGE token detected. No response sent - flow UNKNOWN, see TODO in this file.",
    )
    # TODO(runtime): once confirmed, implement the real challenge flow here.
    return None
