"""Create the bot's local .env through a masked desktop form."""
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

ROOT = Path(__file__).resolve().parent


def existing_env():
    values = {}
    try:
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    except OSError:
        pass
    return values


def main():
    current = existing_env()
    root = tk.Tk()
    root.title("Локальная настройка Marketing Intelligence")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=18, pady=16)
    frame.pack(fill="both", expand=True)
    tk.Label(
        frame,
        text="Введите ключи в этом окне. Они будут записаны в локальный .env\n"
        "и не появятся в терминале или сообщениях Telegram.",
        justify="left",
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

    tk.Label(frame, text="Telegram bot token").grid(row=1, column=0, sticky="w", pady=4)
    telegram = tk.Entry(frame, width=54, show="•")
    telegram.insert(0, current.get("TELEGRAM_BOT_TOKEN", ""))
    telegram.grid(row=1, column=1, sticky="w", pady=4)

    tk.Label(frame, text="ID чата Telegram").grid(row=2, column=0, sticky="w", pady=4)
    chat = tk.Entry(frame, width=54)
    chat.insert(0, current.get("TELEGRAM_CHAT_ID", "366007726"))
    chat.grid(row=2, column=1, sticky="w", pady=4)

    tk.Label(frame, text="GigaChat auth key").grid(row=3, column=0, sticky="w", pady=4)
    giga = tk.Entry(frame, width=54, show="•")
    giga.insert(0, current.get("GIGACHAT_AUTH_KEY", ""))
    giga.grid(row=3, column=1, sticky="w", pady=4)

    def save():
        values = {
            "TELEGRAM_BOT_TOKEN": telegram.get().strip(),
            "TELEGRAM_CHAT_ID": chat.get().strip(),
            "GIGACHAT_AUTH_KEY": giga.get().strip(),
        }
        if not all(values.values()):
            messagebox.showerror("Не заполнено", "Заполните все три поля.", parent=root)
            return
        if any("\n" in value or "\r" in value for value in values.values()):
            messagebox.showerror("Неверный формат", "Каждое значение должно быть одной строкой.", parent=root)
            return
        env_path = ROOT / ".env"
        if env_path.exists() and not messagebox.askyesno(
            "Файл уже есть", "Заменить существующий .env?", parent=root
        ):
            return
        content = "\n".join(f"{key}={value}" for key, value in values.items())
        content += "\nGIGACHAT_MODEL=GigaChat-3-Ultra\nMIN_SCORE=7.5\nMAX_DAILY_ITEMS=7\nEDITORIAL_MIN_SCORE=7.0\n"
        try:
            env_path.write_text(content, encoding="utf-8")
        except OSError:
            messagebox.showerror("Ошибка", "Не удалось сохранить .env в папке проекта.", parent=root)
            return
        telegram.delete(0, "end")
        giga.delete(0, "end")
        messagebox.showinfo("Сохранено", ".env создан в папке бота. Секреты не выводились в терминал.", parent=root)
        root.destroy()

    buttons = tk.Frame(frame)
    buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(14, 0))
    tk.Button(buttons, text="Сохранить локально", command=save).pack(side="left", padx=(0, 8))
    tk.Button(buttons, text="Отмена", command=root.destroy).pack(side="left")
    telegram.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
