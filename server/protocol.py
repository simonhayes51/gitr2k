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
                                 "name found via disassembly. Response CONFIRMED (runtime, 2026-07-23): "
                                 "'OWNER <arena name>\\r\\n' causes arena.exe's activity log to show "
                                 "'connected'/'retrieving moves database' and triggers three new bare "
                                 "follow-up commands: SETPORT, SETINFO, REQMOVES. See commands/mcc.py "
                                 "and captures/2026-07-23_first_real_capture.txt."),
    "RETRCOUNTRIES":  TokenInfo("RETRCOUNTRIES", "gitr2k.exe", CONFIRMED_RUNTIME,
                                 "Sent bare (no CLAUTH envelope) immediately after a METAARENALIST "
                                 "response, on the same connection - this is what the 'Select Arena' "
                                 "dialog's 'retrieving country list' status is actually waiting on. "
                                 "See docs/protocol.md section 3."),
    "COUNTRY":        TokenInfo("COUNTRY", "gitr2k.exe", CONFIRMED_DISASSEMBLY,
                                 "Found in the same string-constant table as METAARENALIST/"
                                 "ENDARENALIST while investigating RETRCOUNTRIES. Assumed per-country "
                                 "line prefix in the (experimental, unconfirmed) RETRCOUNTRIES response."),
    "ARENA":          TokenInfo("ARENA", "gitr2k.exe", CONFIRMED_DISASSEMBLY,
                                 "Found alongside COUNTRY/ENDCOUNTRYLIST. Assumed per-arena line prefix "
                                 "in the (experimental, unconfirmed) RETRCOUNTRIES response."),
    "ENDCOUNTRYLIST": TokenInfo("ENDCOUNTRYLIST", "gitr2k.exe", CONFIRMED_DISASSEMBLY,
                                 "Assumed terminator for the (experimental, unconfirmed) "
                                 "RETRCOUNTRIES response."),
    "RETRARENALIST":  TokenInfo("RETRARENALIST", "gitr2k.exe", CONFIRMED_RUNTIME,
                                 "Not previously known at all (not found via static analysis). "
                                 "Sent bare, with a country name argument, immediately after a "
                                 "successful RETRCOUNTRIES response: "
                                 "'RETRARENALIST <country name>\\r\\n'. Confirms a three-stage "
                                 "lazy hierarchy: METAARENALIST -> RETRCOUNTRIES -> "
                                 "RETRARENALIST <country>. See docs/protocol.md section 3."),
    "GRANTED":        TokenInfo("GRANTED", "arena.exe", CONFIRMED_DISASSEMBLY,
                                 "Found (2026-07-23) clustered with OWNER near arena.exe's "
                                 "GMCC.OnArenaOwner handler. Zero findable references anywhere in "
                                 "the binary - possibly dead code, or referenced through addressing "
                                 "this analysis pass couldn't trace."),
    "OWNER":          TokenInfo("OWNER", "arena.exe", CONFIRMED_RUNTIME,
                                 "Found (2026-07-23) clustered with GRANTED near arena.exe's "
                                 "GMCC.OnArenaOwner handler (docs/protocol.md section 4, previously "
                                 "unanalyzed). Its trivial getter function IS referenced once, "
                                 "unlike GRANTED. CONFIRMED (runtime, 2026-07-23) as the MCC "
                                 "acknowledgment: 'OWNER <arena name>\\r\\n' sent in response to MCC "
                                 "unblocks arena.exe's registration flow (real, observed client "
                                 "reaction - see commands/mcc.py)."),
    "GETARENA":       TokenInfo("GETARENA", "gitr2k.exe", CONFIRMED_DISASSEMBLY,
                                 "Found (2026-07-23, second static analysis pass) as a distinct "
                                 "9-byte constant 'GETARENA ' (trailing space baked in, same pattern "
                                 "as confirmed METAMSG), separate from the 5-byte 'ARENA' constant. "
                                 "Being tried as the RETRARENALIST per-item line prefix after six "
                                 "straight rejections of ARENA-prefixed guesses."),
    "BOGUS":          TokenInfo("BOGUS", "gitr2k.exe", CONFIRMED_RUNTIME,
                                 "Sent bare, repeatedly (~every 40s, confirmed periodic - not a "
                                 "one-shot signal) while a request sits unanswered/unsatisfied. "
                                 "Purpose still UNKNOWN - being tested (echo it back) to see if "
                                 "acknowledging it unblocks whatever the client is actually waiting "
                                 "on, versus it being unrelated network-level keepalive noise. "
                                 "RESOLVED (2026-07-23): observed over 6 cycles / 4+ minutes with a "
                                 "fixed ~40s period regardless of server response; echoing it back "
                                 "had zero effect. Concluded to be unrelated network-level keepalive "
                                 "noise, not protocol-semantic."),
    "SETPORT":        TokenInfo("SETPORT", "arena.exe", CONFIRMED_RUNTIME,
                                 "Sent bare (no CLAUTH envelope) on the same connection immediately "
                                 "after arena.exe receives the MCC/OWNER acknowledgment: "
                                 "'SETPORT <port>\\r\\n'. Observed value 7072, matching the "
                                 "CONFIRMED (disassembly) default listening port. Correlated back to "
                                 "the registering arena via the per-connection context dict's "
                                 "arena_name (set by commands/mcc.py), since this command does not "
                                 "repeat the arena name. No response sent by the server (untested "
                                 "whether one is expected). See commands/setport.py."),
    "SETINFO":        TokenInfo("SETINFO", "arena.exe", CONFIRMED_RUNTIME,
                                 "Sent bare immediately after SETPORT on the same connection: "
                                 "'SETINFO <a> <b>\\r\\n'. Observed values '0 15'. Field order "
                                 "(player_count then max_players) is STRONG_INFERENCE from typical "
                                 "convention, not independently confirmed - both observed numbers are "
                                 "consistent with either order for a freshly-started, empty arena. "
                                 "See commands/setinfo.py."),
    "MOVESDB":        TokenInfo("MOVESDB", "arena.exe", CONFIRMED_DISASSEMBLY,
                                 "Found (2026-07-23) as arena.exe's 'TMovesDBCommand' class name, "
                                 "clustered with 'REQMOVES' and an 'invalid response' error string. "
                                 "Previously misclassified in this project as an unrelated "
                                 "Pascal-scripting keyword - that was WRONG, it's a real protocol-related "
                                 "class. CORRECTED (runtime+disassembly cross-validated, 2026-07-23): the "
                                 "response must NOT be an exact match to the literal 'MOVESDB' (first 7 "
                                 "chars) - sending exactly that triggers arena.exe's 'invalid response' "
                                 "exception, confirmed both by re-reading the _LStrCmp-based equality "
                                 "check correctly and by the real client's reaction to the (now known "
                                 "wrong) first experiment. RETRACTED (2026-07-23, fourth pass): an "
                                 "earlier claim that this chains directly into REQACTIONS/ACTIONSDB via a "
                                 "specific VMT+0x9c virtual dispatch was based on disassembling raw DATA "
                                 "as if it were code (confirmed by direct byte dump) - the mechanism by "
                                 "which (if at all) this reaches the Actions stage is UNCONFIRMED. A "
                                 "genuinely solid, separately-found fact: TMovesDBCommand.Execute, "
                                 "TActionsDBCommand.Execute, TSwearDBCommand.Execute, and a 4th "
                                 "not-previously-known Execute (sends 'WINDB ') sit together as a clean "
                                 "4-entry function-pointer array at VA 0x461686 - found by searching for "
                                 "TMovesDBCommand.Execute's own confirmed address as raw data, not by "
                                 "offset guessing. What content the 'success' path of MOVESDB actually "
                                 "expects remains UNKNOWN. See commands/reqmoves.py."),
    "ACTIONSDB":      TokenInfo("ACTIONSDB", "arena.exe", CONFIRMED_DISASSEMBLY,
                                 "Found (2026-07-23) as a sibling command class to MOVESDB/SWEARDB - "
                                 "TActionsDBCommand.Execute (VA 0x461b2c, independently confirmed via a "
                                 "clean disassembly with a proper function prologue). Its request token "
                                 "is 'REQACTIONS' (10 chars); its handler has the identical shape as "
                                 "TMovesDBCommand's - reads one line, rejects an exact match to the "
                                 "literal 'ACTIONSDB' (9 chars) via the same 'invalid response' error. "
                                 "Whether/how TMovesDBCommand actually reaches this stage is UNCONFIRMED "
                                 "(an earlier claim of a direct VMT-dispatched chain was retracted - see "
                                 "MOVESDB). Not yet observed on the wire. Previously grouped (wrongly, "
                                 "like MOVESDB) with unrelated scripting keywords."),
    "REQACTIONS":     TokenInfo("REQACTIONS", "arena.exe", CONFIRMED_DISASSEMBLY,
                                 "Found (2026-07-23) as the request token sent by TActionsDBCommand.Execute "
                                 "(VA 0x461b2c), a sibling of REQMOVES/MOVESDB found via the same 4-entry "
                                 "Execute-pointer array at VA 0x461686. Not yet observed on the wire - see "
                                 "ACTIONSDB."),
    "WINDB":          TokenInfo("WINDB", "arena.exe", CONFIRMED_DISASSEMBLY,
                                 "Found (2026-07-23) as the 4th entry in the same Execute-pointer array as "
                                 "REQMOVES/REQACTIONS/REQSWLIST's handlers (VA 0x461686), at VA 0x4624a8. "
                                 "FULLY REVERSED (2026-07-23, fifth pass) - complete function body traced "
                                 "start to ret, nothing omitted: builds 'WINDB ' (VA 0x462538, 6 bytes, "
                                 "trailing space) + Arg1 + ' ' (VA 0x462548) + Arg2 via System._LStrCatN "
                                 "(traced directly to confirm argument order - it processes pushed args in "
                                 "push order, not reversed), giving the exact command 'WINDB <Arg1> <Arg2>' "
                                 "(Arg1=method's edx-param, Arg2=ecx-param), sent via the same +0x84 "
                                 "SendCommand slot as the other three. CONFIRMED: no ReadLn-shaped call or "
                                 "any response-processing logic exists anywhere in this function - it sends "
                                 "and returns immediately, does not wait for a reply. Whether/when arena.exe "
                                 "invokes it (participates in startup or not) is UNCONFIRMED - like the "
                                 "other three, it has zero external cross-references anywhere in the binary "
                                 "(no CALL/JMP site, no raw pointer outside the table itself). Purpose "
                                 "UNKNOWN - name suggests a match win/loss or results report."),
    "REQMOVES":       TokenInfo("REQMOVES", "arena.exe", CONFIRMED_RUNTIME,
                                 "Sent bare immediately after SETINFO on the same connection, with no "
                                 "arguments: 'REQMOVES\\r\\n'. Matches arena.exe's 'retrieving moves "
                                 "database' UI status text. CONFIRMED (disassembly, 2026-07-23): "
                                 "arena.exe's TMovesDBCommand reads exactly one response line and "
                                 "rejects it (raises 'invalid response') if it exactly matches the "
                                 "7-char literal 'MOVESDB' - the opposite of what an earlier reading of "
                                 "this same disassembly concluded. What response IS accepted remains "
                                 "UNKNOWN; no response currently sent. See commands/reqmoves.py."),
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
