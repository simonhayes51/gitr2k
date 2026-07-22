# Deploying to Railway

## What this gets you
An always-on capture server, reachable from anywhere, without keeping a
desktop machine running. Good for logging/development immediately.

## What it does NOT solve yet
**Railway's public TCP proxy assigns you a random external port** (e.g.
`shuttle.proxy.rlwy.net:15140`), not port 9182. The original `gitr2k.exe`
has port `9182` compiled directly into it and will always try to connect
there — HOSTS-file redirection only changes the hostname it resolves to,
not the port it connects on. So immediately after deploying, the
*unmodified* client will not be able to reach this server yet.

Two ways to close that gap, once you're ready:
1. **Patch the client's compiled port value** to match whatever port
   Railway assigns you (see `docs/PORT_PATCHING.md` — not written until
   we've confirmed the exact bytes to change, since we don't want to
   guess at a binary patch).
2. **Use the VPS setup instead** (`docs/VPS_DEPLOY.md`) for a host where
   you control the literal external port and can keep it at 9182 with no
   client changes at all.

Either way, deploying to Railway now is still useful groundwork - it's
just not plug-and-play with the original client until one of the above
is resolved.

## Steps

1. **Push this project to a GitHub repo** (Railway deploys from Git).
   ```bash
   cd gitr2k_meta_server
   git init
   git add .
   git commit -m "GITR2K meta server - initial scaffold"
   git branch -M main
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Create a new Railway project** at [railway.app](https://railway.app),
   choose "Deploy from GitHub repo", and select this repository.

3. Railway will detect it as a Python project (via `requirements.txt`) and
   use the `railway.json` / `Procfile` in this repo to run:
   ```
   python3 server/main.py --port 9182 --bind 0.0.0.0
   ```

4. **Enable the TCP Proxy** (this is not automatic - Railway defaults to
   HTTP routing):
   - Open your service → **Settings** → **Networking**
   - Under **Public Networking**, choose **TCP Proxy** instead of a
     generated HTTP domain
   - Set the **target port** to `9182` (this is the *internal* port the
     app listens on - matches the `--port 9182` above)
   - Railway will show you the generated public address, e.g.
     `shuttle.proxy.rlwy.net:15140` — **note both the hostname and the
     port number**, you'll need them.

5. **Turn off the HTTP health check.** Railway's default health check
   expects an HTTP response; this is a raw TCP service and will fail that
   check. In service Settings → look for "Healthcheck" and either disable
   it or leave it unset - the `railway.json` above already omits a
   `healthcheckPath`, which should avoid this, but check the dashboard to
   confirm.

6. **Check the logs tab** in the Railway dashboard - this is where you'll
   see the same `SERVER_LISTENING` / `CONNECT` / `RECV` output the local
   version prints to console. Captures are also being written into the
   container's `captures/` folder, but note: **container filesystems on
   Railway are ephemeral by default** - a redeploy or restart can wipe
   `captures/`. If you want captures to persist, either:
   - add a Railway Volume mounted at `/app/captures`, or
   - periodically download the capture files via `railway run` / the
     dashboard, or
   - simplest for now: just copy the relevant log lines out of the
     Railway dashboard logs view when you see something interesting.

## Once you have the assigned port

Come back and tell me the hostname:port Railway gave you. From there we
can either look at patching the client's port (once we've confirmed the
right bytes), or just use this deployment for logging while the VPS
handles the actual client-facing connection.
