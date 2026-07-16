import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import (
    ContextTypes, ConversationHandler,
    MessageHandler, CallbackQueryHandler, filters, CommandHandler
)
from database.db import (
    get_message, get_setting, get_button_label, is_admin,
    create_order, get_order, update_order, log_action
)
from handlers.keyboards import main_menu_kb, deposit_platform_kb, dep_cancel_order_kb, order_admin_kb
from handlers.utils import make_mention, now_str, broadcast_to_admins
from states.states import DEP_PLATFORM, DEP_ACCOUNT_ID, DEP_AMOUNT, DEP_CONFIRM


async def dep_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if await get_setting("maintenance_mode") == "1" and not await is_admin(user.id):
        await update.message.reply_text("🔧 البوت في وضع الصيانة.")
        return ConversationHandler.END
    if await get_setting("deposit_enabled") == "0":
        await update.message.reply_text("⚠️ خدمة الإيداع غير متاحة حالياً.")
        return ConversationHandler.END

    await update.message.chat.send_action(ChatAction.TYPING)
    mention = make_mention(user)
    template = await get_message("deposit_intro")
    text = template.replace("{mention}", mention)
    kb = await deposit_platform_kb()
    await update.message.reply_text(text, reply_markup=kb)
    return DEP_PLATFORM


async def dep_platform(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.chat.send_action(ChatAction.TYPING)
    plat_key = query.data.split(":")[1]
    platform_name = await get_button_label(plat_key)
    ctx.user_data["dep_platform"] = platform_name

    ask = await get_message("deposit_ask_id")
    text = ask.replace("{platform}", platform_name)
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("رجوع 🔙", callback_data="dep_back_platform")]
    ]))
    return DEP_ACCOUNT_ID


async def dep_back_platform(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mention = make_mention(query.from_user)
    template = await get_message("deposit_intro")
    text = template.replace("{mention}", mention)
    kb = await deposit_platform_kb()
    await query.edit_message_text(text, reply_markup=kb)
    return DEP_PLATFORM


async def dep_account_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(ChatAction.TYPING)
    ctx.user_data["dep_account_id"] = update.message.text.strip()
    ask = await get_message("deposit_ask_amount")
    await update.message.reply_text(ask, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("رجوع 🔙", callback_data="dep_back_id")]
    ]))
    return DEP_AMOUNT


async def dep_back_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    platform = ctx.user_data.get("dep_platform", "")
    ask = await get_message("deposit_ask_id")
    text = ask.replace("{platform}", platform)
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("رجوع 🔙", callback_data="dep_back_platform")]
    ]))
    return DEP_ACCOUNT_ID


async def dep_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("⚠️ يرجى إدخال أرقام فقط.")
        return DEP_AMOUNT

    await update.message.chat.send_action(ChatAction.TYPING)
    ctx.user_data["dep_amount"] = text
    user = update.effective_user
    mention = make_mention(user)
    platform = ctx.user_data.get("dep_platform", "")
    account_id = ctx.user_data.get("dep_account_id", "")

    order_id, seq = await create_order(
        order_type="deposit", platform=platform,
        account_id=account_id, amount=text,
        user_id=user.id, user_mention=mention, user_full_name=user.full_name,
    )
    ctx.user_data["dep_order_id"] = order_id

    sent_msg = await get_message("deposit_sent")
    await update.message.reply_text(sent_msg, reply_markup=dep_cancel_order_kb(order_id))

    date_str, time_str = now_str()
    admin_text = (
        f"📥 *طلب إيداع جديد*\n\n"
        f"Order #{seq}\n\n"
        f"👤 المستخدم: {mention}\n"
        f"🆔 Telegram ID: `{user.id}`\n\n"
        f"✳️ الزر المختار: {platform}\n"
        f"💠 ID الحساب: `{account_id}`\n"
        f"💶 المبلغ: {text}\n\n"
        f"🕒 الوقت: {date_str} - {time_str}"
    )
    kb = order_admin_kb(order_id, "deposit")
    admin_msgs = await broadcast_to_admins(update.get_bot(), admin_text, reply_markup=kb)
    await update_order(order_id, cancel_msg_ids=json.dumps({str(k): v for k, v in admin_msgs.items()}))
    return DEP_CONFIRM


async def dep_cancel_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split(":")[1])
    order = await get_order(order_id)
    if not order or order[7] != "pending":
        await query.edit_message_text("⚠️ لا يمكن إلغاء هذا الطلب.")
        return ConversationHandler.END

    await update_order(order_id, status="cancelled")
    if order[11]:
        try:
            for admin_id, msg_id in json.loads(order[11]).items():
                try:
                    await query.get_bot().delete_message(int(admin_id), msg_id)
                except Exception:
                    pass
        except Exception:
            pass

    cancelled_msg = await get_message("order_cancelled_user")
    await query.edit_message_text(cancelled_msg)
    kb = await main_menu_kb()
    await query.get_bot().send_message(query.from_user.id, "🏠 القائمة الرئيسية:", reply_markup=kb)
    return ConversationHandler.END


async def dep_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.delete_message()
    except Exception:
        pass
    kb = await main_menu_kb()
    await query.get_bot().send_message(query.from_user.id, "🏠 تم الإلغاء.", reply_markup=kb)
    ctx.user_data.clear()
    return ConversationHandler.END


def get_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(dep_platform, pattern=r"^dep_plat:")],
        states={
            DEP_ACCOUNT_ID: [
                CallbackQueryHandler(dep_back_platform, pattern=r"^dep_back_platform$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, dep_account_id),
            ],
            DEP_AMOUNT: [
                CallbackQueryHandler(dep_back_id, pattern=r"^dep_back_id$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, dep_amount),
            ],
            DEP_CONFIRM: [
                CallbackQueryHandler(dep_cancel_order, pattern=r"^dep_cancel:\d+$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", lambda u, c: ConversationHandler.END),
            CallbackQueryHandler(dep_cancel, pattern=r"^cancel$"),
        ],
        per_user=True,
        allow_reentry=True,
        name="deposit_conv",
    )
