
import subprocess
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
load_dotenv()

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")  # токен хранить в env

# Telegram ID разрешённых пользователей
ALLOWED_USERS = {7524470943}  # <-- замени на свой TG ID

# Разрешённые команды (белый список)
ALLOWED_COMMANDS = {
    "ls",
    "pwd",
    "whoami",
    "df -h",
    "uptime",
    "cd ..",
    "cd",
}

# =================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("Доступ запрещён")
        return

    keyboard = [["Открыть терминал"]]
    await update.message.reply_text(
        "Бот управления сервером",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def terminal_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return

    context.user_data["terminal"] = True
    await update.message.reply_text(
        "Терминал открыт.\n"
        "Разрешённые команды:\n" + "\n".join(ALLOWED_COMMANDS)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return

    text = update.message.text.strip()

    if text == "Открыть терминал":
        await terminal_mode(update, context)
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
            timeout=5
        )
        output = result.stdout or result.stderr or "(пусто)"
        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()



