"""Fight mechanics for the GITR2000 browser revival.

The original client had 14 unlabeled action buttons driven entirely by
server-side logic that no longer exists (the real GITR2000 server is long
gone, and none of its move list, point costs, or commentary text survived
in the client binaries). This module is a fresh, from-scratch mechanic
inspired by the original's shape (energy bar, points, live commentary) —
not a recovered or reverse-engineered ruleset.
"""

import random
import time

POINTS_TO_WIN = 100
MAX_ENERGY = 100
REGEN_PER_SEC = 3
ACTION_COOLDOWN = 1.2
REVERSAL_CHANCE = 0.15


class Move:
    def __init__(self, id, name, energy_cost, points_range, reversal_chance, templates, reversal_templates):
        self.id = id
        self.name = name
        self.energy_cost = energy_cost
        self.points_range = points_range
        self.reversal_chance = reversal_chance
        self.templates = templates
        self.reversal_templates = reversal_templates

    def roll_points(self):
        return random.randint(*self.points_range)


MOVES = [
    Move(1, "Jab", 5, (3, 6), 0.05,
         ["{a} snaps a jab into {d}'s face!"],
         ["{d} slips {a}'s jab and fires back!"]),
    Move(2, "Right Hand", 8, (5, 9), 0.08,
         ["{a} rocks {d} with a big right hand!"],
         ["{d} ducks and counters {a}'s right hand!"]),
    Move(3, "Chop", 6, (4, 8), 0.08,
         ["{a} chops {d}'s chest raw!"],
         ["{d} no-sells the chop and chops back!"]),
    Move(4, "Clothesline", 12, (8, 14), 0.12,
         ["{a} turns {d} inside out with a clothesline!"],
         ["{d} ducks the clothesline and levels {a}!"]),
    Move(5, "Dropkick", 15, (10, 16), 0.15,
         ["{a} launches into a dropkick, catching {d} flush!"],
         ["{d} sidesteps and {a} crashes to the mat!"]),
    Move(6, "Suplex", 18, (12, 20), 0.15,
         ["{a} snaps off a beautiful suplex on {d}!"],
         ["{d} blocks and reverses the suplex attempt!"]),
    Move(7, "DDT", 20, (14, 22), 0.18,
         ["{a} plants {d} with a DDT!"],
         ["{d} shoves {a} away before the DDT connects!"]),
    Move(8, "Powerbomb", 25, (18, 28), 0.2,
         ["{a} drives {d} down with a powerbomb!"],
         ["{d} slips out and turns the powerbomb into a counter!"]),
    Move(9, "Piledriver", 28, (20, 30), 0.22,
         ["{a} spikes {d} with a piledriver!"],
         ["{d} backdrops out of the piledriver attempt!"]),
    Move(10, "Elbow Drop", 10, (6, 10), 0.1,
         ["{a} drops an elbow across {d}!"],
         ["{d} rolls away and the elbow drop misses!"]),
    Move(11, "Irish Whip Slam", 14, (9, 15), 0.13,
         ["{a} whips {d} into the ropes and slams them down!"],
         ["{d} reverses the whip and slams {a} instead!"]),
    Move(12, "Submission Hold", 22, (16, 24), 0.25,
         ["{a} locks {d} in a brutal submission hold!"],
         ["{d} powers out and turns the hold on {a}!"]),
    Move(13, "Signature Move", 30, (22, 32), 0.28,
         ["{a} connects with their signature move! {d} is in trouble!"],
         ["{d} somehow avoids the signature move entirely!"]),
    Move(14, "Taunt & Rest", 0, (0, 2), 0.0,
         ["{a} taunts the crowd, catching a breath."],
         []),
]

MOVES_BY_ID = {m.id: m for m in MOVES}


class Fighter:
    def __init__(self, username):
        self.username = username
        self.energy = float(MAX_ENERGY)
        self.points = 0
        self.last_action_ts = 0.0
        self.last_regen_ts = time.time()

    def regen(self):
        now = time.time()
        elapsed = now - self.last_regen_ts
        self.energy = min(MAX_ENERGY, self.energy + elapsed * REGEN_PER_SEC)
        self.last_regen_ts = now

    def public_state(self):
        return {"username": self.username, "energy": round(self.energy), "points": self.points}


class Fight:
    def __init__(self, fight_id, usernames, match_type="singles"):
        self.id = fight_id
        self.match_type = match_type
        self.fighters = {u: Fighter(u) for u in usernames}
        self.order = list(usernames)
        self.commentary = []
        self.spectators = set()
        self.status = "active"
        self.winner = None
        self.started_ts = time.time()

    def opponent_of(self, username):
        for u in self.order:
            if u != username:
                return u
        return None

    def add_commentary(self, text):
        entry = {"text": text, "ts": time.time()}
        self.commentary.append(entry)
        if len(self.commentary) > 100:
            self.commentary = self.commentary[-100:]
        return entry

    def try_action(self, username, move_id):
        """Returns (ok, error_or_None, commentary_text_or_None)."""
        if self.status != "active":
            return False, "fight is over", None
        if username not in self.fighters:
            return False, "not a participant", None
        move = MOVES_BY_ID.get(move_id)
        if move is None:
            return False, "unknown move", None

        actor = self.fighters[username]
        actor.regen()
        now = time.time()
        if now - actor.last_action_ts < ACTION_COOLDOWN:
            return False, "action on cooldown", None
        if actor.energy < move.energy_cost:
            return False, "not enough energy", None

        opp_name = self.opponent_of(username)
        opponent = self.fighters[opp_name]
        opponent.regen()

        actor.last_action_ts = now
        actor.energy -= move.energy_cost

        reversed_ = move.reversal_templates and random.random() < move.reversal_chance
        gained = move.roll_points()
        if reversed_:
            opponent.points += gained
            text = random.choice(move.reversal_templates).format(a=username, d=opp_name)
            beneficiary = opp_name
        else:
            actor.points += gained
            text = random.choice(move.templates).format(a=username, d=opp_name)
            beneficiary = username

        self.add_commentary(text)

        if self.fighters[beneficiary].points >= POINTS_TO_WIN:
            self.status = "finished"
            self.winner = beneficiary
            self.add_commentary(f"{beneficiary} wins the match!")

        return True, None, text

    def forfeit(self, username):
        if self.status != "active":
            return
        opp = self.opponent_of(username)
        self.status = "finished"
        self.winner = opp
        self.add_commentary(f"{username} has left the match. {opp} wins by forfeit.")

    def public_state(self):
        return {
            "id": self.id,
            "matchType": self.match_type,
            "status": self.status,
            "winner": self.winner,
            "fighters": [self.fighters[u].public_state() for u in self.order],
            "commentary": [c["text"] for c in self.commentary[-30:]],
        }
