"""Build or refresh a local, month-bounded metadata catalog. Never called by analysis."""

import argparse
import calendar
import contextlib
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sqlite3
import urllib.request
import zipfile

SOURCES = {
    "arxiv": "https://www.kaggle.com/api/v1/datasets/download/Cornell-University/arxiv",
    "acl": "https://aclanthology.org/anthology+abstracts.bib.gz",
}
DEFAULTS = {"arxiv": "cache/arxiv.zip", "acl": "cache/anthology.bib.gz"}


def digest(path):
    with open(path, "rb") as stream:
        h = hashlib.sha256()
        for chunk in iter(lambda: stream.read(2**20), b""):
            h.update(chunk)
        return h.hexdigest()


def refresh(source, path):
    tmp = path.with_suffix(".partial")
    with urllib.request.urlopen(SOURCES[source], timeout=180) as response, tmp.open(
        "wb"
    ) as out:
        shutil.copyfileobj(response, out)
    tmp.replace(path)


@contextlib.contextmanager
def stream(path):
    with contextlib.ExitStack() as stack:
        if zipfile.is_zipfile(path):
            archive = stack.enter_context(zipfile.ZipFile(path))
            (member,) = [
                p
                for p in archive.namelist()
                if p.endswith("arxiv-metadata-oai-snapshot.json")
            ]
            raw = stack.enter_context(archive.open(member))
        else:
            with open(path, "rb") as sniff:
                compressed = sniff.read(2) == b"\x1f\x8b"
            raw = stack.enter_context(
                gzip.open(path, "rb") if compressed else open(path, "rb")
            )
        yield stack.enter_context(io.TextIOWrapper(raw, encoding="utf-8"))


def compact(s):
    return " ".join((s or "").split())


def arxiv_rows(src):
    for line in src:
        p = json.loads(line)
        ident = p["id"]
        if not re.match(r"^\d{4}\.", ident):
            continue
        month = "20" + ident[:2] + "-" + ident[2:4]
        yield (
            ident,
            month,
            compact(p["title"]),
            compact(p["abstract"]),
            p["authors"],
            (p.get("doi") or "").lower(),
            p["categories"],
            "https://arxiv.org/abs/" + ident,
        )


FIELD = re.compile(
    r"^    ([\w-]+) = (.*?)(?=,?\n    [\w-]+ = |,?\n\}\s*$)", re.M | re.S
)


def acl_entry(block):
    if not block.startswith(("@inproceedings{", "@article{")):
        return
    p = {k: compact(v.strip().strip('"')) for k, v in FIELD.findall(block)}
    if not p.get("url") or not p.get("year"):
        return
    month = p.get("month", "").lower()
    named = re.search(r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec", month)
    if named:
        m = [x.lower() for x in calendar.month_abbr].index(named[0])
    elif month.isdigit() and 1 <= int(month) <= 12:
        m = int(month)
    else:
        m = 0
    url = p["url"]
    tidy = lambda s: s.replace("{", "").replace("}", "").replace("~", " ")
    return (
        url.rstrip("/").split("/")[-1],
        f"{p['year']}-{m:02}",
        tidy(p["title"]),
        tidy(p.get("abstract", "")),
        tidy(p.get("author", "")),
        p.get("doi", "").lower(),
        tidy(p.get("booktitle", p.get("journal", ""))),
        url,
    )


def acl_rows(src):
    block = []
    for line in src:
        if line.startswith("@") and block:
            row = acl_entry("".join(block))
            if row:
                yield row
            block = []
        block.append(line)
    row = acl_entry("".join(block))
    if row:
        yield row


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", choices=SOURCES)
    ap.add_argument("--input", type=Path)
    ap.add_argument(
        "--refresh", action="store_true", help="explicitly download latest snapshot"
    )
    ap.add_argument("--start", default="2021-11")
    ap.add_argument("--end", default="2026-10")
    ap.add_argument("--db", type=Path, default=Path("cache/catalog.sqlite"))
    args = ap.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    path = args.input or Path(DEFAULTS[args.source])
    if args.refresh:
        path.parent.mkdir(parents=True, exist_ok=True)
        refresh(args.source, path)
    fingerprint = digest(path)
    with sqlite3.connect(args.db) as db:
        db.executescript(
            """
        CREATE TABLE IF NOT EXISTS papers(source TEXT, id TEXT, month TEXT, title TEXT, abstract TEXT,
                authors TEXT, doi TEXT, venue TEXT, url TEXT, UNIQUE(source,id));
        CREATE VIRTUAL TABLE IF NOT EXISTS ft USING fts5(title,abstract,content='papers',content_rowid='rowid');
        CREATE TRIGGER IF NOT EXISTS added AFTER INSERT ON papers BEGIN
            INSERT INTO ft(rowid,title,abstract) VALUES(new.rowid,new.title,new.abstract);
        END;
        CREATE TRIGGER IF NOT EXISTS removed AFTER DELETE ON papers BEGIN
            INSERT INTO ft(ft,rowid,title,abstract) VALUES('delete',old.rowid,old.title,old.abstract);
        END;
        CREATE TABLE IF NOT EXISTS sources(source TEXT PRIMARY KEY, sha TEXT, start TEXT, end TEXT, count INTEGER, url TEXT);
        """
        )
        prior = db.execute(
            "SELECT sha,start,end FROM sources WHERE source=?", (args.source,)
        ).fetchone()
        if prior == (fingerprint, args.start, args.end):
            print("Already indexed", args.source)
            return
        db.execute("DELETE FROM papers WHERE source=?", (args.source,))
        with stream(path) as src:
            rows = (arxiv_rows if args.source == "arxiv" else acl_rows)(src)
            db.executemany(
                "INSERT INTO papers VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    (args.source, *r)
                    for r in rows
                    if args.start <= r[1] <= args.end
                    and not (
                        r[1].endswith("-00")
                        and r[1][:4] in (args.start[:4], args.end[:4])
                    )
                ),
            )
        n = db.execute(
            "SELECT count(*) FROM papers WHERE source=?", (args.source,)
        ).fetchone()[0]
        if not n:
            raise ValueError("No records in the window")
        db.execute(
            "INSERT OR REPLACE INTO sources VALUES(?,?,?,?,?,?)",
            (args.source, fingerprint, args.start, args.end, n, SOURCES[args.source]),
        )
        print(args.source, n, fingerprint)


if __name__ == "__main__":
    main()
