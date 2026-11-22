"""Download comparator inputs and page through Radar's public topic listings."""

import argparse
import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from attention import ROOT


def radar(topic, folder):
    first = "https://aisafetyradar.org/research?topic=" + topic
    url = first
    seen = set()
    rows = {}
    while url and url not in seen:
        seen.add(url)
        page = folder / (
            "page-" + hashlib.sha256(url.encode()).hexdigest()[:20] + ".html"
        )
        if not page.exists():
            r = requests.get(url, timeout=(10, 60))
            r.raise_for_status()
            page.write_bytes(r.content)
        markup = BeautifulSoup(page.read_bytes(), "html.parser")
        dates = []
        for article in markup.select("article[data-id]"):
            key = article["data-id"]
            label = article.find(
                string=re.compile(r"^~?\d{1,2} [A-Z][a-z]{2,3} 20\d{2}$")
            )
            if label is None:
                raise ValueError("Unrecognized Radar date for " + key)
            date = (
                datetime.strptime(
                    label.strip().lstrip("~").replace("Sept", "Sep"), "%d %b %Y"
                )
                .date()
                .isoformat()
            )
            dates.append(date)
            if date.startswith("2026-10") and key.startswith("arxiv:"):
                link = article.select_one("h2 a[href]")
                rows[key] = dict(
                    key=key,
                    title=link.get_text(" ", strip=True),
                    url=link["href"],
                    date=date,
                    topics=[
                        a["href"].split("topic=")[1]
                        for a in article.select('a[href^="/research?topic="]')
                    ],
                )
        if not dates:
            raise ValueError("No dated Radar records at " + url)
        if min(dates) < "2026-10-01":
            return dict(
                pages=len(seen),
                first_url=first,
                last_url=url,
                last_page_min_date=min(dates),
                rows=list(rows.values()),
            )
        older = next(
            (a for a in markup.select("a[href]") if "Load older" in a.get_text()), None
        )
        url = urljoin(url, older["href"]) if older else None
        time.sleep(0.3)
    raise ValueError("Radar pagination ended before October was covered")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    args = p.parse_args()
    args.folder.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "results/external_comparison.json").read_text())[
        "provenance"
    ]
    for key, source in manifest.items():
        dest = args.folder / key
        if not dest.exists():
            if key.startswith("radar_"):
                dest.write_text(json.dumps(radar(key[len("radar_") :], args.folder)))
            else:
                with requests.get(
                    source["url"], timeout=(15, 90), stream=True
                ) as reply:
                    reply.raise_for_status()
                    tmp = dest.with_suffix(".part")
                    with tmp.open("wb") as f:
                        for chunk in reply.iter_content(1048576):
                            f.write(chunk)
                    tmp.replace(dest)
                dest.with_suffix(".url").write_text(source["url"])
        same = hashlib.sha256(dest.read_bytes()).hexdigest() == source["sha256"]
        print(
            key,
            "same snapshot" if same else "source changed since frozen measurement",
            flush=True,
        )


if __name__ == "__main__":
    main()
