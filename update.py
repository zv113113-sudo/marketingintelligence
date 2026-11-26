#!/usr/bin/env python3
"""Safely install the newest marketing_intel_v*.zip from this directory."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import py_compile
import shutil
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent
PROTECTED={".env"}
PROTECTED_DIRS={"state","backups"}

def newest_archive():
 archives=sorted(ROOT.glob("marketing_intel_v*.zip"),key=lambda p:p.stat().st_mtime,reverse=True)
 if not archives:raise RuntimeError("архив marketing_intel_v*.zip не найден")
 return archives[0]

def safe_members(z):
 members=[]
 for info in z.infolist():
  name=info.filename.replace("\\","/")
  path=Path(name)
  if path.is_absolute() or ".." in path.parts:
   raise RuntimeError(f"небезопасный путь в архиве: {name}")
  if not name or name.endswith("/"):continue
  if path.name in PROTECTED or (path.parts and path.parts[0] in PROTECTED_DIRS):continue
  members.append((info,path))
 return members

def validate(stage):
 run=stage/"run.py";sources=stage/"config"/"sources.json"
 if not run.exists() or not sources.exists():
  raise RuntimeError("в архиве нет run.py или config/sources.json")
 py_compile.compile(str(run),doraise=True)
 data=json.loads(sources.read_text(encoding="utf-8"))
 if not isinstance(data.get("sources"),list) or not data["sources"]:
  raise RuntimeError("некорректный список источников")

def main():
 archive=newest_archive()
 stage=Path(tempfile.mkdtemp(prefix=".update_",dir=ROOT))
 stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
 backup=ROOT/"backups"/stamp
 installed=[];created=[]
 try:
  with zipfile.ZipFile(archive) as z:
   members=safe_members(z)
   z.extractall(stage,[info for info,_ in members])
  validate(stage)
  backup.mkdir(parents=True,exist_ok=False)
  for _,rel in members:
   src=stage/rel;dst=ROOT/rel
   if dst.exists():
    old=backup/rel;old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,old)
   else:created.append(dst)
   dst.parent.mkdir(parents=True,exist_ok=True)
   pending=dst.with_name(dst.name+".new")
   shutil.copy2(src,pending);os.replace(pending,dst);installed.append((dst,rel))
  py_compile.compile(str(ROOT/"run.py"),doraise=True)
  json.loads((ROOT/"config"/"sources.json").read_text(encoding="utf-8"))
  digest=hashlib.sha256(archive.read_bytes()).hexdigest()[:12]
  print(f"UPDATE OK: {archive.name} [{digest}]")
  print(f"BACKUP: {backup}")
 except Exception as error:
  for dst,rel in reversed(installed):
   old=backup/rel
   if old.exists():shutil.copy2(old,dst)
  for dst in created:
   if dst.exists() and dst.is_file():dst.unlink()
  print(f"UPDATE FAILED: {error}")
  print("Рабочая версия восстановлена.")
 finally:
  shutil.rmtree(stage,ignore_errors=True)

if __name__=="__main__":main()
