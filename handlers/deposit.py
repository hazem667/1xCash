import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler,
    MessageHandler, CallbackQueryHandler, filters, CommandHandler
)
from database.db import (
    get_message, get_setting, get_button_label, is_admin,
    create_order, get_order, update_order,
    get_all_admins, log_action
)
from handlers.keyboards import (
    main_menu_kb, deposit_platform_kb, dep_cancel_order_kb, order_admin_kb
)
from handlers.utils import make_mention, now_str, broadcast_to_admins
from states.states import DEP_PLATFORM, DEP_ACCOUNT_ID, DEP_AMOUNT, DEP_CONFIRM


# ══════════════════════════════════════════════
# ENTRY
# ══════════════════════════════════════════════

async def dep_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if await get_setting("maintenance_mode") == "1" and not await is_admin(user.id):
        await update.message.reply_text("🔧 البوت في وضع الصيانة.")
        return ConversationHandler.END
    if await get_setting("deposit_enabled") == "0":
        await update.message.reply_text("⚠️ خدمة الإيداع غير متاحة حالياً.")
        return ConversationHandler.END

    mention = make_mention(user)
    template = await get_message("deposit_intro")
    text = template.replace("{mention}", mention)
    kb = await deposit_platform_kb()
    await update.message.reply_text(text, reply_markup=kb)
    return DEP_PLATFORM


# ══════════════════════════════════════════════
# STEP 1: PLATFORM
# ══════════════════════════════════════════════

async def dep_platform(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plat_key = query.data.split(":")[1]
    platform_name = await get_button_label(plat_key)
    ctx.user_data["dep_platform"] = platform_name

    ask = await get_message("deposit_ask_id")
    text = ask.replace("{platform}", platform_name)
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("رجوع 🔙", callback_data="dep_back_platform")]
        ])
    )
    return DEP_ACCOUNT_ID


async def dep_back_platform(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    mention = make_mention(user)
    template = await get_message("deposit_intro")
    text = template.replace("{mention}", mention)
    kb = await deposit_platform_kb()
    await query.edit_message_text(text, reply_markup=kb)
    return DEP_PLATFORM


# ══════════════════════════════════════════════
# STEP 2: ACCOUNT ID
# ══════════════════════════════════════════════

async def dep_account_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["dep_account_id"] = update.message.text.strip()
    ask = await get_message("deposit_ask_amount")
    await update.message.reply_text(
        ask,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("رجوع 🔙", callback_data="dep_back_id")]
        ])
    )
    return DEP_AMOUNT


async def dep_back_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    platform = ctx.user_data.get("dep_platform", "")
    ask = await get_message("deposit_ask_id")
    text = ask.replace("{platform}", platform)
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("رجوع 🔙", callback_data="dep_back_platform")]
        ])
    )
    return DEP_ACCOUNT_ID


# ══════════════════════════════════════════════
# STEP 3: AMOUNT
# ══════════════════════════════════════════════

async def dep_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("⚠️ يرجى إدخال أرقام فقط.")
        return DEP_AMOUNT
    ctx.user_data["dep_amount"] = text

    user = update.effective_user
    mention = make_mention(user)
    platform = ctx.user_data.get("dep_platform", "")
    account_id = ctx.user_data.get("dep_account_id", "")
    amount = text

    # إنشاء الطلب
    order_id, seq = await create_order(
        order_type="deposit",
        platform=platform,
        account_id=account_id,
        amount=amount,
        user_id=user.id,
        user_mention=mention,
        user_full_name=user.full_name,
    )
    ctx.user_data["dep_order_id"] = order_id

    # رسالة للمستخدم
    sent_msg = await get_message("deposit_sent")
    user_msg = await update.message.reply_text(
        sent_msg,
        reply_markup=dep_cancel_order_kb(order_id)
    )
    ctx.user_data["dep_user_msg_id"] = user_msg.message_id

    # رسالة للمشرفين
    date_str, time_str = now_str()
    admin_text = (
        f"📥 *طلب إيداع جديد*\n\n"
        f"Order #{seq}\n\n"
        f"👤 المستخدم: {mention}\n"
        f"🆔 Telegram ID: `{user.id}`\n\n"
        f"✳️ الزر المختار: {platform}\n"
        f"💠 ID الحساب: `{account_id}`\n"
        f"💶 المبلغ: {amount}\n\n"
        f"🕒 الوقت: {date_str} - {time_str}"
    )
    kb = order_admin_kb(order_id, "deposit")
    admin_msgs = await broadcast_to_admins(update.get_bot(), admin_text, reply_markup=kb)

    # حفظ IDs رسائل الإدارة
    await update_order(order_id, cancel_msg_ids=json.dumps(
        {str(k): v for k, v in admin_msgs.items()}
    ))

    return DEP_CONFIRM


async def dep_amount_invalid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ يرجى إدخال أرقام فقط.")
    return DEP_AMOUNT


# ══════════════════════════════════════════════
# CANCEL ORDER (المستخدم يلغي)
# ══════════════════════════════════════════════

async def dep_cancel_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split(":")[1])

    order = await get_order(order_id)
    if not order:
        await query.edit_message_text("⚠️ الطلب غير موجود.")
        return ConversationHandler.END

    if order[7] != "pending":  # status
        await query.edit_message_text("⚠️ لا يمكن إلغاء هذا الطلب.")
        return ConversationHandler.END

    await update_order(order_id, status="cancelled")

    # حذف رسائل الإدارة
    if order[11]:  # cancel_msg_ids
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


# ══════════════════════════════════════════════
# CANCEL CONVERSATION
# ══════════════════════════════════════════════

async def dep_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    kb = await main_menu_kb()
    await query.get_bot().send_message(
        query.from_user.id,
        "🏠 تم الإلغاء، العودة للقائمة الرئيسية.",
        reply_markup=kb
    )
    ctx.user_data.clear()
    return ConversationHandler.END


# ══════════════════════════════════════════════
# HANDLER BUILDER
# ══════════════════════════════════════════════

async def _entry_filter(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    label = await get_button_label("deposit")
    return update.message.text == label


def get_handler():
    from telegram.ext import filters as f

    async def dep_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        label = await get_button_label("deposit")
        if update.message.text != label:
            return ConversationHandler.END
        return await dep_start(update, ctx)

    return ConversationHandler(
        entry_points=[MessageHandler(f.TEXT & ~f.COMMAND, dep_entry)],
        states={
            DEP_PLATFORM: [
                CallbackQueryHandler(dep_platform, pattern=r"^dep_plat:"),
                CallbackQueryHandler(dep_cancel, pattern=r"^cancel$"),
            ],
            DEP_ACCOUNT_ID: [
                CallbackQueryHandler(dep_back_platform, pattern=r"^dep_back_platform$"),
                MessageHandler(f.TEXT & ~f.COMMAND, dep_account_id),
            ],
            DEP_AMOUNT: [
                CallbackQueryHandler(dep_back_id, pattern=r"^dep_back_id$"),
                MessageHandler(f.TEXT & ~f.COMMAND, dep_amount),
            ],
            DEP_CONFIRM: [
                CallbackQueryHandler(dep_cancel_order, pattern=r"^dep_cancel:\d+$"),
            ],
        },
        fallbacks=[CommandHandler("start", lambda u, c: ConversationHandler.END)],
        per_user=True,
        allow_reentry=True,
        name="deposit_conv",
    )
