"""Build an offline visual summary with the detailed analysis available on demand."""

from pathlib import Path

import markdown

from attention_figures import section as figure_section
from build_cluster_view import section as cluster_section

ROOT = Path(__file__).resolve().parent


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
.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;vertical-align:top;padding:11px 9px;border-bottom:1px solid var(--rule)}th{color:var(--muted);background:#eeefe8}
.hypotheses td:first-child{width:39%}.hypotheses>p{font-size:13px;color:var(--muted)}details{border-top:1px solid var(--rule);padding:10px 0}summary{cursor:pointer;font-weight:620;color:var(--a)}a:focus-visible,summary:focus-visible{outline:3px solid var(--b)}
@media(max-width:560px){main{padding:22px 15px 50px}figure{padding:14px 12px}.estimate{grid-template-columns:43px minmax(60px,1fr) 114px;gap:7px}.value{font-size:14px}.value small{font-size:10px}header p{font-size:16px}td,th{padding:8px 5px}.hypotheses table{font-size:13px}}
@media print{body,figure{background:white}main{padding:0}figure,tr{break-inside:avoid}}
"""
    html = (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Where does AI research put its effort?</title><style>{styles}</style></head><body><main>"
        f'<header>{render(lead)}</header>{figure_section()}{cluster_section()}{render("## " + measures)}<section class="hypotheses">{render("## " + hypotheses)}</section>'
        f'<h2>Evidence and methods</h2>{"".join(cards)}</main></body></html>'
    )
    (ROOT / "attention-overview.html").write_text(html + "\n")


if __name__ == "__main__":
    main()
