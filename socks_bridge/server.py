"""SOCKS4/4a/5 -> GITR2000 meta server bridge.

Why this exists: gitr2k.exe/arena.exe have GETINTR2K.MINIDNS.NET:9182
compiled in, and redirecting that normally means editing the local HOSTS
file - which needs admin rights the client machine might not have. Both
apps *do* expose a real Proxy setting in their own GUI (settings.UseProxy /
ProxyHost / ProxyPort - confirmed by inspecting the client binaries),
which is an ordinary user-level preference, no elevation needed.

This bridge speaks just enough SOCKS4/4a/5 to satisfy that proxy setting,
then ignores whatever destination the client actually asked for and
always connects on to the real meta server (META_HOST/META_PORT below).
It's a dumb byte-relay after the handshake - no protocol awareness of
GITR2000 itself.

We don't have a copy of the real client to test the handshake against,
so this supports all three SOCKS variants the "SocksInfo.Version" field
in the binary suggests (svSocks4/svSocks4A/svSocks5) to maximize the
odds one of them just works. Watch the logs for which VER byte shows up.
"""

import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("socks_bridge")

META_HOST = os.environ.get("META_HOST", "sakura.proxy.rlwy.net")
META_PORT = int(os.environ.get("META_PORT", "31599"))
LISTEN_PORT = int(os.environ.get("PORT", "1080"))


async def relay(src, dst, label):
    try:
        while True:
            data = await src.read(4096)
            if not data:
                break
            dst.write(data)
            await dst.drain()
    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        dst.close()


async def connect_to_meta():
    log.info("connecting onward to meta server at %s:%s", META_HOST, META_PORT)
    return await asyncio.open_connection(META_HOST, META_PORT)


async def handle_socks5(reader, writer, first_byte):
    nmethods = (await reader.readexactly(1))[0]
    methods = await reader.readexactly(nmethods)
    log.info("SOCKS5 greeting, methods offered: %s", list(methods))
    # We don't implement username/password auth - always offer "no auth".
    writer.write(bytes([0x05, 0x00]))
    await writer.drain()

    header = await reader.readexactly(4)
    ver, cmd, _rsv, atyp = header
    if atyp == 0x01:  # IPv4
        dest = await reader.readexactly(4)
        dest_repr = ".".join(str(b) for b in dest)
    elif atyp == 0x03:  # domain name
        length = (await reader.readexactly(1))[0]
        dest = await reader.readexactly(length)
        dest_repr = dest.decode("latin-1", errors="replace")
    elif atyp == 0x04:  # IPv6
        dest = await reader.readexactly(16)
        dest_repr = dest.hex()
    else:
        log.warning("SOCKS5 unknown ATYP %s, aborting", atyp)
        writer.close()
        return
    port_bytes = await reader.readexactly(2)
    port = int.from_bytes(port_bytes, "big")
    log.info("SOCKS5 CONNECT requested for %s:%s (cmd=%s) - ignoring, forwarding to meta server", dest_repr, port, cmd)

    try:
        meta_reader, meta_writer = await connect_to_meta()
    except OSError as exc:
        log.error("could not reach meta server: %s", exc)
        writer.write(bytes([0x05, 0x01, 0x00, 0x01, 0, 0, 0, 0, 0, 0]))
        await writer.drain()
        writer.close()
        return

    writer.write(bytes([0x05, 0x00, 0x00, 0x01, 0, 0, 0, 0, 0, 0]))
    await writer.drain()

    await asyncio.gather(
        relay(reader, meta_writer, "client->meta"),
        relay(meta_reader, writer, "meta->client"),
    )


async def handle_socks4(reader, writer, first_byte):
    header = await reader.readexactly(7)
    cmd = header[0]
    port = int.from_bytes(header[1:3], "big")
    ip_bytes = header[3:7]
    is_socks4a = ip_bytes[0:3] == b"\x00\x00\x00" and ip_bytes[3] != 0

    userid = b""
    while True:
        b = await reader.readexactly(1)
        if b == b"\x00":
            break
        userid += b

    dest_repr = ".".join(str(b) for b in ip_bytes)
    if is_socks4a:
        domain = b""
        while True:
            b = await reader.readexactly(1)
            if b == b"\x00":
                break
            domain += b
        dest_repr = domain.decode("latin-1", errors="replace")

    log.info("SOCKS4%s CONNECT requested for %s:%s (cmd=%s, userid=%r) - ignoring, forwarding to meta server",
              "a" if is_socks4a else "", dest_repr, port, cmd, userid)

    try:
        meta_reader, meta_writer = await connect_to_meta()
    except OSError as exc:
        log.error("could not reach meta server: %s", exc)
        writer.write(bytes([0x00, 0x5B, 0, 0, 0, 0, 0, 0]))
        await writer.drain()
        writer.close()
        return

    writer.write(bytes([0x00, 0x5A, 0, 0, 0, 0, 0, 0]))
    await writer.drain()

    await asyncio.gather(
        relay(reader, meta_writer, "client->meta"),
        relay(meta_reader, writer, "meta->client"),
    )


async def handle_connection(reader, writer):
    peer = writer.get_extra_info("peername")
    try:
        first_byte = await reader.readexactly(1)
    except asyncio.IncompleteReadError:
        writer.close()
        return

    version = first_byte[0]
    log.info("connection from %s, SOCKS version byte=%s", peer, version)
    try:
        if version == 0x05:
            await handle_socks5(reader, writer, first_byte)
        elif version == 0x04:
            await handle_socks4(reader, writer, first_byte)
        else:
            log.warning("unrecognized SOCKS version byte %s from %s, closing", version, peer)
            writer.close()
    except (asyncio.IncompleteReadError, ConnectionResetError) as exc:
        log.info("connection from %s ended early: %s", peer, exc)
    finally:
        if not writer.is_closing():
            writer.close()


async def main():
    server = await asyncio.start_server(handle_connection, "0.0.0.0", LISTEN_PORT)
    log.info("SOCKS bridge listening on 0.0.0.0:%s, forwarding to %s:%s", LISTEN_PORT, META_HOST, META_PORT)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
