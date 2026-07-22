# GITR2K Meta Server — Preservation Project

An open, honest-by-design replacement meta server for **Get In The Ring 2000**
(GITR2000), a freeware wrestling simulation game from ~2000-2001 whose
original online infrastructure (`GETINTR2K.MINIDNS.NET`) is long gone.

This project's guiding rule: **compatibility over invention**. Nothing here
fabricates protocol behaviour. Every command handler logs and categorizes
traffic, but sends no response until that response has been confirmed by
either disassembly or, ideally, real runtime capture against the original
`gitr2k.exe` / `arena.exe` binaries. See `docs/protocol.md` for exactly
what's confirmed vs unknown, updated as evidence comes in.

## Project layout

```
server/
    main.py         entry point
    connection.py   per-client socket handling (never crashes, never disconnects first)
    protocol.py     known-token registry + safe dispatch (no fabricated responses)
    registry.py     in-memory arena registry (Phase 4)
    logger.py       structured capture writer + non-authoritative framing heuristics
commands/
    getnews.py
    metaarenalist.py
    sendchat.py
    challenge.py
    userenter.py
    ping.py
docs/
    protocol.md     living, evidence-graded protocol specification
captures/
    (created at runtime — one .log + one .jsonl per session)
```

## Running it

### Locally
```bash
python3 server/main.py --port 9182
```

### Online (always-on, no desktop install)
Two options, see the linked guides for full steps:

- **[docs/VPS_DEPLOY.md](docs/VPS_DEPLOY.md)** — recommended for now. Keeps
  the external port at exactly 9182, matching what's compiled into
  `gitr2k.exe`, so no client changes are needed.
- **[docs/RAILWAY_DEPLOY.md](docs/RAILWAY_DEPLOY.md)** — easier to set up,
  but Railway's TCP proxy assigns a random external port rather than
  9182, so the unmodified client can't reach it yet without either a
  client-side port patch (not yet confirmed/implemented) or falling back
  to the VPS approach for the client-facing connection.

Then, on the machine running the original client, add to
`C:\Windows\System32\drivers\etc\hosts`:

```
<this-machine-IP>   GETINTR2K.MINIDNS.NET
```

Launch `gitr2k.exe` (or `arena.exe`) and watch the console / `captures/`
directory for what it sends. The server will not respond to anything yet —
by design, until we've confirmed real responses (see `docs/protocol.md`).

## Contributing findings back

As real captures come in:
1. Add/update rows in `docs/protocol.md` §5 (recovered protocol table).
2. Only ever move a confidence marker from `STRONG INFERENCE`/`UNKNOWN` to
   `CONFIRMED (runtime)` when there's a corresponding file in `captures/`
   to point to.
3. Once a command's format is confirmed, update the matching file in
   `commands/` to construct and return the real response bytes instead of
   `None` — and update its docstring to reflect the new confidence level.

## License / status

Freeware game preservation project. Original game copyright 1999-2001 WCFC
Wrestling; this project reimplements only the network-facing server
component based on protocol analysis, for the purpose of keeping the
original client software usable.
