"""Package the three paper maps and audited data into a self-contained HTML section."""

import base64
import csv
import gzip
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALIGN_NAMES = [
    "Multimodal alignment",
    "Direct preference optimization",
    "Ethics and governance",
    "Agent security and prompt injection",
    "Jailbreaks and defenses",
    "Safety-preserving fine-tuning",
    "Reward learning and RLHF",
    "Preference alignment and feedback",
]
CONTROL_NAMES = [
    "Language models",
    "Robotics and reinforcement learning",
    "Energy and infrastructure",
    "Learning and estimation",
    "Optimization, dynamics and control",
    "Computer vision",
]


def load(name):
    return json.loads((ROOT / "results" / name).read_text())


def csv_index(path):
    op = gzip.open if str(path).endswith(".gz") else open
    with op(ROOT / path, "rt") as f:
        return {r["paper_id"]: r for r in csv.DictReader(f)}


def judgments(path):
    rows = [json.loads(s) for s in (ROOT / "results" / path).read_text().splitlines()]
    return {
        r["paper_id"]: [
            r["scores"][k]
            for k in ("weights", "supervision", "scaffolding", "feedback", "dynamics")
        ]
        for r in rows
    }


def pack_frame(
    geometry,
    meta,
    assignment,
    labels,
    *,
    shortlist=False,
    paper_reviews=None,
    jev=None,
    authors=None,
):
    geo = csv_index("results/" + geometry)
    order = list(geo)
    index = {pid: i for i, pid in enumerate(order)}
    papers = []
    for pid in order:
        r = meta[pid]
        g = geo[pid]
        a = assignment[pid]
        paper = {
            "id": pid,
            "t": r["title"],
            "y": int(r["year"]),
            "c": int(a["semantic_cluster"] if shortlist else a["cluster"]),
            "x": float(g["x"]),
            "ypos": float(g["y"]),
            "dist": float(a["distance"]),
            "nn": [index[n] for n in g["neighbors"].split()],
        }
        if shortlist:
            paper["a"] = r["authors"]
            paper["team"] = int(authors[pid]["cluster"])
            paper["url"] = r["url"]
        else:
            paper["category"] = r["category"]
        if paper_reviews and pid in paper_reviews:
            paper["review"] = paper_reviews[pid]
        if jev and pid in jev:
            paper["jev"] = jev[pid]
        papers.append(paper)
    return {"labels": labels, "papers": papers}


def section():
    audit = load("cluster_audit.json")
    mechanism = judgments("jev_mechanisms.jsonl")
    cluster = judgments("jev_cluster_audit.jsonl")
    control_jev = judgments("jev_checks.jsonl")
    shortlist = csv_index("results/alignment_papers.csv")
    control = csv_index("results/control_map.csv")
    original = {
        pid: r["common_codes"]
        for pid, r in csv_index("data/attention_review.csv").items()
    }
    control_reviews = {
        pid: ("feedback " if r["feedback_loop"] == "1" else "")
        + ("dynamics" if r["dynamics"] == "1" else "")
        or "neither"
        for pid, r in csv_index("data/control_validation.csv").items()
    }
    common_args = dict(paper_reviews=control_reviews, jev=control_jev)
    general_names = [
        "Learning methods and optimization",
        "Computer vision and generation",
        "Robotics and reinforcement learning",
        "Language models and applications",
    ]
    frames = [
        pack_frame(
            "shortlist_geometry.csv",
            shortlist,
            csv_index("results/semantic_clusters.csv"),
            ALIGN_NAMES,
            shortlist=True,
            authors=csv_index("results/author_clusters.csv"),
            paper_reviews=original,
            jev={**mechanism, **cluster},
        ),
        pack_frame(
            "general_geometry.csv",
            control,
            csv_index("results/general_topics.csv"),
            general_names,
            **common_args,
        ),
        pack_frame(
            "control_geometry.csv", control, control, CONTROL_NAMES, **common_args
        ),
    ]
    frames[0][
        "description"
    ] = "7,735 shortlisted papers. Colors show eight topics learned from title and abstract embeddings. The fit also included 179 baseline papers outside the shortlist."
    frames[1][
        "description"
    ] = "800 papers drawn from seven AI-related arXiv categories without a wording filter. Topics were fitted to these 800 papers alone."
    frames[2][
        "description"
    ] = "The same 800 AI papers plus 400 from systems, control and optimization. The extra sample makes control research easier to see and changes the topic mix."
    agreement = load("coauthor_topic_test.json")
    stats = audit["thresholds"]["0.5"]
    counts = stats["counts"]
    neither = [0] * 8
    extra = csv_index("results/semantic_clusters.csv")
    for pid, score in cluster.items():
        if max(score[:3]) < 0.5:
            neither[int(extra[pid]["semantic_cluster"])] += 1
    table = []
    for i, name in enumerate(ALIGN_NAMES):
        table.append(
            "<tr><th scope='row'>"
            + html.escape(name)
            + "</th>"
            + "".join(
                f"<td style='--fill:{n/32:.3f}'>{n}</td>"
                for n in [*counts[i], neither[i]]
            )
            + "</tr>"
        )
    section = (ROOT / "cluster-view.template.html").read_text()
    payload = json.dumps(frames, separators=(",", ":"), ensure_ascii=False).encode()
    packed = base64.b64encode(gzip.compress(payload, compresslevel=9, mtime=0)).decode()
    return (
        section.replace("{{PAYLOAD}}", packed)
        .replace("{{HEATMAP}}", "".join(table))
        .replace("{{EDGES}}", f'{agreement["edges"]:,}')
        .replace("{{SAME}}", f'{agreement["observed_share"]:.1%}')
        .replace("{{NULL}}", f'{agreement["year_permuted_mean"]:.1%}')
    )
