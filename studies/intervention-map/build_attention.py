"""Build an offline visual summary with the detailed analysis available on demand."""

import json
import math
from pathlib import Path

import markdown

from build_cluster_view import section as cluster_section

ROOT = Path(__file__).resolve().parent
FRAMES = [
    ("general_ai", "General AI"),
    ("explicit", "Explicit alignment"),
    ("core", "Broader alignment"),
]


def read_result(filename):
    return json.loads((ROOT / "results" / filename).read_text())


def interval_chart():
    rubric = read_result("attention.json")
    jev = read_result("jev_validation.json")["mechanisms"]
    chart = []
    for key, label in FRAMES:
        est = rubric[key]["full"]
        marks = []
        for name, result in [
            ("Rubric", est["W_either"]),
            ("Jev", jev[key]["weight_to_external"]["0.5"]),
        ]:
            lo, hi = result["ci95"]
            ratio = result["ratio"]
            # The horizontal axis spans 0.5 to 8 on a log scale.
            left, point, right = [25 * math.log2(n / 0.5) for n in (lo, ratio, hi)]
            marks.append(
                f'<div class="estimate {name.lower()}"><span class="method">{name}</span>'
                f'<div class="track" aria-hidden="true"><i style="left:{left:.3f}%;width:{right-left:.3f}%"></i>'
                f'<b style="left:{point:.3f}%"></b></div>'
                f'<span class="value"><strong>{ratio:.2f}</strong> <small>({lo:.2f}–{hi:.2f})</small></span></div>'
            )
        chart.append(
            f'<div class="group"><h3>{label} <small>n = {est["domain_review_n"]}</small></h3>{"".join(marks)}</div>'
        )
    return (
        "<figure><figcaption>Weight papers per paper on a control or harness</figcaption>"
        "<p>1 = equal counts. Lines show 95% sampling intervals. Jev cutoff 0.50.</p>"
        + "".join(chart)
        + '<div class="estimate axis" aria-hidden="true"><span></span><div class="ticks">'
        "<span>0.5</span><span>1</span><span>2</span><span>4</span><span>8</span></div><span></span></div>"
        '<p class="note">The 72 papers using alignment language are included in the 215 broader alignment papers. Each paper can study both approaches.</p></figure>'
    )


def render(source):
    return (
        markdown.markdown(source, extensions=["tables", "toc"])
        .replace("<table>", '<div class="scroll"><table>')
        .replace("</table>", "</table></div>")
    )


def main():
    source = (ROOT / "ATTENTION.md").read_text()
    lead, *sections = source.split("\n## ")
    hypotheses, detail = sections[0], sections[1:]
    measures = detail.pop(0)
    assert measures.startswith("What measures research attention?")
    cards = []
    for section in detail:
        heading, body = section.split("\n", 1)
        cards.append(f"<details><summary>{heading}</summary>{render(body)}</details>")
    styles = """
:root{color-scheme:light;--ink:#172e2c;--muted:#415e5a;--rule:#cbd4ce;--paper:#faf9f4;--a:#08685e;--b:#9a452a}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 Inter,system-ui,sans-serif}
main{max-width:920px;margin:auto;padding:36px 38px 72px}h1,h2,figcaption{font-family:Georgia,serif;font-weight:500;letter-spacing:-.035em;line-height:1.13}
h1{font-size:clamp(36px,6vw,64px);margin:0}h2,figcaption{font-size:clamp(23px,3.2vw,32px)}h2{margin:28px 0 14px}
header p{font-size:19px;max-width:76ch}header strong{color:var(--a)}p{margin:10px 0}a{color:var(--a);text-underline-offset:3px}
figure{margin:22px 0;padding:20px 24px;border:1px solid var(--rule);background:#f0f3ec;border-radius:5px}figure p,.note{color:var(--muted);font-size:13px}
.group{padding:8px 0;border-top:1px solid var(--rule)}h3{font-size:16px;margin:0 0 3px}h3 small{font-size:12px;font-weight:400;color:var(--muted);margin-left:4px}
.estimate{display:grid;grid-template-columns:56px minmax(72px,1fr) 148px;gap:14px;align-items:center;line-height:1.45;font-variant-numeric:tabular-nums}
.method{font-size:13px;font-weight:650}.rubric{color:var(--a)}.jev{color:var(--b)}.value{text-align:right}.value small{color:var(--muted);font-size:12px}
.track{height:21px;position:relative;background:linear-gradient(to right,transparent calc(25% - .75px),#788881 calc(25% - .75px),#788881 calc(25% + .75px),transparent calc(25% + .75px))}
.track i,.track b{display:block;position:absolute;background:currentColor;top:50%;transform:translateY(-50%)}
.track i{height:3px}.track b{width:9px;height:9px;transform:translate(-50%,-50%);border-radius:50%}.jev .track b{border-radius:0}
.ticks{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);border-top:1px solid var(--rule)}
.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;vertical-align:top;padding:11px 9px;border-bottom:1px solid var(--rule)}th{color:var(--muted);background:#eeefe8}
.hypotheses td:first-child{width:39%}.hypotheses>p{font-size:13px;color:var(--muted)}details{border-top:1px solid var(--rule);padding:10px 0}summary{cursor:pointer;font-weight:620;color:var(--a)}a:focus-visible,summary:focus-visible{outline:3px solid var(--b)}
@media(max-width:560px){main{padding:22px 15px 50px}figure{padding:14px 12px}.estimate{grid-template-columns:43px minmax(60px,1fr) 114px;gap:7px}.value{font-size:14px}.value small{font-size:10px}header p{font-size:16px}td,th{padding:8px 5px}.hypotheses table{font-size:13px}}
@media print{body,figure{background:white}main{padding:0}figure,tr{break-inside:avoid}}
"""
    html = (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Where does AI research put its effort?</title><style>{styles}</style></head><body><main>"
        f'<header>{render(lead)}</header>{cluster_section()}{render("## " + measures)}{interval_chart()}<section class="hypotheses">{render("## " + hypotheses)}</section>'
        f'<h2>Evidence and methods</h2>{"".join(cards)}</main></body></html>'
    )
    (ROOT / "attention-overview.html").write_text(html + "\n")


if __name__ == "__main__":
    main()
