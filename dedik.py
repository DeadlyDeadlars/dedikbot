import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("TG_BOT_TOKEN не найден. Проверь .env")

ALLOWED_USERS = {7524470943}

ALLOWED_COMMANDS = {
    "ls",
    "pwd",
    "whoami",
    "df -h",
    "uptime",
}

WORKDIR = Path(".").resolve()
MAX_TEXT_FILE_SIZE = 100_000  # 100 KB
# =================================================


def is_allowed(update: Update) -> bool:
    return update.effective_user.id in ALLOWED_USERS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("Доступ запрещён")
        return

    keyboard = [["Открыть терминал"]]
    await update.message.reply_text(
        "Бот управления сервером\n"
        "Команды:\n"
        "/get <path> — скачать файл\n"
        "/cat <path> — показать текстовый файл\n"
        "/put <path> — заменить файл текстом из следующего сообщения\n"
        "Отправь файл — он загрузится в текущую директорию",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )


async def terminal_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    context.user_data["terminal"] = True
    await update.message.reply_text(
        "Терминал открыт. Разрешённые команды:\n"
        + "\n".join(ALLOWED_COMMANDS)
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    text = update.message.text

    if text == "Открыть терминал":
        await terminal_mode(update, context)
        return

    # режим редактирования файла
    if context.user_data.get("put_path"):
        path = context.user_data.pop("put_path")
        path = (WORKDIR / path).resolve()
        if not str(path).startswith(str(WORKDIR)):
            await update.message.reply_text("Запрещённый путь")
            return
        path.write_text(text, encoding="utf-8")
        await update.message.reply_text(f"Файл сохранён: {path}")
        return

    if not context.user_data.get("terminal"):
        await update.message.reply_text("Нажмите 'Открыть терминал'")
        return

    if text not in ALLOWED_COMMANDS:
        await update.message.reply_text("Команда запрещена")
        return

    try:
        result = subprocess.run(
            text,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout or result.stderr or "(пусто)"
        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


async def cmd_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    if not context.args:
        await update.message.reply_text("Использование: /get <path>")
        return

    path = (WORKDIR / context.args[0]).resolve()
    if not path.exists() or not path.is_file():
        await update.message.reply_text("Файл не найден")
        return

    if not str(path).startswith(str(WORKDIR)):
        await update.message.reply_text("Запрещённый путь")
        return

    await update.message.reply_document(InputFile(path))


async def cmd_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    if not context.args:
        await update.message.reply_text("Использование: /cat <path>")
        return

    path = (WORKDIR / context.args[0]).resolve()
    if not path.exists() or not path.is_file():
        await update.message.reply_text("Файл не найден")
        return

    if path.stat().st_size > MAX_TEXT_FILE_SIZE:
        await update.message.reply_text("Файл слишком большой")
        return

    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        await update.message.reply_text("Не удалось прочитать как текст")
        return

    await update.message.reply_text(f"```\n{text}\n```", parse_mode="Markdown")


async def cmd_put(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    if not context.args:
        await update.message.reply_text("Использование: /put <path>")
        return

    context.user_data["put_path"] = context.args[0]
    await update.message.reply_text(
        "Отправь СЛЕДУЮЩИМ сообщением новый текст файла (он полностью заменит старый)."
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    doc = update.message.document
    filename = doc.file_name
    target = (WORKDIR / filename).resolve()

    if not str(target).startswith(str(WORKDIR)):
        await update.message.reply_text("Запрещённый путь")
        return

    file = await doc.get_file()
    await file.download_to_drive(custom_path=str(target))
    await update.message.reply_text(f"Файл загружен: {target}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get", cmd_get))
    app.add_handler(CommandHandler("cat", cmd_cat))
    app.add_handler(CommandHandler("put", cmd_put))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()


if __name__ == "__main__":
    main()
