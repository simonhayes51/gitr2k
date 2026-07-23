"""
protocol.py
-----------
Central place tracking what we actually know about the GITR2000 meta-server
protocol, and dispatching incoming data to the right command module - WITHOUT
assuming framing or fabricating responses that haven't been confirmed.

Confidence levels used everywhere in this project (see docs/protocol.md):
    CONFIRMED_RUNTIME     - verified by observing real client/arena traffic
    CONFIRMED_DISASSEMBLY - verified directly in the compiled binaries
    STRONG_INFERENCE      - not proven, but follows tightly from confirmed evidence
    UNKNOWN               - genuinely undetermined

KNOWN_TOKENS below lists every command-like token we have found in the
binaries via static analysis (CONFIRMED_DISASSEMBLY: the token exists in
the compiled code) or the earlier logging setup. Their presence as a string
in the binary does NOT mean we know their wire format, argument order,
delimiters, or expected response - that requires runtime capture. Treat
this list as "things to look out for", not "things we know how to speak".
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Dict

CONFIRMED_RUNTIME = "CONFIRMED (runtime)"
CONFIRMED_DISASSEMBLY = "CONFIRMED (disassembly)"
STRONG_INFERENCE = "STRONG INFERENCE"
UNKNOWN = "UNKNOWN"


@dataclass
class TokenInfo:
    token: str
    source_binary: str          # "gitr2k.exe", "arena.exe", or "both"
    confidence: str             # one of the constants above
    notes: str = ""


# Tokens confirmed to exist as literal strings in the compiled binaries.
# This is CONFIRMED_DISASSEMBLY for "this token exists in the program" only -
# NOT for wire format, delimiters, or semantics, which remain UNKNOWN until
# a real packet is captured.
KNOWN_TOKENS: Dict[str, TokenInfo] = {
    "GETNEWS":        TokenInfo("GETNEWS", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "GITRNEWS":       TokenInfo("GITRNEWS", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "ENDNEWSLIST":    TokenInfo("ENDNEWSLIST", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "GETWELCOMEMSG":  TokenInfo("GETWELCOMEMSG", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "WELCOMEMSG":     TokenInfo("WELCOMEMSG", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "METAARENALIST":  TokenInfo("METAARENALIST", "gitr2k.exe", CONFIRMED_DISASSEMBLY,
                                 "Exists exactly once in gitr2k.exe as a compiled string constant. "
                                 "Handler function NOT yet located (see docs/protocol.md)."),
    "ENDARENALIST":   TokenInfo("ENDARENALIST", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "USERENTER":      TokenInfo("USERENTER", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "USERLEAVE":      TokenInfo("USERLEAVE", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "SENDCHAT":       TokenInfo("SENDCHAT", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "CHATID":         TokenInfo("CHATID", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "BASECHAT":       TokenInfo("BASECHAT", "gitr2k.exe", CONFIRMED_DISASSEMBLY,
                                 "Used together with METAMSG inside the disassembled "
                                 "GMCCMetaMessage handler in arena.exe."),
    "METAMSG":        TokenInfo("METAMSG", "both", CONFIRMED_DISASSEMBLY,
                                 "Confirmed literal string 'METAMSG ' (with trailing space) "
                                 "used inside arena.exe's GMCCMetaMessage handler body."),
    "CHALLENGE":      TokenInfo("CHALLENGE", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "DENYCHALLENGE":  TokenInfo("DENYCHALLENGE", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "FIGHTSTART":     TokenInfo("FIGHTSTART", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "FIGHTSTOP":      TokenInfo("FIGHTSTOP", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "PINGECHO":       TokenInfo("PINGECHO", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "PING":           TokenInfo("PING", "arena.exe", CONFIRMED_DISASSEMBLY),
    "YOURIP":         TokenInfo("YOURIP", "gitr2k.exe", CONFIRMED_DISASSEMBLY),
    "SETDIVIDER":     TokenInfo("SETDIVIDER", "gitr2k.exe", CONFIRMED_DISASSEMBLY,
                                 "Suggests the field delimiter may be set dynamically by the "
                                 "server rather than being fixed. Treat delimiter as UNKNOWN "
                                 "until confirmed."),
    "CHATREQ":        TokenInfo("CHATREQ", "arena.exe", CONFIRMED_DISASSEMBLY),
    "CLAUTH":         TokenInfo("CLAUTH", "both", CONFIRMED_RUNTIME,
                                 "Not an arena.exe-only admin verb as originally assumed - this is "
                                 "the envelope wrapping every outbound command from both binaries: "
                                 "'CLAUTH <username> <password> <COMMAND> <version>\\r\\n'. "
                                 "See docs/protocol.md section 3 and captures/2026-07-23_first_real_capture.txt."),
    "FIGHTREQ":       TokenInfo("FIGHTREQ", "arena.exe", CONFIRMED_DISASSEMBLY),
    "GRANTOP":        TokenInfo("GRANTOP", "arena.exe", CONFIRMED_DISASSEMBLY),
    "KICKUSER":       TokenInfo("KICKUSER", "arena.exe", CONFIRMED_DISASSEMBLY),
    "SETADMINLIST":   TokenInfo("SETADMINLIST", "arena.exe", CONFIRMED_DISASSEMBLY),
    "SETBANLIST":     TokenInfo("SETBANLIST", "arena.exe", CONFIRMED_DISASSEMBLY),
    "SETMAXNUM":      TokenInfo("SETMAXNUM", "arena.exe", CONFIRMED_DISASSEMBLY),
    "SETWELCOMEMSG":  TokenInfo("SETWELCOMEMSG", "arena.exe", CONFIRMED_DISASSEMBLY),
    "MCC":            TokenInfo("MCC", "arena.exe", CONFIRMED_RUNTIME,
                                 "arena.exe's registration command with the meta server, sent as the "
                                 "<COMMAND> field of a CLAUTH envelope: 'CLAUTH <arena name> "
                                 "<arena password> MCC <version>\\r\\n'. Matches the GMCC component "
                                 "name found via disassembly. Response format still UNKNOWN."),
}


def parse_clauth_envelope(raw: bytes) -> Optional[dict]:
    """
    CONFIRMED (runtime, 2026-07-23): every outbound command from both
    gitr2k.exe and arena.exe is wrapped as
        CLAUTH <username> <password> <COMMAND> <version>\\r\\n
    space-delimited, CRLF-terminated. See docs/protocol.md section 3 and
    captures/2026-07-23_first_real_capture.txt.

    Returns None if `raw` doesn't match this envelope shape at all. Field
    splitting is a plain single-space split, which is known to be wrong if
    username/password ever contain spaces - no evidence either way yet,
    so this is a reasonable first pass, not a confirmed parser.
    """
    try:
        text = raw.decode("ascii", errors="strict")
    except UnicodeDecodeError:
        return None
    line = text.split("\r\n", 1)[0].split("\n", 1)[0]
    parts = line.split(" ")
    if len(parts) < 5 or parts[0].upper() != "CLAUTH":
        return None
    username, password, command, version = parts[1], parts[2], parts[3], " ".join(parts[4:])
    return {"username": username, "password": password, "command": command.upper(), "version": version}


@dataclass
class Dispatcher:
    """
    Maps a recognized command token to a handler callable. Handlers live in
    commands/*.py. A handler receives (raw_line: bytes, client_info: dict,
    context: dict) and MAY return bytes to send back - every handler in
    this project returns None unless a response has been CONFIRMED
    (runtime) or is an explicitly-labeled, disclosed experiment being
    tested against the real client, per the project's compatibility-first
    rule: "do not invent packets [without saying so]."
    """
    handlers: Dict[str, Callable] = field(default_factory=dict)

    def register(self, token: str, handler: Callable):
        self.handlers[token.upper()] = handler

    def find_candidate_token(self, raw: bytes) -> Optional[str]:
        """
        Best-effort, NON-authoritative: looks for any known token appearing
        at the start of the data (after stripping leading whitespace/CR/LF),
        up to the first space or line ending. Fallback path only, used when
        `raw` isn't a CLAUTH envelope - see dispatch() below.
        """
        stripped = raw.lstrip(b" \t\r\n")
        if not stripped:
            return None
        # Take up to the first space, CR, or LF as the candidate token.
        for sep in (b" ", b"\r", b"\n"):
            idx = stripped.find(sep)
            if idx != -1:
                candidate = stripped[:idx]
                break
        else:
            candidate = stripped

        try:
            candidate_str = candidate.decode("ascii", errors="strict").upper()
        except UnicodeDecodeError:
            return None

        if candidate_str in KNOWN_TOKENS:
            return candidate_str
        return None

    def dispatch(self, raw: bytes, client_info: dict, context: dict):
        envelope = parse_clauth_envelope(raw)
        if envelope is not None:
            token = envelope["command"]
            client_info = {**client_info, **envelope}
        else:
            token = self.find_candidate_token(raw)
        if token and token in self.handlers:
            return self.handlers[token](raw, client_info, context)
        return None
