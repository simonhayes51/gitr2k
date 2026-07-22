"""
commands/ping.py
------------------
Handler for PINGECHO (gitr2k.exe) and PING (arena.exe).

Confidence: token existence = CONFIRMED (disassembly) for both. This is
almost certainly a keepalive mechanism given the name, but the exact
framing (does the client send "PINGECHO" and expect the literal same
token back? does it carry a sequence number/timestamp argument to match
requests to responses?) is UNKNOWN.

This is a good first candidate to confirm via runtime capture, since
keepalives are usually simple, frequent, and easy to spot in a capture -
if you see a short, regularly-repeating message from the client with no
other traffic in between, PINGECHO/PING is a likely explanation.

TODO(runtime):
    - Confirm exact bytes sent by the client for a ping.
    - Confirm whether the server is expected to echo verbatim, echo with
      a modification (e.g. appended timestamp), or just acknowledge.
    - Confirm the expected interval/timeout behaviour, since getting this
      wrong could cause the original client to consider the connection
      dead.
"""


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note="Candidate PING/PINGECHO token detected. No response sent yet - exact echo format UNKNOWN, see TODO in this file.",
    )
    # TODO(runtime): once confirmed, return the correct keepalive response here.
    # Likely candidate once confirmed: `return raw` (verbatim echo) - but do
    # NOT enable this until a real capture confirms that's actually correct.
    return None
