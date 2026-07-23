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

So this is EXPERIMENT #3: send only the bare terminator, no COUNTRY/
ARENA lines at all, to isolate whether the error comes from the
per-item line format specifically, or from something more basic (the
terminator itself, a missing count prefix, etc). One variable changed
at a time so the client's reaction stays informative.

    ENDCOUNTRYLIST\r\n   (nothing else)

Known risks with this guess: still no evidence either way about the
count/framing question above - this is a diagnostic probe, not a belief
that this is the real format.
"""


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    registry = context["registry"]
    arenas = registry.list_arenas()

    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note=(
            f"RETRCOUNTRIES request. Sending EXPERIMENT #3: bare ENDCOUNTRYLIST "
            f"only, no COUNTRY/ARENA lines, to isolate why experiment #2 "
            f"produced 'an error has occured.' ({len(arenas)} arena(s) "
            f"registered but deliberately omitted this round - see docstring "
            f"in commands/retrcountries.py)."
        ),
    )

    return b"ENDCOUNTRYLIST\r\n"
