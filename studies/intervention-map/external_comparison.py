"""Match public comparison catalogs to the paper master, preserving each source taxonomy."""

import argparse
import csv
import gzip
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl
import pandas as pd
from bs4 import BeautifulSoup

from attention import ROOT

ID = re.compile(
    r"(?:arxiv[.:/]?(?:(?:org/)?(?:abs|pdf)/)?)(\d{4}\.\d{4,5})(?:v\d+)?", re.I
)
DATES = ("2111", "2610")
GOV_LABELS = set(
    "not_ai_safety testing_and_evaluation ethics_and_bias privacy_and_security interpretability_and_transparency alignment_pre_deployment policy_and_governance post_deployment_risks_and_model_traits multi_agent_and_agentic_safety".split()
)


def norm(title):
    return " ".join(
        re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", title).casefold())
    )


def arxiv(url):
    m = ID.search(url or "")
    return m.group(1) if m else ""


def sources(folder):
    for r in json.loads((folder / "guardrail").read_bytes())["papers"]:
        ident = r["id"]
        if re.fullmatch(r"\d{4}\.\d{4,5}", ident) and DATES[0] <= ident[:4] <= DATES[1]:
            yield "guardrail", ident, r["title"], "arxiv:" + ident, [
                *r["tags"],
                *("category:" + c for c in r["categories"]),
            ]
    with (folder / "stampy").open() as f:
        for r in map(json.loads, f):
            ident = arxiv(r["url"])
            if ident and DATES[0] <= ident[:4] <= DATES[1]:
                yield "stampy", ident, r["title"], r["url"], []
    with (folder / "company").open("rb") as f:
        sheet = openpyxl.load_workbook(f, read_only=True, data_only=True)["All papers"]
        for row in list(sheet.values)[1:]:
            if len(row) < 5:
                continue
            _, title, _, url, category = row[:5]
            if (
                title
                and category
                and category != "No"
                and not category.startswith("[Duplicate]")
            ):
                yield "company", norm(title), title, url or "", [category.strip()]
    with (folder / "governance").open(newline="") as f:
        for r in csv.DictReader(f):
            category = r["safety_classification"].strip()
            if category in GOV_LABELS:
                yield "governance", norm(r["title"]), r["title"], "", [category]
    heading = ""
    for line in (folder / "llm").read_text().splitlines():
        if line.startswith("#"):
            heading = line.lstrip("# ").strip()
        hit = re.match(r"\d+\. \*\*(.+?)\*\*", line)
        if hit:
            title = hit[1].rstrip(".")
            url = re.search(r"\[Paper\]\(([^)]+)", line, re.I)
            yield "llm_survey", norm(title), title, url[1] if url else "", [heading]
    soup = BeautifulSoup((folder / "control").read_bytes(), "html.parser")
    for link in soup.select("main strong a[href]"):
        title = link.get_text(" ", strip=True)
        yield "controlarena", norm(title), title, link["href"], [
            "ControlArena bibliography"
        ]
    for topic in ("alignment_training", "control_monitoring"):
        result = json.loads((folder / ("radar_" + topic)).read_bytes())
        if result["last_page_min_date"] >= "2026-10-01":
            raise ValueError("Incomplete Radar month")
        for r in result["rows"]:
            if not r["key"].startswith("arxiv:2610."):
                continue
            if topic not in r["topics"]:
                raise ValueError("Missing requested Radar topic")
            yield "radar_october", r["key"], r["title"], r["url"], r["topics"]


def run(folder, output):
    master = pd.read_csv(
        ROOT / "results/paper_master.csv.gz", keep_default_na=False
    ).set_index("paper_id", verify_integrity=True)
    full = set(pd.read_csv(ROOT / "results/fulltext_measures.csv").paper_id)
    titles = defaultdict(set)
    for pid, title in master.title.items():
        titles[norm(title)].add(pid)
    groups = {}
    for source, key, title, url, tags in sources(folder):
        if not key:
            continue
        r = groups.setdefault((source, key), dict(title=title, url=url, tags=set()))
        r["tags"].update(tags)
    summary = {}
    matches = []
    misses = []
    for (source, key), item in sorted(groups.items()):
        url = item["url"]
        ident = arxiv(url)
        title = item["title"]
        tags = sorted(item["tags"])
        pid = "arxiv:" + ident
        metrics = summary.setdefault(source, Counter())
        metrics["eligible_external_records"] += 1
        if ident and pid in master.index:
            method = "arxiv_id"
        else:
            candidates = titles.get(norm(title), set())
            if len(candidates) != 1:
                metrics["ambiguous_titles" if candidates else "unmatched"] += 1
                misses.append((source, key, title, url, "|".join(tags)))
                continue
            pid = next(iter(candidates))
            if ident and pid.startswith("arxiv:") and pid != "arxiv:" + ident:
                metrics["conflicting_id"] += 1
                misses.append((source, key, title, url, "|".join(tags)))
                continue
            method = "unique_title"
        match = master.loc[pid]
        metrics[method] += 1
        matches.append(
            dict(
                source=source,
                external_key=key,
                paper_id=pid,
                match=method,
                labels="|".join(tags),
                shortlist="alignment_shortlist" in match.cohorts.split("|"),
                full_paper=pid in full,
                jev_weight=float(match.jev_weights) >= 0.5,
                jev_external=float(match.jev_external_max) >= 0.5,
            )
        )
    out = pd.DataFrame(matches)
    for source, g in out.groupby("source"):
        unique = g.drop_duplicates("paper_id")
        summary[source].update(
            dict(
                matched_external_records=len(g),
                distinct_master_ids=len(unique),
                shortlist=int(unique.shortlist.sum()),
                full_paper=int(unique.full_paper.sum()),
            )
        )
    output.mkdir(parents=True, exist_ok=True)
    out.to_csv(
        output / "external_matches.csv.gz",
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )
    # A reproducible diagnostic set of external-only works. Sampling within each source avoids domination by volume.
    gaps = []
    for src in sorted(summary):
        sample = sorted(
            [row for row in misses if row[0] == src],
            key=lambda r: hashlib.sha256(
                ("external-coverage-v1/" + r[0] + "/" + r[1]).encode()
            ).digest(),
        )[:20]
        gaps.extend(sample)
    pd.DataFrame(
        gaps, columns=["source", "external_key", "title", "url", "labels"]
    ).to_csv(output / "external_gap_sample.csv", index=False)
    radar = []
    for (src, key), item in sorted(groups.items()):
        if src == "radar_october":
            radar.append(
                dict(
                    paper_id=key,
                    title=item["title"],
                    alignment_training="alignment_training" in item["tags"],
                    control_monitoring="control_monitoring" in item["tags"],
                    in_master=key in master.index,
                    in_shortlist=key in master.index
                    and "alignment_shortlist" in master.at[key, "cohorts"].split("|"),
                )
            )
    pd.DataFrame(radar).to_csv(output / "external_radar_frame.csv", index=False)
    checks = {}
    for source, tags in {
        "guardrail": [
            "category:alignment",
            "guardrails",
            "sandboxing",
            "preference-learning",
            "reward-modeling",
        ],
        "radar_october": ["alignment_training", "control_monitoring"],
        "llm_survey": ["RL-based Methods", "SL-based Methods"],
        "controlarena": ["ControlArena bibliography"],
        "governance": [
            "alignment_pre_deployment",
            "post_deployment_risks_and_model_traits",
        ],
        "company": ["Enhancing human feedback", "Mechanistic interpretability"],
    }.items():
        for tag in tags:
            subset = out[
                out.source.eq(source) & out.labels.map(lambda s: tag in s.split("|"))
            ].drop_duplicates("paper_id")
            ext = sum(
                1
                for (src, _), r in groups.items()
                if src == source and tag in r["tags"]
            )
            checks[source + "/" + tag] = dict(
                external_records=ext,
                matched_papers=len(subset),
                jev_weight=int(subset.jev_weight.sum()),
                jev_external=int(subset.jev_external.sum()),
            )
    files = [
        "guardrail",
        "stampy",
        "company",
        "governance",
        "llm",
        "control",
        "radar_alignment_training",
        "radar_control_monitoring",
    ]
    provenance = {}
    for name in files:
        data = (folder / name).read_bytes()
        url = folder / (name + ".url")
        provenance[name] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "url": (
                url.read_text().strip()
                if url.exists()
                else json.loads(data)["first_url"]
            ),
        }
    index = json.loads((folder / "guardrail").read_bytes())
    papers = index["papers"]
    guardrail = dict(
        records=len(papers),
        updated=index["updated"],
        category_counts=Counter(c for r in papers for c in r["categories"]),
        tagged_records=sum(bool(r["tags"]) for r in papers),
        observed_tags=len({t for r in papers for t in r["tags"]}),
    )
    result = dict(
        sources=summary, checks=checks, provenance=provenance, guardrail_index=guardrail
    )
    (output / "external_comparison.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("downloads", type=Path)
    p.add_argument("--output", type=Path, default=ROOT / "results")
    args = p.parse_args()
    run(args.downloads, args.output)
