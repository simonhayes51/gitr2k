# SOCKS bridge for GITR2000 clients without HOSTS-file access

`gitr2k.exe`/`arena.exe` have `GETINTR2K.MINIDNS.NET:9182` compiled in.
The usual fix is a HOSTS-file override, which needs admin rights on the
machine running the client. Both apps also expose a real **Proxy**
setting in their own GUI (`settings.UseProxy` / `ProxyHost` / `ProxyPort`
/ `ProxyUser` / `ProxyPass`, wired to actual form fields - confirmed by
inspecting the client binaries' resources), which is an ordinary
per-user preference, not a system file - no elevation needed to change
it.

This bridge speaks SOCKS4, SOCKS4a, and SOCKS5 (we don't know which one
the client's "SocksInfo.Version" setting actually sends, so it handles
all three) and, once the handshake completes, **ignores whatever
destination the client asked for** and always connects onward to the
real meta server, then relays bytes untouched in both directions. It has
no idea what GITR2000's own protocol looks like - it's just a dumb pipe
past the handshake.

## Configuring the target

Set via environment variables (defaults point at the meta server's
current public Railway TCP proxy address):

- `META_HOST` (default `sakura.proxy.rlwy.net`)
- `META_PORT` (default `31599`)
- `PORT` - the port this bridge itself listens on internally (default
  `1080`)

If you deploy this in the *same* Railway project as the meta server, you
can instead point `META_HOST`/`META_PORT` at the meta server's private
network address (Settings -> Networking -> Private Networking on that
service, looks like `<service-name>.railway.internal`) and its plain
internal port (`9182`) - avoids the public internet round-trip and isn't
affected if the public TCP proxy's assigned port ever changes.

## Deploying to Railway

1. **+ New -> GitHub Repo** -> this repo again, as its own service.
2. **Settings -> Root Directory**: `socks_bridge`.
3. **Settings -> Networking -> TCP Proxy**, target port `1080` (matches
   this app's internal listen port).
4. Note the assigned public `host:port` - that's what goes into the
   game client's Settings dialog.

## Configuring the client

In `gitr2k.exe` (and separately in `arena.exe`, if you're hosting an
arena), open Settings and look for the Proxy section:

- **Use Proxy**: checked
- **Proxy Host**: the bridge's Railway-assigned hostname (step 4 above)
- **Proxy Port**: the bridge's Railway-assigned port
- **Proxy User / Pass**: leave blank

Then try connecting as normal. Watch this service's Railway logs - every
connection attempt logs which SOCKS version byte it saw and what it did
with it, which is the main thing we need if the first attempt doesn't
work: it'll tell us whether the client's handshake even reached the
bridge, and if so, which SOCKS variant to focus on.
