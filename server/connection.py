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

            # Best-effort categorization for the human reading the log.
            # This never raises - malformed/binary data is handled safely.
            try:
                response = dispatcher.dispatch(data, {"ip": ip, "port": port}, context)
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
            # If response is None (the current, honest default for every
            # command), we simply keep the socket open and wait for more
            # data - "keep sockets alive unless the client disconnects."
    finally:
        try:
            conn.close()
        except OSError:
            pass
