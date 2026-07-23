"""
commands/metaarenalist.py
--------------------------
Handler for the METAARENALIST token - arguably the most important command
for Phase 4 (arena support), since this is what lets the client discover
player-hosted arenas.

Confidence: CONFIRMED (runtime, 2026-07-23) that gitr2k.exe sends
    CLAUTH <username> <password> METAARENALIST <version>\r\n
when the "Select Arena" dialog opens (see docs/protocol.md section 3,
captures/2026-07-23_first_real_capture.txt). ENDARENALIST is CONFIRMED
(disassembly) to exist as a related token.

Everything about the RESPONSE below is an ACTIVE, DISCLOSED EXPERIMENT,
not a confirmed format - static disassembly hit a wall (the string is
returned by a trivial getter function with no traceable direct callers,
implying it's invoked through a Delphi VMT/virtual-dispatch slot that
objdump/radare2 can't follow without Delphi-RTTI-aware tooling we don't
have). Rather than stall indefinitely, this handler sends a first-guess
response, informed by the GETNEWS/GITRNEWS/ENDNEWSLIST naming pattern
(command name echoed per-item, explicit end token), and the operator
observes how the real client reacts. If the "Select Arena" dialog
actually populates, that's empirical (runtime) confirmation of this
shape - if not, we learn something and adjust.

GUESSED response shape (NOT confirmed):
    METAARENALIST <name> <player_count> <max_players>\r\n   (one per arena)
    ENDARENALIST\r\n

Known risks with this guess:
    - Delimiter assumed to be a single space, matching CLAUTH's confirmed
      framing - but arena names containing spaces would break this. Only
      tested so far with the single-word arena name "Test".
    - No evidence at all for whether "METAARENALIST" needs to prefix each
      line, whether a country/region grouping field is expected (the
      "Select Arena" dialog's status text said "retrieving country
      list"), or whether max_players is even part of this message.
"""

DEFAULT_MAX_PLAYERS = 20  # no evidence for this number at all - pure placeholder


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    registry = context["registry"]
    arenas = registry.list_arenas()

    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note=(
            f"METAARENALIST request. Sending EXPERIMENTAL guessed response "
            f"with {len(arenas)} registered arena(s) - see docstring in "
            f"commands/metaarenalist.py. Not a confirmed format."
        ),
    )

    lines = []
    for arena in arenas:
        max_players = arena["max_players"] if arena["max_players"] is not None else DEFAULT_MAX_PLAYERS
        lines.append(f"METAARENALIST {arena['name']} {arena['player_count']} {max_players}\r\n")
    lines.append("ENDARENALIST\r\n")

    return "".join(lines).encode("ascii", errors="replace")
