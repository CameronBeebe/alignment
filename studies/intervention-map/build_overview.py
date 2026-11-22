"""Render the offline literature explorer from the frozen study outputs."""
import csv
import json
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def read_json(name):
    return json.loads((RESULTS / name).read_text())


def main():
    estimates = read_json("inference.json")["estimates"]
    labels = {
        "core": "Core alignment research",
        "core_named": "Explicit alignment vocabulary",
        "core_plus_adjacent": "Including adjacent safety engineering",
        "core_external_or_steering": "Including soft steering as a comparator",
        "core_early": "Core · through December 2024",
        "core_late": "Core · January 2025 onward",
    }
    comparisons = []
    for key, label in labels.items():
        estimate = estimates[key]
        lo, hi = estimate["ci95"]
        comparisons.append(f"<tr><th scope='row'>{label}</th><td>{estimate['ratio']:.2f}</td><td>{lo:.2f}–{hi:.2f}</td></tr>")
    with (RESULTS / "alignment_papers.csv").open(newline="") as file:
        papers = list(csv.DictReader(file))
    for paper in papers:
        url = urlsplit(paper["url"])
        if url.scheme != "https" or url.hostname not in {"arxiv.org", "aclanthology.org"}:
            raise ValueError(f"Unexpected source URL for {paper['paper_id']}")
    topics = read_json("topics.json")["clusters"]
    options = "".join(f"<option value='{t['cluster']}'>{escape(' · '.join(t['terms'][:3]))}</option>" for t in topics)
    template = (ROOT / "overview.template.html").read_text()
    page = (template.replace("{{comparisons}}", "".join(comparisons))
            .replace("{{topics}}", options)
            .replace("{{count}}", f"{len(papers):,}")
            .replace("{{papers}}", json.dumps(papers, ensure_ascii=False, separators=(",", ":")).replace("<", r"\u003c")))
    (ROOT / "alignment-overview.html").write_text(page)


if __name__ == "__main__":
    main()
