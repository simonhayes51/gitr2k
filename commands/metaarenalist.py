"""
commands/metaarenalist.py
--------------------------
Handler for the METAARENALIST token - arguably the most important command
for Phase 4 (arena support), since this is what lets the client discover
player-hosted arenas.

Confidence: token existence = CONFIRMED (disassembly) - found exactly once
in gitr2k.exe as a compiled string constant. The handler function that
parses/sends it has NOT yet been located in either binary (see
docs/protocol.md, section on GMCCMetaMessage - that function handles
BASECHAT/METAMSG, not this token).

Everything below is UNKNOWN until confirmed by runtime capture:
    - Whether the client sends bare "METAARENALIST" to request the list,
      or whether it's purely a server->client push token.
    - Whether ENDARENALIST (also CONFIRMED to exist in the binary)
      terminates a list of per-arena lines, each prefixed METAARENALIST,
      similar to the GETNEWS/GITRNEWS/ENDNEWSLIST pattern - this is a
      STRONG INFERENCE by symmetry with that naming pattern, not proof.
    - The exact fields per arena line and their delimiter. registry.py's
      ArenaEntry fields (name, host_ip, arena_port, player_count,
      max_players, status) are a reasonable guess at what's needed, based
      on the "Select Arena" UI list columns implied by the ELTArenas
      tree-list component in gitr2k.exe's main form - but the wire
      encoding of those fields is UNKNOWN.

DO NOT wire ArenaRegistry data into a fabricated response here until the
real format is confirmed. Doing so would violate the project's explicit
"do not invent packets" rule.
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
            f"Candidate METAARENALIST token detected. "
            f"{len(arenas)} arena(s) currently in registry, but NOT sent - "
            f"response format UNKNOWN, see TODO in this file."
        ),
    )
    # TODO(runtime): once the real METAARENALIST response format is
    # confirmed (delimiter, per-arena field order, ENDARENALIST framing),
    # serialize `arenas` (from registry.list_arenas()) into that exact
    # format and return it here.
    return None
