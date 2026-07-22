"""GITR2000 browser revival - backend.

A from-scratch reimplementation inspired by the original GITR2000 client's
shape (arenas/chat rooms grouped by country, challenges, a live fight with
energy/points and commentary, mid-fight tag-team/handicap partner invites,
spectating, private messages, ignore lists, standard phrases) - not a
recovered protocol. See game.py for why.

Accounts persist (SQLite, accounts.py) so a username+password combo is
yours across restarts. Everything else (arenas, chat, fights, DMs) is
in-memory and resets when the process restarts.
"""

import re
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

import accounts
from game import Fight, MOVES, MAX_TEAM_SIZE

app = FastAPI()

AREAS = {
    "United States": ["Main Event Arena", "Backyard Brawl", "Hardcore Zone"],
    "United Kingdom": ["Rookie Ring", "Wembley Arena"],
    "International": ["Tag Team Alley", "World Championship Arena"],
}
ARENA_COUNTRY = {name: country for country, names in AREAS.items() for name in names}

NEWS = [
    "Welcome to the GITR2000 browser revival - an unofficial fan recreation.",
    "This is a fresh reimplementation: the original meta server is long gone, so match rules and commentary here are new, not recovered.",
    "Mid-match, either fighter can invite an outside user to join their side for a tag-team or handicap match.",
]
USERNAME_RE = re.compile(r"^[A-Za-z0-9_\-]{3,16}$")
CHAT_HISTORY_LIMIT = 200
CHAT_MESSAGE_LIMIT = 500
PM_MESSAGE_LIMIT = 450
MATCH_TYPES = {"singles", "no-dq", "submission", "falls-count-anywhere"}


class UserSession:
    def __init__(self, username, ws, profile):
        self.username = username
        self.ws = ws
        self.arena = None
        self.fight = None
        self.spectating = None
        self.ignore_list = set(profile["ignoreList"])
        self.standard_phrases = list(profile["standardPhrases"])


users = {}
arenas = {name: {"members": set(), "history": []} for names in AREAS.values() for name in names}
challenges = {}
team_invites = {}
fights = {}


def arena_summary():
    return [
        {"country": country, "arenas": [{"name": n, "count": len(arenas[n]["members"])} for n in names]}
        for country, names in AREAS.items()
    ]


def fights_summary():
    return [
        {"id": f.id, "teamA": f.team_a, "teamB": f.team_b, "matchType": f.match_type}
        for f in fights.values() if f.status == "active"
    ]


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


async def broadcast_fights_update():
    await broadcast_all({"type": "fights_list", "fights": fights_summary()})


def move_summaries():
    return [{"id": m.id, "name": m.name, "energyCost": m.energy_cost} for m in MOVES]


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
    for member in arenas[session.arena]["members"]:
        recipient = users.get(member)
        if recipient and username not in recipient.ignore_list:
            await send(recipient.ws, {"type": "chat", **entry})


async def handle_challenge(username, data):
    session = users[username]
    target = data.get("target")
    match_type = data.get("matchType") if data.get("matchType") in MATCH_TYPES else "singles"
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
    if username in target_session.ignore_list:
        await send(session.ws, {"type": "error", "message": "that user isn't taking challenges right now"})
        return

    challenge_id = uuid.uuid4().hex[:8]
    challenges[challenge_id] = {"from": username, "to": target, "matchType": match_type, "ts": time.time()}
    await send(target_session.ws, {"type": "challenge_received", "id": challenge_id, "from": username, "matchType": match_type})
    await send(session.ws, {"type": "challenge_sent", "id": challenge_id, "to": target})


async def start_fight(team_a, team_b, match_type):
    fight_id = uuid.uuid4().hex[:8]
    fight = Fight(fight_id, team_a, team_b, match_type)
    fights[fight_id] = fight
    for u in fight.order:
        users[u].fight = fight_id
    await broadcast(fight.order, {"type": "fight_start", "fight": fight.public_state(), "moves": move_summaries()})
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

    await start_fight([challenge["from"]], [username], challenge["matchType"])


async def finish_fight_bookkeeping(fight):
    for side, other in (("a", "b"), ("b", "a")):
        won = fight.winner_team == side
        for u in fight.team_list(side):
            accounts.record_result(u, won)
            if u in users:
                users[u].fight = None
    fights.pop(fight.id, None)
    await broadcast_fights_update()


async def handle_fight_action(username, data):
    session = users[username]
    fight = fights.get(session.fight)
    if not fight:
        await send(session.ws, {"type": "error", "message": "not in a match"})
        return

    ok, err, _ = fight.try_action(username, data.get("moveId"), data.get("target"))
    if not ok:
        await send(session.ws, {"type": "error", "message": err})
        return

    recipients = set(fight.order) | fight.spectators
    await broadcast(recipients, {"type": "fight_update", "fight": fight.public_state()})

    if fight.status == "finished":
        await finish_fight_bookkeeping(fight)


async def handle_leave_fight(username, data):
    session = users[username]
    fight = fights.get(session.fight)
    if fight and fight.status == "active":
        fight.forfeit(username)
        recipients = set(fight.order) | fight.spectators
        await broadcast(recipients, {"type": "fight_update", "fight": fight.public_state()})
        await finish_fight_bookkeeping(fight)
    else:
        session.fight = None


async def handle_invite_partner(username, data):
    session = users[username]
    fight = fights.get(session.fight)
    if not fight or fight.status != "active":
        await send(session.ws, {"type": "error", "message": "you're not in an active match"})
        return
    side = fight.team_of(username)
    if fight.team_full(side):
        await send(session.ws, {"type": "error", "message": "your team is already full"})
        return

    target = data.get("username")
    target_session = users.get(target)
    if not target_session or target == username:
        await send(session.ws, {"type": "error", "message": "that user isn't online"})
        return
    if target in fight.fighters or target_session.fight:
        await send(session.ws, {"type": "error", "message": "that user is already in a match"})
        return
    if username in target_session.ignore_list:
        await send(session.ws, {"type": "error", "message": "that user isn't available"})
        return

    invite_id = uuid.uuid4().hex[:8]
    team_invites[invite_id] = {"fightId": fight.id, "from": username, "target": target, "side": side}
    await send(target_session.ws, {
        "type": "team_invite",
        "id": invite_id,
        "from": username,
        "teammates": fight.team_list(side),
        "opponents": fight.team_list("b" if side == "a" else "a"),
    })
    await send(session.ws, {"type": "team_invite_sent", "to": target})


async def handle_respond_team_invite(username, data):
    session = users[username]
    invite_id = data.get("id")
    invite = team_invites.pop(invite_id, None)
    if not invite or invite["target"] != username:
        await send(session.ws, {"type": "error", "message": "invite no longer valid"})
        return

    inviter_session = users.get(invite["from"])
    if not data.get("accept"):
        if inviter_session:
            await send(inviter_session.ws, {"type": "team_invite_declined", "by": username})
        return

    fight = fights.get(invite["fightId"])
    if not fight or fight.status != "active" or fight.team_full(invite["side"]) or session.fight:
        await send(session.ws, {"type": "error", "message": "that match is no longer available"})
        return

    fight.add_fighter(username, invite["side"])
    users[username].fight = fight.id
    others = (set(fight.order) | fight.spectators) - {username}
    await broadcast(others, {"type": "fight_update", "fight": fight.public_state()})
    await send(session.ws, {"type": "fight_start", "fight": fight.public_state(), "moves": move_summaries()})
    await broadcast_fights_update()


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
    await send(session.ws, {"type": "fight_start", "fight": fight.public_state(), "asSpectator": True, "moves": move_summaries()})


async def handle_stop_spectate(username, data):
    session = users[username]
    if session.spectating:
        fight = fights.get(session.spectating)
        if fight:
            fight.spectators.discard(username)
        session.spectating = None


async def handle_private_message(username, data):
    session = users[username]
    target = data.get("to")
    target_session = users.get(target)
    text = (data.get("text") or "").strip()[:PM_MESSAGE_LIMIT]
    if not text:
        return
    if not target_session:
        await send(session.ws, {"type": "error", "message": "that user isn't online"})
        return
    entry = {"from": username, "text": text, "ts": time.time()}
    await send(session.ws, {"type": "private_message_sent", "to": target, "text": text, "ts": entry["ts"]})
    if username not in target_session.ignore_list:
        await send(target_session.ws, {"type": "private_message_received", **entry})


async def handle_set_ignore(username, data):
    session = users[username]
    target = data.get("target")
    if not target or target == username:
        return
    if data.get("ignore"):
        session.ignore_list.add(target)
    else:
        session.ignore_list.discard(target)
    accounts.set_ignore_list(username, sorted(session.ignore_list))
    await send(session.ws, {"type": "ignore_list_updated", "ignoreList": sorted(session.ignore_list)})


async def handle_save_phrases(username, data):
    session = users[username]
    phrases = [p.strip()[:200] for p in (data.get("phrases") or []) if p.strip()][:20]
    session.standard_phrases = phrases
    accounts.set_standard_phrases(username, phrases)
    await send(session.ws, {"type": "phrases_updated", "standardPhrases": phrases})


HANDLERS = {
    "join_arena": handle_join_arena,
    "chat": handle_chat,
    "challenge": handle_challenge,
    "respond_challenge": handle_respond_challenge,
    "fight_action": handle_fight_action,
    "leave_fight": handle_leave_fight,
    "invite_partner": handle_invite_partner,
    "respond_team_invite": handle_respond_team_invite,
    "list_fights": handle_list_fights,
    "spectate": handle_spectate,
    "stop_spectate": handle_stop_spectate,
    "private_message": handle_private_message,
    "set_ignore": handle_set_ignore,
    "save_phrases": handle_save_phrases,
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
            await finish_fight_bookkeeping(fight)
    if session.spectating:
        fight = fights.get(session.spectating)
        if fight:
            fight.spectators.discard(username)


async def try_login(websocket, candidate, password):
    if not USERNAME_RE.match(candidate):
        await send(websocket, {"type": "error", "message": "username must be 3-16 letters/numbers/_/-"})
        return None
    if not password or len(password) < 4:
        await send(websocket, {"type": "error", "message": "password must be at least 4 characters"})
        return None
    if candidate in users:
        await send(websocket, {"type": "error", "message": "that username is already connected"})
        return None

    if accounts.account_exists(candidate):
        if not accounts.verify_password(candidate, password):
            await send(websocket, {"type": "error", "message": "wrong password for that username"})
            return None
    else:
        accounts.create_account(candidate, password)

    return candidate


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
            username = await try_login(websocket, (data.get("username") or "").strip(), data.get("password") or "")

        profile = accounts.get_profile(username)
        users[username] = UserSession(username, websocket, profile)
        await send(websocket, {
            "type": "welcome",
            "username": username,
            "news": NEWS,
            "arenas": arena_summary(),
            "ignoreList": profile["ignoreList"],
            "standardPhrases": profile["standardPhrases"],
            "wins": profile["wins"],
            "losses": profile["losses"],
        })

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
        if username:
            await cleanup(username)


frontend_dir = Path(__file__).resolve().parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
