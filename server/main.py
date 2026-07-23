#!/usr/bin/env python3
"""
main.py
-------
Entry point for the GITR2000 meta-server replacement.

This server is intentionally passive/observational by default: it accepts
connections on the confirmed meta-server port (9182), logs everything it
receives, does best-effort (non-authoritative) categorization of any
recognized command tokens, and does NOT send any fabricated responses -
because no responses have been confirmed by runtime capture yet.

See docs/protocol.md for the living, evidence-graded protocol
specification, and captures/ for recorded traffic once you run this
against the real gitr2k.exe / arena.exe.

Usage:
    python3 -m server.main [--port 9182] [--bind 0.0.0.0]

Then redirect the client via the Windows HOSTS file:
    <this-machine-IP>   GETINTR2K.MINIDNS.NET
"""

import argparse
import socket
import sys
import threading

# Support running both as `python3 server/main.py` and `python3 -m server.main`
try:
    from . import connection, protocol, registry, logger as logger_module
except ImportError:  # running as a plain script, not a package
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from server import connection, protocol, registry, logger as logger_module

# Import command handlers
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
from commands import getnews, metaarenalist, sendchat, challenge, userenter, ping, mcc, retrcountries


def build_dispatcher() -> protocol.Dispatcher:
    d = protocol.Dispatcher()
    d.register("GETNEWS", getnews.handle)
    d.register("GITRNEWS", getnews.handle)
    d.register("METAARENALIST", metaarenalist.handle)
    d.register("RETRCOUNTRIES", retrcountries.handle)
    d.register("SENDCHAT", sendchat.handle)
    d.register("CHALLENGE", challenge.handle)
    d.register("USERENTER", userenter.handle)
    d.register("PINGECHO", ping.handle)
    d.register("PING", ping.handle)
    d.register("MCC", mcc.handle)
    return d


def main():
    ap = argparse.ArgumentParser(description="GITR2000 meta-server replacement (observational mode)")
    ap.add_argument("--port", type=int, default=9182,
                     help="Meta server port. 9182 is CONFIRMED (disassembly) as the port both "
                          "gitr2k.exe and arena.exe use to connect to GETINTR2K.MINIDNS.NET.")
    ap.add_argument("--bind", default="0.0.0.0")
    args = ap.parse_args()

    cap_logger = logger_module.CaptureLogger()
    arena_registry = registry.ArenaRegistry()
    dispatcher = build_dispatcher()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.bind, args.port))
    srv.listen(100)

    cap_logger.event(
        "SERVER_LISTENING",
        note=f"Listening on {args.bind}:{args.port}. Logs: {cap_logger.text_path} / {cap_logger.jsonl_path}",
    )
    cap_logger.event(
        "REMINDER",
        note="This server does not send any responses yet - it only observes and logs. "
             "See docs/protocol.md for what's confirmed vs unknown.",
    )

    try:
        while True:
            conn, addr = srv.accept()
            t = threading.Thread(
                target=connection.handle_client,
                args=(conn, addr, cap_logger, dispatcher, arena_registry),
                daemon=True,
            )
            t.start()
    except KeyboardInterrupt:
        cap_logger.event("SERVER_SHUTDOWN", note="Ctrl+C received.")
        cap_logger.close()
        srv.close()
        sys.exit(0)


if __name__ == "__main__":
    main()
