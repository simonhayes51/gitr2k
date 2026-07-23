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

EXPERIMENT #1 RESULT (2026-07-23): "ARENA Test 0 20\r\nENDARENALIST\r\n"
produced "an error has occured." - same generic error as RETRCOUNTRIES's
early rejected attempts. Meanwhile RETRCOUNTRIES's own COUNTRY line is
confirmed solid (the "International" node with count 1 kept showing
correctly throughout). So the fault is specifically in this response,
not a regression elsewhere.

EXPERIMENT #2 (now live): apply the same isolation technique that found
RETRCOUNTRIES's fix - test with an EMPTY arena list first (bare
ENDARENALIST\r\n, no ARENA lines at all), to check whether the basic
framing/terminator is right before troubleshooting the ARENA line
format itself.

    ENDARENALIST\r\n   (nothing else)

Known risks: if this ALSO errors, ENDARENALIST might not actually be
this response's terminator at all (recall it was only ever an ASSUMED
pairing with METAARENALIST, never itself confirmed - METAARENALIST's
own response has never been validated by client reaction either, since
the client always moved on to RETRCOUNTRIES regardless of what
METAARENALIST got back). If it works cleanly, the next round should add
back a single ARENA line, probably needing an extra field the way
COUNTRY did (a host/port pair the client would need to actually connect
to the arena is a reasonable next guess, since nothing else in the
protocol so far carries that information).

We don't track which country an arena belongs to yet (only one
placeholder country exists at all, from commands/retrcountries.py), so
every registered arena would be returned regardless of the requested
country name, once ARENA lines are reintroduced.
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
            f"EXPERIMENT #2: bare ENDARENALIST only, no ARENA lines, to "
            f"isolate why experiment #1 produced 'an error has occured.' "
            f"({len(arenas)} arena(s) registered but deliberately omitted "
            f"this round - see docstring in commands/retrarenalist.py)."
        ),
    )

    return b"ENDARENALIST\r\n"
