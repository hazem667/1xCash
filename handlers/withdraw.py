import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler,
    MessageHandler, CallbackQueryHandler, filters, CommandHandler
)
from database.db import (
    get_message, get_setting, get_button_label, is_admin,
    create_order, get_order, update_order, log_action
)
from handlers.keyboards import (
    main_menu_kb, withdraw_platform_kb, wit_cancel_order_kb, order_admin_kb
)
from handlers.utils import make_mention, now_str, broadcast_to_admins
from states.states import WIT_PLATFORM, WIT_AMOUNT, WIT_CONFIRM


async def wit_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if await get_setting("maintenance_mode") == "1" and not await is_admin(user.id):
        await update.message.reply_text("🔧 البوت في وضع الصيانة.")
        return ConversationHandler.END
    if await get_setting("withdraw_enabled") == "0":
        await update.message.reply_text("⚠️ خدمة السحب غير متاحة حالياً.")
        return ConversationHandler.END

    mention = make_mention(user)
    template = await get_message("withdraw_intro")
    text = template.replace("{mention}", mention)
    kb = await withdraw_platform_kb()
    await update.message.reply_text(text, reply_markup=kb)
    return WIT_PLATFORM


async def wit_platform(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plat_key = query.data.split(":")[1]
    platform_name = await get_button_label(plat_key)
    ctx.user_data["wit_platform"] = platform_name

    ask = await get_message("withdraw_ask_amount")
    await query.edit_message_text(
        ask,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("رجوع 🔙", callback_data="wit_back_platform")]
        ])
    )
    return WIT_AMOUNT


async def wit_back_platform(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    mention = make_mention(user)
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

    ctx.user_data["wit_amount"] = text
    user = update.effective_user
    mention = make_mention(user)
    platform = ctx.user_data.get("wit_platform", "")
    amount = text

    order_id, seq = await create_order(
        order_type="withdraw",
        platform=platform,
        account_id=None,
        amount=amount,
        user_id=user.id,
        user_mention=mention,
        user_full_name=user.full_name,
    )
    ctx.user_data["wit_order_id"] = order_id

    sent_msg = await get_message("withdraw_sent")
    await update.message.reply_text(sent_msg, reply_markup=wit_cancel_order_kb(order_id))

    date_str, time_str = now_str()
    admin_text = (
        f"📤 *طلب سحب جديد*\n\n"
        f"Order #{seq}\n\n"
        f"👤 المستخدم: {mention}\n"
        f"🆔 Telegram ID: `{user.id}`\n\n"
        f"✳️ الزر المختار: {platform}\n"
        f"💶 المبلغ: {amount}\n\n"
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
            msg_ids = json.loads(order[11])
            for admin_id, msg_id in msg_ids.items():
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
    await query.delete_message()
    kb = await main_menu_kb()
    await query.get_bot().send_message(query.from_user.id, "🏠 تم الإلغاء.", reply_markup=kb)
    ctx.user_data.clear()
    return ConversationHandler.END


def get_handler():
    from telegram.ext import filters as f

    async def wit_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        label = await get_button_label("withdraw")
        if update.message.text != label:
            return ConversationHandler.END
        return await wit_start(update, ctx)

    return ConversationHandler(
        entry_points=[MessageHandler(f.TEXT & ~f.COMMAND, wit_entry)],
        states={
            WIT_PLATFORM: [
                CallbackQueryHandler(wit_platform, pattern=r"^wit_plat:"),
                CallbackQueryHandler(wit_cancel, pattern=r"^cancel$"),
            ],
            WIT_AMOUNT: [
                CallbackQueryHandler(wit_back_platform, pattern=r"^wit_back_platform$"),
                MessageHandler(f.TEXT & ~f.COMMAND, wit_amount),
            ],
            WIT_CONFIRM: [
                CallbackQueryHandler(wit_cancel_order, pattern=r"^wit_cancel:\d+$"),
            ],
        },
        fallbacks=[CommandHandler("start", lambda u, c: ConversationHandler.END)],
        per_user=True,
        allow_reentry=True,
        name="withdraw_conv",
    )
