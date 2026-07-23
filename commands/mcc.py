"""
commands/mcc.py
----------------
Handler for arena.exe's MCC command - CONFIRMED (runtime, 2026-07-23) to be
its registration handshake with the meta server, sent as:
    CLAUTH <arena name> <arena password> MCC <version>\r\n
(the GMCC component name found via disassembly matches this - "MCC" almost
certainly stands for something like "Meta Connect Command").

This handler records the registration into ArenaRegistry so it's visible
to commands/metaarenalist.py, but returns no response - the expected
response format (what makes arena.exe's own UI show anything past an
empty activity log) is still UNKNOWN. Sending a guessed response here
risks confusing arena.exe in ways we can't predict, unlike
metaarenalist.py's response, which is disclosed to the operator as an
active, isolated experiment.

arena.exe's own listening port isn't present in the MCC line itself -
9182 -> 31599 or whatever the meta server's own patched port is has no
bearing on it; arena.exe listens separately (CONFIRMED (disassembly):
port 7072 by default, see docs/protocol.md section 1). We don't have a
confirmed way to learn the real per-instance port from this command
alone, so we record the known default as a placeholder - it may be wrong
for a specific arena.exe instance that's been reconfigured.
"""

DEFAULT_ARENA_PORT = 7072  # CONFIRMED (disassembly) default only - see docstring above


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    registry = context["registry"]

    arena_name = client_info.get("username", "")
    entry = registry.register(
        name=arena_name,
        host_ip=client_info["ip"],
        arena_port=DEFAULT_ARENA_PORT,
    )
    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note=(
            f"MCC (arena registration) from arena.exe: name={arena_name!r}. "
            f"Recorded in ArenaRegistry (host_ip={entry.host_ip}, "
            f"arena_port={entry.arena_port} - default placeholder, not confirmed "
            f"per-instance). No response sent - expected MCC response format is UNKNOWN."
        ),
    )
    return None
