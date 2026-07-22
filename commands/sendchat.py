"""
commands/sendchat.py
---------------------
Handler for the SENDCHAT token.

Confidence: token existence = CONFIRMED (disassembly). Related tokens
CHATID and BASECHAT also confirmed to exist, and BASECHAT is confirmed
(by disassembly of arena.exe's GMCCMetaMessage) to be used together with
METAMSG - suggesting a relationship between chat messages and the METAMSG
framing, but the exact tie between SENDCHAT (client->server, assumed) and
METAMSG (seen server-side in arena.exe) is UNKNOWN.

TODO(runtime):
    - Confirm direction: is SENDCHAT sent by the client to submit a chat
      message, with the server echoing it back via a different token
      (e.g. METAMSG or CHATID) to all connected clients?
    - Confirm argument format: is the message plain text after a space,
      or are there additional fields (e.g. sender name, channel/arena id)?
    - Confirm any escaping needed for delimiter characters appearing in
      user-typed chat text.
"""


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note="Candidate SENDCHAT token detected. No response/relay sent - behaviour UNKNOWN, see TODO in this file.",
    )
    # TODO(runtime): once confirmed, relay/echo per the real protocol here.
    return None
