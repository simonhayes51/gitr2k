"""
commands/retrarenalist.py
--------------------------
Handler for RETRARENALIST - CONFIRMED (runtime, 2026-07-23) to be a
brand-new command, not previously known at all (not even as a compiled
string constant we'd noticed). gitr2k.exe sends it automatically right
after a successful RETRCOUNTRIES response, as a bare command (no CLAUTH
envelope) with the country name as its argument:

    RETRARENALIST <country name>\r\n

This confirms the real flow is a three-stage lazy hierarchy:
    METAARENALIST  -> (some ack/stub - still unconfirmed what it needs)
    RETRCOUNTRIES  -> COUNTRY <name> <arena_count>\r\n per country,
                      ENDCOUNTRYLIST\r\n (CONFIRMED working - see
                      commands/retrcountries.py experiment #5)
    RETRARENALIST <country> -> the actual per-arena details for that
                      one country, requested lazily (e.g. only once the
                      user expands that tree node)

GUESSED response shape (NOT confirmed, active experiment #1 for this
command): reuses ARENA (already a known token, used in the RETRCOUNTRIES
guess) and ENDARENALIST (already CONFIRMED to exist, previously assumed
to terminate METAARENALIST's response) as this request's terminator -
a country-scoped list is still fundamentally "a list of arenas", so
reusing that pairing is a reasonable first guess:

    ARENA <name> <player_count> <max_players>\r\n   (per arena)
    ENDARENALIST\r\n

We don't track which country an arena belongs to yet (only one
placeholder country exists at all, from commands/retrcountries.py), so
every registered arena is returned regardless of the requested country
name for this first test.
"""


def parse_country_arg(raw: bytes) -> str:
    text = raw.decode("ascii", errors="replace")
    line = text.split("\r\n", 1)[0].split("\n", 1)[0]
    parts = line.split(" ", 1)
    return parts[1] if len(parts) > 1 else ""


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    registry = context["registry"]
    country = parse_country_arg(raw)
    arenas = registry.list_arenas()

    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note=(
            f"RETRARENALIST request for country={country!r}. Sending "
            f"EXPERIMENTAL guessed response with {len(arenas)} registered "
            f"arena(s) (country filtering not implemented yet - see "
            f"docstring in commands/retrarenalist.py)."
        ),
    )

    lines = []
    for arena in arenas:
        max_players = arena["max_players"] if arena["max_players"] is not None else 20
        lines.append(f"ARENA {arena['name']} {arena['player_count']} {max_players}\r\n")
    lines.append("ENDARENALIST\r\n")

    return "".join(lines).encode("ascii", errors="replace")
