"""
commands/setport.py
--------------------
Handler for arena.exe's SETPORT command - CONFIRMED (runtime, 2026-07-23):
sent bare (no CLAUTH envelope, no arena name) on the same connection
immediately after arena.exe receives the MCC/OWNER acknowledgment:

    SETPORT <port>\r\n

Observed value: 7072, matching the CONFIRMED (disassembly) default arena
listening port - so this is arena.exe self-reporting its real listening
port, replacing the DEFAULT_ARENA_PORT placeholder that commands/mcc.py
recorded at registration time.

Since this command doesn't repeat the arena name, it's correlated back to
the right registry entry via context["arena_name"], set by commands/mcc.py
earlier on this same connection.

No response is sent - not confirmed whether arena.exe expects one, and
sending nothing hasn't broken anything observed so far.
"""


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    registry = context["registry"]
    arena_name = context.get("arena_name")

    text = raw.decode("ascii", errors="replace").strip()
    parts = text.split()
    port = None
    if len(parts) >= 2:
        try:
            port = int(parts[1])
        except ValueError:
            port = None

    if arena_name and port is not None:
        registry.set_port(arena_name, port)

    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note=(
            f"SETPORT from arena.exe (name={arena_name!r}): raw={text!r}, "
            f"parsed_port={port!r}. "
            + (
                f"Recorded in ArenaRegistry."
                if arena_name and port is not None
                else "NOT recorded - missing arena_name in context or unparseable port."
            )
        ),
    )
    return None
