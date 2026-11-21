"""Render the research update and its interval plot for offline reading."""

import html
import json
import math
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent


def interval_chart():
    data = json.loads((ROOT / "results/attention.json").read_text())

    def x(ratio):
        return 158 + 500 * math.log(ratio / 0.5) / math.log(16)

    svg = [
        '<svg viewBox="0 0 690 164" role="img" aria-labelledby="plot-title plot-desc">',
        '<title id="plot-title">Weight papers per external-mechanism paper</title>',
        '<desc id="plot-desc">Design-weighted point estimates and 95 percent sampling intervals on a logarithmic scale. Numerical results follow in the table.</desc>',
    ]
    for tick in (0.5, 1, 2, 4, 8):
        xpos = x(tick)
        color = "#183c37" if tick == 1 else "#d6dcd8"
        svg += [
            f'<path d="M{xpos} 8 V134" stroke="{color}" stroke-dasharray="3 3"/>',
            f'<text x="{xpos}" y="151" text-anchor="middle">{tick:g}</text>',
        ]
    for i, (key, label) in enumerate(
        [
            ("general_ai", "General AI"),
            ("explicit", "Explicit alignment"),
            ("core", "Broader alignment"),
        ]
    ):
        est = data[key]["full"]["W_either"]
        y = 31 + i * 40
        lo, hi = map(x, est["ci95"])
        svg += [
            f'<text x="0" y="{y+5}">{label}</text>',
            f'<path d="M{lo} {y} H{hi} M{lo} {y-5} v10 M{hi} {y-5} v10" fill="none" stroke="#14756a" stroke-width="2.5"/>',
            f'<circle cx="{x(est["ratio"])}" cy="{y}" r="6" fill="#103f39"/>',
        ]
    return (
        "<figure><figcaption>Weight papers per external-mechanism paper · 95% intervals</figcaption>"
        + "".join(svg)
        + "</svg></figure>"
    )


def main():
    md = markdown.Markdown(extensions=["tables", "toc"])
    article = md.convert((ROOT / "ATTENTION.md").read_text())
    pos = article.index("<table>")
    article = article[:pos] + interval_chart() + article[pos:]
    article = article.replace("<table>", '<div class="table-scroll"><table>').replace(
        "</table>", "</table></div>"
    )
    nav = " ".join(
        f'<a href="#{h["id"]}">{html.escape(h["name"])}</a>'
        for h in md.toc_tokens[0]["children"]
    )
    css = """
:root{color-scheme:light;--ink:#1e302d;--green:#125c52}*{box-sizing:border-box}body{margin:0;background:#f9f8f4;color:var(--ink);font:17px/1.65 Inter,system-ui,sans-serif}main{max-width:940px;margin:auto;padding:48px 42px 90px}h1,h2{font-family:Georgia,serif;line-height:1.14;font-weight:500;letter-spacing:-.035em}h1{font-size:clamp(42px,7vw,80px);max-width:780px;margin:.55em 0 .25em}h1+p{color:var(--green);font-size:14px;letter-spacing:.015em}h2{font-size:clamp(29px,4vw,42px);margin:1.55em 0 .45em;border-top:1px solid #c4d0ca;padding-top:24px}p{margin:1em 0}strong{font-weight:650}a{color:var(--green);text-decoration-thickness:1px;text-underline-offset:3px}details{border-bottom:1px solid #c4d0ca;padding-bottom:10px}summary{cursor:pointer;font-weight:650;color:var(--green)}nav{display:grid;gap:3px;margin-top:9px}.table-scroll{overflow:auto}table{width:100%;border-collapse:collapse;margin:.5em 0;font-size:14px;line-height:1.48}th,td{padding:12px 10px;text-align:left;vertical-align:top;border-bottom:1px solid #d4ddd6}th{background:#e9eee8;color:#18433c;border-top:2px solid #467568}figure{margin:24px 0;padding:18px 20px;background:#edf2ec;border-radius:5px}figcaption{font-weight:650;font-size:15px}svg{width:100%;max-height:190px;display:block;margin:8px 0 0}svg text{fill:#233c37;font:14px system-ui,sans-serif}a:focus-visible,summary:focus-visible{outline:3px solid #a54b20}@media(max-width:600px){main{padding:20px 17px 45px}body{font-size:16px}figure{padding:9px}th,td{min-width:88px;padding:8px 6px}}@media print{body{background:white;font-size:11pt}main{max-width:none;padding:0}details{display:none}h2,figure,tr{break-inside:avoid}h2{break-after:avoid}}"""
    page = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Where does AI research put its effort?</title><style>{css}</style></head><body><main><details><summary>Contents</summary><nav>{nav}</nav></details><article>{article}</article></main></body></html>'
    (ROOT / "attention-overview.html").write_text(page + "\n")


if __name__ == "__main__":
    main()
