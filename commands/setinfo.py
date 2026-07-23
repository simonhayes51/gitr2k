"""
commands/setinfo.py
--------------------
Handler for arena.exe's SETINFO command - CONFIRMED (runtime, 2026-07-23):
sent bare on the same connection immediately after SETPORT:

    SETINFO <a> <b>\r\n

Observed values: "0 15". Field order (player_count then max_players) is
STRONG_INFERENCE from typical convention, not independently confirmed -
both observed numbers are consistent with either order for a freshly
started, empty arena. Treat player_count/max_players attribution as
tentative until a non-symmetric case is observed (e.g. players actually
in the arena).

Correlated back to the registry entry via context["arena_name"], set by
commands/mcc.py earlier on this same connection.
"""


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    registry = context["registry"]
    arena_name = context.get("arena_name")

    text = raw.decode("ascii", errors="replace").strip()
    parts = text.split()
    a = b = None
    if len(parts) >= 3:
        try:
            a = int(parts[1])
            b = int(parts[2])
        except ValueError:
            a = b = None

    if arena_name and a is not None and b is not None:
        registry.set_info(arena_name, player_count=a, max_players=b)

    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note=(
            f"SETINFO from arena.exe (name={arena_name!r}): raw={text!r}, "
            f"parsed=({a!r}, {b!r}) assumed (player_count, max_players) - "
            f"STRONG_INFERENCE, not confirmed field order. "
            + (
                f"Recorded in ArenaRegistry."
                if arena_name and a is not None and b is not None
                else "NOT recorded - missing arena_name in context or unparseable fields."
            )
        ),
    )
    return None
