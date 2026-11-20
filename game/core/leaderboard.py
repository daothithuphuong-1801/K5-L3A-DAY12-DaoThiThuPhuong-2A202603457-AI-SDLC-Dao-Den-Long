"""Local leaderboard (Ticket-04 §3). Pure Python, no engine imports.

Entry: {name, score, nights_won, achieved_at (ISO 8601 with tz), seed}. Top 10, score desc,
ties: whoever achieved it first stays above. Stored in ~/.dao_den_long/leaderboard.json.
"""
import json
import re
from datetime import datetime
from pathlib import Path

LEADERBOARD_PATH = Path.home() / ".dao_den_long" / "leaderboard.json"
MAX_ENTRIES = 10
# 3-12 characters: ASCII letters/digits/underscore, plus Vietnamese letters with diacritics (bonus)
_VI = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
NAME_RE = re.compile(rf"^[A-Za-z0-9_{_VI}{_VI.upper()}]{{3,12}}$")


def valid_name(name: str) -> bool:
    return isinstance(name, str) and bool(NAME_RE.match(name))


def _sort_key(e):
    return (-int(e["score"]), datetime.fromisoformat(e["achieved_at"]).timestamp(), e.get("_seq", 0))


def load(path=LEADERBOARD_PATH):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = [e for e in data.get("entries", []) if valid_name(e.get("name", ""))]
        return sorted(entries, key=_sort_key)[:MAX_ENTRIES]
    except (OSError, ValueError, TypeError, KeyError):
        return []


def save(entries, path=LEADERBOARD_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    clean = [{k: e[k] for k in ("name", "score", "nights_won", "achieved_at", "seed")} for e in entries]
    Path(path).write_text(json.dumps({"entries": clean}, ensure_ascii=False, indent=2), encoding="utf-8")


def add(name, score, nights_won, seed, path=LEADERBOARD_PATH, now=None):
    """Validate + insert + keep top 10. Returns (entries, rank or None if not in top 10)."""
    if not valid_name(name):
        raise ValueError("Tên phải dài 3-12 ký tự: chữ, số hoặc _")
    if not 0 <= int(nights_won) <= 3:
        raise ValueError("nights_won must be 0..3")
    entries = load(path)
    for i, e in enumerate(entries):
        e["_seq"] = i
    at = (now or datetime.now().astimezone()).isoformat(timespec="seconds")
    new = {"name": name, "score": int(score), "nights_won": int(nights_won), "achieved_at": at, "seed": seed,
           "_seq": len(entries)}
    entries = sorted(entries + [new], key=_sort_key)[:MAX_ENTRIES]
    save(entries, path)
    rank = next((i + 1 for i, e in enumerate(entries) if e is new), None)
    return [{k: v for k, v in e.items() if k != "_seq"} for e in entries], rank


def export(out_path, path=LEADERBOARD_PATH):
    entries = load(path)
    Path(out_path).write_text(json.dumps({"entries": [{k: v for k, v in e.items() if k != "_seq"} for e in entries]},
                                         ensure_ascii=False, indent=2), encoding="utf-8")
    return entries
