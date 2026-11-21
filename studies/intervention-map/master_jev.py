"""Collect ten paper-level Jev scores on public metadata with a resumable local cache."""

import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

import aiohttp
from jev_check import QUESTIONS
from master_records import ROOT, master_records, rows

MODEL = "jev-1.14.0"
ITEMS = {
    **QUESTIONS,
    "alignment_relevance": "Does this paper substantively study whether an AI system's behavior meets human intentions, preferences, norms, safety requirements or authorization rules? Exclude generic predictive accuracy and mere feature, image, text or geometric alignment.",
    "evaluation": "Does the paper make a substantive contribution to measuring, benchmarking, auditing or evaluating the behavior or performance of AI systems? Experiments used only to demonstrate another method are insufficient.",
    "theory": "Does the paper contribute a formal analysis, theorem, proof, bound or explicitly mathematical characterization of a learning, decision or control problem? Writing down a training loss alone is insufficient.",
    "data_resources": "Does the paper introduce or substantively study a dataset, data collection, annotation or curation method as a research contribution? Merely consuming an existing dataset is insufficient.",
    "governance": "Does the paper substantively analyze institutional governance, policy, accountability, societal impacts or normative frameworks concerning AI systems? A passing mention of ethical implications is insufficient.",
}
QUESTIONS_TYPED = {k: {"type": "noul", "instructions": v} for k, v in ITEMS.items()}


def payload(title, abstract):
    return json.dumps(
        {
            "model": MODEL,
            "state": {"title": title, "abstract": abstract},
            "questions": QUESTIONS_TYPED,
        },
        sort_keys=True,
    ).encode()


class Limiter:
    def __init__(self, rps):
        self.interval = 1 / rps
        self.next_time = 0
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            delay = max(0, self.next_time - time.monotonic())
            if delay:
                await asyncio.sleep(delay)
            self.next_time = time.monotonic() + self.interval


async def fetch(session, limiter, body):
    for attempt in range(6):
        await limiter.acquire()
        try:
            async with session.post(
                "https://api.typesafe.ai/v1/systemone", data=body
            ) as reply:
                if reply.status in (429, 500, 502, 503, 504):
                    wait = reply.headers.get("Retry-After", "")
                    if attempt == 5:
                        raise RuntimeError(
                            f"TypeSafe HTTP {reply.status} after retries"
                        )
                    await asyncio.sleep(
                        max(float(wait) if wait.isdigit() else 0, 2**attempt)
                    )
                    continue
                if reply.status != 200:
                    raise RuntimeError(
                        f"TypeSafe HTTP {reply.status}: {str(await reply.text())[:200]}"
                    )
                result = await reply.json()
                if result["model"] != MODEL:
                    raise ValueError("Unexpected returned model version")
                values = {k: float(result["answers"][k]["noul"]) for k in ITEMS}
                if not all(0 <= v <= 1 for v in values.values()):
                    raise ValueError("Invalid score")
                return result["model"], values, result["usage"]
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
            if attempt == 5:
                raise
            await asyncio.sleep(2**attempt)


async def run(args):
    records, roles = master_records()
    db = sqlite3.connect(args.cache)
    db.execute(
        "CREATE TABLE IF NOT EXISTS measurements (paper_id TEXT, request_sha TEXT, model TEXT, scores TEXT, usage TEXT, PRIMARY KEY(paper_id,request_sha))"
    )
    released = ROOT / "results/paper_master.csv.gz"
    if released.exists():
        for row in rows(released):
            if row["jev_model"] != MODEL:
                continue
            pid = row["paper_id"]
            if pid not in records:
                continue
            signature = hashlib.sha256(payload(*records[pid])).hexdigest()
            if signature != row["jev_request_sha256"]:
                continue
            scores = {key: float(row["jev_" + key]) for key in ITEMS}
            usage = {k: int(row["jev_" + k]) for k in ("input_tokens", "output_tokens")}
            db.execute(
                "INSERT OR IGNORE INTO measurements VALUES (?,?,?,?,?)",
                (pid, signature, MODEL, json.dumps(scores), json.dumps(usage)),
            )
        db.commit()
    done = set(db.execute("SELECT paper_id, request_sha FROM measurements"))
    pending = []
    for pid in sorted(
        records, key=lambda p: ("alignment_shortlist" not in roles[p], p)
    ):
        body = payload(*records[pid])
        signature = hashlib.sha256(body).hexdigest()
        if (pid, signature) not in done:
            pending.append((pid, signature, body))
    print(
        f"{len(records)} unique works; {len(pending)} unscored; {args.limit if args.limit is not None else 'all'} request limit",
        flush=True,
    )
    if not pending or args.limit == 0:
        db.close()
        return
    pending = iter(pending if args.limit is None else pending[: args.limit])
    limiter = Limiter(args.rps)
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + os.environ["TYPESAFE_API_KEY"],
    }
    async with aiohttp.ClientSession(
        headers=headers,
        trust_env=True,
        timeout=aiohttp.ClientTimeout(total=45),
        connector=aiohttp.TCPConnector(limit=args.workers),
    ) as session:
        count = 0

        async def worker():
            nonlocal count
            for pid, signature, body in pending:
                model, scores, usage = await fetch(session, limiter, body)
                db.execute(
                    "INSERT INTO measurements VALUES (?,?,?,?,?)",
                    (pid, signature, model, json.dumps(scores), json.dumps(usage)),
                )
                db.commit()
                count += 1
                if count % 500 == 0:
                    print(f"{count} new measurements persisted", flush=True)

        await asyncio.gather(*(worker() for _ in range(args.workers)))
    db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", required=True, type=Path)
    p.add_argument(
        "--limit",
        type=int,
        help="Maximum number of new billable papers. Omit to score all missing rows.",
    )
    p.add_argument("--workers", type=int, default=72)
    p.add_argument("--rps", type=int, default=48)
    args = p.parse_args()
    if args.workers < 1 or args.rps < 1 or (args.limit is not None and args.limit < 0):
        p.error("Invalid collection limits")
    asyncio.run(run(args))
