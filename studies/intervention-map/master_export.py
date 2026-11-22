"""Assemble the canonical paper-level measurement table from verified source rows."""

import argparse
import collections
import csv
import gzip
import hashlib
import io
import json
import os
import sqlite3
from pathlib import Path
from tempfile import NamedTemporaryFile

from master_records import ROOT, master_records, rows
from snapshot import archive_path
from master_jev import ITEMS, MODEL, payload

FILE = ROOT / "results/paper_master.csv.gz"


def index(path, key="paper_id", prefix=""):
    result = {}
    for r in rows(path):
        pid = prefix + r[key]
        if pid in result:
            raise ValueError(f"Duplicate {pid} in {path}")
        result[pid] = r
    return result


def comparison_metadata(pid, title):
    ident = pid.removeprefix("arxiv:")
    if not pid.startswith("arxiv:"):
        raise ValueError("Expected arXiv comparison paper")
    return dict(
        title=title,
        year="20" + ident[:2],
        month="20" + ident[:2] + "-" + ident[2:4],
        url="https://arxiv.org/abs/" + ident,
        sources="arxiv",
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--semantics", type=Path, required=True)
    args = p.parse_args()
    records, roles = master_records()
    scope = index("results/language_model_scores.csv.gz")
    if set(scope) != set(records):
        raise ValueError("Incomplete language-model scope measurements")
    scope_cols = ["jev_language_model_focus", "literal_llm", "family_mention"]
    source = index("results/papers.csv")
    source_cols = list(next(iter(source.values())))
    bibliography = index("data/comparison_bibliography.csv")
    venues = {}
    categories = {}
    with gzip.open(archive_path(ROOT / "data"), "rt") as archive:
        for record in map(json.loads, archive):
            pid = record["paper_id"]
            venues[pid] = record.get("venue", "")
            arxiv = [
                v.get("venue", "")
                for v in record["records"]
                if v["source"] == "arxiv" and v.get("venue")
            ]
            if arxiv:
                categories[pid] = arxiv[0].split()[0]
    title_counts = collections.Counter(
        title.casefold().strip() for title, abstract in records.values()
    )
    shortlist = index("results/alignment_papers.csv")
    map_labels = index("results/semantic_clusters.csv")
    authors = index("results/author_clusters.csv")
    role_reviews = index("data/master_role_review.csv")
    control = index("results/control_map.csv")
    general = index("results/general_topics.csv")
    reviewed = index("results/reviewed_papers.csv")
    codes = index("data/attention_review.csv")
    base = index("data/baseline_draw.csv", "arxiv_id", "arxiv:")
    base_codes = index("data/baseline_review.csv", "arxiv_id", "arxiv:")
    matches = index("data/matched_review.csv", "comparison_id")
    matched_ids = index("data/matched_cscl.csv", "comparison_id")
    validation = index("data/control_validation.csv")
    geometry = {
        name: index("results/" + name + "_geometry.csv")
        for name in ("shortlist", "general", "control")
    }
    with args.semantics.open() as f:
        reader = csv.DictReader(f)
        sem_keys = reader.fieldnames[1:]
        semantic = {}
        for r in reader:
            pid = r.pop("paper_id")
            if pid in semantic:
                raise ValueError("Duplicate semantic measurements")
            semantic[pid] = r
    if set(semantic) != set(records):
        raise ValueError("Incomplete semantic measurements")
    db = sqlite3.connect(args.cache.resolve().as_uri() + "?mode=ro", uri=True)
    cols = [
        *source_cols,
        *scope_cols,
        "cohorts",
        "text_source",
        "evidence_basis",
        "category",
        "venue",
        "same_title_records",
        "shortlist_selection",
        "shortlist_core_score",
        "alignment_review_scope",
        "alignment_review_codes",
        "alignment_harmonized_codes",
        "alignment_stratum",
        "alignment_N_h",
        "alignment_n_h",
        "baseline_review_codes",
        "baseline_stratum",
        "baseline_N_h",
        "baseline_n_h",
        "matched_review_codes",
        "matched_core_id",
        "control_review_feedback",
        "control_review_dynamics",
        "coauthor_group",
        "coauthor_group_size",
        *[
            f"{k}_map_{v}"
            for k in geometry
            for v in ("topic", "center_distance", "x", "y")
        ],
        *[
            "role_review_" + k
            for k in ("evaluation", "theory", "data_resources", "governance")
        ],
        *sem_keys,
        "jev_model",
        "jev_request_sha256",
        "jev_input_tokens",
        "jev_output_tokens",
        *["jev_" + key for key in ITEMS],
        "jev_external_max",
        "jev_feedback_dynamics_max",
        "jev_labels_at_050",
        "jev_near_threshold_labels",
    ]
    if len(cols) != len(set(cols)):
        raise ValueError("Nonunique column names")
    counts = collections.Counter()
    label_counts = collections.Counter()
    by_topic = collections.defaultdict(collections.Counter)
    with NamedTemporaryFile(dir=FILE.parent, delete=False) as tmp:
        tmpname = tmp.name
    try:
        with open(tmpname, "wb") as raw, gzip.GzipFile(
            fileobj=raw, mode="wb", mtime=0, filename="", compresslevel=9
        ) as zipped, io.TextIOWrapper(zipped, encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=cols, lineterminator="\n")
            writer.writeheader()
            for pid, (title, abstract) in records.items():
                category = (
                    categories.get(pid)
                    or codes.get(pid, {}).get("primary_arxiv_category")
                    or base.get(pid, {}).get("category")
                    or control.get(pid, {}).get("category")
                    or ("cs.CL" if pid in matches else "")
                )
                item = (
                    dict(source[pid])
                    if pid in source
                    else comparison_metadata(pid, title)
                )
                if pid in bibliography:
                    item.update(bibliography[pid])
                    category = (
                        item["venue"].split()[0] if item.get("venue") else category
                    )
                else:
                    item["venue"] = venues[pid]
                item["same_title_records"] = title_counts[title.casefold().strip()]
                item["paper_id"] = pid
                item.update(
                    cohorts="|".join(sorted(roles[pid])),
                    category=category,
                    text_source=(
                        "candidates"
                        if pid in source
                        else (
                            "baseline_draw"
                            if pid in base
                            else "control_sample" if pid in control else "matched_cscl"
                        )
                    ),
                    evidence_basis=(
                        "title_abstract" if abstract.strip() else "title_only"
                    ),
                    shortlist_selection=shortlist.get(pid, {}).get("selection", ""),
                    shortlist_core_score=shortlist.get(pid, {}).get("core_score", ""),
                )
                a = reviewed.get(pid, {})
                b = base.get(pid, {})
                item.update(
                    alignment_review_scope=a.get("scope", ""),
                    alignment_review_codes=a.get("mechanisms", ""),
                    alignment_harmonized_codes=codes.get(pid, {}).get(
                        "common_codes", ""
                    ),
                    alignment_stratum=a.get("stratum", ""),
                    alignment_N_h=a.get("N_h", ""),
                    alignment_n_h=a.get("n_h", ""),
                    baseline_review_codes=base_codes.get(pid, {}).get("codes", ""),
                    baseline_stratum=b.get("stratum", ""),
                    baseline_N_h=b.get("population", ""),
                    baseline_n_h=b.get("sample", ""),
                    matched_review_codes=matches.get(pid, {}).get("common_codes", ""),
                    matched_core_id=matched_ids.get(pid, {}).get("core_id", ""),
                    control_review_feedback=validation.get(pid, {}).get(
                        "feedback_loop", ""
                    ),
                    control_review_dynamics=validation.get(pid, {}).get("dynamics", ""),
                    coauthor_group=authors.get(pid, {}).get("cluster", ""),
                    coauthor_group_size=authors.get(pid, {}).get("cluster_size", ""),
                )
                for name, assignments, label in [
                    ("shortlist", map_labels, "semantic_cluster"),
                    ("general", general, "cluster"),
                    ("control", control, "cluster"),
                ]:
                    if pid in geometry[name]:
                        item[name + "_map_topic"] = assignments[pid][label]
                        item[name + "_map_center_distance"] = assignments[pid][
                            "distance"
                        ]
                        for v in ("x", "y"):
                            item[name + "_map_" + v] = geometry[name][pid][v]
                for k in ("evaluation", "theory", "data_resources", "governance"):
                    item["role_review_" + k] = role_reviews.get(pid, {}).get(k, "")
                item.update(semantic[pid])
                sig = hashlib.sha256(payload(title, abstract)).hexdigest()
                result = db.execute(
                    "SELECT model,scores,usage FROM measurements WHERE paper_id=? AND request_sha=?",
                    (pid, sig),
                ).fetchone()
                if not result or result[0] != MODEL:
                    raise ValueError(f"No matching pinned Jev response for {pid}")
                probs = json.loads(result[1])
                usage = json.loads(result[2])
                if set(probs) != set(ITEMS) or not all(
                    0 <= v <= 1 for v in probs.values()
                ):
                    raise ValueError(f"Invalid scores for {pid}")
                labels = [k for k in ITEMS if probs[k] >= 0.5]
                item.update(
                    jev_model=MODEL,
                    jev_request_sha256=sig,
                    jev_input_tokens=usage["input_tokens"],
                    jev_output_tokens=usage["output_tokens"],
                    jev_external_max=max(probs["supervision"], probs["scaffolding"]),
                    jev_feedback_dynamics_max=max(probs["feedback"], probs["dynamics"]),
                    jev_labels_at_050="|".join(labels) or "none",
                    jev_near_threshold_labels="|".join(
                        k for k in ITEMS if abs(probs[k] - 0.5) <= 0.10000001
                    )
                    or "none",
                )
                item.update({"jev_" + k: probs[k] for k in ITEMS})
                item.update({k: scope[pid][k] for k in scope_cols})
                writer.writerow(item)
                counts.update(roles[pid])
                counts[item["evidence_basis"]] += 1
                label_counts.update(labels)
                if pid in shortlist:
                    t = by_topic[item["shortlist_map_topic"]]
                    t["papers"] += 1
                    t["weights"] += probs["weights"] >= 0.5
                    t["external"] += item["jev_external_max"] >= 0.5
                    t["feedback_or_dynamics"] += (
                        item["jev_feedback_dynamics_max"] >= 0.5
                    )
                    t["neither"] += (
                        probs["weights"] < 0.5 and item["jev_external_max"] < 0.5
                    )
        os.replace(tmpname, FILE)
    finally:
        Path(tmpname).unlink(missing_ok=True)
    manifest = {
        "rows": len(records),
        "columns": len(cols),
        "cohort_and_evidence_counts": counts,
        "model": MODEL,
        "questions": ITEMS,
        "language_model_scope_file": "results/language_model_scores.csv.gz",
        "positive_counts_050_all_works": label_counts,
        "shortlist_topic_counts": dict(by_topic),
        "sha256": hashlib.sha256(FILE.read_bytes()).hexdigest(),
        "file_bytes": FILE.stat().st_size,
    }
    with gzip.open(FILE, "rt") as stream:
        tokens = [
            (int(r["jev_input_tokens"]), int(r["jev_output_tokens"]))
            for r in csv.DictReader(stream)
        ]
    manifest["input_tokens"] = sum(t[0] for t in tokens)
    manifest["output_tokens"] = sum(t[1] for t in tokens)
    (ROOT / "results/master_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
