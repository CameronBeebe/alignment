"""Explore recurring collaborations across the frozen alignment shortlist.

Run with Python 3.12 and networkx==3.4.2. Writes paper-level assignments and
a summary to results/. Only substantive labels from the original audit are used.
"""

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import networkx as nx

RESULTS = Path(__file__).resolve().parent / "results"


def read_rows(filename):
    with (RESULTS / filename).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def author_names(row):
    text = " ".join(row["authors"].split())
    # Remove nested parenthetical affiliation notes before splitting bylines.
    while re.search(r"\([^()]*\)", text):
        text = re.sub(r"\([^()]*\)", "", text)
    if row["paper_id"].startswith("acl:"):
        names = []
        for author in text.split(" and "):
            family, comma, given = author.partition(",")
            names.append(f"{given} {family}" if comma else family)
    else:
        text = re.sub(r"^[^,:]{1,50}:\s*", "", text)
        names = re.split(r"\s*,\s*|\s+and\s+|\s*;\s*", text)
    keys = set()
    for name in names:
        name = re.sub(r"^and\s+", "", name.strip())
        name = unicodedata.normalize("NFC", name.casefold())
        name = " ".join(name.split())
        if len(name.split()) >= 2 and name not in {"et al.", "et al"}:
            keys.add(name)
    return keys


def make_graph(byline):
    # Count distinct shared names; requiring two reduces accidental links.
    papers_by_name = defaultdict(list)
    shared = Counter()
    for paper, names in sorted(byline.items()):
        for name in sorted(names):
            for earlier in papers_by_name[name]:
                shared[earlier, paper] += 1
            papers_by_name[name].append(paper)
    graph = nx.Graph()
    graph.add_nodes_from(sorted(byline))
    for (left, right), count in sorted(shared.items()):
        if count >= 2:
            graph.add_edge(left, right, weight=count)
    return graph


def partition(graph, seed):
    groups = nx.community.louvain_communities(graph, weight="weight", seed=seed)
    return sorted(groups, key=lambda g: (-len(g), min(g)))


def totals(ids, audit):
    votes = Counter()
    for pid in ids:
        r = audit[pid]
        for m in "WE":
            if m in r["mechanisms"]:
                votes[m] += int(r["N_h"]) / int(r["n_h"])
    return votes


def summarize(ids, audit, groups):
    selected = set(ids)
    total = totals(sorted(ids), audit)
    observed = []
    singles_removed = []
    for group in groups:
        hits = sorted(selected & group)
        if not hits:
            continue
        votes = totals(hits, audit)
        observed.append(hits)
        remaining_e = total["E"] - votes["E"]
        if remaining_e > 1e-8:
            singles_removed.append((total["W"] - votes["W"]) / remaining_e)
    return {
        "distinct_papers": len(selected),
        "weight_papers": sum("W" in audit[i]["mechanisms"] for i in selected),
        "external_papers": sum("E" in audit[i]["mechanisms"] for i in selected),
        "represented_groups": len(observed),
        "largest_reviewed_count_in_one_group": max(map(len, observed)),
        "groups_with_both_mechanisms": sum(
            all(any(m in audit[i]["mechanisms"] for i in g) for m in "WE")
            for g in observed
        ),
        "weighted_ratio": total["W"] / total["E"],
        "leave_one_group_out_range": [min(singles_removed), max(singles_removed)],
        "leave_one_group_out_undefined": len(observed) - len(singles_removed),
    }


def main():
    shortlist = {r["paper_id"]: r for r in read_rows("alignment_papers.csv")}
    named = {r["paper_id"] for r in read_rows("papers.csv") if r["named"] == "True"}
    audit = {
        r["paper_id"]: r
        for r in read_rows("reviewed_alignment.csv")
        if set(r["mechanisms"]) & {"W", "E"}
    }
    byline = {i: author_names(r) for i, r in shortlist.items()}
    graph = make_graph(byline)
    summary = {
        "networkx": nx.__version__,
        "shortlist": len(graph),
        "papers_without_parsed_names": sum(not v for v in byline.values()),
        "edges": graph.number_of_edges(),
        "isolated_papers": len(list(nx.isolates(graph))),
        "analyses": {},
    }
    for label, groups in (
        ("primary", partition(graph, 17)),
        ("alternate_seed", partition(graph, 43)),
        (
            "three_shared_names",
            partition(
                nx.subgraph_view(
                    graph, filter_edge=lambda u, v: graph[u][v]["weight"] >= 3
                ),
                17,
            ),
        ),
    ):
        summary["analyses"][label] = {
            "named": summarize(named & audit.keys(), audit, groups),
            "other": summarize(audit.keys() - named, audit, groups),
            "all": summarize(audit, audit, groups),
        }
        if label == "primary":
            with (RESULTS / "author_clusters.csv").open(
                "w", encoding="utf-8", newline=""
            ) as stream:
                writer = csv.writer(stream)
                writer.writerow(
                    [
                        "cluster",
                        "cluster_size",
                        "paper_id",
                        "title",
                        "url",
                        "authors",
                        "explicit_vocabulary",
                        "reviewed_mechanisms",
                        "selection",
                    ]
                )
                for index, group in enumerate(groups, 1):
                    for i in sorted(group):
                        row = shortlist[i]
                        writer.writerow(
                            [
                                index,
                                len(group),
                                i,
                                row["title"],
                                row["url"],
                                row["authors"],
                                i in named,
                                row["reviewed_mechanisms"],
                                row["selection"],
                            ]
                        )
    # Direct overlap in the reviewed explicit-vocabulary W/E papers alone.
    direct = sorted(named & audit.keys())
    summary["direct_named_overlap"] = {}
    for k in (1, 2):
        overlap = nx.Graph()
        overlap.add_nodes_from(direct)
        overlap.add_edges_from(
            (a, b)
            for a, b in combinations(direct, 2)
            if len(byline[a] & byline[b]) >= k
        )
        components = list(nx.connected_components(overlap))
        summary["direct_named_overlap"][k] = {
            "linked_pairs": overlap.number_of_edges(),
            "largest_connected_set": max(map(len, components)),
        }
    (RESULTS / "author_balance.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
