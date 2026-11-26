#!/usr/bin/env python3
"""Minimal public subscription layer for the Marketing Intelligence bot."""
from pathlib import Path
from urllib import request
import json, time, ssl
import re
from feedback import rating_markup, record_vote

ROOT=Path(__file__).resolve().parent

def env():
 d={}
 for line in (ROOT/".env").read_text(encoding="utf-8").splitlines():
  if line.strip() and not line.lstrip().startswith("#") and "=" in line:
   k,v=line.split("=",1);d[k.strip()]=v.strip()
 return d

E=env(); TOKEN=E["TELEGRAM_BOT_TOKEN"]; OWNER=str(E.get("TELEGRAM_CHAT_ID", ""))
STATE=ROOT/"state"; FILE=STATE/"subscribers.json"; OFFSET=STATE/"telegram_offset.txt"
CTX=ssl._create_unverified_context()

def api(method,payload=None):
 body=None; headers={"User-Agent":"MarketingIntelligenceBot/1.0"}
 if payload is not None:
  body=json.dumps(payload).encode();headers["Content-Type"]="application/json"
 req=request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}",data=body,headers=headers)
 with request.urlopen(req,timeout=40,context=CTX) as r:return json.loads(r.read().decode())

def load():
 try:data=json.loads(FILE.read_text(encoding="utf-8"))
 except Exception:data={"active":[]}
 active=[str(x) for x in data.get("active",[]) if str(x).strip()]
 if OWNER and OWNER not in active:active.insert(0,OWNER)
 return {"active":list(dict.fromkeys(active))}

def save(data):
 STATE.mkdir(exist_ok=True)
 tmp=FILE.with_suffix(".tmp")
 tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
 tmp.replace(FILE)

def offset():
 try:return int(OFFSET.read_text(encoding="utf-8"))
 except Exception:return 0

def save_offset(n):
 STATE.mkdir(exist_ok=True);OFFSET.write_text(str(n),encoding="utf-8")

def reply(chat,text):
 try:api("sendMessage",{"chat_id":chat,"text":text,"disable_web_page_preview":True})
 except Exception as e:print("reply error:",e)

def handle_callback(query):
 callback_id=query.get("id")
 data=query.get("data","")
 match=re.fullmatch(r"mi:(like|dislike):([0-9a-f]{40})",data)
 message=query.get("message") or {}
 chat_id=message.get("chat",{}).get("id")
 message_id=message.get("message_id")
 user_id=(query.get("from") or {}).get("id")
 if not callback_id:return
 if not match or chat_id is None or message_id is None or user_id is None:
  api("answerCallbackQuery",{"callback_query_id":callback_id,"text":"Не удалось определить карточку для оценки.","show_alert":True})
  return
 reaction,item_id=match.groups()
 status=record_vote(item_id,user_id,chat_id,message_id,reaction)
 if status=="not_delivered":
  api("answerCallbackQuery",{"callback_query_id":callback_id,"text":"Эта карточка больше недоступна для оценки.","show_alert":True})
  return
 text={"saved":"Спасибо, оценка сохранена.","updated":"Оценка обновлена.","same":"Эта оценка уже учтена."}[status]
 api("answerCallbackQuery",{"callback_query_id":callback_id,"text":text})
 api("editMessageReplyMarkup",{
  "chat_id":chat_id,
  "message_id":message_id,
  "reply_markup":rating_markup(item_id,selected=reaction),
 })

def main():
 print("subscriber bot: polling")
 while True:
  try:
   data=api("getUpdates",{"offset":offset(),"timeout":25,"allowed_updates":["message","callback_query"]})
   subs=load()
   for update in data.get("result",[]):
    callback=update.get("callback_query")
    if callback:
     handle_callback(callback)
     save_offset(int(update["update_id"])+1)
     continue
    msg=update.get("message") or {};chat=msg.get("chat",{}).get("id")
    text=(msg.get("text") or "").strip().lower()
    if chat is None:continue
    if text.startswith("/start"):
     sid=str(chat)
     if sid not in subs["active"]:subs["active"].append(sid);save(subs)
     reply(chat,"Подписка включена. Новые материалы будут приходить в общей ленте.")
    elif text.startswith("/stop"):
     sid=str(chat)
     if sid != OWNER and sid in subs["active"]:subs["active"].remove(sid);save(subs)
     reply(chat,"Подписка отключена. Чтобы включить снова, отправьте /start.")
    elif text.startswith("/help"):
     reply(chat,"Команды:\n/start — подписаться\n/stop — отписаться\n/help — помощь")
    save_offset(int(update["update_id"])+1)
  except Exception as e:
   print("polling error:",e);time.sleep(5)

if __name__=="__main__":main()
