import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

PIECES = ["Helm", "Armor", "Gauntlets", "Greaves"]


@dataclass
class Candidate:
    family: str
    piece: str
    name: str
    score: int


def tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9']+", (text or "").lower())


def score_name_match(family: str, name: str) -> int:
    fam_tokens = set(tokenize(family))
    name_tokens = set(tokenize(name))
    overlap = len(fam_tokens.intersection(name_tokens))
    phrase_bonus = 3 if family and family in name.lower() else 0
    return overlap * 2 + phrase_bonus


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def choose_audit_file(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    session_dir = Path("docs/session")
    matches = sorted(session_dir.glob("*_armor_family_audit.json"))
    if not matches:
        raise FileNotFoundError("No audit file found. Expected docs/session/*_armor_family_audit.json")
    return matches[-1]


def build_piece_lookup(incomplete_items: List[dict]) -> Dict[str, List[Tuple[str, str]]]:
    lookup: Dict[str, List[Tuple[str, str]]] = {piece: [] for piece in PIECES}
    for entry in incomplete_items:
        family = entry.get("family", "")
        pieces = entry.get("pieces", {})
        for piece in PIECES:
            for name in pieces.get(piece, []) or []:
                lookup[piece].append((family, name))
    return lookup


def find_candidates(family: str, missing_piece: str, lookup: Dict[str, List[Tuple[str, str]]], limit: int = 6) -> List[Candidate]:
    candidates: List[Candidate] = []
    for source_family, name in lookup.get(missing_piece, []):
        score = score_name_match(family, name)
        if score <= 0:
            continue
        candidates.append(Candidate(source_family, missing_piece, name, score))
    candidates.sort(key=lambda c: (-c.score, c.name))
    return candidates[:limit]


def ensure_decisions_file(path: Path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "decisions": []
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_decisions(path: Path) -> dict:
    ensure_decisions_file(path)
    return json.loads(path.read_text(encoding="utf-8"))


def save_decisions(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def already_reviewed_set(decisions_payload: dict) -> set:
    reviewed = set()
    for decision in decisions_payload.get("decisions", []):
        fam = decision.get("family")
        piece = decision.get("missing_piece")
        if fam and piece:
            reviewed.add((fam, piece))
    return reviewed


def add_decision(decisions_payload: dict, decision: dict):
    decisions_payload.setdefault("decisions", []).append(decision)


def print_header(audit_path: Path, decisions_path: Path, queue_count: int):
    print("=" * 78)
    print("Armor Family Review Wizard")
    print(f"Audit:     {audit_path}")
    print(f"Decisions: {decisions_path}")
    print(f"Queue:     {queue_count} items")
    print("=" * 78)


def print_family(entry: dict, missing_piece: str):
    print(f"\nFamily: {entry.get('family','')}  | Missing: {missing_piece}")
    print("Current pieces:")
    pieces = entry.get("pieces", {})
    for piece in PIECES:
        names = pieces.get(piece, []) or []
        if names:
            print(f"  {piece}: {', '.join(names)}")
        else:
            print(f"  {piece}: <missing>")


def run_interactive(audit: dict, decisions_payload: dict, decisions_path: Path, limit: int | None):
    incomplete = audit.get("incomplete", [])
    lookup = build_piece_lookup(incomplete)

    queue = []
    for entry in incomplete:
        present = entry.get("pieces", {})
        present_count = sum(1 for p in PIECES if (present.get(p, []) or []))
        if present_count != 3:
            continue
        missing = [p for p in PIECES if not (present.get(p, []) or [])]
        if not missing:
            continue
        queue.append((entry, missing[0]))

    reviewed = already_reviewed_set(decisions_payload)
    queue = [(e, m) for (e, m) in queue if (e.get("family"), m) not in reviewed]
    if limit is not None:
        queue = queue[:limit]

    print_header(Path(args.audit), decisions_path, len(queue))
    if not queue:
        print("No pending 3-piece families to review.")
        return

    for idx, (entry, missing_piece) in enumerate(queue, start=1):
        family = entry.get("family", "")
        print(f"\n[{idx}/{len(queue)}]")
        print_family(entry, missing_piece)

        candidates = find_candidates(family, missing_piece, lookup)
        if candidates:
            print("\nSuggested candidates:")
            for c_idx, candidate in enumerate(candidates, start=1):
                print(f"  {c_idx}. {candidate.name}  (from family: {candidate.family}, score={candidate.score})")
        else:
            print("\nSuggested candidates: none")

        print("\nActions: [k]eep as-is / [m <n>] match candidate / [h]ide family / [s]kip / [q]quit")
        while True:
            raw = input("> ").strip().lower()
            if raw == "k":
                add_decision(decisions_payload, {
                    "family": family,
                    "missing_piece": missing_piece,
                    "action": "keep",
                    "note": "kept as 3-piece family"
                })
                save_decisions(decisions_path, decisions_payload)
                break
            if raw.startswith("m"):
                parts = raw.split()
                if len(parts) != 2 or not parts[1].isdigit():
                    print("Use: m <number>")
                    continue
                pick = int(parts[1])
                if pick < 1 or pick > len(candidates):
                    print("Invalid candidate number.")
                    continue
                chosen = candidates[pick - 1]
                add_decision(decisions_payload, {
                    "family": family,
                    "missing_piece": missing_piece,
                    "action": "match",
                    "candidate_name": chosen.name,
                    "candidate_family": chosen.family,
                    "score": chosen.score
                })
                save_decisions(decisions_path, decisions_payload)
                break
            if raw == "h":
                add_decision(decisions_payload, {
                    "family": family,
                    "missing_piece": missing_piece,
                    "action": "hide",
                    "note": "hide from full-scope candidates"
                })
                save_decisions(decisions_path, decisions_payload)
                break
            if raw == "s":
                break
            if raw == "q":
                print("Stopping review. Decisions saved.")
                return
            print("Unknown command.")

    print("\nReview batch complete. Decisions saved.")


def run_dry_run(audit: dict, decisions_payload: dict, limit: int | None):
    incomplete = audit.get("incomplete", [])
    lookup = build_piece_lookup(incomplete)
    reviewed = already_reviewed_set(decisions_payload)

    queue = []
    for entry in incomplete:
        present = entry.get("pieces", {})
        present_count = sum(1 for p in PIECES if (present.get(p, []) or []))
        if present_count != 3:
            continue
        missing = [p for p in PIECES if not (present.get(p, []) or [])]
        if not missing:
            continue
        family = entry.get("family")
        if (family, missing[0]) in reviewed:
            continue
        queue.append((entry, missing[0]))

    if limit is not None:
        queue = queue[:limit]

    print(f"Dry-run queue size: {len(queue)}")
    for entry, missing_piece in queue[:20]:
        family = entry.get("family", "")
        cands = find_candidates(family, missing_piece, lookup, limit=3)
        print(f"- {family} | missing: {missing_piece}")
        for c in cands:
            print(f"    -> {c.name} (family={c.family}, score={c.score})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive reviewer for incomplete armor families")
    parser.add_argument("--audit", default=None, help="Path to armor audit JSON")
    parser.add_argument("--decisions", default="docs/session/2026-02-15_armor_family_decisions.json", help="Path to decisions JSON")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of queue entries")
    parser.add_argument("--dry-run", action="store_true", help="Print queue and suggestions without prompting")
    args = parser.parse_args()

    audit_path = choose_audit_file(args.audit)
    decisions_path = Path(args.decisions)

    audit = load_json(audit_path)
    decisions_payload = load_decisions(decisions_path)

    if args.dry_run:
        run_dry_run(audit, decisions_payload, args.limit)
    else:
        # stash resolved path back for display inside runner
        args.audit = str(audit_path)
        run_interactive(audit, decisions_payload, decisions_path, args.limit)
