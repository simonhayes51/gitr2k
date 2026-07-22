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

**STRONG INFERENCE:** Windows `HOSTS` file redirection of `GETINTR2K.MINIDNS.NET` should be sufficient to point the client/arena.exe at a replacement server — no binary patching confirmed necessary. This should be verified empirically the first time the server is run against a real client (see §6).

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
| `CHATREQ`, `CLAUTH`, `FIGHTREQ`, `GRANTOP`, `KICKUSER`, `SETADMINLIST`, `SETBANLIST`, `SETMAXNUM`, `SETWELCOMEMSG` | arena.exe only | assumed admin/host-side commands | CONFIRMED (disassembly) | UNKNOWN |

**Note:** `arena.exe` also contains Pascal-like scripting keywords (`BEGIN`, `WHILE`, `FUNC`, `SCRIPT`, `PLUGIN`, `ACTIONSDB`, `MOVESDB`, `SWEARDB`). These belong to an embedded scripting/plugin engine, unrelated to the network protocol, and are intentionally excluded from the table above.

---

## 3. Login / authentication (UNKNOWN)

No confirmed login/handshake sequence has been found. What we do know:

- `GITRNewsList`/`GMCC` connection defaults include `Authorization = atClear`, `Username = "NIL"`, `Password = "NIL"` — but these property names match Indy's SOCKS-proxy configuration convention as much as they match a hypothetical game-login mechanism, so this is **UNKNOWN**, not confirmed, whether it reflects real credentials or unused proxy defaults.
- UI captions "Login as a Guest User" and "Login with current Username" exist, and a `GUEST` token exists — but no clean `LOGIN`/`LOGON` wire-protocol verb has been found in either binary's strings.
- **TODO(runtime):** capture the very first bytes the client sends after connecting — this is the highest-priority open question, since without it we can't confirm whether any handshake/auth step happens before other commands are meaningful.

---

## 4. Dispatcher / handler functions located via disassembly

Using Delphi's compiled **published-method RTTI table** (maps component event properties to real function addresses — a reliable technique, not string-guessing):

| Event | Method | Address (arena.exe) | Status |
|---|---|---|---|
| `GMCC.OnMetaMessage` | `GMCCMetaMessage` | `0x0049F80C` | CONFIRMED (disassembly) — full body disassembled, see below |
| `GMCC.OnArenaOwner` | `GMCCArenaOwner` | `0x0049F8F0` | CONFIRMED (disassembly) — location only, body not yet analyzed |
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

---

## 5. Recovered protocol — command table

*(To be filled in as `captures/` gets real data. Structure ready; nothing here should be invented ahead of evidence.)*

| Command | Direction | Args | Delimiter | Example packet | Meaning | Expected response | Confidence |
|---|---|---|---|---|---|---|---|
| *(none yet — awaiting first capture)* | | | | | | | |

---

## 6. Open questions to resolve first (priority order)

1. **What does the client send immediately on connect?** (Answers: login/handshake existence, first-command framing, whether `SETDIVIDER` shows up early.)
2. **Is there a fixed delimiter, or does the server send `SETDIVIDER` to set one dynamically?** This affects how every other field should be parsed, so needs resolving before trusting any other field-splitting.
3. **Does `HOSTS` file redirection alone work**, or does the client perform some check that requires further investigation?
4. **What does arena.exe send to register an arena** with the meta server? (Needed for Phase 4 — populating `ArenaRegistry` from real registration traffic rather than guesswork.)
5. **What is the real `METAARENALIST` response format** — field order, per-arena delimiter, whether `ENDARENALIST` terminates the list.

Update the table in §5 and the confidence markers throughout this document as each of these gets resolved — and please don't upgrade a confidence marker without a corresponding file in `captures/` (for runtime) or a specific address/offset (for disassembly) to point to.
