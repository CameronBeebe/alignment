"""Run the paired abstract / complete PDF audit. Cached successful calls are reusable."""

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from fulltext_questions import QUESTIONS, RULE
from fulltext_sources import cohort, digest, local_name
from master_jev import MODEL
from semantic_map import records

QWEN = "qwen/qwen3-30b-a3b-instruct-2507"
PRIMARY = ("weights", "supervision", "scaffolding")
SERVICES = {
    "jev": ("https://api.typesafe.ai/v1/systemone", "TYPESAFE_API_KEY"),
    "qwen": ("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"),
}


def payload(reviewer, title, basis, content):
    state = {"title": title, basis: content}
    if reviewer == "jev":
        return {
            "model": MODEL,
            "state": {**state, "coding_rule": RULE},
            "questions": {
                k: {"type": "noul", "instructions": v} for k, v in QUESTIONS.items()
            },
        }
    rubric = {k: QUESTIONS[k] for k in PRIMARY}
    instruction = (
        RULE
        + " Answer each independent question with a JSON boolean. Return only a JSON object with exactly the question keys. Questions: "
        + json.dumps(rubric)
    )
    return {
        "model": QWEN,
        "temperature": 0,
        "max_tokens": 175,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps(state, ensure_ascii=False)},
        ],
    }


def rate(task, cache):
    pid, title, basis, content, reviewer = task
    query = payload(reviewer, title, basis, content)
    body = json.dumps(query, sort_keys=True, ensure_ascii=False).encode()
    signature = digest(body)
    file = cache / f"{local_name(pid)}.{reviewer}.{basis}.{signature}.json"
    if file.exists():
        return
    url, envname = SERVICES[reviewer]
    headers = {
        "Authorization": "Bearer " + os.environ[envname],
        "Content-Type": "application/json",
    }
    for attempt in range(6):
        try:
            r = requests.post(url, headers=headers, data=body, timeout=(12, 180))
            if (
                r.status_code in (400, 413, 422)
                and reviewer == "jev"
                and "TypeSafe-Danger-Zone-Long-Context" not in headers
                and any(
                    word in r.text.lower() for word in ["context", "token", "length"]
                )
            ):
                headers["TypeSafe-Danger-Zone-Long-Context"] = "true"
                continue
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 5:
                delay = r.headers.get("Retry-After", "")
                time.sleep(max(2**attempt, float(delay) if delay.isdigit() else 0))
                continue
            if not r.ok:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:320]}")
            reply = r.json()
            if reply.get("model") != query["model"]:
                raise ValueError(
                    "Provider returned unexpected model: " + str(reply.get("model"))
                )
            if reviewer == "jev":
                scores = {k: float(v["noul"]) for k, v in reply["answers"].items()}
                if set(scores) != set(QUESTIONS) or not all(
                    0 <= v <= 1 for v in scores.values()
                ):
                    raise ValueError("Invalid score set")
            else:
                choice = reply["choices"][0]
                if choice["finish_reason"] != "stop":
                    raise ValueError("Incomplete Qwen response")
                scores = json.loads(choice["message"]["content"])
                if set(scores) != set(PRIMARY) or not all(
                    type(v) is bool for v in scores.values()
                ):
                    raise ValueError("Invalid Qwen labels")
            record = dict(
                paper_id=pid,
                reviewer=reviewer,
                basis=basis,
                model=reply["model"],
                provider=reply.get("provider"),
                long_context="TypeSafe-Danger-Zone-Long-Context" in headers,
                request_sha256=signature,
                content_sha256=digest(content.encode()),
                scores=scores,
                usage=reply.get("usage"),
            )
            temp = file.with_suffix(".tmp")
            temp.write_text(json.dumps(record, sort_keys=True) + "\n")
            temp.replace(file)
            return
        except (requests.ConnectionError, requests.Timeout, ValueError) as exc:
            if attempt == 5:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("No complete response")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("sources", type=Path)
    p.add_argument("cache", type=Path)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--basis", choices=["abstract", "paper", "both"], default="both")
    p.add_argument("--reviewer", choices=["jev", "qwen", "both"], default="both")
    p.add_argument("--limit", type=int)
    p.add_argument(
        "--cohort", choices=["headline", "language-comparators"], default="headline"
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Count paper IDs without collecting ratings or contacting either provider",
    )
    args = p.parse_args()
    selected = cohort(args.cohort)
    if args.limit is not None:
        if args.limit < 0:
            p.error("--limit must be nonnegative")
        selected = selected.head(args.limit)
    if args.dry_run:
        print(f"{len(selected)} selected IDs, cohort {args.cohort}.")
        return
    args.cache.mkdir(parents=True, exist_ok=True)
    papers = records()
    tasks = []
    for row in selected.itertuples():
        pid = row.paper_id
        title, abstract = papers[pid]
        inputs = {"abstract": abstract}
        meta = args.sources / (local_name(pid) + ".json")
        if meta.exists():
            source = json.loads(meta.read_text())
            if source.get("text_sha256"):
                content = meta.with_suffix(".txt").read_bytes()
                if digest(content) != source["text_sha256"]:
                    raise ValueError("Source digest mismatch")
                inputs["paper"] = content.decode()
        for basis, content in inputs.items():
            if args.basis not in ("both", basis):
                continue
            for reviewer in SERVICES:
                if args.reviewer in ("both", reviewer):
                    tasks.append((pid, title, basis, content, reviewer))
    with ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(rate, task, args.cache): task for task in tasks}
        failures = 0
        for f in as_completed(futures):
            pid, _, basis, _, reviewer = futures[f]
            try:
                f.result()
            except Exception as e:
                failures += 1
                print(pid, basis, reviewer, str(e)[:400], flush=True)
    print(f"{len(tasks)-failures}/{len(tasks)} requested ratings available", flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
