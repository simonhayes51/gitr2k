"""Persistent account storage (SQLite) for the GITR2000 browser revival.

Simple password-claimed usernames - the first login with a given username
sets its password, later logins must match. No email/recovery flow; this
is a hobby-project account store, not a production auth system.
"""

import hashlib
import json
import os
import sqlite3
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "gitr2000.db")

_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        wins INTEGER NOT NULL DEFAULT 0,
        losses INTEGER NOT NULL DEFAULT 0,
        ignore_list TEXT NOT NULL DEFAULT '[]',
        standard_phrases TEXT NOT NULL DEFAULT '[]',
        created_ts REAL NOT NULL
    )
""")
_conn.commit()


def _hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000).hex()


def account_exists(username):
    row = _conn.execute("SELECT 1 FROM accounts WHERE username = ?", (username,)).fetchone()
    return row is not None


def create_account(username, password):
    salt = os.urandom(16).hex()
    password_hash = _hash_password(password, salt)
    _conn.execute(
        "INSERT INTO accounts (username, password_hash, salt, created_ts) VALUES (?, ?, ?, ?)",
        (username, password_hash, salt, time.time()),
    )
    _conn.commit()


def verify_password(username, password):
    row = _conn.execute("SELECT password_hash, salt FROM accounts WHERE username = ?", (username,)).fetchone()
    if not row:
        return False
    password_hash, salt = row
    return _hash_password(password, salt) == password_hash


def get_profile(username):
    row = _conn.execute(
        "SELECT wins, losses, ignore_list, standard_phrases FROM accounts WHERE username = ?", (username,)
    ).fetchone()
    if not row:
        return None
    wins, losses, ignore_list, standard_phrases = row
    return {
        "wins": wins,
        "losses": losses,
        "ignoreList": json.loads(ignore_list),
        "standardPhrases": json.loads(standard_phrases),
    }


def record_result(username, won):
    field = "wins" if won else "losses"
    _conn.execute(f"UPDATE accounts SET {field} = {field} + 1 WHERE username = ?", (username,))
    _conn.commit()


def set_ignore_list(username, ignore_list):
    _conn.execute("UPDATE accounts SET ignore_list = ? WHERE username = ?", (json.dumps(ignore_list), username))
    _conn.commit()


def set_standard_phrases(username, phrases):
    _conn.execute("UPDATE accounts SET standard_phrases = ? WHERE username = ?", (json.dumps(phrases), username))
    _conn.commit()
