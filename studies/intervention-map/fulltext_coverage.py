"""Measure the fixed out-of-frame draw and two targeted cases using the same instrument."""

import argparse
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from fulltext_alphaxiv import coverage_draw
from fulltext_questions import QUESTIONS
from fulltext_rate import PRIMARY, payload, rate
from fulltext_sources import ROOT, digest, local_name

OUT = ROOT / "results"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("catalog", type=Path)
    p.add_argument("sources", type=Path)
    p.add_argument("cache", type=Path)
    args = p.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    tasks = []
    rows = {}
    with sqlite3.connect(args.catalog.resolve().as_uri() + "?mode=ro", uri=True) as db:
        for item in coverage_draw().itertuples():
            pid = item.paper_id
            title, abstract = db.execute(
                "SELECT title,abstract FROM papers WHERE source='arxiv' AND id=?",
                (pid.split(":")[1],),
            ).fetchone()
            key = local_name(pid)
            source = json.loads((args.sources / (key + ".json")).read_text())
            content = (args.sources / (key + ".txt")).read_bytes()
            if digest(content) != source["text_sha256"]:
                raise ValueError(pid + " text mismatch")
            rows[pid] = dict(
                paper_id=pid,
                title=title,
                selection=item.selection,
                pages=source["pages"],
                pages_under_40_chars=source["pages_under_40_chars"],
                source_url=source["url"],
                pdf_sha256=source["pdf_sha256"],
                text_sha256=source["text_sha256"],
            )
            for basis, text in [("abstract", abstract), ("paper", content.decode())]:
                for reviewer in ("jev", "qwen"):
                    tasks.append((pid, title, basis, text, reviewer))
    with ThreadPoolExecutor(6) as pool:
        list(pool.map(lambda task: rate(task, args.cache), tasks))
    prior = pd.read_csv(OUT / "external_radar_ratings.csv.gz").set_index("paper_id")
    for pid, title, basis, text, reviewer in tasks:
        signature = digest(
            json.dumps(
                payload(reviewer, title, basis, text),
                sort_keys=True,
                ensure_ascii=False,
            ).encode()
        )
        name = f"{local_name(pid)}.{reviewer}.{basis}.{signature}.json"
        record = json.loads((args.cache / name).read_text())
        if record["content_sha256"] != digest(text.encode()) or set(
            record["scores"]
        ) != set(QUESTIONS if reviewer == "jev" else PRIMARY):
            raise ValueError("Invalid ratings")
        if (
            basis == "abstract"
            and pid in prior.index
            and prior.loc[pid, reviewer + "_request_sha256"] != signature
        ):
            raise ValueError("Earlier abstract audit differs")
        prefix = f"{reviewer}_{basis}_"
        row = rows[pid]
        row.update({prefix + k: float(v) for k, v in record["scores"].items()})
        row[prefix + "request_sha256"] = signature
        row[prefix + "model"] = record["model"]
        row[prefix + "long_context"] = record["long_context"]
        usage = record["usage"]
        row[prefix + "input_tokens"] = usage.get(
            "input_tokens", usage.get("prompt_tokens")
        )
        row[prefix + "usd"] = (
            usage["input_tokens"] * 0.042 / 1e6 if reviewer == "jev" else usage["cost"]
        )
    df = pd.DataFrame(rows.values())
    df.to_csv(OUT / "fulltext_coverage_cases.csv", index=False)
    summary = {}
    for group, g in df.groupby("selection"):
        result = summary[group] = {"n": len(g), "pages": int(g.pages.sum())}
        for basis in ("abstract", "paper"):
            external = {}
            for reviewer in ("jev", "qwen"):
                pref = f"{reviewer}_{basis}_"
                e = g[[pref + "supervision", pref + "scaffolding"]].ge(0.5).any(axis=1)
                external[reviewer] = e
                result[pref + "external"] = int(e.sum())
                result[pref + "weights"] = int(g[pref + "weights"].ge(0.5).sum())
            result[basis + "_both_external"] = int(
                (external["jev"] & external["qwen"]).sum()
            )
    summary["new_cost_usd"] = {
        rev: float(
            df[f"{rev}_paper_usd"].sum()
            + df.loc[df.selection.eq("alphaxiv_case"), f"{rev}_abstract_usd"].sum()
        )
        for rev in ("jev", "qwen")
    }
    (OUT / "fulltext_coverage_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
