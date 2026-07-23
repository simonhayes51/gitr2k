"""
commands/retrcountries.py
--------------------------
Handler for RETRCOUNTRIES - CONFIRMED (runtime, 2026-07-23) to be sent by
gitr2k.exe immediately after a METAARENALIST response, on the SAME
connection, as a BARE command with no CLAUTH envelope (the envelope only
wraps the first message per connection - see docs/protocol.md section 3).
This is what the "Select Arena" dialog's "retrieving country list" status
text is actually waiting on; our METAARENALIST guess alone didn't satisfy
it, and the client disconnected ~10s later after getting no reply here.

CONFIRMED (disassembly, found while investigating this capture): the
same string-constant table that holds METAARENALIST/ENDARENALIST also
contains COUNTRY, ARENA, and ENDCOUNTRYLIST as compiled literals in
gitr2k.exe. These give real anchors for a response guess, unlike the
METAARENALIST response, which had none.

EXPERIMENT #2 RESULT (2026-07-23): the COUNTRY/ARENA/ENDCOUNTRYLIST guess
above got as far as the client actually processing it - but the "Select
Arena" dialog then showed "an error has occured." (a real, generic
Delphi error-display string found in the binary) instead of populating.
Static disassembly hit the same VMT-dispatch wall as METAARENALIST (an
exhaustive scan of every CALL rel32 in gitr2k.exe's code section found
zero direct call sites to either the METAARENALIST getter or this error
string's setter function - both are only reachable through Delphi
virtual dispatch, untraceable without Delphi-RTTI-aware tooling).

EXPERIMENT #3 RESULT (2026-07-23): bare ENDCOUNTRYLIST\r\n alone (no
COUNTRY/ARENA lines) worked cleanly - the "Select Arena" dialog showed
its normal "No arenas online. Start own arena server?" prompt instead of
an error. This isolates the problem precisely: the basic framing/
terminator is fine; something about the per-item COUNTRY/ARENA line
format specifically is what experiment #2 got wrong.

EXPERIMENT #4 (now live): add back just a bare COUNTRY line, still with
zero ARENA lines under it, to check whether the COUNTRY line itself is
fine on its own and the problem is isolated to ARENA lines specifically.

    COUNTRY <name>\r\n
    ENDCOUNTRYLIST\r\n

Known risks with this guess: if this also errors, the problem is in
COUNTRY's own format (or in having any non-empty list at all). If it
works cleanly, the next round should test adding a single ARENA line
back in.
"""

PLACEHOLDER_COUNTRY = "International"


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    registry = context["registry"]
    arenas = registry.list_arenas()

    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note=(
            f"RETRCOUNTRIES request. Sending EXPERIMENT #4: bare COUNTRY line "
            f"plus ENDCOUNTRYLIST, still no ARENA lines, to isolate whether "
            f"COUNTRY itself is fine on its own ({len(arenas)} arena(s) "
            f"registered but deliberately omitted this round - see docstring "
            f"in commands/retrcountries.py)."
        ),
    )

    return f"COUNTRY {PLACEHOLDER_COUNTRY}\r\nENDCOUNTRYLIST\r\n".encode("ascii", errors="replace")
