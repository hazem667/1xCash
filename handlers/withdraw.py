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
from handlers.keyboards import main_menu_kb, withdraw_platform_kb, wit_cancel_order_kb, order_admin_kb
from handlers.utils import make_mention, now_str, broadcast_to_admins
from states.states import WIT_PLATFORM, WIT_AMOUNT, WIT_CONFIRM


async def wit_platform(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    if await get_setting("maintenance_mode") == "1" and not await is_admin(user.id):
        await query.answer("🔧 البوت في وضع الصيانة.", show_alert=True)
        return ConversationHandler.END
    if await get_setting("withdraw_enabled") == "0":
        await query.answer("⚠️ خدمة السحب غير متاحة حالياً.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    await query.message.chat.send_action(ChatAction.TYPING)
    plat_key = query.data.split(":")[1]
    platform_name = await get_button_label(plat_key)
    ctx.user_data["wit_platform"] = platform_name

    ask = await get_message("withdraw_ask_amount")
    await query.edit_message_text(ask, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("رجوع 🔙", callback_data="wit_back_platform")]
    ]))
    return WIT_AMOUNT


async def wit_back_platform(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mention = make_mention(query.from_user)
    template = await get_message("withdraw_intro")
    text = template.replace("{mention}", mention)
    kb = await withdraw_platform_kb()
    await query.edit_message_text(text, reply_markup=kb)
    return WIT_PLATFORM


async def wit_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("⚠️ يرجى إدخال أرقام فقط.")
        return WIT_AMOUNT

    await update.message.chat.send_action(ChatAction.TYPING)
    user = update.effective_user
    mention = make_mention(user)
    platform = ctx.user_data.get("wit_platform", "")

    order_id, seq = await create_order(
        order_type="withdraw", platform=platform,
        account_id=None, amount=text,
        user_id=user.id, user_mention=mention, user_full_name=user.full_name,
    )

    sent_msg = await get_message("withdraw_sent")
    await update.message.reply_text(sent_msg, reply_markup=wit_cancel_order_kb(order_id))

    date_str, time_str = now_str()
    admin_text = (
        f"📤 *طلب سحب جديد*\n\n"
        f"Order #{seq}\n\n"
        f"👤 المستخدم: {mention}\n"
        f"🆔 Telegram ID: `{user.id}`\n\n"
        f"✳️ الزر المختار: {platform}\n"
        f"💶 المبلغ: {text}\n\n"
        f"🕒 الوقت: {date_str} - {time_str}"
    )
    kb = order_admin_kb(order_id, "withdraw")
    admin_msgs = await broadcast_to_admins(update.get_bot(), admin_text, reply_markup=kb)
    await update_order(order_id, cancel_msg_ids=json.dumps({str(k): v for k, v in admin_msgs.items()}))
    return WIT_CONFIRM


async def wit_cancel_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
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


async def wit_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
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
        entry_points=[CallbackQueryHandler(wit_platform, pattern=r"^wit_plat:")],
        states={
            WIT_PLATFORM: [
                CallbackQueryHandler(wit_back_platform, pattern=r"^wit_back_platform$"),
            ],
            WIT_AMOUNT: [
                CallbackQueryHandler(wit_back_platform, pattern=r"^wit_back_platform$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, wit_amount),
            ],
            WIT_CONFIRM: [
                CallbackQueryHandler(wit_cancel_order, pattern=r"^wit_cancel:\d+$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", lambda u, c: ConversationHandler.END),
            CallbackQueryHandler(wit_cancel, pattern=r"^cancel$"),
        ],
        per_user=True,
        allow_reentry=True,
        name="withdraw_conv",
    )
