"""Build linked publication, measurement and survey figures from frozen study outputs."""

import csv
import html
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from build_cluster_view import ALIGN_NAMES, CONTROL_NAMES, GENERAL_NAMES

ROOT = Path(__file__).resolve().parent
FRAMES = [
    ("general_ai", "General AI"),
    ("explicit", "Explicit alignment"),
    ("core", "Broader alignment"),
]
ROLES = {
    "weights": "Weights",
    "supervision": "Supervision",
    "scaffolding": "Harness",
    "feedback": "Feedback",
    "dynamics": "Dynamics",
    "alignment_relevance": "Alignment relevance",
    "evaluation": "Evaluation",
    "theory": "Theory",
    "data_resources": "Data resources",
    "governance": "Governance",
}
CANDIDATE_NAMES = [
    "Safe control and robotics",
    "Language model adaptation",
    "Vision-language models",
    "Jailbreaks and defenses",
    "Preference training",
    "AI safety and agent systems",
]
COLORS = ["#216458", "#a85a30", "#665992", "#65716b"]


def read(name):
    return json.loads((ROOT / "results" / name).read_text())


def note(text):
    return f'<p class="chart-note">{text}</p>'


def table(headers, rows):
    cells = "".join(f'<th scope="col">{h}</th>' for h in headers)
    body = "".join(
        '<tr><th scope="row">'
        + str(r[0])
        + "</th>"
        + "".join(f"<td>{c}</td>" for c in r[1:])
        + "</tr>"
        for r in rows
    )
    return f'<div class="scroll"><table class="fig-table"><thead><tr>{cells}</tr></thead><tbody>{body}</tbody></table></div>'


def bar(frac, label=None, color=COLORS[0]):
    assert 0 <= frac <= 1
    label = label if label is not None else f"{frac:.0%}"
    return f'<span class="bar-cell"><i aria-hidden="true" style="width:{frac * 100:.3f}%;background:{color}"></i><span>{label}</span></span>'


def portfolio(attention, caption=None):
    keys = ["weights_only", "external_only", "both", "neither"]
    labels = ["Weights only", "Control or harness only", "Both", "Neither"]
    legend = "".join(
        f'<span><b style="background:{c}"></b>{s}</span>'
        for c, s in zip(COLORS, labels)
    )
    plots = []
    for key, label in FRAMES:
        shares = [attention[key]["paper_shares"][k] for k in keys]
        assert abs(sum(shares) - 1) < 1e-8
        segments = "".join(
            f'<i style="width:{v*100:.4f}%;background:{c}" title="{s} · {v:.1%}"></i>'
            for v, c, s in zip(shares, COLORS, labels)
        )
        nums = " · ".join(f"{s} {v:.1%}" for s, v in zip(labels, shares))
        plots.append(
            f'<div class="mix-row"><strong>{label} <small>n = {attention[key]["full"]["domain_review_n"]}</small></strong><div class="mix-strip" aria-hidden="true">{segments}</div><small>{nums}</small></div>'
        )
    return (
        '<h3>What share of papers studies each approach?</h3><p class="mix-legend">'
        + legend
        + "</p>"
        + "".join(plots)
        + note(
            caption
            or "Sampling-weighted rubric estimates. Each strip totals 100%. The 72 explicitly framed papers are included in the 215 broader alignment papers. External mechanisms include supervision and runtime harnesses."
        )
    )


def forest(rows, ticks, caption):
    low, high = ticks[0], ticks[-1]

    def position(v):
        return 100 * math.log(v / low) / math.log(high / low)

    plots = []
    for label, point, ci in rows:
        lo, hi = ci
        assert low <= lo <= point <= hi <= high, (label, ci, ticks)
        marks = (
            f'<i class="one" style="left:{position(1):.3f}%"></i><i class="ci" style="left:{position(lo):.3f}%;width:{position(hi)-position(lo):.3f}%"></i>'
            f'<i class="dot" style="left:{position(point):.3f}%"></i>'
        )
        plots.append(
            f'<div class="forest-row"><span>{label}</span><span class="rail" aria-hidden="true">{marks}</span><span class="numeric"><b>{point:.2f}</b> ({lo:.2f}–{hi:.2f})</span></div>'
        )
    axis = "".join(f'<span style="left:{position(t):.3f}%">{t:g}</span>' for t in ticks)
    return (
        "".join(plots)
        + f'<div class="forest-row"><span></span><div class="forest-axis">{axis}</div></div>'
        + note(caption)
    )


def ratio_panels(a):
    j = read("jev_validation.json")["mechanisms"]
    panels = []
    for mode in (
        "Reviewers",
        "External definition",
        "Earlier and later",
        "Jev cutoff",
        "Direct comparison",
    ):
        rows = []
        for key, label in FRAMES:

            def add(s, r):
                rows.append((f"{label} · {s}", r["ratio"], r["ci95"]))

            if mode == "Reviewers":
                add("Rubric", a[key]["full"]["W_either"])
                add("Jev", j[key]["weight_to_external"]["0.5"])
            if mode == "External definition":
                for k, s in [
                    ("W_E", "supervision"),
                    ("W_H", "harness"),
                    ("W_either", "either"),
                ]:
                    add(s, a[key]["full"][k])
            if mode == "Earlier and later":
                for k, s in [("2021_24", "2021–24"), ("2025_26", "2025–26")]:
                    add(s, a[key][k]["W_either"])
            if mode == "Jev cutoff":
                for v in ("0.3", "0.5", "0.7"):
                    add(v, j[key]["weight_to_external"][v])
        ticks = [0.5, 1, 2, 4, 8]
        caption = "Weights per paper studying supervision or a harness. The line marks equal counts. Bars show 95% sampling intervals conditional on the labels. Jev uses the five-question audit at 0.50."
        if mode == "External definition":
            ticks = [0.5, 1, 2, 4, 8, 16, 32]
            caption = "Each row uses the same sampling-weighted rubric weight count. The denominator changes from supervision to harness to their union. Hybrids receive credit on each applicable side."
        elif mode == "Earlier and later":
            ticks = [0.5, 1, 2, 4, 8, 16, 32]
            caption = "Rubric estimates, with 95% sampling intervals. The periods cover November 2021–December 2024 and January 2025–October 2026. Paper and subject mix can change between periods."
        elif mode == "Jev cutoff":
            ticks = [0.25, 0.5, 1, 2, 4, 8, 16, 32]
            caption = "Five-question audit at three score cutoffs on the same reviewed papers. A paper receives an external vote when supervision or harness reaches the cutoff."
        elif mode == "Direct comparison":
            ticks = [0.125, 0.25, 0.5, 1, 2, 4, 8]
            ratios = read("frame_contrast.json")
            rows = [
                (
                    f"Explicit / general AI · {k.title()}",
                    v["ratio_of_ratios"],
                    v["ci95"],
                )
                for k, v in ratios.items()
            ]
            pair = read("semantic_checks.json")["pairs"]
            rows.append(
                (
                    "Matched alignment / comparison",
                    pair["ratio_of_ratios"],
                    pair["paired_bootstrap_ci"],
                )
            )
            caption = "Ratio of weight-to-external ratios. Above 1 means the first group is more weight-focused. The last row is a separate rubric check on 49 year- and category-matched computational-linguistics pairs with a paired bootstrap interval."
        panels.append((mode, forest(rows, ticks, caption)))
    return tabs("ratio", "Compare estimates", panels)


def tabs(prefix, title, choices):
    buttons = "".join(
        f'<button type="button" aria-pressed="{str(i==0).lower()}" aria-controls="{prefix}-{i}" data-panel="{prefix}-{i}">{label}</button>'
        for i, (label, _) in enumerate(choices)
    )
    sections = "".join(
        f'<section id="{prefix}-{i}"{"" if i==0 else " hidden"}>{body}</section>'
        for i, (_, body) in enumerate(choices)
    )
    return f'<div class="fig-switch"><div class="fig-tabs" role="group" aria-label="{title}">{buttons}</div>{sections}</div>'


def audit():
    v = read("master_validation.json")
    frames = [
        ("core", "Broader alignment"),
        ("general_ai_audit", "General AI"),
        ("control_review", "AI, systems and control"),
        ("descriptive_roles_32", "Contribution roles"),
    ]
    blocks = []
    for key, label in frames:
        rows = []
        for role, s in v[key].items():
            rows.append(
                [
                    ROLES[role],
                    f'{s["positive_reference"]} / {s["n"]}',
                    bar(s["recall_050"]),
                    bar(s["precision_050"], color=COLORS[1]),
                    f'{s["fn"]} / {s["fp"]}',
                ]
            )
        blocks.append(
            (
                label,
                table(
                    [
                        "Dimension",
                        "Rubric positives",
                        "Recall",
                        "Precision",
                        "Missed / extra calls",
                    ],
                    rows,
                ),
            )
        )
    return (
        "<h3>Which mechanisms does Jev miss?</h3>"
        + note(
            "Recall is the share of rubric positives Jev recovers. Precision is the share of Jev positives the rubric also identifies. Both reviews use AI and public paper metadata. Cutoff 0.50."
        )
        + tabs("audit", "Validation sample", blocks)
        + note(
            'Percentages use the audit sampling weights. Counts are observed paper IDs. The 32-paper contribution-role check is unweighted and has only three theory positives. <a href="results/master_validation.json">Validation data</a>'
        )
    )


def vocabulary(a):
    rows = []
    for frame, group in a["terminology"].items():
        for v in group:
            n = v["reviewed_harness"]
            period = "2021–24" if v["period"] == "2021_24" else "2025–26"
            rows.append(
                [
                    ("Alignment" if frame == "alignment" else "General AI")
                    + " · "
                    + period,
                    str(n),
                    bar(v["literal_matches"] / n, str(v["literal_matches"])),
                    bar(v["expanded_matches"] / n, str(v["expanded_matches"])),
                ]
            )
    return (
        "<h3>Would a keyword search have found the harness papers?</h3>"
        + table(
            [
                "Reviewed sample",
                "Rubric harness papers",
                "Literal “harness”",
                "Expanded vocabulary",
            ],
            rows,
        )
        + note(
            'Cells give counts. Bar length shows the fraction of reviewed harness papers found. The expanded search includes older terms such as scaffolding and orchestration. These are unweighted audit counts. <a href="results/attention.json">Terminology data</a>'
        )
    )


def coverage(a):
    c = read("semantic_checks.json")["coverage"]
    control = read("control_map.json")["groups"]
    rows = []
    for v in a["control_validation"]["groups"]:
        i = v["id"]
        s = c[str(i)]
        n = s["n"]
        ai = control[i]["general_ai"]
        rows.append(
            [
                CONTROL_NAMES[i],
                f"{ai} / {n-ai}",
                bar(v["positive"] / v["n"], f'{v["positive"]} / {v["n"]}'),
                f'{s["candidate_id_overlap"]} / {n}',
                f'{s["shortlist_id_overlap"]} / {n}',
            ]
        )
    comparison = table(
        [
            "Topic",
            "AI / systems draw",
            "Reviewed feedback or dynamics",
            "Found in candidates",
            "Found in shortlist",
        ],
        rows,
    )
    b = read("author_balance.json")["analyses"]["primary"]
    network = read("coauthor_topic_test.json")
    team_rows = []
    for key, label in [
        ("named", "Explicit wording"),
        ("other", "Other wording"),
        ("all", "Combined"),
    ]:
        g = b[key]
        lo, hi = g["leave_one_group_out_range"]
        team_rows.append(
            [
                label,
                f'{g["distinct_papers"]} / {g["represented_groups"]}',
                str(g["largest_reviewed_count_in_one_group"]),
                f'{g["weighted_ratio"]:.2f}',
                f"{lo:.2f}–{hi:.2f}",
            ]
        )
    return (
        "<h3>Where does the alignment search lose coverage?</h3>"
        + comparison
        + note(
            "800 general-AI papers and 400 systems/control/optimization papers were drawn without topical keywords. Fifteen abstracts per topic were reviewed. Overlap counts require the same paper ID. Physical control systems can fall outside alignment by design."
        )
        + "<h3>Do papers with shared authors study similar topics?</h3>"
        + table(
            ["Share of linked pairs in the same shortlist topic", "Percent"],
            [
                ["Observed across linked papers", bar(network["observed_share"])],
                [
                    "Topic labels shuffled within publication year",
                    bar(network["year_permuted_mean"], color=COLORS[3]),
                ],
            ],
        )
        + note(
            f'{network["edges"]:,} paper pairs share at least two author names. The shuffle preserves the topic mix within each year.'
        )
        + "<h3>How sensitive is the 7.20 ratio to individual groups?</h3>"
        + table(
            [
                "Review subset",
                "Papers / groups",
                "Max papers in one group",
                "Weight / supervision",
                "Range after dropping one group",
            ],
            team_rows,
        )
        + note(
            'This comparison counts alignment-directed weights and external supervision. The range describes the effect of removing one represented coauthor group at a time. <a href="results/author_balance.json">Group sensitivity</a> · <a href="results/semantic_checks.json">Coverage data</a>'
        )
    )


def people():
    with (ROOT / "data/attention_indicators.csv").open() as stream:
        indicators = list(csv.DictReader(stream))

    def group(source):
        return [r for r in indicators if r["source"] == source]

    def credit(data):
        return f'<a href="{html.escape(data[0]["url"],quote=True)}">{html.escape(data[0]["source"])}</a>'

    pew = group("Pew US")
    rows = []
    for m in dict.fromkeys(r["measure"] for r in pew):
        public, expert = [r for r in pew if r["measure"] == m]
        rows.append(
            [
                html.escape(m),
                bar(float(public["value"]) / 100),
                bar(float(expert["value"]) / 100, color=COLORS[1]),
            ]
        )
    prod = group("Pan et al.")
    production = [
        [html.escape(r["measure"]), bar(float(r["value"]) / 100)] for r in prod
    ]
    global_survey = group("Pew global")
    geography = []
    for m in dict.fromkeys(r["measure"] for r in global_survey):
        high, middle = [r for r in global_survey if r["measure"] == m]
        geography.append(
            [
                html.escape(m),
                bar(float(high["value"]) / 100),
                bar(float(middle["value"]) / 100, color=COLORS[1]),
            ]
        )
    public_chart = (
        "<h3>Where do US adults and AI experts agree?</h3>"
        + table(["Survey question", "US adults", "AI experts"], rows)
        + note(
            "2024 fieldwork. 5,410 US adults and 1,013 conference-affiliated AI experts. Personal control can mean choosing, correcting or refusing an AI use. "
            + credit(pew)
        )
        + "<h3>How do job expectations vary across countries?</h3>"
        + table(
            ["2026 survey", "18 high-income countries", "18 middle-income countries"],
            geography,
        )
        + note(
            "Median percentage across countries in each group, with each country weighted equally. "
            + credit(global_survey)
        )
    )
    forecasts = [r for r in group("ESPAI") if r["unit"] == "calendar year"]
    risk = group("ESPAI safety")[0]
    public_chart += (
        "<h3>What futures do publishing researchers expect?</h3>"
        + table(
            ["2023 researcher survey", "Aggregate 50% date"],
            [[html.escape(r["measure"]), r["value"]] for r in forecasts],
        )
        + note(
            f'Of responding authors, about {risk["value"]}% wanted higher societal priority for risk-reduction research. The survey covered 2,778 AI authors. Forecasts depend on the question and continued scientific progress. '
            + credit(forecasts)
        )
    )
    deploy = (
        "<h3>What do people deploying agents report?</h3>"
        + table(["Practice", "Share reporting"], production)
        + note(
            "Selected study of 86 practitioners across 26 domains. Responses can overlap. "
            + credit(prod)
        )
    )

    def compare_years(source):
        data = group(source)
        maximum = max(float(r["value"]) for r in data)
        rows = []
        for measure in dict.fromkeys(r["measure"] for r in data):
            values = sorted(
                (r for r in data if r["measure"] == measure),
                key=lambda r: r["observation_period"],
            )
            rows.append(
                [
                    html.escape(measure),
                    *[
                        bar(float(r["value"]) / maximum, f'{int(r["value"]):,}')
                        for r in values
                    ],
                ]
            )
        return table(["Indicator", "2024", "2025"], rows)

    resources = (
        "<h3>How did demand for agent skills change?</h3>"
        + compare_years("AI Index hiring")
        + note(
            "US AI job postings tracked by Lightcast. Skill labels can overlap and change over time. "
            + credit(group("AI Index hiring"))
        )
        + "<h3>How many incidents were reported?</h3>"
        + compare_years("AI Index safety")
        + note(
            "Counts depend on exposure and reporting coverage. The ledger lacks deployments or user-hours for estimating a rate. "
            + credit(group("AI Index safety"))
        )
        + "<h3>Can spending or researcher time establish misallocation?</h3>"
        + note(
            'The ledger records investment, grants and hiring in different units. It lacks comparable spending, engineer-hours and safety gains for weights and harnesses. The return per dollar or hour is unknown. <a href="data/attention_indicators.csv">All 32 observations and their sources</a>'
        )
    )
    return tabs(
        "people",
        "Human and operational evidence",
        [
            ("Public and researchers", public_chart),
            ("Deployment", deploy),
            ("Hiring, incidents and spending", resources),
        ],
    )


def profile_counts(sub, topic, names):
    years = sub.year.to_numpy(int)
    topics = sub[topic].to_numpy(int)
    scores = sub[["jev_" + k for k in ROLES]].to_numpy(float)
    dims = {}
    for cut in (0.3, 0.5, 0.7):
        hits = (scores >= cut).astype(int)

        def groups(v, keys):
            counts = []
            for k in keys:
                mask = v == k
                counts.append([int(mask.sum()), *hits[mask].sum(axis=0).tolist()])
            return counts

        dims[str(cut)] = {
            "topic": groups(topics, range(len(names))),
            "year": groups(years, range(2021, 2027)),
            "overlap": np.column_stack((hits.sum(axis=0), hits.T @ hits)).tolist(),
        }
    return {"names": names, "n": len(sub), "cuts": dims}


def explorer_data():
    papers = pd.read_csv(ROOT / "results/paper_master.csv.gz", keep_default_na=False)
    memberships = papers.cohorts.str.split("|", regex=False)
    profiles = {}
    for frame, role, topic, names in [
        (
            "Alignment shortlist",
            "alignment_shortlist",
            "shortlist_map_topic",
            ALIGN_NAMES,
        ),
        ("General AI draw", "general_ai", "general_map_topic", GENERAL_NAMES),
        (
            "Systems/control draw",
            "control_and_optimization",
            "control_map_topic",
            CONTROL_NAMES,
        ),
        (
            "All alignment-search candidates",
            "candidate",
            "candidate_topic",
            CANDIDATE_NAMES,
        ),
    ]:
        sub = papers[memberships.map(lambda g: role in g)]
        profiles[frame] = {
            "all": profile_counts(sub, topic, names),
            "lm": profile_counts(
                sub[sub.jev_language_model_focus.ge(0.5)], topic, names
            ),
        }
    return {"roles": list(ROLES.values()), "frames": profiles}


def fullpaper_panel():
    data = read("fulltext_summary.json")
    n = data["paired"]
    rows = []
    for key, label in [("jev", "Jev"), ("qwen", "Qwen")]:
        for basis, source in [("abstract", "Abstract"), ("paper", "Full paper")]:
            r = data["ratios"][f"{key}_{basis}"]
            low, high = r["ci95"]
            rows.append(
                [
                    label,
                    source,
                    int(r["observed_W"]),
                    int(r["observed_E"]),
                    f'<b>{r["ratio"]:.2f}</b> ({low:.2f}–{high:.2f})',
                ]
            )
    out = (
        '<h3 id="full-paper-check">Does reading the full paper change the result?</h3>'
    )
    out += note(
        f'{n} of {data["eligible"]} explicitly alignment-worded language-model papers have paired reads. Same papers, same questions within each reviewer. External includes supervision and runtime harnesses. A hybrid enters both counts.'
    )
    out += table(
        [
            "Reviewer",
            "Evidence",
            "Weight papers",
            "External papers",
            "Weighted ratio (95% CI)",
        ],
        rows,
    )
    out += note(
        "At a permissive Jev cutoff of 0.30 the full-paper ratio is 1.02 (0.79–1.32). At 0.70 it is 2.64 (1.57–4.45). Intervals measure sampling uncertainty conditional on the labels."
    )
    out += "<details><summary>Which papers change classification?</summary>"
    out += table(
        [
            "Reviewer",
            "Weight gained / lost",
            "External gained / lost",
            "Full / abstract ratio (95% CI)",
        ],
        [
            [
                name,
                f'{chg["weights"]["gained"]} / {chg["weights"]["lost"]}',
                f'{chg["external"]["gained"]} / {chg["external"]["lost"]}',
                f'{chg["full_over_abstract"]:.2f} ({chg["ci95"][0]:.2f}–{chg["ci95"][1]:.2f})',
            ]
            for name, chg in ((k.title(), v) for k, v in data["changes"].items())
        ],
    )
    out += note(
        f'On full papers, Jev and Qwen agree on the weight label for {data["agreement"]["paper"]["weights"]}/{n} papers and the external label for {data["agreement"]["paper"]["external"]}/{n}.'
    )
    out += note(
        'One disagreement concerns <a href="https://arxiv.org/abs/2411.08733">Dynamic Rewarding with Prompt Optimization</a>. The authors optimize instructions without updating the acting model. Qwen marks weights present and Jev scores weights at 0.08. The paper also discusses training-based comparisons.'
    )
    out += "</details><details><summary>Change the Jev decision cutoff</summary>"
    out += table(
        [
            "Full-paper cutoff",
            "Weight papers",
            "External papers",
            "Weighted ratio (95% CI)",
        ],
        [
            [
                cut,
                int(r["observed_W"]),
                int(r["observed_E"]),
                f'{r["ratio"]:.2f} ({r["ci95"][0]:.2f}–{r["ci95"][1]:.2f})',
            ]
            for cut, r in data["jev_paper_cutoffs"].items()
        ],
    )
    out += "</details><details><summary>Explore all 67 Jev questions</summary>"

    out += note(
        f"Bars count papers scoring at least 0.50 out of {n} paired papers. Gained and lost count papers crossing that cutoff. These exploratory labels have no independent accuracy estimate."
    )
    for group, items in data["questions"].items():
        out += "<details><summary>" + html.escape(group) + f" ({len(items)})</summary>"
        out += table(
            ["Question", "Abstract", "Full paper", "Gained / lost"],
            [
                [
                    html.escape(v["question"]),
                    bar(v["abstract"] / n, str(v["abstract"])),
                    bar(v["paper"] / n, str(v["paper"])),
                    f'{v["gained"]} / {v["lost"]}',
                ]
                for v in items.values()
            ],
        )
        out += "</details>"
    out += "</details>"
    out += note(
        '<a href="results/fulltext_measures.csv" download>Paper scores and PDF sources (CSV)</a> · <a href="results/fulltext_requests.csv" download>Request and token ledger (CSV)</a>'
    )
    return out


def language_panel():
    result = read("language_comparison.json")
    variants = [
        ("semantic_050", "Language-model focus"),
        ("literal_or_family", "LLM wording or model name"),
        ("literal", "Literal LLM wording"),
        ("semantic_030", "Scope cutoff 0.30"),
        ("semantic_070", "Scope cutoff 0.70"),
        ("all", "All model families"),
    ]
    choices = []
    for selector, label in variants:
        v = result[selector]
        rows = []
        points = []
        for key, frame in [
            ("explicit", "Explicit alignment"),
            ("other_wording", "Other alignment wording"),
            ("core", "Broader alignment (both groups)"),
            ("general_ai", "General AI"),
        ]:
            r = v["frames"][key]

            def estimate(method):
                est = r[method]
                lo, hi = est["ci95"]
                return f'<b>{est["ratio"]:.2f}</b> ({lo:.2f}–{hi:.2f})'

            rows.append(
                [
                    frame,
                    f'{r["selected_n"]} / {r["frame_n"]}',
                    f'{int(r["rubric"]["observed_W"])} / {int(r["rubric"]["observed_E"])}',
                    estimate("rubric"),
                    estimate("jev"),
                ]
            )
            for method in ("rubric", "jev"):
                est = r[method]
                points.append(
                    (
                        frame + " · " + ("Rubric" if method == "rubric" else "Jev"),
                        est["ratio"],
                        est["ci95"],
                    )
                )
        lo = min(math.floor(math.log2(min(p[2][0] for p in points))), -1)
        hi = max(math.ceil(math.log2(max(p[2][1] for p in points))), 1)
        body = table(
            [
                "Reviewed sample",
                "Included / reviewed",
                "Rubric papers W / external",
                "Rubric ratio (95%)",
                "Jev ratio (95%)",
            ],
            rows,
        )
        body += note(
            f'{v["master_n"]:,} of 26,697 master paper IDs meet this selection. W counts changes to the acting model’s weights. External counts supervision or runtime harnesses. Ratios use sampling weights. Hybrids can enter both counts.'
        )
        body += (
            "<details><summary>Plot the ratios and sampling intervals</summary>"
            + forest(
                points,
                [2**i for i in range(lo, hi + 1)],
                "Above 1 means more papers study weights than external supervision or harnesses. Intervals condition on the abstract classifications.",
            )
            + "</details>"
        )
        contrast = v["explicit_vs_other"]
        descriptions = []
        for method, title in [("rubric", "Rubric"), ("jev", "Jev")]:
            comp = contrast[method]
            low, high = comp["ci95"]
            descriptions.append(
                f'{title} {comp["ratio_of_ratios"]:.2f} ({low:.2f}–{high:.2f})'
            )
        body += note(
            "Weight-to-external ratio in explicitly framed alignment divided by the ratio in other alignment papers, with 95% intervals. "
            + " · ".join(descriptions)
            + "."
        )
        mix = {
            key: {
                "paper_shares": row["rubric_shares"],
                "full": {"domain_review_n": row["selected_n"]},
            }
            for key, row in v["frames"].items()
        }
        body += (
            "<details><summary>See the publication mix, including both and neither</summary>"
            + portfolio(
                mix,
                "Sampling-weighted shares within the selected sample. External includes supervision and runtime harnesses.",
            )
            + "</details>"
        )
        if "periods" in v:
            period_rows = []
            for key, title in [
                ("explicit", "Explicit"),
                ("other_wording", "Other wording"),
            ]:
                for era, entry in v["periods"][key].items():
                    cells = []
                    for method in ("rubric", "jev"):
                        est = entry[method]
                        low, high = est["ci95"]
                        cells.append(f'{est["ratio"]:.2f} ({low:.2f}–{high:.2f})')
                    period_rows.append([title, era, entry["reviewed"], *cells])
            body += (
                "<details><summary>Compare earlier and later publications</summary>"
                + table(
                    [
                        "Alignment wording",
                        "Period",
                        "Reviewed",
                        "Rubric ratio (95%)",
                        "Jev ratio (95%)",
                    ],
                    period_rows,
                )
                + note(
                    "Each estimate uses the original sampling weights for that period. Small counts widen the intervals."
                )
                + "</details>"
            )
        choices.append((label, body))
    check = result["review_check"]
    v = check["semantic_050"]
    return (
        '<h3 id="language-models">How weight-focused are language-model papers?</h3>'
        + note(
            "The default selects work substantively studying or using an LLM or language Transformer, including GPT, BERT and language-based multimodal agents. A vision-only Transformer or a passing LLM mention falls outside this definition. The selection uses a separate Jev score of at least 0.50 on the title and available abstract."
        )
        + note(
            '<a href="results/language_model_papers.csv.gz" download>Download the language-model paper catalog</a> · <a href="results/paper_master.csv.gz" download>Download all papers</a>'
        )
        + tabs("lm", "Model-scope definition", choices)
        + fullpaper_panel()
        + note(
            "Explicit alignment means the paper uses one of the study’s alignment phrases. The comparison with other wording uses two disjoint groups. The broader alignment row combines them. The same model-scope selection is used for both mechanism reviewers."
        )
        + note(
            f'In a separate AI check of 40 abstracts balanced by sample and wording, {check["unclear"]} had uncertain scope. Jev agreed on {v["tp"]+v["tn"]} of {v["tp"]+v["tn"]+v["fp"]+v["fn"]} determinate cases. <a href="results/language_comparison.json">Data</a> · <a href="data/language_scope_review.csv">Review decisions</a>'
        )
    )


def section():
    a = read("attention.json")
    template = (ROOT / "attention-figures.template.html").read_text()
    layout, controls = template.split("<!-- controls -->")
    profile = json.dumps(explorer_data(), separators=(",", ":")).replace("<", "\\u003c")
    panels = [
        ("Language models", language_panel()),
        (
            "Publication mix",
            portfolio(a)
            + "<h3>How does the weight-to-external ratio change?</h3>"
            + ratio_panels(a),
        ),
        ("Topics, years & overlap", controls),
        ("Reviewer agreement", audit() + vocabulary(a)),
        ("Authors & coverage", coverage(a)),
        ("People & practice", people()),
    ]
    return layout.replace(
        "{{PANELS}}", tabs("insight", "Research questions", panels)
    ).replace("{{DATA}}", profile)
