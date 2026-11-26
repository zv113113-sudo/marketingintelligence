from pathlib import Path
from urllib import request, error
import json
import socket


TARGETS = {
    "Marketing Intelligence": Path(__file__).resolve().parent / ".env",
    "Jobs Monitor": Path(
        r"C:\Users\0\Documents\Codex\2026-09-03\referenced-chatgpt-conversation-this-is-an\runtime\jobs_monitor\.env"
    ),
}


def read_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def check(name, env_path):
    print(f"\n{name}")
    if not env_path.is_file():
        print("  .env не найден")
        return
    try:
        addresses = socket.getaddrinfo("api.telegram.org", 443, type=socket.SOCK_STREAM)
        ips = sorted({row[4][0] for row in addresses})
        print("  DNS: OK (" + ", ".join(ips[:3]) + ")")
    except OSError as exc:
        print(f"  DNS: ОШИБКА ({type(exc).__name__}: {exc})")
        return
    try:
        token = read_env(env_path).get("TELEGRAM_BOT_TOKEN")
        if not token:
            print("  Telegram API: токен не настроен")
            return
        req = request.Request(
            f"https://api.telegram.org/bot{token}/getMe",
            headers={"User-Agent": "MarketingIntelligenceConnectivityCheck/1.0"},
        )
        with request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
        print("  Telegram API: " + ("OK" if result.get("ok") else "ОШИБКА ответа API"))
    except error.HTTPError as exc:
        print(f"  Telegram API: HTTP {exc.code}")
    except Exception as exc:
        print(f"  Telegram API: ОШИБКА ({type(exc).__name__}: {exc})")


if __name__ == "__main__":
    for target_name, env_file in TARGETS.items():
        check(target_name, env_file)
    input("\nПроверка завершена. Нажмите Enter, чтобы закрыть окно...")
