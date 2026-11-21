"""Optional, resumable Jev cross-check on public paper metadata only."""

import argparse
import csv
import hashlib
import json
import os
import gzip
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from pathlib import Path
import urllib.request

from semantic_map import ROOT, records

QUESTIONS = {
    "weights": "Does a substantive contribution train, update or study changing the parameters of the principal predictor or acting policy?",
    "supervision": "Does a substantive contribution govern an AI system's outputs or actions using a separate monitor, verifier, approval step or enforced constraint?",
    "scaffolding": "Does the paper develop or study an external execution system coordinating models, tools, memory, verifiers, or people as the task runs? Include historical equivalents without requiring any particular term. Exclude training alone, passing mentions and benchmark setups without a substantive execution method.",
    "feedback": "Is the subsequent action or intervention adjusted using observations of the system, performance error, or sensed state as a substantive mechanism? A one-time check and ordinary model fitting alone are insufficient.",
    "dynamics": "Does the paper substantively reason about controlled state evolution, equilibria, stability, observability, or trajectories through a dynamical system? Mere use of 'dynamic' or references in background are insufficient.",
}


def evaluate(item, model):
    pid, title, abstract = item
    questions = {k: {"type": "noul", "instructions": v} for k, v in QUESTIONS.items()}
    payload = json.dumps(
        {
            "model": model,
            "state": {"title": title, "abstract": abstract},
            "questions": questions,
        },
        sort_keys=True,
    ).encode()
    signature = hashlib.sha256(payload).hexdigest()
    return pid, signature, payload


def fetch(item):
    pid, signature, payload = item
    req = urllib.request.Request(
        "https://api.typesafe.ai/v1/systemone",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + os.environ["TYPESAFE_API_KEY"],
        },
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                result = json.load(response)
            break
        except (HTTPError, URLError, TimeoutError) as err:
            if (
                isinstance(err, HTTPError) and err.code not in (429, 500, 502, 503, 504)
            ) or attempt == 3:
                raise
            time.sleep(3 * 2**attempt)
    values = {k: float(result["answers"][k]["noul"]) for k in QUESTIONS}
    if not all(0 <= v <= 1 for v in values.values()):
        raise ValueError("Invalid probability")
    return {
        "paper_id": pid,
        "request_sha256": signature,
        "requested_model": json.loads(payload)["model"],
        "model": result["model"],
        "scores": values,
        "usage": result.get("usage"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum new requests, billable through TypeSafe",
    )
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=1)
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument(
        "--sample", choices=["control", "mechanisms"], default="control"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("Set TYPESAFE_API_KEY in the calling environment.")
    output = args.output or ROOT / "results" / (
        "jev_checks.jsonl" if args.sample == "control" else "jev_mechanisms.jsonl"
    )
    if args.sample == "control":
        with gzip.open(ROOT / "data/control_sample.csv.gz", "rt") as f:
            papers = {
                r["paper_id"]: (r["title"], r["abstract"]) for r in csv.DictReader(f)
            }
        with (ROOT / "data/control_validation.csv").open() as f:
            ids = {r["paper_id"] for r in csv.DictReader(f)}
    else:
        from attention import paper_tables

        alignment, general = paper_tables()
        ids = set(alignment.loc[alignment.core, "paper_id"]) | set(general.paper_id)
        papers = records()
    existing = (
        [json.loads(line) for line in output.read_text().splitlines()]
        if output.exists()
        else []
    )
    done = {(r["paper_id"], r["request_sha256"]) for r in existing}
    ids = sorted(ids, key=lambda i: hashlib.sha256(i.encode()).digest())
    items = [evaluate((pid, *papers[pid]), args.model) for pid in ids]
    pending = [item for item in items if item[:2] not in done][: max(0, args.limit)]
    with ThreadPoolExecutor(args.workers) as pool, output.open("a") as f:
        for row in pool.map(fetch, pending):
            print(json.dumps(row), file=f, flush=True)


if __name__ == "__main__":
    main()
