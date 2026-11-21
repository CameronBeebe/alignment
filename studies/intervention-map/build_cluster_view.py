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
GENERAL_NAMES = [
    "Learning methods and optimization",
    "Computer vision and generation",
    "Robotics and reinforcement learning",
    "Language models and applications",
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


def pack_frame(
    geometry,
    meta,
    assignment,
    labels,
    *,
    shortlist=False,
    paper_reviews=None,
    measurements,
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
        paper.update(measurements[pid])
        papers.append(paper)
    return {"labels": labels, "papers": papers}


def section():
    manifest = load("master_manifest.json")
    keys = list(manifest["questions"])
    measurements = {}
    sources = {}
    with gzip.open(ROOT / "results/paper_master.csv.gz", "rt") as f:
        for row in csv.DictReader(f):
            sources[row["paper_id"]] = (row["title"], row["url"])
            measurements[row["paper_id"]] = {
                "jev": [float(row["jev_" + k]) for k in keys],
                "near_cos": float(row["nearest_cosine"]),
                "near_id": row["nearest_paper_id"],
                "topic_margin": float(row["topic_distance_margin"]),
                "score_basis": row["evidence_basis"],
                "lm": float(row["jev_language_model_focus"]),
            }
    for measurement in measurements.values():
        measurement["near_title"], measurement["near_url"] = sources[
            measurement["near_id"]
        ]
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
    common_args = dict(paper_reviews=control_reviews, measurements=measurements)
    frames = [
        pack_frame(
            "shortlist_geometry.csv",
            shortlist,
            csv_index("results/semantic_clusters.csv"),
            ALIGN_NAMES,
            shortlist=True,
            authors=csv_index("results/author_clusters.csv"),
            paper_reviews=original,
            measurements=measurements,
        ),
        pack_frame(
            "general_geometry.csv",
            control,
            csv_index("results/general_topics.csv"),
            GENERAL_NAMES,
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
    table = []
    for i, name in enumerate(ALIGN_NAMES):
        group = manifest["shortlist_topic_counts"][str(i)]
        n = group["papers"]
        cells = []
        for metric in ("weights", "external", "feedback_or_dynamics", "neither"):
            count = group[metric]
            cells.append(
                f"<td style='--fill:{count/n:.3f}' title='{count} of {n}'>{count/n:.0%}</td>"
            )
        table.append(
            f"<tr><th scope='row'>{html.escape(name)}</th><td>{n:,}</td>{''.join(cells)}</tr>"
        )
    section = (ROOT / "cluster-view.template.html").read_text()
    payload = json.dumps(frames, separators=(",", ":"), ensure_ascii=False).encode()
    packed = base64.b64encode(gzip.compress(payload, compresslevel=9, mtime=0)).decode()
    return (
        section.replace("{{PAYLOAD}}", packed)
        .replace("{{JEV_KEYS}}", json.dumps(keys))
        .replace("{{HEATMAP}}", "".join(table))
        .replace("{{EDGES}}", f'{agreement["edges"]:,}')
        .replace("{{SAME}}", f'{agreement["observed_share"]:.1%}')
        .replace("{{NULL}}", f'{agreement["year_permuted_mean"]:.1%}')
    )
