# Deploying to a VPS (recommended for now - exact port match, no client changes)

This path keeps the external port at exactly `9182`, matching what's
compiled into `gitr2k.exe`, so HOSTS-file redirection works precisely like
it does when running the server locally - just pointed at a public IP
instead of `127.0.0.1`. No binary patching needed.

Any small Linux VPS works (DigitalOcean, Linode, Hetzner, Vultr, etc. -
the cheapest tier is plenty for this). Steps below assume Ubuntu.

## 1. Provision the VPS
Create a small Ubuntu 22.04/24.04 instance with your provider of choice.
Note its public IPv4 address - you'll need it for the HOSTS file later.

## 2. Copy the project over
From your local machine:
```bash
scp -r gitr2k_meta_server root@<VPS-IP>:/opt/gitr2k_meta_server
```
(or `git clone` your repo directly on the VPS if you pushed it to GitHub
for the Railway setup - same repo works fine here too)

## 3. Install Python (usually already present on Ubuntu)
```bash
ssh root@<VPS-IP>
python3 --version   # confirm 3.8+
```

## 4. Open the firewall for port 9182
```bash
ufw allow 9182/tcp
ufw status
```
If your provider also has a separate cloud firewall/security-group panel
(common on DigitalOcean/AWS/etc.), open TCP 9182 there too - `ufw` alone
isn't enough if the provider's network-level firewall blocks it first.

## 5. Run it as a systemd service (so it survives reboots/crashes)

Create `/etc/systemd/system/gitr2k-meta.service`:
```ini
[Unit]
Description=GITR2K Meta Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/gitr2k_meta_server
ExecStart=/usr/bin/python3 server/main.py --port 9182 --bind 0.0.0.0
Restart=on-failure
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

Then:
```bash
systemctl daemon-reload
systemctl enable gitr2k-meta
systemctl start gitr2k-meta
systemctl status gitr2k-meta
```

## 6. Watch it work
```bash
journalctl -u gitr2k-meta -f
```
This tails the same `SERVER_LISTENING` / `CONNECT` / `RECV` output you'd
see running it locally. Captures are also written to
`/opt/gitr2k_meta_server/captures/` on the VPS's own disk - and unlike the
Railway container, this persists across restarts (as long as you don't
destroy the VPS).

## 7. Point the client at it
On the Windows machine running `gitr2k.exe`, edit
`C:\Windows\System32\drivers\etc\hosts` as Administrator and add:
```
<VPS-public-IP>   GETINTR2K.MINIDNS.NET
```

Launch the game. Traffic should now hit the VPS on port 9182 exactly as
it would locally.

## Updating the server later
```bash
ssh root@<VPS-IP>
cd /opt/gitr2k_meta_server
git pull            # or scp updated files over
systemctl restart gitr2k-meta
```

## A note on exposure
This opens port 9182 to the whole internet, not just you - fine for a
low-traffic preservation project, but worth being aware of. If you want
to restrict it to just your own IP while testing, you can scope the `ufw`
rule instead of allowing it broadly:
```bash
ufw allow from <your-home-IP> to any port 9182 proto tcp
```
