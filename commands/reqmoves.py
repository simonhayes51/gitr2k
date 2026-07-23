"""
commands/reqmoves.py
---------------------
Handler for arena.exe's REQMOVES command - CONFIRMED (runtime, 2026-07-23):
sent bare, with no arguments, on the same connection immediately after
SETINFO:

    REQMOVES\r\n

Matches arena.exe's "retrieving moves database" UI status text observed
right after the MCC/OWNER handshake succeeded, so this is almost certainly
arena.exe asking the meta server for some kind of moves/moveset database.

Response format is completely UNKNOWN. Deliberately NOT guessing a
response yet - per the project's isolate-one-variable-at-a-time
methodology (see RETRCOUNTRIES/RETRARENALIST history in docs/protocol.md),
we log and observe first: does arena.exe retry REQMOVES if unanswered
(like BOGUS did)? Does its UI get stuck on "retrieving moves database"
forever, or does the "Start" button eventually enable anyway? That
evidence should drive the first real experiment here, rather than
guessing blind.
"""


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    arena_name = context.get("arena_name")

    text = raw.decode("ascii", errors="replace").strip()

    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note=(
            f"REQMOVES from arena.exe (name={arena_name!r}): raw={text!r}. "
            f"No response sent - format UNKNOWN, deliberately observing only. "
            f"See docstring in commands/reqmoves.py."
        ),
    )
    return None
