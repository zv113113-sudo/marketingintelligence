#!/usr/bin/env python3
"""Run the bot without Telegram or state changes."""
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
raise SystemExit(subprocess.call([sys.executable,str(root/"run.py"),"--dry-run"],cwd=root))
