"""Staged read-only audit of collection, filters, and GigaChat scoring."""
from __future__ import annotations

import concurrent.futures
import csv
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib import request

import run

ROOT = Path(run.ROOT)
OUT = ROOT / "outputs"
STATE = ROOT / "state"
OUT.mkdir(exist_ok=True)
STATE.mkdir(exist_ok=True)
CFG = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
SOURCES = [dict(s) for s in CFG["sources"] if s.get("enabled", True)]

# Five latest cards per source is a bounded, comparable diagnostic sample.
for source in SOURCES:
    source["max_items"] = min(int(source.get("max_items", 15)), 5)

def fast_text(url):
    req = request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with request.urlopen(req, timeout=12, context=run.ctx()) as response:
        return response.read().decode(response.headers.get_content_charset() or "utf-8", "replace")

run.text = fast_text
CSV_PATH = OUT / "source_pipeline_audit_latest.csv"
JSON_PATH = OUT / "source_pipeline_audit_latest.json"
CANDIDATES_PATH = STATE / "source_pipeline_candidates_latest.json"
SCORES_PATH = STATE / "source_pipeline_scores_latest.json"
COLLECTION_CHECKPOINT = STATE / "source_pipeline_collection_checkpoint.json"

def dump_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def save_csv(rows):
    if not rows:
        return
    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def collect_stage():
    print(f"Collecting up to 5 recent items from {len(SOURCES)} enabled sources...", flush=True)
    try:
        checkpoint = json.loads(COLLECTION_CHECKPOINT.read_text(encoding="utf-8"))
    except Exception:
        checkpoint = {"collected": {}, "errors": {}}
    collected, errors = checkpoint.get("collected", {}), checkpoint.get("errors", {})
    pending = [s for s in SOURCES if s["name"] not in collected]
    print(f"Resuming {len(collected)} completed sources; {len(pending)} remain.", flush=True)
    def one(source):
        try:
            return source, run.collect(source), ""
        except Exception as exc:
            return source, [], f"{type(exc).__name__}: {str(exc)[:240]}"
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(one, s) for s in pending]
        for future in concurrent.futures.as_completed(futures):
            source, items, error = future.result()
            name = source["name"]
            if error:
                errors[name] = error
            else:
                collected[name] = items
                errors.pop(name, None)
            dump_json(COLLECTION_CHECKPOINT, {"collected": collected, "errors": errors})
            # Checkpoint each source so an interrupted collection still has a usable table.
            print(f"COLLECT {name}: {len(items)}" + (f" ERROR {error}" if error else ""), flush=True)

    all_items = [a for source in SOURCES for a in collected.get(source["name"], [])]
    gate_items, rejected = [], []
    for item in all_items:
        track, reason = run.classify_topic(item)
        if track:
            item["topic_track"] = track
            gate_items.append(item)
        else:
            rejected.append({"source": item.get("source", ""), "title": item.get("title", ""), "reason": reason})
    unique = run.dedupe_events(gate_items)
    seen = run.load_seen()
    fresh = [a for a in unique if run.item_key(a) not in seen]
    groups = {}
    for item in fresh:
        groups.setdefault(item["source"], []).append(item)
    pool = run.balanced(groups, 60)

    stages = {s["name"]: {k: set() for k in ("topic", "unique", "fresh", "pool")} for s in SOURCES}
    for item in gate_items: stages[item["source"]]["topic"].add(run.item_key(item))
    for item in unique: stages[item["source"]]["unique"].add(run.item_key(item))
    for item in fresh: stages[item["source"]]["fresh"].add(run.item_key(item))
    for item in pool: stages[item["source"]]["pool"].add(run.item_key(item))
    rows = []
    for source in SOURCES:
        name = source["name"]
        stage = stages[name]
        items = collected.get(name, [])
        rows.append({
            "source": name, "region": source.get("region", ""), "kind": source.get("kind", ""),
            "collected": len(items), "full_text_ge_250_chars": sum(len(a.get("text", "")) >= 250 for a in items),
            "passed_topic_filter": len(stage["topic"]), "unique_after_dedupe": len(stage["unique"]),
            "new_not_seen": len(stage["fresh"]), "selected_for_gigachat": len(stage["pool"]),
            "collection_error": errors.get(name, ""), "scored_by_gigachat": 0, "passed_ai_editorial": 0,
        })
    save_csv(rows)
    report = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sample_cap_per_source": 5, "enabled_sources": len(SOURCES), "items_collected": len(all_items),
        "passed_topic_filter": len(gate_items), "rejected_by_topic_filter": len(rejected),
        "unique_after_dedupe": len(unique), "new_not_seen": len(fresh),
        "selected_for_gigachat": len(pool), "candidate_pool_limit": 60,
        "sources_with_items": sum(bool(collected.get(s["name"])) for s in SOURCES),
        "sources_with_collection_errors": len(errors), "gate_rejected_sample": rejected,
        "sources": rows,
    }
    dump_json(JSON_PATH, report)
    dump_json(CANDIDATES_PATH, {"created_at": report["created_at"], "candidates": pool})
    COLLECTION_CHECKPOINT.unlink(missing_ok=True)
    # A fresh collection starts a fresh score checkpoint, without touching bot state.
    if SCORES_PATH.exists(): SCORES_PATH.unlink()
    print(f"REPORT_CSV {CSV_PATH}", flush=True)
    print(f"REPORT_JSON {JSON_PATH}", flush=True)
    print(f"SUMMARY collected={len(all_items)} topic_pass={len(gate_items)} unique={len(unique)} fresh={len(fresh)} scoring_pool={len(pool)}", flush=True)

def score_stage(limit):
    if not CANDIDATES_PATH.exists():
        raise SystemExit("Сначала выполните этап collect, он создаст выборку и CSV.")
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))["candidates"]
    limit = max(1, min(int(limit), len(candidates)))
    done = json.loads(SCORES_PATH.read_text(encoding="utf-8")) if SCORES_PATH.exists() else {}
    todo = [a for a in candidates[:limit] if run.item_key(a) not in done]
    print(f"Scoring {len(todo)} remaining items (cap {limit}); previously completed scores are reused.", flush=True)
    token = run.token()
    for index, item in enumerate(todo, 1):
        key = run.item_key(item)
        try:
            result = run.score(token, item)
            editorial = run.editorial_score({**item, **result})
            passed = bool(run.passes_editorial(result) and float(editorial) >= run.EDITORIAL_MIN)
            done[key] = {"source": item["source"], "title": item.get("title", ""), "score": result.get("score", 0),
                         "editorial_score": editorial, "passed_ai_editorial": passed, "error": ""}
            print(f"SCORE {index}/{len(todo)} {item['source']} AI={result.get('score',0)} editorial={editorial} pass={passed}", flush=True)
        except Exception as exc:
            done[key] = {"source": item["source"], "title": item.get("title", ""), "score": 0,
                         "editorial_score": 0, "passed_ai_editorial": False,
                         "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
            print(f"SCORE_ERROR {item['source']}: {done[key]['error']}", flush=True)
        dump_json(SCORES_PATH, done)  # checkpoint after every model call
        time.sleep(1.2)

    rows = json.loads(JSON_PATH.read_text(encoding="utf-8"))["sources"]
    by_source = Counter(x["source"] for x in done.values())
    passed_by_source = Counter(x["source"] for x in done.values() if x.get("passed_ai_editorial"))
    for row in rows:
        row["scored_by_gigachat"] = by_source[row["source"]]
        row["passed_ai_editorial"] = passed_by_source[row["source"]]
    save_csv(rows)
    report = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    report["sources"] = rows
    report["scoring_limit"] = limit
    report["scored_by_gigachat"] = len(done)
    report["passed_ai_editorial"] = sum(x.get("passed_ai_editorial", False) for x in done.values())
    dump_json(JSON_PATH, report)
    print(f"REPORT_CSV {CSV_PATH}", flush=True)
    print(f"SUMMARY scored={len(done)} passed_ai={report['passed_ai_editorial']}", flush=True)

if len(sys.argv) < 2 or sys.argv[1] not in {"collect", "score"}:
    raise SystemExit("Usage: python audit_pipeline.py collect | python audit_pipeline.py score 20")
if sys.argv[1] == "collect": collect_stage()
else: score_stage(sys.argv[2] if len(sys.argv) > 2 else 20)
