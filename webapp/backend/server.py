"""GITR2000 browser revival - backend.

A from-scratch reimplementation inspired by the original GITR2000 client's
shape (arenas/chat rooms, challenges, a live fight with energy/points and
commentary, spectating) - not a recovered protocol. See game.py for why.

In-memory only: state resets on restart. No accounts/passwords - a
username is claimed for the duration of the connection.
"""

import re
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from game import Fight, MOVES

app = FastAPI()

ARENA_NAMES = ["Main Event Arena", "Backyard Brawl", "Tag Team Alley", "Rookie Ring", "Hardcore Zone"]
NEWS = [
    "Welcome to the GITR2000 browser revival - an unofficial fan recreation.",
    "This is a fresh reimplementation: the original meta server is long gone, so match rules and commentary here are new, not recovered.",
]
USERNAME_RE = re.compile(r"^[A-Za-z0-9_\-]{3,16}$")
CHAT_HISTORY_LIMIT = 200
CHAT_MESSAGE_LIMIT = 500


class UserSession:
    def __init__(self, username, ws):
        self.username = username
        self.ws = ws
        self.arena = None
        self.fight = None
        self.spectating = None


users = {}
arenas = {name: {"members": set(), "history": []} for name in ARENA_NAMES}
challenges = {}
fights = {}


def arena_summary():
    return [{"name": n, "count": len(a["members"])} for n, a in arenas.items()]


async def send(ws, payload):
    try:
        await ws.send_json(payload)
    except Exception:
        pass


async def broadcast(usernames, payload):
    for u in usernames:
        session = users.get(u)
        if session:
            await send(session.ws, payload)


async def broadcast_all(payload):
    await broadcast(list(users.keys()), payload)


async def handle_join_arena(username, data):
    session = users[username]
    name = data.get("name")
    if name not in arenas:
        await send(session.ws, {"type": "error", "message": "no such arena"})
        return

    old = session.arena
    if old and old in arenas:
        arenas[old]["members"].discard(username)
        await broadcast(arenas[old]["members"], {"type": "user_leave", "arena": old, "username": username})

    arenas[name]["members"].add(username)
    session.arena = name
    await broadcast(arenas[name]["members"] - {username}, {"type": "user_enter", "arena": name, "username": username})
    await send(session.ws, {
        "type": "arena_state",
        "name": name,
        "history": arenas[name]["history"][-CHAT_HISTORY_LIMIT:],
        "users": sorted(arenas[name]["members"]),
    })
    await broadcast_all({"type": "arenas_update", "arenas": arena_summary()})


async def handle_chat(username, data):
    session = users[username]
    if not session.arena:
        await send(session.ws, {"type": "error", "message": "join an arena first"})
        return
    text = (data.get("text") or "").strip()[:CHAT_MESSAGE_LIMIT]
    if not text:
        return
    entry = {"user": username, "text": text, "ts": time.time()}
    history = arenas[session.arena]["history"]
    history.append(entry)
    del history[:-CHAT_HISTORY_LIMIT]
    await broadcast(arenas[session.arena]["members"], {"type": "chat", **entry})


async def handle_challenge(username, data):
    session = users[username]
    target = data.get("target")
    match_type = (data.get("matchType") or "singles")[:32]
    target_session = users.get(target)

    if target == username:
        await send(session.ws, {"type": "error", "message": "can't challenge yourself"})
        return
    if not target_session:
        await send(session.ws, {"type": "error", "message": "that user isn't online"})
        return
    if session.fight or target_session.fight:
        await send(session.ws, {"type": "error", "message": "someone's already in a match"})
        return

    challenge_id = uuid.uuid4().hex[:8]
    challenges[challenge_id] = {"from": username, "to": target, "matchType": match_type, "ts": time.time()}
    await send(target_session.ws, {"type": "challenge_received", "id": challenge_id, "from": username, "matchType": match_type})
    await send(session.ws, {"type": "challenge_sent", "id": challenge_id, "to": target})


def fights_summary():
    return [{"id": f.id, "participants": f.order, "matchType": f.match_type} for f in fights.values() if f.status == "active"]


async def broadcast_fights_update():
    await broadcast_all({"type": "fights_list", "fights": fights_summary()})


async def start_fight(usernames, match_type):
    fight_id = uuid.uuid4().hex[:8]
    fight = Fight(fight_id, usernames, match_type)
    fights[fight_id] = fight
    for u in usernames:
        users[u].fight = fight_id
    await broadcast(usernames, {"type": "fight_start", "fight": fight.public_state(), "moves": [{"id": m.id, "name": m.name, "energyCost": m.energy_cost} for m in MOVES]})
    await broadcast_fights_update()


async def handle_respond_challenge(username, data):
    session = users[username]
    challenge_id = data.get("id")
    challenge = challenges.pop(challenge_id, None)
    if not challenge or challenge["to"] != username:
        await send(session.ws, {"type": "error", "message": "challenge no longer valid"})
        return

    challenger_session = users.get(challenge["from"])
    if not data.get("accept"):
        if challenger_session:
            await send(challenger_session.ws, {"type": "challenge_declined", "by": username})
        return

    if not challenger_session or session.fight or challenger_session.fight:
        await send(session.ws, {"type": "error", "message": "match no longer available"})
        return

    await start_fight([challenge["from"], username], challenge["matchType"])


async def handle_fight_action(username, data):
    session = users[username]
    fight = fights.get(session.fight)
    if not fight:
        await send(session.ws, {"type": "error", "message": "not in a match"})
        return

    ok, err, _ = fight.try_action(username, data.get("moveId"))
    if not ok:
        await send(session.ws, {"type": "error", "message": err})
        return

    recipients = set(fight.order) | fight.spectators
    await broadcast(recipients, {"type": "fight_update", "fight": fight.public_state()})

    if fight.status == "finished":
        for u in fight.order:
            if u in users:
                users[u].fight = None
        fights.pop(fight.id, None)
        await broadcast_fights_update()


async def handle_leave_fight(username, data):
    session = users[username]
    fight = fights.get(session.fight)
    if fight and fight.status == "active":
        fight.forfeit(username)
        recipients = set(fight.order) | fight.spectators
        await broadcast(recipients, {"type": "fight_update", "fight": fight.public_state()})
        for u in fight.order:
            if u in users:
                users[u].fight = None
        fights.pop(fight.id, None)
        await broadcast_fights_update()
    else:
        session.fight = None


async def handle_list_fights(username, data):
    session = users[username]
    await send(session.ws, {"type": "fights_list", "fights": fights_summary()})


async def handle_spectate(username, data):
    session = users[username]
    fight = fights.get(data.get("fightId"))
    if not fight or fight.status != "active":
        await send(session.ws, {"type": "error", "message": "that match has ended"})
        return
    fight.spectators.add(username)
    session.spectating = fight.id
    await send(session.ws, {"type": "fight_start", "fight": fight.public_state(), "asSpectator": True,
                             "moves": [{"id": m.id, "name": m.name, "energyCost": m.energy_cost} for m in MOVES]})


async def handle_stop_spectate(username, data):
    session = users[username]
    if session.spectating:
        fight = fights.get(session.spectating)
        if fight:
            fight.spectators.discard(username)
        session.spectating = None


HANDLERS = {
    "join_arena": handle_join_arena,
    "chat": handle_chat,
    "challenge": handle_challenge,
    "respond_challenge": handle_respond_challenge,
    "fight_action": handle_fight_action,
    "leave_fight": handle_leave_fight,
    "list_fights": handle_list_fights,
    "spectate": handle_spectate,
    "stop_spectate": handle_stop_spectate,
}


async def cleanup(username):
    session = users.pop(username, None)
    if not session:
        return
    if session.arena and session.arena in arenas:
        arenas[session.arena]["members"].discard(username)
        await broadcast(arenas[session.arena]["members"], {"type": "user_leave", "arena": session.arena, "username": username})
        await broadcast_all({"type": "arenas_update", "arenas": arena_summary()})
    if session.fight:
        fight = fights.get(session.fight)
        if fight and fight.status == "active":
            fight.forfeit(username)
            recipients = (set(fight.order) | fight.spectators) - {username}
            await broadcast(recipients, {"type": "fight_update", "fight": fight.public_state()})
            for u in fight.order:
                if u in users:
                    users[u].fight = None
            fights.pop(fight.id, None)
            await broadcast_fights_update()
    if session.spectating:
        fight = fights.get(session.spectating)
        if fight:
            fight.spectators.discard(username)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    username = None
    try:
        while username is None:
            data = await websocket.receive_json()
            if data.get("type") != "login":
                await send(websocket, {"type": "error", "message": "login required"})
                continue
            candidate = (data.get("username") or "").strip()
            if not USERNAME_RE.match(candidate):
                await send(websocket, {"type": "error", "message": "username must be 3-16 letters/numbers/_/-"})
                continue
            if candidate in users:
                await send(websocket, {"type": "error", "message": "that username is already in use"})
                continue
            username = candidate
            users[username] = UserSession(username, websocket)
            await send(websocket, {"type": "welcome", "username": username, "news": NEWS, "arenas": arena_summary()})

        while True:
            data = await websocket.receive_json()
            handler = HANDLERS.get(data.get("type"))
            if handler:
                await handler(username, data)
            else:
                await send(websocket, {"type": "error", "message": f"unknown message type {data.get('type')!r}"})
    except WebSocketDisconnect:
        pass
    finally:
        await cleanup(username)


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
