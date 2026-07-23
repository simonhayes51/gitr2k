"""
connection.py
-------------
Per-client connection handling.

Design goals (per project requirements):
- Never crash on malformed data - all parsing is defensive.
- Never disconnect the client ourselves; only stop when the client
  disconnects or the socket errors out.
- Never send fabricated bytes back to the client. We only send a response
  if a command handler explicitly returns one, and right now none do,
  because no response has been CONFIRMED (runtime) yet. This keeps the
  server 100% passive/observational until we have real evidence, exactly
  as requested ("do not invent packets").
"""

import socket


def handle_client(conn: socket.socket, addr, logger, dispatcher, registry):
    ip, port = addr
    logger.event("CONNECT", ip=ip, port=port)
    context = {"registry": registry, "logger": logger}

    # CONFIRMED (runtime, 2026-07-23): a single recv() can contain more than
    # one \r\n-terminated command - observed directly when arena.exe sent
    # "SETINFO 0 15\r\nREQMOVES\r\n" as one TCP segment. dispatch() only
    # looks at the first token of whatever bytes it's given, so passing the
    # whole multi-line chunk through unsplit silently dropped REQMOVES
    # entirely - it was never dispatched or logged as COMMAND_SEEN. Buffer
    # incoming bytes and split on line boundaries before dispatching, so
    # every command gets its own dispatch() call regardless of how the
    # client happened to batch them on the wire.
    buffer = b""

    try:
        while True:
            try:
                data = conn.recv(4096)
            except ConnectionResetError:
                logger.event("RESET", ip=ip, port=port, note="connection reset by peer")
                return
            except OSError as e:
                logger.event("ERROR", ip=ip, port=port, note=str(e))
                return

            if not data:
                logger.event("DISCONNECT", ip=ip, port=port)
                return

            # Always log the raw packet first, unconditionally, before any
            # attempt at interpretation - this is our ground truth record.
            logger.packet("RECV", ip, port, data)

            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                raw_line = line + b"\n"

                # Best-effort categorization for the human reading the log.
                # This never raises - malformed/binary data is handled safely.
                try:
                    response = dispatcher.dispatch(raw_line, {"ip": ip, "port": port}, context)
                except Exception as e:  # noqa: BLE001 - deliberately broad: must never crash the server
                    logger.event("HANDLER_ERROR", ip=ip, port=port, note=repr(e))
                    response = None

                if response:
                    try:
                        conn.sendall(response)
                        logger.packet("SEND", ip, port, response)
                    except OSError as e:
                        logger.event("SEND_ERROR", ip=ip, port=port, note=str(e))
                        return
                # If response is None (the current, honest default for most
                # commands), we simply keep the socket open and wait for more
                # data - "keep sockets alive unless the client disconnects."
    finally:
        try:
            conn.close()
        except OSError:
            pass
