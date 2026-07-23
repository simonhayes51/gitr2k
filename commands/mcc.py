"""
commands/mcc.py
----------------
Handler for arena.exe's MCC command - CONFIRMED (runtime, 2026-07-23) to be
its registration handshake with the meta server, sent as:
    CLAUTH <arena name> <arena password> MCC <version>\r\n
(the GMCC component name found via disassembly matches this - "MCC" almost
certainly stands for something like "Meta Connect Command").

This handler records the registration into ArenaRegistry so it's visible
to commands/metaarenalist.py.

arena.exe's own listening port isn't present in the MCC line itself -
9182 -> 31599 or whatever the meta server's own patched port is has no
bearing on it; arena.exe listens separately (CONFIRMED (disassembly):
port 7072 by default, see docs/protocol.md section 1). We don't have a
confirmed way to learn the real per-instance port from this command
alone, so we record the known default as a placeholder - it may be wrong
for a specific arena.exe instance that's been reconfigured.

EXPERIMENT #1 (2026-07-23): arena.exe's "Start" button stays permanently
disabled and its activity log stays empty across every test so far, with
no response ever sent to MCC. Static analysis of arena.exe (going back
to disassembly after RETRARENALIST stalled) found the already-located
but never-analyzed GMCC.OnArenaOwner handler (docs/protocol.md section
4), plus two new string constants clustered near it: "GRANTED" (7 bytes)
and "OWNER" (5 bytes). Neither has a traceable caller (same Delphi
virtual-dispatch wall hit before), and GRANTED has zero findable
references anywhere in the binary at all (possibly dead code) - but
OWNER's trivial getter function IS referenced once, suggesting it's
actually used. "OnArenaOwner" as an event name strongly suggests this is
exactly the callback fired when the meta server confirms an arena
registration.

Testing a minimal guess: echo the arena name back with OWNER as a bare
acknowledgment token:

    OWNER <arena name>\r\n

Known risks: this is a genuine guess informed by real (but caller-less)
tokens, not a confirmed format. If it does nothing, worth trying GRANTED
instead, or a combined shape (e.g. "GRANTED OWNER <name>\r\n"), or
reconsidering whether the ack lives on a completely different event
we haven't looked at yet.
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
            f"per-instance). Sending EXPERIMENT #1: 'OWNER {arena_name}' - see "
            f"docstring in commands/mcc.py. Not a confirmed format."
        ),
    )
    return f"OWNER {arena_name}\r\n".encode("ascii", errors="replace")
