"""
commands/getnews.py
--------------------
Handler for the GETNEWS token.

Confidence: token existence = CONFIRMED (disassembly). Everything else
about this command (whether it takes arguments, exact response framing,
whether GITRNEWS/ENDNEWSLIST wrap each news item or the whole list, etc.)
is UNKNOWN pending runtime capture.

TODO(runtime): capture a real GETNEWS request and response, then fill in:
    - Does the client send bare "GETNEWS" with no arguments?
    - Does the server reply with one line per news item, each prefixed
      "GITRNEWS", terminated by a bare "ENDNEWSLIST" line?
    - What delimiter (if any) separates fields within a single news item?
"""


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note="Candidate GETNEWS token detected. No response sent - format UNKNOWN, see TODO in this file.",
    )
    # TODO(runtime): once confirmed, return the real response bytes here.
    return None
