"""Identify substantive language-model research in the frozen corpus."""

import argparse
import asyncio
import csv
import gzip
import hashlib
import io
import json
import re
import sqlite3
from pathlib import Path

from master_jev import MODEL, payload, run
from master_records import ROOT, master_records

ITEMS = {
    "language_model_focus": (
        "Does the paper substantively study, train, evaluate, or develop a method or system around a large language model or a Transformer-based language model? "
        "Include named systems such as GPT or BERT, language-oriented foundation models, and multimodal or agent systems where such a language model plays a material role. "
        "Exclude incidental mentions, background comparisons, a generic agent without evidence of a language model, and applications of a Transformer only to non-language signals or vision. "
        "Classify the paper's research focus from the title and abstract; proprietary architectural details need not be reported."
    )
}
FILE = ROOT / "results/language_model_scores.csv.gz"
LITERAL = re.compile(r"\b(?:llms?|large[-\s]+language[-\s]+models?)\b", re.I)
FAMILY = re.compile(
    r"\b(?:chatgpt|(?:instruct)?gpt(?:[- .]?(?:[2345](?:\.\d+)?[a-z]*|neo[x]?|j))?|llama(?:[- ]?\d+(?:\.\d+)?)?|claude(?:[- ]?\d+)?|gemini(?:[- ]?\d+(?:\.\d+)?)?|deepseek(?:[- ]?[rv]\d+)?|qwen\w*|bert|roberta|deberta|flan[- ]?t5|t5)\b",
    re.I,
)


def freeze(cache):
    records, _ = master_records()
    db = sqlite3.connect(cache.resolve().as_uri() + "?mode=ro", uri=True)
    typed = {k: {"type": "noul", "instructions": v} for k, v in ITEMS.items()}
    temp = FILE.with_suffix(".tmp")
    fields = [
        "paper_id",
        "jev_model",
        "jev_request_sha256",
        "jev_language_model_focus",
        "literal_llm",
        "family_mention",
        "jev_input_tokens",
        "jev_output_tokens",
    ]
    try:
        with temp.open("wb") as raw, gzip.GzipFile(
            filename="", fileobj=raw, mode="wb", mtime=0
        ) as gz, io.TextIOWrapper(gz, encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(fields)
            for pid, text in records.items():
                sig = hashlib.sha256(payload(*text, typed)).hexdigest()
                row = db.execute(
                    "SELECT model,scores,usage FROM measurements WHERE paper_id=? AND request_sha=?",
                    (pid, sig),
                ).fetchone()
                if not row or row[0] != MODEL:
                    raise ValueError(f"No matching score for {pid}")
                score = json.loads(row[1])["language_model_focus"]
                usage = json.loads(row[2])
                title_abstract = " ".join(text)
                if not 0 <= score <= 1:
                    raise ValueError(f"Invalid score for {pid}")
                writer.writerow(
                    [
                        pid,
                        MODEL,
                        sig,
                        score,
                        int(bool(LITERAL.search(title_abstract))),
                        int(bool(FAMILY.search(title_abstract))),
                        usage["input_tokens"],
                        usage["output_tokens"],
                    ]
                )
        temp.replace(FILE)
    finally:
        db.close()
        temp.unlink(missing_ok=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum new API requests. Use 0 to restore released scores offline.",
    )
    p.add_argument("--workers", type=int, default=72)
    p.add_argument("--rps", type=int, default=48)
    p.add_argument("--freeze", action="store_true")
    args = p.parse_args()
    if min(args.workers, args.rps) < 1 or args.limit < 0:
        p.error("Invalid collection limits")
    asyncio.run(run(args, ITEMS, FILE))
    if args.freeze:
        freeze(args.cache)
