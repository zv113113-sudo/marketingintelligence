#!/usr/bin/env python3
"""Quick collection check for the sources added in v1.6; sends nothing."""
import json
from pathlib import Path
from run import collect

ROOT=Path(__file__).resolve().parent
NEW={
 "AdExchanger","Search Engine Land","Digiday","IPA Effectiveness","Ehrenberg-Bass",
 "System1 Creative Effectiveness","LinkedIn B2B Institute","SparkToro Authors",
 "Growth Unhinged","Tom Roach","Science Says"
}

cfg=json.loads((ROOT/"config"/"sources.json").read_text(encoding="utf-8"))
for source in (s for s in cfg["sources"] if s.get("name") in NEW):
 try:
  rows=collect(source)
  sample=(rows[0].get("title","")[:100] if rows else "нет материалов")
  print(f'✓ {source["name"]}: {len(rows)} | {sample}')
 except Exception as error:
  print(f'✗ {source["name"]}: {error}')
