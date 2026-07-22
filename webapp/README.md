# GITR2000 Browser Revival

A from-scratch, browser-playable reimagining of GITR2000, inspired by what
we recovered by inspecting the original client binaries: country-grouped
arenas (chat rooms), a challenge system, a live "fight" with an energy
bar, points, 14 action moves and running commentary, mid-fight tag-team
and handicap partner invites, spectating, private messages, an ignore
list, and standard phrases.

This is **not** a recovered protocol or ruleset. The original meta server
is gone, and no move list, point values, or commentary text survived in
the client - only the shape of the feature set did (see the form names
inside `gitr2k.exe`'s resources: `TfrmArenaSelect`, `TfrmChallenge`,
`TfrmFight` with its "invite tag team partner" controls, `TfrmWatchFight`,
`TfrmPrivateMsg`, `TIgnoreList`, `TfrmStdPhrases`, etc). Everything in
`backend/game.py` is a new design in that spirit.

## Running locally

```bash
cd webapp/backend
pip install -r requirements.txt
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` in a browser. Open it in two or three
tabs with different username/password combos to chat, challenge, and
fight between live connections.

Accounts persist in `backend/gitr2000.db` (SQLite, gitignored) - a
username's password, wins/losses, ignore list, and standard phrases all
survive a server restart. Arenas, chat history, live fights, and DMs are
in-memory only and reset when the process restarts.

## What's implemented

- **Accounts**: first login with a username claims it with that password;
  later logins must match. Wins/losses, ignore list, and standard phrases
  persist across restarts.
- **Arenas**: a handful of themed chat rooms grouped by country (matching
  the original's country-grouped arena tree), with live chat.
- **Challenges**: challenge another user in your arena to a 1-on-1 match
  with a match-type label (Singles / No DQ / Submission / Falls Count
  Anywhere).
- **Tag team & handicap matches**: once a fight is underway, either side
  can invite an outside user (from the same arena) to join their team,
  turning a 1v1 into a 2v1 handicap or 2v2 tag match - the invitee must
  accept. This mirrors `TfrmFight`'s "invite tag team partner" controls
  more directly than trying to assemble teams before the match starts.
- **Fights**: energy bar, points bar, 14 moves with energy costs and a
  small reversal chance, auto-generated commentary, a target picker when
  you have more than one opponent, first team to 100 combined points wins.
- **Spectating**: watch any in-progress match from the arena view.
- **Private messages**: a floating DM panel, one tab per open thread.
- **Ignore list**: ignored users' arena chat and DMs are silently filtered
  on the recipient's side; toggle from the user list.
- **Standard phrases**: save a personal list of quick phrases (one per
  line) that appear as one-click send buttons in arena chat.
- Forfeiting a match or a disconnect ends it in the opponent's favor.

## Known simplifications vs. the original

- No accounts recovery/email - lose your password, lose the username.
- Arenas, chat history, active fights, and DM threads are in-memory only;
  a server restart clears them (only accounts persist).
- The original's challenge dialog had a "third opponent" field for
  pre-match handicap setup; here, team assembly happens live via in-fight
  invites instead (see above) - functionally similar, different UX.
- No arena admin controls (welcome message, user cap) or arena creation.

## Deploying to Railway

Unlike the original raw-TCP meta server (see `../docs/RAILWAY_DEPLOY.md`),
this is a normal web app - Railway's HTTP routing handles it with no
manual TCP proxy or port-patching needed.

1. In your Railway project, click **+ New** -> **GitHub Repo** -> select
   this repo again (a second service in the same project is fine, or use
   a separate project - either works).
2. In that service's **Settings**, set **Root Directory** to
   `webapp/backend`. Railway will detect it as Python (via
   `requirements.txt`) and use the `Procfile`/`railway.json` there, which
   both bind to Railway's `$PORT` automatically.
3. Under **Networking**, click **Generate Domain** to get a public HTTPS
   URL - no TCP proxy setup needed, this is plain HTTP(S).
4. Open the generated URL - that's the whole app, playable immediately.

**Note on persistence**: Railway's container filesystem is ephemeral by
default, so `gitr2000.db` (accounts) resets on redeploy/restart unless you
add a Railway Volume mounted at the service's working directory
(`webapp/backend`). Without a volume, treat accounts as resetting
periodically, same as the in-memory arena/fight state.
