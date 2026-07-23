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

STATIC ANALYSIS (2026-07-23, second pass) found a real class named
"TMovesDBCommand" in arena.exe (previously, "MOVESDB" had been wrongly
dismissed as an unrelated Pascal-scripting keyword - that was incorrect,
see docs/protocol.md's correction note). Disassembling its method
(arena.exe VA 0x461d34-0x461e92) showed it sends "REQMOVES", reads
exactly ONE response line via ReadLn("\r\n"), takes Copy(line, 1, 7),
and compares that against the literal "MOVESDB" via what looked at a
glance like a prefix/format check.

EXPERIMENT #1 (2026-07-23) - REJECTED, and the reasoning behind it was
backwards: sent a bare `MOVESDB\r\n`. Real client reaction: arena.exe's
activity log showed an explicit error - "Could not connect to main GITR
server, message follows: Exception: invalid response" - worse than the
prior silent "stuck on retrieving moves database" state, not better.

Re-examined the actual comparison helper at VA 0x404064 and confirmed
it's Delphi's `_LStrCmp` (byte-for-byte AnsiString equality, ending in a
sign-preserving `add eax,eax` on the length difference - a real `S1 = S2`
check, ZF=1 exactly when the strings are fully equal). The caller does
`je 0x461def` straight off that call with no intervening test - and
0x461def is the "invalid response" *raise* block, not the success path.
So the branch actually taken on an EXACT match to "MOVESDB" is the
EXCEPTION path - the opposite of the original (wrong) reading, which
assumed matching meant success. This cross-validates cleanly against
the real client reaction: our bare `MOVESDB\r\n` matched exactly and
triggered exactly the exception this corrected reading predicts.

CORRECTED UNDERSTANDING: the response must NOT begin with the exact
7-character sequence "MOVESDB", or arena.exe explicitly rejects it. The
non-exception path (VMT+0x9c, not yet disassembled) is what actually
receives and parses real "moves database" content - but what it expects
instead of "MOVESDB" is still completely UNKNOWN. Tracing further would
require locating and disassembling the concrete implementation behind
that virtual call (which needs identifying the actual VMT in the data
section, not just following a dynamic dispatch) - a substantially bigger
task than anything solved so far in this project (RETRCOUNTRIES/MCC were
one function each; this needs a second one plus VMT reconstruction).

Reverted to NOT sending a response for now (safer than an explicit,
worse-than-silence error) while this is discussed further - see the
"MOVESDB" token note in server/protocol.py and docs/protocol.md section
2/4/6 for the corrected, disclosed writeup.
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
            f"No response sent - EXPERIMENT #1 ('MOVESDB\\r\\n') was tried and "
            f"REJECTED (produced an explicit 'invalid response' exception, "
            f"confirmed by corrected disassembly to be the expected outcome "
            f"of an exact match to the literal 'MOVESDB'). Reverted to "
            f"observing only until the next experiment is designed. See "
            f"docstring in commands/reqmoves.py."
        ),
    )
    return None
