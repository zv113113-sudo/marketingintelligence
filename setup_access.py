#!/usr/bin/env python3
"""Install the dedicated deployment public key and make SSH reachable."""
from pathlib import Path
import os
import shutil
import subprocess

PUBLIC_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIAX7XFGe8EgsSeyH0YLo1dIzbD9+mDTUi+MqKSYAvUX codex-marketing-intel"


def run(command):
    return subprocess.run(command, text=True, capture_output=True)


def main():
    if os.geteuid() != 0:
        raise SystemExit("Нужно запустить от root.")

    ssh_dir = Path("/root/.ssh")
    authorized_keys = ssh_dir / "authorized_keys"
    ssh_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(ssh_dir, 0o700)

    existing = authorized_keys.read_text(encoding="utf-8") if authorized_keys.exists() else ""
    keys = {line.strip() for line in existing.splitlines() if line.strip()}
    if PUBLIC_KEY not in keys:
        with authorized_keys.open("a", encoding="utf-8") as target:
            if existing and not existing.endswith("\n"):
                target.write("\n")
            target.write(PUBLIC_KEY + "\n")
    os.chmod(authorized_keys, 0o600)

    service = "ssh" if shutil.which("systemctl") else None
    if service:
        result = run(["systemctl", "enable", "--now", service])
        if result.returncode != 0:
            fallback = run(["systemctl", "enable", "--now", "sshd"])
            if fallback.returncode != 0:
                print("Внимание: не удалось автоматически запустить SSH-службу.")

    if shutil.which("ufw"):
        status = run(["ufw", "status"])
        if "Status: active" in status.stdout:
            opened = run(["ufw", "allow", "22/tcp"])
            if opened.returncode != 0:
                print("Внимание: не удалось автоматически открыть порт 22 в UFW.")

    print("ACCESS READY")
    print("Публичный ключ установлен; пароль не передавался.")


if __name__ == "__main__":
    main()
