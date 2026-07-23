"""
commands/bogus.py
------------------
Handler for BOGUS - CONFIRMED (runtime, 2026-07-23) to be sent bare by
gitr2k.exe, repeatedly, roughly every 40 seconds, while it's waiting for
a response it hasn't gotten yet (observed while a RETRARENALIST request
sat unanswered/unsatisfied). Not previously known at all, not even as a
compiled string constant we'd noticed - genuinely brand new.

Given the ~40s periodicity, this looks like a keepalive/liveness probe
rather than a one-shot "giving up" signal. It's not clear whether this
is protocol-semantic (something the server is expected to acknowledge
before the client will continue whatever it was waiting on) or just
network-level noise (some clients send junk periodically purely to keep
an idle TCP connection from being dropped by an intermediate proxy).

EXPERIMENT #1 (now live): echo BOGUS back verbatim. Cheap, safe test of
whether the client's request-in-progress needs this acknowledged before
it'll proceed, versus BOGUS being unrelated network-level noise that a
response has no effect on either way.
"""


def handle(raw: bytes, client_info: dict, context: dict):
    logger = context["logger"]
    logger.event(
        "COMMAND_SEEN",
        ip=client_info["ip"],
        port=client_info["port"],
        note=(
            "BOGUS request seen. Sending EXPERIMENT #1: echoing it back "
            "verbatim, to test whether it needs acknowledging before the "
            "client will proceed with whatever it's actually waiting on - "
            "see docstring in commands/bogus.py."
        ),
    )
    return b"BOGUS\r\n"
