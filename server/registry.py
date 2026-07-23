"""
registry.py
-----------
In-memory registry of arena.exe instances that have registered themselves
with this meta server.

IMPORTANT: The actual registration command/format has NOT been confirmed
by runtime capture yet (see docs/protocol.md). This registry is deliberately
built around the fields we can reasonably expect an arena listing to need
(based on UI strings found in gitr2k.exe such as "Select Arena", and DFM
component names like ELTArenas), but the exact wire format used to populate
these fields is UNKNOWN until arena.exe's real registration traffic is
captured.

Do not wire this registry's data into a METAARENALIST response until the
real response format has been confirmed by runtime capture (see
commands/metaarenalist.py).
"""

import threading
import time


class ArenaEntry:
    def __init__(self, name: str, host_ip: str, arena_port: int):
        self.name = name
        self.host_ip = host_ip
        self.arena_port = arena_port
        self.player_count = 0          # TODO(runtime): confirm how this is reported/updated
        self.max_players = None        # TODO(runtime): confirm field and default
        self.status = "unknown"        # TODO(runtime): confirm status enum (open/full/in-fight/etc.)
        self.last_seen = time.time()

    def touch(self):
        self.last_seen = time.time()

    def to_dict(self):
        return {
            "name": self.name,
            "host_ip": self.host_ip,
            "arena_port": self.arena_port,
            "player_count": self.player_count,
            "max_players": self.max_players,
            "status": self.status,
            "last_seen": self.last_seen,
        }


class ArenaRegistry:
    """
    Thread-safe in-memory registry. No persistence yet - TODO(project):
    decide whether arenas should survive a meta-server restart, once we
    know how the real server behaved (also UNKNOWN).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._arenas = {}  # key: arena name -> ArenaEntry

    def register(self, name: str, host_ip: str, arena_port: int) -> ArenaEntry:
        """
        Keyed by name, not (host_ip, arena_port): CONFIRMED (runtime,
        2026-07-23) that arena.exe's outbound IP as seen by the meta
        server can differ between reconnects (Railway's internal proxy
        assigns a new source IP each time), which caused this to key
        every re-registration as a brand-new arena and produce visible
        duplicates in METAARENALIST responses. Name is the only stable
        identifier MCC actually gives us.
        """
        with self._lock:
            entry = self._arenas.get(name)
            if entry is None:
                entry = ArenaEntry(name, host_ip, arena_port)
                self._arenas[name] = entry
            else:
                entry.host_ip = host_ip
                entry.arena_port = arena_port
                entry.touch()
            return entry

    def unregister(self, name: str):
        with self._lock:
            self._arenas.pop(name, None)

    def list_arenas(self):
        with self._lock:
            return [e.to_dict() for e in self._arenas.values()]

    def prune_stale(self, max_age_seconds: int = 300):
        """
        TODO(runtime): confirm whether the real meta server expires arenas
        after inactivity, and after how long. 300s is a placeholder guess
        for hygiene only - it is NOT a confirmed protocol behaviour and
        should not be presented as such.
        """
        now = time.time()
        with self._lock:
            stale = [k for k, v in self._arenas.items() if now - v.last_seen > max_age_seconds]
            for k in stale:
                del self._arenas[k]
