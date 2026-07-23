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

GUESSED response shape (NOT confirmed, active experiment #2):
    COUNTRY <name>\r\n            (one per country)
    ARENA <name> <players> <maxplayers>\r\n   (per arena in that country)
    ENDCOUNTRYLIST\r\n

We have no real country data at all (arena.exe's MCC registration didn't
include one), so every registered arena is grouped under a single
placeholder country for this first test.

Known risks with this guess:
    - No evidence for whether ARENA lines nest directly under the
      preceding COUNTRY line (assumed here) or are listed some other way.
    - No evidence for whether a per-country ENDARENALIST is expected
      before the next COUNTRY line, or whether ENDCOUNTRYLIST alone
      terminates everything.
    - Placeholder country name ("International") is arbitrary.
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
            f"RETRCOUNTRIES request. Sending EXPERIMENTAL guessed response "
            f"with {len(arenas)} registered arena(s) grouped under a single "
            f"placeholder country - see docstring in commands/retrcountries.py."
        ),
    )

    lines = [f"COUNTRY {PLACEHOLDER_COUNTRY}\r\n"]
    for arena in arenas:
        max_players = arena["max_players"] if arena["max_players"] is not None else 20
        lines.append(f"ARENA {arena['name']} {arena['player_count']} {max_players}\r\n")
    lines.append("ENDCOUNTRYLIST\r\n")

    return "".join(lines).encode("ascii", errors="replace")
