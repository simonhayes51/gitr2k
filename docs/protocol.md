# GITR2K (Get In The Ring 2000) — Protocol Specification
**Living document. Update this file as captures/ fills in with real traffic — never upgrade a confidence level without evidence.**

Confidence levels used throughout this project:
- `CONFIRMED (runtime)` — verified by observing real client/arena traffic (a file under `captures/`).
- `CONFIRMED (disassembly)` — verified directly in the compiled binaries.
- `STRONG INFERENCE` — not proven, but follows tightly from confirmed evidence.
- `UNKNOWN` — genuinely undetermined. Marked explicitly rather than guessed.

---

## 1. Infrastructure (all CONFIRMED by disassembly)

| Fact | Value | Source |
|---|---|---|
| Meta server hostname | `GETINTR2K.MINIDNS.NET` | Default `Host` property, `TIdTCPClient`-family component, both `gitr2k.exe` (`GITRNewsList`) and `arena.exe` (`GMCC`) |
| Meta server port | `9182` | Decoded `Port` property (`0x23DE` LE) in both binaries |
| arena.exe listening port | `7072` | Decoded `Port`/`DefaultPort` properties (`0x1BA0` LE) on `arena.exe`'s `GITRServer` component |
| Registry key | `HKCU\Software\SIPSolutions\GITR2000` | `TRegAuto.RegPath` in both binaries' forms |
| Networking stack | Delphi + Indy (`TIdTCPConnection`/`TIdTCPClient`/`TIdTCPServer`) | Class names visible in compiled RTTI/DFM data |
| Resolver | Standard Winsock `gethostbyname`/`WSAAsyncGetHostByName` | Import table / string analysis — no custom DNS, no hardcoded IP fallback found |

**STRONG INFERENCE:** Windows `HOSTS` file redirection of `GETINTR2K.MINIDNS.NET` should be sufficient to point the client/arena.exe at a replacement server — no binary patching confirmed necessary. This still hasn't been tested directly (our first successful runtime test used a binary-patched client instead, on a machine without admin rights to edit `HOSTS`), so it remains unconfirmed either way.

**CONFIRMED (runtime, 2026-07-23):** Redirecting both the host and port the client/arena.exe connect to (tested via direct binary patch of the DFM-embedded `Host`/`Port` properties, not `HOSTS`) is sufficient for both clients to establish a TCP connection and begin sending real protocol traffic. See `captures/2026-07-23_first_real_capture.txt`.

---

## 2. Known protocol tokens (CONFIRMED to exist in the binaries — semantics mostly UNKNOWN)

The presence of a string in the compiled code confirms the program *recognizes* that token somewhere. It does **not** confirm argument format, delimiters, direction, or expected response — those require a runtime capture.

| Token | Found in | Direction (assumed) | Confidence of token existence | Confidence of everything else |
|---|---|---|---|---|
| `GETNEWS` | gitr2k.exe | client→server | CONFIRMED (disassembly) | UNKNOWN |
| `GITRNEWS` | gitr2k.exe | server→client | CONFIRMED (disassembly) | UNKNOWN |
| `ENDNEWSLIST` | gitr2k.exe | server→client | CONFIRMED (disassembly) | UNKNOWN |
| `GETWELCOMEMSG` / `WELCOMEMSG` | gitr2k.exe | both directions (assumed) | CONFIRMED (disassembly) | UNKNOWN |
| `METAARENALIST` | gitr2k.exe | server→client (assumed) | CONFIRMED (disassembly) — exists exactly once in the binary | UNKNOWN — handler not yet located, see §4 |
| `ENDARENALIST` | gitr2k.exe | server→client (assumed) | CONFIRMED (disassembly) | UNKNOWN |
| `USERENTER` / `USERLEAVE` | gitr2k.exe | server→client (assumed) | CONFIRMED (disassembly) | UNKNOWN |
| `SENDCHAT` / `CHATID` | gitr2k.exe | client→server (assumed) | CONFIRMED (disassembly) | UNKNOWN |
| `BASECHAT` | arena.exe | n/a — used internally as a check value | CONFIRMED (disassembly) — used inside the disassembled `GMCCMetaMessage` handler | UNKNOWN semantics |
| `METAMSG` (note: literal string is `"METAMSG "` with a trailing space) | arena.exe | server→client (assumed) | CONFIRMED (disassembly) — literal constant used in `GMCCMetaMessage` | STRONG INFERENCE that message framing is `METAMSG <space><rest of line>` |
| `CHALLENGE` / `DENYCHALLENGE` | gitr2k.exe | client↔server (assumed) | CONFIRMED (disassembly) | UNKNOWN |
| `FIGHTSTART` / `FIGHTSTOP` | gitr2k.exe | server→client (assumed) | CONFIRMED (disassembly) | UNKNOWN |
| `PINGECHO` | gitr2k.exe | client↔server (assumed keepalive) | CONFIRMED (disassembly) | UNKNOWN exact framing |
| `PING` | arena.exe | client↔server (assumed keepalive) | CONFIRMED (disassembly) | UNKNOWN exact framing |
| `YOURIP` | gitr2k.exe | server→client (assumed) | CONFIRMED (disassembly) | UNKNOWN |
| `SETDIVIDER` | gitr2k.exe | server→client (assumed) | CONFIRMED (disassembly) | **Important**: suggests the field delimiter may be assigned dynamically by the server rather than fixed. Treat the delimiter as UNKNOWN until confirmed either way. |
| `CHATREQ`, `FIGHTREQ`, `GRANTOP`, `KICKUSER`, `SETADMINLIST`, `SETBANLIST`, `SETMAXNUM`, `SETWELCOMEMSG` | arena.exe only | assumed admin/host-side commands | CONFIRMED (disassembly) | UNKNOWN |
| `CLAUTH` | both `gitr2k.exe` and `arena.exe` | client→server | CONFIRMED (runtime) — see §3, it's the envelope wrapping every outbound command, not an arena.exe-only admin verb as previously assumed | CONFIRMED (runtime) for framing/args; response format still UNKNOWN |
| `MCC` | arena.exe | client→server, as the `<COMMAND>` value inside a `CLAUTH` line | CONFIRMED (runtime) — not previously in this table at all | CONFIRMED (runtime, 2026-07-23) — arena.exe's registration/handshake with the meta server (matches the `GMCC` component name found via disassembly); acknowledged by an `OWNER <arena name>\r\n` response, see below |
| `RETRCOUNTRIES` | gitr2k.exe | client→server, sent bare (no `CLAUTH` envelope) | CONFIRMED (runtime) — not previously known | CONFIRMED (runtime) response shape — see §5 |
| `COUNTRY` | gitr2k.exe | server→client, per-country line prefix | CONFIRMED (disassembly) — found in the same string table as `METAARENALIST`/`ENDARENALIST` while investigating `RETRCOUNTRIES` | CONFIRMED (runtime) — needs a trailing arena-count field, see §5 |
| `ARENA` | gitr2k.exe | server→client, per-arena line prefix | CONFIRMED (disassembly), same table as above | STRONG INFERENCE (reused in both `METAARENALIST` and `RETRARENALIST` responses) — exact field set still being validated |
| `ENDCOUNTRYLIST` | gitr2k.exe | server→client, terminates a `RETRCOUNTRIES` response | CONFIRMED (disassembly), same table as above | CONFIRMED (runtime) — see §5 |
| `RETRARENALIST` | gitr2k.exe | client→server, sent bare with a country name argument | CONFIRMED (runtime) — brand new, not previously known at all, not even as a string constant we'd noticed | UNKNOWN — response is an active, disclosed guess, see §5 |
| `BOGUS` | gitr2k.exe | client→server, sent bare | CONFIRMED (runtime) — sent repeatedly, exactly every 40s, while a request sits unanswered | **RESOLVED (2026-07-23):** echoing it back verbatim over 6 consecutive cycles (4+ minutes) had zero effect - same 40s interval, no client behavior change. This is unrelated network-level keepalive noise, not a protocol-semantic message needing acknowledgment. No further action needed on this token. |
| `GETARENA` (literal constant is `"GETARENA "` with a trailing space) | gitr2k.exe | server→client (assumed), per-item line prefix candidate for `RETRARENALIST`'s response | CONFIRMED (disassembly) — found in the same string table as `ARENA`/`COUNTRY`/`ENDCOUNTRYLIST`, missed in the first analysis pass | UNKNOWN — being tested as of experiment #7, see §5 |
| `GRANTED` | arena.exe | UNKNOWN direction/usage | CONFIRMED (disassembly) — found near arena.exe's `GMCC.OnArenaOwner` handler | UNKNOWN — zero findable references anywhere in the binary, possibly dead code |
| `OWNER` | arena.exe | server→client, `MCC` acknowledgment token | CONFIRMED (disassembly) — found near `GMCC.OnArenaOwner`; its trivial getter function is actively referenced (unlike `GRANTED`) | **CONFIRMED (runtime, 2026-07-23)** — `OWNER <arena name>\r\n` sent in response to `MCC` causes arena.exe's activity log to show "connected" / "retrieving moves database" and unblocks three brand-new follow-up commands, see below |
| `SETPORT` | arena.exe | client→server, sent bare immediately after `MCC`/`OWNER` | CONFIRMED (runtime, 2026-07-23) — new token, not previously known | CONFIRMED (runtime) — `SETPORT <port>\r\n`, arena.exe self-reporting its real listening port (observed: `7072`), see §5 |
| `SETINFO` | arena.exe | client→server, sent bare immediately after `SETPORT` | CONFIRMED (runtime, 2026-07-23) — new token, not previously known | CONFIRMED (runtime) for shape — `SETINFO <a> <b>\r\n` (observed `0 15`); STRONG INFERENCE only for field meaning/order (assumed player_count, max_players), see §5 |
| `REQMOVES` | arena.exe | client→server, sent bare immediately after `SETINFO`, no arguments | CONFIRMED (runtime, 2026-07-23) — new token, not previously known | CONFIRMED (disassembly, 2026-07-23) — response must be a single line starting with the literal `MOVESDB` prefix; payload past the prefix still UNKNOWN, see §4/§5 |
| `MOVESDB` | arena.exe | server→client, response prefix for `REQMOVES` | CONFIRMED (disassembly, 2026-07-23) — `TMovesDBCommand` class name and response-prefix literal, found clustered with `REQMOVES` and an "invalid response" error string | CONFIRMED (disassembly) for the prefix requirement; payload shape past it UNKNOWN, see §4/§5 |

**Correction (2026-07-23):** an earlier pass of this document lumped `MOVESDB` in with `arena.exe`'s Pascal-like scripting keywords (`BEGIN`, `WHILE`, `FUNC`, `SCRIPT`, `PLUGIN`, `ACTIONSDB`, `SWEARDB`) as unrelated to the network protocol. That was **wrong for `MOVESDB` specifically** - disassembly now shows it's the real response-prefix literal for a genuine protocol command class, `TMovesDBCommand`, directly tied to the confirmed-runtime `REQMOVES` token (see §4). The other keywords in that list (`BEGIN`/`WHILE`/`FUNC`/`SCRIPT`/`PLUGIN`/`ACTIONSDB`) remain believed unrelated - they belong to an embedded scripting/plugin engine - but this should be treated as unconfirmed rather than dismissed outright, given this correction. `SWEARDB` (with request token `REQSWLIST`) turns out to be a near-identical sibling command class to `TMovesDBCommand`, likely a swear-word/chat-filter list - also a real protocol command, not a scripting keyword.

---

## 3. Login / authentication

**CONFIRMED (runtime, 2026-07-23)** — see `captures/2026-07-23_first_real_capture.txt`. Every outbound command from both clients is wrapped in a single-line envelope:

```
CLAUTH <username> <password> <COMMAND> <version>\r\n
```

- Fields are space-delimited (confirmed: exactly 4 spaces in every captured line, 5 fields total including `CLAUTH` itself), line-terminated with `\r\n`.
- This is sent **immediately on connect, before any other handshake** — answers open question #1 from §6. There is no separate login/handshake step before commands become meaningful; `CLAUTH` *is* the envelope, sent per-command, not once per session.
- Observed `<username>`/`<password>` values so far:
  - `gitr2k.exe` requesting `GITRNEWS` on startup: `NIL NIL` (both literal string `"NIL"`)
  - `gitr2k.exe` requesting `METAARENALIST` (from the arena-select dialog): empty-string username, literal `"NIL"` password — i.e. these two fields are **not** filled in consistently from one command to the next by the same unauthenticated session. Worth resolving once we've captured a command sent *after* an actual login.
  - `arena.exe` requesting `MCC`: username `"Test"` (the literal arena name typed into its GUI), password `"none"` (literal word, distinct from `gitr2k.exe`'s `"NIL"` placeholder)
- `<version>` was `0` in all three captures so far — UNKNOWN whether this is a fixed protocol version or something else entirely.
- Still **UNKNOWN**: what a real login (`Login as a Guest User` / `Register a Username` / `Login with current Username`) actually sends — none of our captures so far came from clicking those options.

**CONFIRMED (runtime, 2026-07-23, second session):** the `CLAUTH` envelope only wraps the *first* message sent on a connection — subsequent commands on the same already-open connection are sent bare, with no envelope at all. Observed directly: after receiving a response to `METAARENALIST`, `gitr2k.exe` sent a bare `RETRCOUNTRIES\r\n` on that same connection (see `captures/2026-07-23_first_real_capture.txt`, second session).

`RETRCOUNTRIES` is a previously-unknown token, discovered only because the real client sent it. Investigating it turned up `COUNTRY`, `ARENA`, and `ENDCOUNTRYLIST` as compiled string constants in `gitr2k.exe`, sitting in the *same* string-constant table as `METAARENALIST`/`ENDARENALIST` — real anchors we didn't know to look for before this. This is what the "Select Arena" dialog's "retrieving country list" status text is actually waiting on; the `METAARENALIST` response alone didn't satisfy it. See `commands/retrcountries.py` for the follow-up experimental response (untested as of this writing).

**CONFIRMED (runtime, 2026-07-23) - the real arena-discovery flow is a three-stage lazy hierarchy**, established by iterating the `RETRCOUNTRIES` response until the client accepted it, then observing what it did next:

1. `METAARENALIST` → still-unconfirmed ack/stub response
2. `RETRCOUNTRIES` → `COUNTRY <name> <arena_count>\r\n` per country, then `ENDCOUNTRYLIST\r\n` — **this exact shape is confirmed working**: the "Select Arena" tree populates cleanly (verified with an "International" node showing count 1)
3. `RETRARENALIST <country>` → sent automatically by the client once (2) succeeds, requesting that one country's actual arena details. A brand-new command, not previously known at all. Response is an active, disclosed guess (see `commands/retrarenalist.py`) reusing the already-known `ARENA`/`ENDARENALIST` tokens.

Also observed: `BOGUS\r\n`, sent bare ~38 seconds after a `RETRARENALIST` request got no response. **RESOLVED (2026-07-23):** confirmed via 6 observed cycles over 4+ minutes to repeat exactly every 40 seconds regardless of server response; echoing it back had zero effect. Concluded to be unrelated network-level keepalive noise, not a protocol-semantic message.

**CONFIRMED (runtime, 2026-07-23) — the `MCC` (arena registration) handshake is now unblocked.** After `RETRARENALIST` guessing stalled (7 attempts, all rejected/inconclusive), work shifted to arena.exe's registration flow instead, which had been stuck the entire time: its "Start" button stayed permanently disabled and its activity log stayed empty across every prior test, with no response ever sent to `MCC`. Sending `OWNER <arena name>\r\n` (e.g. `OWNER Test\r\n`) in response to `MCC` produced an immediate, real client reaction:

- arena.exe's activity log showed **"connected"** and then **"retrieving moves database"**
- three brand-new bare commands appeared on the same connection, in order: `SETPORT 7072\r\n`, then `SETINFO 0 15\r\n`, then `REQMOVES\r\n`

This confirms `OWNER <arena name>\r\n` is the correct (or at least sufficient) `MCC` acknowledgment. `SETPORT`/`SETINFO` are arena.exe self-reporting its real listening port and stats back to the meta server — both are now parsed and recorded into `ArenaRegistry` (see `commands/setport.py`, `commands/setinfo.py`, `server/registry.py`). `REQMOVES` matches the "retrieving moves database" status text but its response format is completely unknown; the server currently only observes/logs it (see `commands/reqmoves.py`) rather than guessing blind, per this project's isolate-one-variable methodology.

Since `SETPORT`/`SETINFO`/`REQMOVES` are all sent bare with no arena name repeated, they're correlated back to the arena that registered via `MCC` earlier on the same connection through the per-connection `context` dict (`context["arena_name"]`, set once by `commands/mcc.py` and read by the later handlers).

**Bug found and fixed (2026-07-23, same session):** the real capture showed `SETINFO 0 15\r\n` and `REQMOVES\r\n` arriving **coalesced in a single TCP `recv()`** (`SETINFO 0 15\r\nREQMOVES\r\n`, one packet). The server's connection handler previously passed each raw `recv()` chunk straight to the dispatcher unsplit, and the dispatcher only inspects the *first* token of whatever bytes it's given - so `REQMOVES` was silently dropped: never dispatched, never logged as `COMMAND_SEEN`. Fixed in `server/connection.py` by buffering incoming bytes and splitting on line boundaries (`\n`) before dispatching each line separately, so every command gets its own `dispatch()` call regardless of how the client batches them on the wire. This means arena.exe (and possibly gitr2k.exe) can and does coalesce multiple commands into one TCP segment - worth remembering for any future capture where a command "goes missing" from the log.

---

## 4. Dispatcher / handler functions located via disassembly

Using Delphi's compiled **published-method RTTI table** (maps component event properties to real function addresses — a reliable technique, not string-guessing):

| Event | Method | Address (arena.exe) | Status |
|---|---|---|---|
| `GMCC.OnMetaMessage` | `GMCCMetaMessage` | `0x0049F80C` | CONFIRMED (disassembly) — full body disassembled, see below |
| `GMCC.OnArenaOwner` | `GMCCArenaOwner` | `0x0049F8F0` | CONFIRMED (disassembly) — body analyzed (2026-07-23): a tiny event-relay stub (~20 bytes, forwards to a generic dispatch helper at `0x403188` with a constant `0xFFED`), not directly informative about wire format. But the nearby string-constant table led to `GRANTED`/`OWNER` (see §2, §5) - `OWNER` is now CONFIRMED (runtime) as the `MCC` acknowledgment. |
| `GMCC.OnDisconnected` | `GMCCDisconnected` | not yet extracted | UNKNOWN address |
| `GMCC.OnError` | `GMCCError` | not yet extracted | UNKNOWN address |

### `GMCCMetaMessage` (0x49F80C–0x49F890) — CONFIRMED disassembly summary

```
if Pos('BASECHAT', Self.field_at_0x2D4) <> 0 then
    ; calls an internal routine twice with the literal string "METAMSG "
    ; (8 bytes, includes trailing space) as one operand, then calls
    ; another internal routine using Self.field_at_0x300
    ; -> STRONG INFERENCE: this appends/displays a "METAMSG <text>"
    ;    formatted chat line
else
    ; falls through to cleanup, does nothing
```

This function does **not** reference `METAARENALIST` anywhere in its body — that command's handler is still UNKNOWN / not located. It's either in a different branch of a larger dispatcher not yet mapped, or reached through a different event entirely.

Internal helper addresses referenced but not identified: `0x45A36C` (calling convention matches `System.Pos`), `0x403FA0` (called twice with `"METAMSG "` — purpose unconfirmed), `0x462FA0` (purpose unconfirmed). These would be worth revisiting once real `METAMSG` traffic is captured, since we'll then have ground truth to check candidate interpretations against.

### `TMovesDBCommand` (arena.exe VA `0x461d34`–`0x461e92`) — CONFIRMED disassembly summary

Located (2026-07-23) via exhaustive raw-bytes cross-reference search for the compiled `"REQMOVES"` (VA `0x461ef4`) and `"MOVESDB"` (VA `0x461f14`) string constants - each has exactly one reference in the whole binary, both inside this single method. A near-identical sibling method exists nearby (VA `0x461f38`–`0x462096`) referencing `"REQSWLIST"`/`"SWEARDB"` instead - same shape, different literals, confirming a small family of "request a named database" command classes rather than a one-off.

```
procedure TMovesDBCommand.Execute(Self, P2: <unknown>);
begin
  Self.SomeMethod();                          ; VMT+0x84 call below actually sends the command
  list_obj := SomeGlobal.Create(...);          ; VA 0x461728, via helper 0x402f7c

  Self.SendCommand("REQMOVES");                ; virtual call, VMT+0x84 - matches confirmed wire traffic
  received_line := Self.ReadLn(Terminator:="\r\n", MaxLen:=-2);  ; virtual call, VMT+0x74 - ONE line only, no loop
  prefix7 := Copy(received_line, 1, 7);         ; System.Copy via helper 0x40415c

  if CompareStr(prefix7, "MOVESDB") <> 0 then   ; helper 0x404064
      raise EInvalidResponse.Create("invalid response")   ; string at VA 0x461f24
  else
      Self.field_0xC4.SomeParseMethod(received_line);      ; virtual call, VMT+0x9c - full line, not just remainder
end;
```

Key findings, all CONFIRMED (disassembly):
- The response to `REQMOVES` is read with a **single** `ReadLn`-shaped call - no loop back for further lines, unlike the multi-line-plus-terminator shape used by `RETRCOUNTRIES`/`RETRARENALIST`/`METAARENALIST`. STRONG INFERENCE: the response is exactly one line.
- That line's first 7 characters **must** equal the literal `"MOVESDB"`, or arena.exe raises/logs an `"invalid response"` error internally (same error string and same code shape reused by the `SWEARDB` sibling class).
- If the prefix matches, the **entire line** (prefix included) is handed to a further virtual method (`VMT+0x9c`) not disassembled this pass - so the exact fields expected after `"MOVESDB"` remain UNKNOWN. See `commands/reqmoves.py` for the disclosed first experiment (`MOVESDB\r\n`, bare) built on this evidence.

**Dead end found (2026-07-23):** traced the `"METAARENALIST"` string constant (in gitr2k.exe) to a tiny function at `0x54D01C` that does nothing but return that literal (classic Delphi codegen for `Result := 'METAARENALIST'` — almost certainly a command-name getter on one class in a family of protocol-message classes). Static cross-reference analysis (radare2, full `aaa` auto-analysis, 5353 functions found) turned up **zero callers** of that function. This strongly suggests it's invoked through a Delphi virtual-method-table slot (polymorphic dispatch) rather than a direct call instruction — tracing that needs Delphi-VMT/RTTI-aware tooling (e.g. IDA with Delphi analysis, or "Interactive Delphi Reconstructor") that wasn't available for this pass. Static disassembly is stalled here for now; see §5/§6 for the empirical approach taken instead.

---

## 5. Recovered protocol — command table

*(To be filled in as `captures/` gets real data. Structure ready; nothing here should be invented ahead of evidence.)*

| Command | Direction | Args | Delimiter | Example packet | Meaning | Expected response | Confidence |
|---|---|---|---|---|---|---|---|
| `GITRNEWS` | client→server | username, password | space, `\r\n` terminated | `CLAUTH NIL NIL GITRNEWS 0\r\n` | gitr2k.exe requesting the news bulletin on startup | UNKNOWN (see `GITRNEWS`/`ENDNEWSLIST` tokens in §2) | CONFIRMED (runtime) for the request; response UNKNOWN |
| `METAARENALIST` | client→server | username, password | space, `\r\n` terminated | `CLAUTH  NIL METAARENALIST 0\r\n` | gitr2k.exe requesting the arena list for the "Select Arena" dialog | **ACTIVE EXPERIMENT (2026-07-23, unconfirmed):** server now replies `METAARENALIST <name> <player_count> <max_players>\r\n` per registered arena, then bare `ENDARENALIST\r\n`. Guessed by symmetry with `GETNEWS`/`GITRNEWS`/`ENDNEWSLIST`, not derived from disassembly (see the dead-end note in §4). Awaiting real client reaction as validation - does the arena-select dialog actually populate? | CONFIRMED (runtime) for the request; response is a disclosed guess, not confirmed |
| `MCC` | client→server | arena name, arena password | space, `\r\n` terminated | `CLAUTH Test none MCC 0\r\n` | arena.exe registering itself with the meta server | **CONFIRMED (runtime, 2026-07-23):** `OWNER <arena name>\r\n`, e.g. `OWNER Test\r\n` - informed by the `GMCC.OnArenaOwner` event and the `OWNER` string constant found near it (see §2, §4). Real client reaction observed: activity log shows "connected" / "retrieving moves database", and arena.exe sends `SETPORT`/`SETINFO`/`REQMOVES` in response (see rows below). GRANTED was never needed since this worked on the first attempt. | **CONFIRMED (runtime)** |
| `RETRCOUNTRIES` | client→server | *(none - sent bare)* | `\r\n` terminated, no envelope | `RETRCOUNTRIES\r\n` | gitr2k.exe requesting the country list for the "Select Arena" tree, sent on the same connection right after a `METAARENALIST` response | **CONFIRMED (runtime, 2026-07-23):** `COUNTRY <name> <arena_count>\r\n` per country, then bare `ENDCOUNTRYLIST\r\n`. The "Select Arena" tree populates cleanly (verified: an "International" node showing count 1, no error) - the first fully client-validated response format in this project. Getting here took 3 rejected/isolating attempts (see git history for `commands/retrcountries.py`): omitting the trailing count field, or including any `ARENA` sub-lines, both produced "an error has occured." | **CONFIRMED (runtime)** |
| `RETRARENALIST` | client→server | country name | `\r\n` terminated, no envelope | `RETRARENALIST International\r\n` | gitr2k.exe requesting the actual per-arena details for one country, sent automatically right after a working `RETRCOUNTRIES` response - not previously known at all, not even as a compiled string constant we'd noticed | **Seven attempts, none confirmed working yet. PAUSED (2026-07-23) per project direction** - work shifted to the `MCC` handshake instead, see below. Six straight `ARENA`-prefixed shapes error outright. **Experiment #7 (`GETARENA <name> <players> <max>\r\n`)** doesn't error, but doesn't resolve either - the client just keeps waiting (confirmed via the periodic `BOGUS` keepalive, since resolved as unrelated noise, see §2/§3). **Correction:** experiment #2 (bare `ENDARENALIST`, empty list) was only ever confirmed "doesn't error immediately" - never actually confirmed to complete, so its "CONFIRMED WORKING" status upgrade earlier was premature. | CONFIRMED (runtime) for the request; response format still unconfirmed after 7 attempts, paused |
| `SETPORT` | client→server | port | space, `\r\n` terminated, no envelope | `SETPORT 7072\r\n` | arena.exe self-reporting its real listening port, sent bare right after `MCC`/`OWNER` | **CONFIRMED (runtime, 2026-07-23):** parsed and recorded into `ArenaRegistry`, replacing the `DEFAULT_ARENA_PORT` placeholder (see `commands/setport.py`, `server/registry.py`). Correlated to the right arena via `context["arena_name"]`. No response sent by the server. | **CONFIRMED (runtime)** for the request; no response attempted/needed so far |
| `SETINFO` | client→server | two integers | space, `\r\n` terminated, no envelope | `SETINFO 0 15\r\n` | arena.exe self-reporting live stats, sent bare right after `SETPORT` | **CONFIRMED (runtime, 2026-07-23)** for the shape; parsed and recorded as `(player_count, max_players)` - **STRONG INFERENCE only** for that field order/meaning, since both observed values (`0`, `15`) are consistent with either order for a freshly-started, empty arena. See `commands/setinfo.py`. No response sent. | **CONFIRMED (runtime)** for the request shape; field semantics STRONG INFERENCE |
| `REQMOVES` | client→server | *(none - sent bare)* | `\r\n` terminated, no envelope | `REQMOVES\r\n` | arena.exe requesting some kind of moves/moveset database, sent bare right after `SETINFO`; matches the "retrieving moves database" UI status text | **EXPERIMENT #1 (2026-07-23), informed by disassembly:** bare `MOVESDB\r\n`. The `TMovesDBCommand` handler (§4) CONFIRMS (disassembly) the response must be a single line starting with the literal 7-char prefix `MOVESDB`, or an internal `"invalid response"` error is raised - but the payload past that prefix is still an open guess. Awaiting real client reaction. | CONFIRMED (runtime) for the request; response prefix CONFIRMED (disassembly), payload shape still a disclosed guess |

---

## 6. Open questions to resolve first (priority order)

1. ~~**What does the client send immediately on connect?**~~ **ANSWERED (2026-07-23):** `CLAUTH <username> <password> <COMMAND> <version>\r\n`, sent per-command rather than once per session — see §3.
2. **Is there a fixed delimiter, or does the server send `SETDIVIDER` to set one dynamically?** Space-delimiter confirmed for the `CLAUTH` envelope itself; still UNKNOWN whether per-command payloads (once we have responses) use the same delimiter or something set by `SETDIVIDER`.
3. **Does `HOSTS` file redirection alone work**, or does the client perform some check that requires further investigation? Still untested — our first successful connection used a binary-patched client instead (see §1), on a machine without admin rights to test `HOSTS` directly.
4. ~~**What does arena.exe send to register an arena, and what response completes the handshake?**~~ **ANSWERED (2026-07-23):** request is `CLAUTH <arena name> <arena password> MCC 0\r\n`; response is `OWNER <arena name>\r\n` — CONFIRMED (runtime): arena.exe's activity log shows "connected"/"retrieving moves database" and it proceeds to send `SETPORT`/`SETINFO`/`REQMOVES` — see §3/§5. Still open: does arena.exe's "Start" button ever actually enable, and does anything further happen once `REQMOVES` gets no response? (new open question #12, below)
5. **What is the real `METAARENALIST` response format?** Static disassembly stalled (see the dead-end note in §4 — the handler is almost certainly reached via Delphi virtual dispatch, untraceable with the tooling available). **Switched to empirical testing (2026-07-23):** a disclosed, guessed response is now live on the server (see §5's `METAARENALIST` row) - next step is observing whether the real client's "Select Arena" dialog actually populates from it, and iterating based on that reaction.
6. ~~**What response ends the arena.exe registration handshake (`MCC`)?**~~ **ANSWERED (2026-07-23):** `OWNER <arena name>\r\n` — see #4 above and §3/§5.
7. **Bug fixed in the same pass:** the server's dispatcher previously looked at the *first word* of each line to decide which command handler to call - which was always `CLAUTH`, for which no handler was ever registered. This meant **no command handler had ever actually fired**, for any of the three 2026-07-23 captures, despite them being logged. Fixed by parsing the `CLAUTH` envelope and dispatching on its embedded `<COMMAND>` field instead (`server/protocol.py`, `parse_clauth_envelope`).
8. **What is the real `RETRCOUNTRIES` response format?** New as of the second 2026-07-23 session - see §3/§5. An experimental response built from real `COUNTRY`/`ARENA`/`ENDCOUNTRYLIST` string constants is deployed; awaiting the next real client reaction (does the "Select Arena" tree actually populate now, with a country node and the registered arena under it?).
9. ~~**Is there a separate per-country terminator, or does `ENDCOUNTRYLIST` alone end everything?**~~ **ANSWERED (2026-07-23):** `ENDCOUNTRYLIST` alone ends the `RETRCOUNTRIES` response - CONFIRMED working with `COUNTRY <name> <arena_count>\r\n` lines and no nested `ARENA`/`ENDARENALIST` inside it. Arenas for a given country are fetched separately, lazily, via `RETRARENALIST <country>` - see §3.
10. **What is the real `RETRARENALIST` response format?** New as of the sixth 2026-07-23 session. An experimental response reusing `ARENA`/`ENDARENALIST` is deployed; awaiting the next real client reaction.
11. ~~**What does `BOGUS` mean, and does it need a response?**~~ **RESOLVED (2026-07-23):** confirmed periodic (every ~40s) regardless of server response; echoing it back had zero effect. Unrelated network-level keepalive noise, not protocol-semantic. No further action needed.
12. **What is the real `REQMOVES` response format, and does arena.exe's "Start" button ever enable?** Framing bug fixed (2026-07-23) - `REQMOVES` now correctly reaches `commands/reqmoves.py` and is logged. Static analysis (2026-07-23, second pass) then found `TMovesDBCommand` in arena.exe, CONFIRMING (disassembly) that the response must be a single line with a literal `MOVESDB` prefix - see §4. **Experiment #1 (bare `MOVESDB\r\n`) is now live** - the payload past the prefix is still an open guess. Next real test should report: does arena.exe accept it (does "Start" ever enable, does the log move past "retrieving moves database")? Does it show an internal error? Does `REQMOVES` retry if the response is rejected, like `BOGUS` did when unanswered?

Update the table in §5 and the confidence markers throughout this document as each of these gets resolved — and please don't upgrade a confidence marker without a corresponding file in `captures/` (for runtime) or a specific address/offset (for disassembly) to point to.
