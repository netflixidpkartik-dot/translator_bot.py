#!/usr/bin/env python3
"""
Telegram Translation Bot — Powered by GROQ (Free!)
Translates: English ↔ Chinese | English ↔ Vietnamese
"""

import logging
from groq import Groq
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ── YOUR KEYS ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = "8273301534:AAG8XXU19905Ukkfe5eb3qqwZ91DjUhVTqg"
GROQ_API_KEY       = "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"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Groq client ───────────────────────────────────────────────────────────────
groq_client = Groq(api_key=GROQ_API_KEY)

# ── Per-user mode storage ─────────────────────────────────────────────────────
user_modes: dict[int, str] = {}

# ── Translation modes ─────────────────────────────────────────────────────────
MODES = {
    "en_zh": "🇬🇧 English  →  🇨🇳 Chinese",
    "zh_en": "🇨🇳 Chinese  →  🇬🇧 English",
    "en_vi": "🇬🇧 English  →  🇻🇳 Vietnamese",
    "vi_en": "🇻🇳 Vietnamese  →  🇬🇧 English",
    "auto":  "🔄 Auto-detect language",
}

LANGUAGE_NAMES = {
    "en_zh": ("English", "Chinese (Simplified)"),
    "zh_en": ("Chinese (Simplified)", "English"),
    "en_vi": ("English", "Vietnamese"),
    "vi_en": ("Vietnamese", "English"),
}

# ── System prompts ────────────────────────────────────────────────────────────
AUTO_PROMPT = """You are a professional translator.
Detect the language of the user's text and translate as follows:
- English    → translate to BOTH Chinese (Simplified) AND Vietnamese
- Chinese    → translate to English only
- Vietnamese → translate to English only
- Any other  → translate to English only

Return ONLY the translation, no detected language, no explanations.

For English input use exactly this format:
🇨🇳 <chinese translation>
🇻🇳 <vietnamese translation>

For Chinese or Vietnamese input, return only the English translation as plain text."""

DIRECT_PROMPT = (
    "You are a professional translator. "
    "Translate the text from {source} to {target}. "
    "Return ONLY the translated text — no labels, no explanations, no quotes."
)


# ── Core translation call ─────────────────────────────────────────────────────
def translate(text: str, mode: str) -> str:
    try:
        if mode == "auto":
            system = AUTO_PROMPT
        else:
            src, tgt = LANGUAGE_NAMES[mode]
            system = DIRECT_PROMPT.format(source=src, target=tgt)

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": text},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error("Translation error: %s", e)
        return f"❌ Error: {e}"


# ── Keyboard builder ──────────────────────────────────────────────────────────
def mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=key)]
        for key, label in MODES.items()
    ])


# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Hello {name}! I'm your Translation Bot powered by Groq AI.\n\n"
        "I can translate between:\n"
        "  🇬🇧 English  ↔  🇨🇳 Chinese\n"
        "  🇬🇧 English  ↔  🇻🇳 Vietnamese\n\n"
        "👇 Choose a mode below, then send me any text!",
        reply_markup=mode_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 How to use:\n\n"
        "1. Use /mode to pick a translation direction\n"
        "2. Send any text — I'll translate it instantly\n"
        "3. Use /current to check your active mode\n\n"
        "Commands:\n"
        "/start   — Welcome screen\n"
        "/mode    — Change translation mode\n"
        "/current — Show current mode\n"
        "/help    — This message",
    )


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🌐 Choose your translation mode:",
        reply_markup=mode_keyboard(),
    )


async def current_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mode = user_modes.get(update.effective_user.id, "auto")
    await update.message.reply_text(f"✅ Current mode: {MODES[mode]}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    mode = query.data
    if mode not in MODES:
        return
    user_modes[query.from_user.id] = mode
    await query.edit_message_text(
        f"✅ Mode set to: {MODES[mode]}\n\nNow send me any text to translate! 👇"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid  = update.effective_user.id
    mode = user_modes.get(uid, "auto")
    text = update.message.text.strip()

    if not text:
        await update.message.reply_text("⚠️ Please send some text.")
        return

    await context.bot.send_chat_action(update.effective_chat.id, "typing")

    result = translate(text, mode)
    await update.message.reply_text(result)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Error: %s", context.error, exc_info=context.error)


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("help",    help_command))
    app.add_handler(CommandHandler("mode",    mode_command))
    app.add_handler(CommandHandler("current", current_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Bot is running! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
