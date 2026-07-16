from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler

from database.db import (
    register_user, get_message, get_setting, is_admin,
    get_button_label, get_custom_buttons
)
from handlers.keyboards import main_menu_kb, admin_menu_kb, proofs_inline_kb
from handlers.utils import make_mention


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await register_user(user.id, user.username, user.full_name)

    if await get_setting("maintenance_mode") == "1" and not await is_admin(user.id):
        await update.message.reply_text("🔧 البوت في وضع الصيانة حالياً، يرجى المحاولة لاحقًا.")
        return

    if await is_admin(user.id):
        await update.message.reply_text(
            "👑 مرحبًا بك في لوحة الإدارة!",
            reply_markup=admin_menu_kb()
        )
        return

    welcome = await get_message("welcome")
    kb = await main_menu_kb()
    await update.message.reply_text(welcome, reply_markup=kb)


async def handle_proofs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    label = await get_button_label("proofs")
    if update.message.text != label:
        return
    kb = await proofs_inline_kb()
    await update.message.reply_text("📋 جروب الإثباتات:", reply_markup=kb)


async def handle_tote(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    label = await get_button_label("tote")
    if update.message.text != label:
        return
    msg = await get_message("tote")
    await update.message.reply_text(msg)


async def handle_custom_buttons(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    custom = await get_custom_buttons()
    for btn in custom:
        if text == btn[1]:
            await update.message.reply_text(
                f"🔗 {btn[1]}",
                reply_markup=__import__('telegram').InlineKeyboardMarkup([
                    [__import__('telegram').InlineKeyboardButton(btn[1], url=btn[2])]
                ])
            )
            return


def get_handlers():
    return [
        CommandHandler("start", cmd_start),
    ]
