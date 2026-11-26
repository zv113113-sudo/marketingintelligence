#!/usr/bin/env python3
"""Run the bot and send accepted signals to Telegram."""
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
raise SystemExit(subprocess.call([sys.executable,str(root/"run.py")],cwd=root))
