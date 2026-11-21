"""Search the persistent catalog. Cache the result once for all subsequent analysis."""

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

from sklearn.feature_extraction.text import CountVectorizer
import numpy as np
from rules import PRE, screen, norm

DATA = Path("data")
SEEDS = {
    "training": ["2305.18290", "2203.02155"],
    "supervision": ["2312.06942", "2503.18813"],
    "harness": ["2608.09885"],
    "inference": ["2402.06147", "2310.12962"],
}
# Held out of query generation. Only used after retrieval for a diagnostic.
CHECKS = [
    "2212.08073",
    "2310.10501",
    "2312.09390",
    "2402.08983",
    "2503.18666",
    "2402.05070",
]


def folded(title):
    plain = unicodedata.normalize("NFKD", title).casefold()
    return re.sub(r"[^a-z0-9]", "", plain)


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def feedback(db, pool, journal, rounds=2):
    """Select discriminative seed phrases, probe the index, admit ranked neighbors, update frontier."""
    for family, ids in SEEDS.items():
        seeds = [
            dict(r)
            for i in ids
            for r in db.execute(
                "SELECT * FROM papers WHERE source='arxiv' AND id=?", (i,)
            )
        ]
        if not seeds:
            continue
        used = set()
        for step in range(rounds):
            texts = [norm(r["title"] + ". " + r["abstract"]) for r in seeds]
            vec = CountVectorizer(
                ngram_range=(2, 3),
                stop_words="english",
                token_pattern=r"(?u)\b[a-z][a-z]+\b",
            )
            m = vec.fit_transform(texts)
            terms = vec.get_feature_names_out()
            tf = np.asarray(m.sum(axis=0)).ravel()
            # Repeated, contiguous phrases are better search expansions than one-off associations.
            ranked = sorted(
                (
                    (-int(f), w)
                    for f, w in zip(tf, terms)
                    if f >= 2 and w not in used and any(w in t for t in texts)
                )
            )
            additions = []
            for _, phrase in ranked:
                if len(additions) >= 3:
                    break
                used.add(phrase)
                q = '"' + phrase + '"'
                # Reject phrases so broad that the first page would be arbitrary.
                count = db.execute(
                    "SELECT count(*) FROM ft WHERE ft MATCH ?", (q,)
                ).fetchone()[0]
                if not 4 <= count <= 1800:
                    continue
                rows = db.execute(
                    """SELECT p.*,bm25(ft,4,1) AS rank FROM ft JOIN papers p ON p.rowid=ft.rowid
                                  WHERE ft MATCH ? ORDER BY rank,p.source,p.id LIMIT 18""",
                    (q,),
                ).fetchall()
                fresh = []
                for record in rows:
                    r = dict(record)
                    r.pop("rank")
                    key = (r["source"], r["id"])
                    if key not in pool:
                        pool[key] = (r, set())
                        fresh.append(r)
                    pool[key][1].add("feedback_" + family)
                if not fresh:
                    continue
                additions.append(fresh[0])
                journal.append(
                    dict(
                        family=family,
                        round=step + 1,
                        phrase=phrase,
                        index_hits=count,
                        examined=len(rows),
                        new_records=len(fresh),
                        next_seed=fresh[0]["url"],
                    )
                )
            if not additions:
                break
            seeds.extend(additions)


def merge(pool):
    # Connected components on exact source ID, normalized title or shared publication DOI.
    rows = sorted(pool.values(), key=lambda v: (v[0]["source"] != "arxiv", v[0]["id"]))
    parent = list(range(len(rows)))

    def root(i):
        while i != parent[i]:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, (p, _) in enumerate(rows):
        title = folded(p["title"])
        keys = ["title:" + title] if len(title) >= 18 else []
        if p["doi"]:
            keys += [
                "doi:" + d.lower().rstrip(".,")
                for d in re.findall(r"10\.\d{4,9}/[^\s;,]+", p["doi"])
            ]
        for k in keys:
            if k in seen:
                parent[root(i)] = root(seen[k])
            else:
                seen[k] = i
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[root(i)].append(row)
    for group in groups.values():
        p = dict(group[0][0])
        p["paper_id"] = p["source"] + ":" + p["id"]
        p["month"] = min(r["month"] for r, _ in group)
        p["lanes"] = sorted(set.union(*(flags for _, flags in group)))
        p["sources"] = sorted({r["source"] for r, _ in group})
        p["records"] = [
            {k: r[k] for k in ["source", "id", "title", "month", "url", "doi", "venue"]}
            for r, _ in group
        ]
        if not p["abstract"]:
            p["abstract"] = max((r["abstract"] for r, _ in group), key=len)
        yield p


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="cache/catalog.sqlite")
    ap.add_argument("--out", type=Path, default=DATA)
    ap.add_argument("--feedback-rounds", type=int, default=2)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    sources = [dict(r) for r in db.execute("SELECT * FROM sources ORDER BY source")]
    if not sources:
        raise SystemExit("Index is empty")
    if len({(r["start"], r["end"]) for r in sources}) != 1:
        raise ValueError("Source windows differ")
    pool = {}
    pre = 0
    for r in db.execute(
        "SELECT p.* FROM ft JOIN papers p ON ft.rowid=p.rowid WHERE ft MATCH ?", (PRE,)
    ):
        pre += 1
        lanes = screen(r["title"], r["abstract"])
        if lanes:
            pool[r["source"], r["id"]] = (dict(r), set(lanes))
    original = len(pool)
    journal = []
    feedback(db, pool, journal, args.feedback_rounds)
    papers = sorted(merge(pool), key=lambda p: p["paper_id"])
    out = args.out / "candidates.jsonl.gz"
    temp = out.with_suffix(".partial")
    with temp.open("wb") as f, gzip.GzipFile(
        filename="", fileobj=f, mode="wb", mtime=0
    ) as gz:
        for p in papers:
            gz.write((json.dumps(p, ensure_ascii=False) + "\n").encode())
    if (
        (args.out / "audit_draw.csv").exists()
        and out.exists()
        and hashlib.sha256(temp.read_bytes()).digest()
        != hashlib.sha256(out.read_bytes()).digest()
    ):
        temp.unlink()
        raise SystemExit(
            "A reviewed snapshot already exists here. Write a changed search to a new --out directory."
        )
    temp.replace(out)
    manifest = dict(
        sources=sources,
        fts_rows=pre,
        lexical_records=original,
        raw_records=len(pool),
        unique=len(papers),
        lane_papers=dict(Counter(l for p in papers for l in p["lanes"])),
        feedback=journal,
        retrieval_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
        sentinels={
            i: bool(("arxiv", i) in pool)
            for i in CHECKS
            if i not in sum(SEEDS.values(), [])
        },
    )
    dump(args.out / "search_manifest.json", manifest)
    print(out, len(papers), len(journal), flush=True)


if __name__ == "__main__":
    main()
