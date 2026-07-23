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

EXPERIMENT #1 (2026-07-23) - CONFIRMED WORKING: arena.exe's "Start" button
had stayed permanently disabled and its activity log stayed empty across
every test up to this point, with no response ever sent to MCC. Static
analysis of arena.exe (going back to disassembly after RETRARENALIST
stalled) found the already-located but never-analyzed GMCC.OnArenaOwner
handler (docs/protocol.md section 4), plus two new string constants
clustered near it: "GRANTED" (7 bytes) and "OWNER" (5 bytes). Neither has
a traceable caller (same Delphi virtual-dispatch wall hit before), and
GRANTED has zero findable references anywhere in the binary at all
(possibly dead code) - but OWNER's trivial getter function IS referenced
once, suggesting it's actually used. "OnArenaOwner" as an event name
strongly suggested this is exactly the callback fired when the meta
server confirms an arena registration.

Sending a minimal guess - echoing the arena name back with OWNER as a
bare acknowledgment token:

    OWNER <arena name>\r\n

CONFIRMED (runtime, 2026-07-23): this real client reaction was observed -
arena.exe's activity log showed "connected" / "retrieving moves
database", and three brand-new bare follow-up commands appeared on the
same connection: SETPORT, SETINFO, REQMOVES (see commands/setport.py,
commands/setinfo.py, commands/reqmoves.py). This is now the confirmed
MCC acknowledgment format (or at least sufficient to unblock arena.exe's
registration flow - GRANTED was never tried since this worked on the
first attempt).

The three follow-up commands are bare (no CLAUTH envelope, no arena name
repeated), so this handler stashes arena_name into the shared per-
connection context dict for those later handlers to look up.
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

    # CONFIRMED (runtime, 2026-07-23): SETPORT/SETINFO/REQMOVES arrive bare
    # (no arena name repeated) on this same connection right after the
    # OWNER ack below. Stash the name here so those handlers can find the
    # right registry entry via this shared per-connection context dict.
    context["arena_name"] = arena_name

    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note=(
            f"MCC (arena registration) from arena.exe: name={arena_name!r}. "
            f"Recorded in ArenaRegistry (host_ip={entry.host_ip}, "
            f"arena_port={entry.arena_port} - default placeholder, will be "
            f"replaced by the real value once SETPORT arrives). Sending "
            f"CONFIRMED WORKING ack: 'OWNER {arena_name}' - see docstring in "
            f"commands/mcc.py."
        ),
    )
    return f"OWNER {arena_name}\r\n".encode("ascii", errors="replace")
