# GITR2000 Browser Revival

A from-scratch, browser-playable reimagining of GITR2000, inspired by what
we recovered by inspecting the original client binaries: arenas (chat
rooms), a challenge system, and a live "fight" with an energy bar, points,
14 action moves, and running commentary, plus spectating.

This is **not** a recovered protocol or ruleset. The original meta server
is gone, and no move list, point values, or commentary text survived in
the client - only the shape of the feature set did (see the form names
inside `gitr2k.exe`'s resources: `TfrmArenaSelect`, `TfrmChallenge`,
`TfrmFight`, `TfrmWatchFight`, etc). Everything in `backend/game.py` is a
new design in that spirit.

## Running locally

```bash
cd webapp/backend
pip install -r requirements.txt
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` in a browser. Open it in two tabs (or
two browsers) with different usernames to challenge yourself and see
chat/fights work between two live connections.

## What's implemented

- Username-only login (no accounts/passwords - in-memory, resets on restart)
- A handful of themed arenas (chat rooms) with live chat
- Challenging another user in your arena to a match (with a match-type label)
- A live fight screen: energy bar, points bar, 14 moves with energy costs
  and a small reversal chance, auto-generated commentary, first to 100
  points wins
- Spectating any in-progress match from the arena view
- Forfeiting a match or a disconnect ends it in the opponent's favor

## Known simplifications vs. the original

- No tag-team / 3-opponent handicap matches (the original's challenge
  dialog had a "third opponent" slot) - singles matches only for now
- No accounts, private messages, ignore lists, or standard phrases
- Arenas are a flat list, not the country-grouped tree the original had
- Everything is in-memory - restarting the server clears all state
