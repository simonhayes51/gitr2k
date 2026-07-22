"""
logger.py
---------
Structured logging and packet-capture writer for the GITR2K meta server
replacement.

This module does NOT assume anything about the protocol. It records raw
bytes exactly as received/sent, and separately runs best-effort *heuristic*
detection (line endings, candidate delimiters, printable-vs-binary ratio)
purely as an aid for a human reviewing captures later. Detected heuristics
are never treated as fact and are never used elsewhere in the server to
make parsing decisions unless a human has confirmed them and updated
protocol.py accordingly.
"""

import datetime
import json
import os
import threading
from collections import Counter

CAPTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "captures")


def ts() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def hexdump(data: bytes, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        hex_part = hex_part.ljust(width * 3 - 1)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"  {i:08x}  {hex_part}  |{ascii_part}|")
    return "\n".join(lines)


def detect_framing(data: bytes) -> dict:
    """
    Best-effort, non-authoritative heuristics about possible framing.
    This NEVER decides how the server parses data - it only informs a human
    reviewing the capture log. Nothing here should be treated as confirmed.
    """
    result = {
        "contains_crlf": b"\r\n" in data,
        "contains_lf_only": b"\n" in data and b"\r\n" not in data,
        "contains_cr_only": b"\r" in data and b"\r\n" not in data,
        "printable_ratio": None,
        "candidate_delimiters": [],
        "notes": [],
    }

    if len(data) > 0:
        printable = sum(1 for b in data if 32 <= b < 127)
        result["printable_ratio"] = round(printable / len(data), 3)
        if result["printable_ratio"] < 0.85:
            result["notes"].append(
                "Less than 85% printable ASCII - may contain binary fields, "
                "do not assume this is a plain text line."
            )

    # Candidate single-byte delimiters: common separators seen in
    # line-based/IRC-like protocols. This is purely frequency counting,
    # not a claim that any of these are actually used as delimiters here.
    candidates = [b" ", b"|", b",", b";", b"\t", b":"]
    counts = Counter()
    for c in candidates:
        counts[c] = data.count(c)
    for c, n in counts.items():
        if n > 0:
            result["candidate_delimiters"].append({"byte": c.decode(errors="replace"), "count": n})

    return result


class CaptureLogger:
    """
    Writes both a human-readable rolling log and a machine-readable JSONL
    capture file (one JSON object per line) for later automated analysis.
    """

    def __init__(self, captures_dir: str = CAPTURES_DIR):
        os.makedirs(captures_dir, exist_ok=True)
        self.captures_dir = captures_dir
        session_name = datetime.datetime.now().strftime("session_%Y%m%d_%H%M%S")
        self.text_path = os.path.join(captures_dir, f"{session_name}.log")
        self.jsonl_path = os.path.join(captures_dir, f"{session_name}.jsonl")
        self._lock = threading.Lock()
        self._text_fh = open(self.text_path, "a", buffering=1)
        self._jsonl_fh = open(self.jsonl_path, "a", buffering=1)
        self.event("SERVER_START", note=f"Capture session started. Text log: {self.text_path}")

    def _write(self, human_line: str, record: dict):
        with self._lock:
            self._text_fh.write(human_line + "\n")
            self._jsonl_fh.write(json.dumps(record) + "\n")
            print(human_line)

    def event(self, kind: str, ip: str = None, port: int = None, note: str = ""):
        record = {
            "timestamp": ts(),
            "kind": kind,
            "ip": ip,
            "port": port,
            "note": note,
        }
        human = f"[{record['timestamp']}] {kind}"
        if ip:
            human += f" {ip}:{port}"
        if note:
            human += f" - {note}"
        self._write(human, record)

    def packet(self, direction: str, ip: str, port: int, data: bytes):
        """
        direction: 'RECV' (client -> server) or 'SEND' (server -> client)
        """
        framing = detect_framing(data)
        record = {
            "timestamp": ts(),
            "kind": "PACKET",
            "direction": direction,
            "ip": ip,
            "port": port,
            "length": len(data),
            "raw_hex": data.hex(),
            "ascii": data.decode("latin-1"),
            "framing_heuristics": framing,
        }
        human = (
            f"[{record['timestamp']}] {direction:<4} {ip}:{port}  len={len(data)}\n"
            f"{hexdump(data)}\n"
            f"  ASCII: {data!r}\n"
            f"  Heuristics: {framing}"
        )
        self._write(human, record)

    def close(self):
        with self._lock:
            self._text_fh.close()
            self._jsonl_fh.close()
