"""
commands/reqmoves.py
---------------------
Handler for arena.exe's REQMOVES command - CONFIRMED (runtime, 2026-07-23):
sent bare, with no arguments, on the same connection immediately after
SETINFO:

    REQMOVES\r\n

Matches arena.exe's "retrieving moves database" UI status text observed
right after the MCC/OWNER handshake succeeded.

A framing bug in server/connection.py previously caused this command to
be silently dropped (coalesced with SETINFO in the same recv() - see
docs/protocol.md section 3) whenever the server only observed/logged it
without responding. Now fixed, and confirmed to reach this handler
correctly.

STATIC ANALYSIS (2026-07-23, second pass after MCC/OWNER breakthrough):
went back to disassembly for REQMOVES specifically, since the earlier
dismissal of "MOVESDB" as an unrelated Pascal-scripting keyword
(alongside BEGIN/WHILE/FUNC/SCRIPT/PLUGIN/ACTIONSDB/SWEARDB) turns out to
have been WRONG - a real class named "TMovesDBCommand" was found in
arena.exe's string-constant table, directly adjacent to the "REQMOVES"
and "MOVESDB" literals, plus an "invalid response" (16 bytes) error
string. This is a genuine command-handler class, not a scripting keyword
collision. A near-identical sibling class exists for "REQSWLIST" /
"SWEARDB" (likely a swear-word filter list) with the same code shape,
confirming this is a family of near-identical "request a named database"
command classes, not a one-off.

Disassembling TMovesDBCommand's method (arena.exe VA 0x461d34-0x461e92)
gives real, disclosed evidence about the expected response shape:

1. It sends "REQMOVES" via a virtual call (VMT+0x84) - matches what we
   already observed on the wire.
2. It then calls a single ReadLn-shaped virtual method (VMT+0x74) with
   terminator "\r\n" - reads exactly ONE line from the socket. There is
   no loop back to read further lines, unlike RETRCOUNTRIES/
   RETRARENALIST's multi-line + terminator-token responses. STRONG
   INFERENCE: the REQMOVES response is a single line, not a
   list-with-terminator shape.
3. It takes Copy(received_line, 1, 7) - the first 7 characters - and
   compares that substring against the literal "MOVESDB" (also 7 chars).
   If it does NOT match, it raises/logs the "invalid response" exception
   found in the string table. CONFIRMED (disassembly): the response line
   MUST begin with the literal 7-character prefix "MOVESDB".
4. If the prefix matches, the ENTIRE line (not just the remainder after
   the prefix) is handed to a further virtual method (VMT+0x9c) for
   parsing - that method's body wasn't disassembled this pass, so the
   exact fields expected after "MOVESDB" remain UNKNOWN.

EXPERIMENT #1 (2026-07-23): send the minimal possible response that
satisfies the confirmed prefix check - a bare line with nothing after
the prefix:

    MOVESDB\r\n

This mirrors the project's established isolate-one-variable-at-a-time
methodology (the same approach that eventually cracked RETRCOUNTRIES):
start minimal, then add fields one at a time based on the real reaction.
If arena.exe still shows an internal error or stays stuck on "retrieving
moves database", the next step is watching whether it retries (like
BOGUS did) and/or adding a trailing count field (e.g. "MOVESDB 0\r\n"),
following the same COUNTRY/METAARENALIST naming convention used
elsewhere in this protocol.

Known risk: unlike RETRCOUNTRIES/METAARENALIST, this response format is
grounded in real disassembly (not pure guesswork) for the prefix, but the
payload shape past the prefix is still unconfirmed - this is a genuine,
disclosed experiment, not a settled format.
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
            f"Sending EXPERIMENT #1: bare 'MOVESDB\\r\\n' - the 7-char 'MOVESDB' "
            f"prefix is CONFIRMED (disassembly) required by arena.exe's "
            f"TMovesDBCommand handler; payload past the prefix is still an "
            f"open, disclosed guess. See docstring in commands/reqmoves.py."
        ),
    )
    return b"MOVESDB\r\n"
