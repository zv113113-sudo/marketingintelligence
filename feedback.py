"""Persistent per-user ratings for delivered Marketing Intelligence cards."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
ITEMS_FILE = STATE / "feedback_items.json"
VOTES_FILE = STATE / "feedback_votes.json"
MAX_ITEMS = 2000
MAX_VOTES = 20000


def item_key(article):
    base = (article.get("url", "") + "|" + article.get("title", "")).encode(
        "utf-8", "ignore"
    )
    return hashlib.sha1(base).hexdigest()


def _load(path, default):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else default
    except (OSError, ValueError, TypeError):
        return default


def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def _article_metadata(article):
    title = article.get("display_title") or article.get("title", "")
    score = article.get("editorial_score", article.get("score"))
    try:
        score = float(score) if score is not None else None
    except (TypeError, ValueError):
        score = None
    return {
        "title": str(title)[:300],
        "url": str(article.get("url", ""))[:2000],
        "source": str(article.get("source", ""))[:160],
        "region": str(article.get("event_region") or article.get("region", ""))[:40],
        "topic_track": str(article.get("topic_track") or article.get("track", ""))[:80],
        "narrow_topic": str(article.get("narrow_topic", ""))[:100],
        "category": str(article.get("category", ""))[:80],
        "editorial_score": score,
    }


def record_delivery(article, chat_id, message_id, state_dir=None):
    """Register a sent card copy so callbacks can be checked against it."""
    state_dir = Path(state_dir) if state_dir else STATE
    path = state_dir / ITEMS_FILE.name
    data = _load(path, {"version": 1, "items": {}})
    items = data.setdefault("items", {})
    key = item_key(article)
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    record = items.setdefault(key, {"key": key, "deliveries": []})
    record.update(_article_metadata(article))
    record["sent_at"] = now
    delivery = {"chat_id": str(chat_id), "message_id": int(message_id)}
    if delivery not in record["deliveries"]:
        record["deliveries"].append(delivery)
    if len(items) > MAX_ITEMS:
        keep = sorted(
            items.items(), key=lambda pair: pair[1].get("sent_at", "")
        )[-MAX_ITEMS:]
        data["items"] = dict(keep)
    _save(path, data)
    return key


def record_vote(item_id, user_id, chat_id, message_id, reaction, state_dir=None):
    """Save or update one user's vote, accepting only a known delivered copy."""
    if reaction not in ("like", "dislike"):
        raise ValueError("reaction must be like or dislike")
    state_dir = Path(state_dir) if state_dir else STATE
    items = _load(state_dir / ITEMS_FILE.name, {"items": {}}).get("items", {})
    item = items.get(item_id)
    if not item or not any(
        delivery.get("chat_id") == str(chat_id)
        and delivery.get("message_id") == int(message_id)
        for delivery in item.get("deliveries", [])
    ):
        return "not_delivered"

    path = state_dir / VOTES_FILE.name
    data = _load(path, {"version": 1, "votes": []})
    votes = data.setdefault("votes", [])
    user_id = str(user_id)
    existing = next(
        (
            vote
            for vote in votes
            if vote.get("item_key") == item_id and vote.get("user_id") == user_id
        ),
        None,
    )
    if existing and existing.get("reaction") == reaction:
        return "same"

    status = "updated" if existing else "saved"
    vote = {
        "item_key": item_id,
        "user_id": user_id,
        "chat_id": str(chat_id),
        "reaction": reaction,
        "rated_at": datetime.now(timezone.utc).astimezone().isoformat(
            timespec="seconds"
        ),
        **{key: value for key, value in item.items() if key not in ("deliveries",)},
    }
    if existing:
        existing.clear()
        existing.update(vote)
    else:
        votes.append(vote)
    data["votes"] = sorted(votes, key=lambda value: value.get("rated_at", ""))[
        -MAX_VOTES:
    ]
    _save(path, data)
    return status


def load_votes(state_dir=None):
    state_dir = Path(state_dir) if state_dir else STATE
    votes = _load(state_dir / VOTES_FILE.name, {"votes": []}).get("votes", [])
    return votes if isinstance(votes, list) else []


def personalization_delta(article, votes, min_votes=5, max_effect=0.5):
    """Return a small bounded local ranking adjustment from prior reactions."""
    usable = [
        vote
        for vote in votes
        if vote.get("reaction") in ("like", "dislike")
    ]
    if len(usable) < min_votes:
        return 0.0

    weights = (
        ("narrow_topic", 0.30),
        ("topic_track", 0.20),
        ("region", 0.20),
        ("source_class", 0.15),
        ("source", 0.15),
    )
    signed_similarity = []
    for vote in usable:
        similarity = sum(
            weight
            for key, weight in weights
            if article.get(key)
            and vote.get(key)
            and article.get(key) == vote.get(key)
        )
        direction = 1 if vote["reaction"] == "like" else -1
        signed_similarity.append(direction * similarity)

    confidence = min(1.0, len(usable) / 12.0)
    average = sum(signed_similarity) / len(signed_similarity)
    adjustment = max_effect * average * confidence
    return round(max(-max_effect, min(max_effect, adjustment)), 2)


def rating_markup(item_id, selected=None):
    return {
        "inline_keyboard": [
            [
                {
                    "text": f"{'✅ ' if selected == 'like' else ''}👍 Нравится",
                    "callback_data": f"mi:like:{item_id}",
                },
                {
                    "text": f"{'✅ ' if selected == 'dislike' else ''}👎 Не подходит",
                    "callback_data": f"mi:dislike:{item_id}",
                },
            ]
        ]
    }
