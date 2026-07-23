"""
commands/getnews.py
--------------------
Handler for the news-request command.

CONFIRMED (runtime, 2026-07-23): gitr2k.exe sends this on startup as
    CLAUTH NIL NIL GITRNEWS 0\r\n
i.e. the embedded <COMMAND> value is "GITRNEWS", not "GETNEWS" as
originally assumed from static analysis alone - see docs/protocol.md
section 3 and captures/2026-07-23_first_real_capture.txt. Registered for
both tokens in server/main.py in case "GETNEWS" turns up in some other
context we haven't captured yet.

Everything about the RESPONSE is still UNKNOWN pending a runtime capture
of the reply - no experiment attempted here yet (unlike
commands/metaarenalist.py). TODO(runtime):
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
        note="GITRNEWS request seen. No response sent - format UNKNOWN, see TODO in this file.",
    )
    # TODO(runtime): once confirmed, return the real response bytes here.
    return None
