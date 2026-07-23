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

EXPERIMENT #2 RESULT (2026-07-23): bare ENDARENALIST\r\n alone (empty
arena list) worked cleanly - no error, status just stayed at "retrieving
arena list" (no crash, no "an error has occured."). This confirms
ENDARENALIST alone is a valid terminator here, mirroring what we found
for RETRCOUNTRIES/ENDCOUNTRYLIST. The fault is specifically in the ARENA
line's own format.

EXPERIMENT #3 (now live): reintroduce a single ARENA line, but minimal -
just the name, no player/max-player fields - mirroring the exact
step-by-step approach that found COUNTRY's fix (name-only first, then
add fields back one at a time instead of guessing a whole shape at once).

    ARENA <name>\r\n
    ENDARENALIST\r\n

EXPERIMENT #3 RESULT (2026-07-23): "ARENA Test\r\n" (name only, zero
extra fields) ALSO produced "an error has occured." - same as experiment
#1's name+2-numbers attempt. This breaks the analogy with COUNTRY (where
name-alone failed but name+one-count-field succeeded): here, BOTH a bare
name and name+2 numbers fail, so it isn't simply "missing the trailing
players/maxplayers fields" the same way COUNTRY was missing its count.

EXPERIMENT #4 (now live): still working through the field-count ladder
systematically rather than jumping straight to a bigger hypothesis -
try name + a single trailing field (player_count only, no max_players),
exactly mirroring COUNTRY's one-extra-field fix, since that specific
combination hasn't been tried yet.

    ARENA <name> <player_count>\r\n
    ENDARENALIST\r\n

EXPERIMENT #4 RESULT (2026-07-23): "ARENA Test 0\r\nENDARENALIST\r\n"
(single trailing field) ALSO produced "an error has occured.". All
three field-count variants tried so far - name only, name+1, name+2 -
fail. This isn't converging the way COUNTRY's fix did; simply adding or
removing numeric fields doesn't seem to be the issue.

EXPERIMENT #5 (now live): pivot to a structurally different hypothesis
instead of continuing the field-count ladder. Unlike a country (just a
display label + count), an arena entry is something the client will
actually try to connect to - so it may need connection info (host/port)
as a structural requirement, not just more display fields. Testing:

    ARENA <name> <host_ip> <port>\r\n
    ENDARENALIST\r\n

Using the registry's recorded host_ip/arena_port for each arena (the
host_ip is Railway's internal proxy address as seen by the meta server,
e.g. 100.64.0.2 - not a real, externally-reachable address a player
could actually connect to; arena_port is a hardcoded placeholder,
7072, since MCC doesn't tell us the real one - so even if this shape is
right, the *values* will need fixing later. This test is purely about
whether the field count/shape is accepted at all.

EXPERIMENT #5 RESULT (2026-07-23): "ARENA Test 100.64.0.2 7072\r\n" also
produced "an error has occured.". Four variants down (name-only, +1,
+2, +host+port) - none work. This is no longer converging as a
field-count problem at all.

EXPERIMENT #6 (now live): new hypothesis - RETRARENALIST's response is a
flat list, not nested under a COUNTRY line the way our RETRCOUNTRIES
guess nested ARENA under COUNTRY conceptually. Maybe each ARENA line
needs to restate which country it belongs to, the same way COUNTRY
needed its own count field:

    ARENA <country> <name> <player_count> <max_players>\r\n
    ENDARENALIST\r\n

Known risks: if this also fails, it's worth stepping back from guessing
field combinations entirely and going back to static analysis - e.g.
checking whether there's a distinct property-name string (like "Status"
"Full" "Open") near ARENA in the binary we haven't looked for yet, since
five straight rejected guesses suggests we may be missing something
qualitatively different, not just a missing/reordered field.
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
            f"EXPERIMENT #6: ARENA <country> <name> <player_count> "
            f"<max_players> (restating the country per-arena, new "
            f"hypothesis after 4 straight rejections), plus ENDARENALIST "
            f"({len(arenas)} arena(s) registered - see docstring in "
            f"commands/retrarenalist.py)."
        ),
    )

    lines = []
    for arena in arenas:
        max_players = arena["max_players"] if arena["max_players"] is not None else 20
        lines.append(f"ARENA {country} {arena['name']} {arena['player_count']} {max_players}\r\n")
    lines.append("ENDARENALIST\r\n")
    return "".join(lines).encode("ascii", errors="replace")
