#!/usr/bin/env python3
"""Back up v1.4 history before v1.5 starts building a clean editorial history."""
from datetime import datetime
from pathlib import Path

root=Path(__file__).resolve().parent
state=root/"state"
stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
for name in ("history.json","report_state.json"):
 src=state/name
 if src.exists():
  dst=state/f"{src.stem}_v14_backup_{stamp}{src.suffix}"
  src.replace(dst)
  print(f"backup: {src.name} -> {dst.name}")
print("v1.5 history is ready; seen.json was not changed")
