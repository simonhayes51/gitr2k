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

EXPERIMENT #4 RESULT (2026-07-23): a bare COUNTRY line with zero ARENA
lines under it ("COUNTRY International\r\nENDCOUNTRYLIST\r\n") ALSO
produced "an error has occured." - same as experiment #2. Combined with
experiment #3 (empty list works), this narrows the fault precisely to
the COUNTRY line's own format, not anything ARENA-specific.

EXPERIMENT #5 (now live): COUNTRY with no other fields is what breaks;
ARENA lines carry trailing numeric fields (players/max), so guessing
COUNTRY is missing a trailing count field of its own (e.g. how many
arenas follow, letting the client pre-size something before reading
them) - a missing integer field is a classic cause of this kind of
generic index/parse error.

    COUNTRY <name> <arena_count>\r\n
    ENDCOUNTRYLIST\r\n

Known risks with this guess: still just a guess at which field is
missing and where; if this also errors, the next round should try
other candidate fields (a country code/ID instead of/alongside the
name, a different field order, etc).
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
            f"RETRCOUNTRIES request. Sending EXPERIMENT #5: COUNTRY line with "
            f"a trailing arena-count field added, plus ENDCOUNTRYLIST, still "
            f"no ARENA lines, to test whether COUNTRY needs a count field "
            f"({len(arenas)} arena(s) registered - count reflected below, "
            f"lines still omitted - see docstring in commands/retrcountries.py)."
        ),
    )

    return f"COUNTRY {PLACEHOLDER_COUNTRY} {len(arenas)}\r\nENDCOUNTRYLIST\r\n".encode("ascii", errors="replace")
