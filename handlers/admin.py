import aiosqlite
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from database.db import (
    get_message, set_message, get_setting, set_setting,
    get_stats, get_all_admins, add_admin, remove_admin,
    get_deposit_order, update_deposit_status, log_action,
    is_admin, get_button_label, set_button_label,
    get_custom_buttons, add_custom_button, delete_custom_button
)
from handlers.keyboards import (
    admin_menu_keyboard, main_menu_keyboard,
    edit_messages_keyboard, settings_keyboard, buttons_manage_keyboard
)
from states.states import AdminStates
from datetime import datetime

router = Router()


# ── إحصائيات ──────────────────────────────────────────────

@router.message(F.text == "📊 الإحصائيات")
async def show_stats(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    stats = await get_stats()
    text = (
        f"📊 *إحصائيات البوت*\n\n"
        f"👥 المستخدمين: {stats['users']}\n\n"
        f"💵 *الإيداع*\n"
        f"  🟡 قيد المراجعة: {stats['dep_pending']}\n"
        f"  🟢 مقبول: {stats['dep_accepted']}\n\n"
        f"💸 *السحب*\n"
        f"  🟡 قيد المراجعة: {stats['wit_pending']}\n"
        f"  🟢 مقبول: {stats['wit_accepted']}\n"
    )
    await message.answer(text, parse_mode="Markdown")


# ── الإذاعة ───────────────────────────────────────────────

@router.message(F.text == "📣 إذاعة")
async def broadcast_start(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    await message.answer(
        "📣 اكتب الرسالة التي تريد إرسالها لجميع المستخدمين:\n"
        "(اكتب /cancel للإلغاء)"
    )
    await state.set_state(AdminStates.waiting_broadcast)


@router.message(AdminStates.waiting_broadcast)
async def broadcast_send(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("تم الإلغاء.", reply_markup=admin_menu_keyboard())
        return

    from database.db import get_all_users
    users = await get_all_users()
    success = 0
    for uid in users:
        try:
            await bot.copy_message(uid, message.chat.id, message.message_id)
            success += 1
        except Exception:
            pass

    await state.clear()
    await message.answer(
        f"✅ تم الإرسال لـ {success} من {len(users)} مستخدم.",
        reply_markup=admin_menu_keyboard()
    )
    await log_action("broadcast", message.from_user.id, details=f"sent to {success} users")


# ── تعديل الرسائل ─────────────────────────────────────────

@router.message(F.text == "📝 تعديل الرسائل")
async def edit_messages_menu(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    await message.answer("📝 اختر الرسالة التي تريد تعديلها:", reply_markup=edit_messages_keyboard())


@router.callback_query(F.data.startswith("edit_msg:"))
async def edit_msg_select(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("غير مصرح!")
        return
    key = callback.data.split(":")[1]
    current = await get_message(key)
    await state.update_data(editing_key=key)
    await state.set_state(AdminStates.waiting_edit_message_value)
    await callback.message.answer(
        f"📝 *الرسالة الحالية:*\n\n{current}\n\n"
        f"أرسل الرسالة الجديدة:\n(اكتب /cancel للإلغاء)",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AdminStates.waiting_edit_message_value)
async def edit_msg_save(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("تم الإلغاء.", reply_markup=admin_menu_keyboard())
        return

    data = await state.get_data()
    key = data.get("editing_key")
    await set_message(key, message.text)
    await state.clear()
    await message.answer("✅ تم تحديث الرسالة بنجاح!", reply_markup=admin_menu_keyboard())
    await log_action("edit_message", message.from_user.id, details=key)


# ── الإعدادات ─────────────────────────────────────────────

@router.message(F.text == "⚙️ الإعدادات")
async def show_settings(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    dep = await get_setting("deposit_enabled")
    wit = await get_setting("withdraw_enabled")
    promo = await get_setting("promo_enabled")
    maint = await get_setting("maintenance_mode")
    soon = await get_setting("soon_enabled")
    soon_url = await get_setting("soon_url")

    text = (
        f"⚙️ *الإعدادات الحالية*\n\n"
        f"💵 الإيداع: {'✅ مفعّل' if dep == '1' else '❌ موقوف'}\n"
        f"💸 السحب: {'✅ مفعّل' if wit == '1' else '❌ موقوف'}\n"
        f"🎟 البرومو: {'✅ مفعّل' if promo == '1' else '❌ موقوف'}\n"
        f"🔧 الصيانة: {'✅ مفعّلة' if maint == '1' else '❌ موقوفة'}\n"
        f"🔜 Soon: {'✅ مفعّل' if soon == '1' else '❌ موقوف'}\n"
        f"🔗 رابط Soon: {soon_url or 'غير محدد'}\n"
    )
    await message.answer(text, reply_markup=settings_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data.startswith("toggle:"))
async def toggle_setting(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("غير مصرح!")
        return
    key = callback.data.split(":")[1]
    current = await get_setting(key)
    new_val = "0" if current == "1" else "1"
    await set_setting(key, new_val)

    labels = {
        "deposit_enabled": "الإيداع",
        "withdraw_enabled": "السحب",
        "promo_enabled": "البرومو",
        "maintenance_mode": "وضع الصيانة",
        "soon_enabled": "Soon",
    }
    label = labels.get(key, key)
    status = "✅ مفعّل" if new_val == "1" else "❌ موقوف"
    await callback.answer(f"{label}: {status}")

    dep = await get_setting("deposit_enabled")
    wit = await get_setting("withdraw_enabled")
    promo = await get_setting("promo_enabled")
    maint = await get_setting("maintenance_mode")
    soon = await get_setting("soon_enabled")
    soon_url = await get_setting("soon_url")

    text = (
        f"⚙️ *الإعدادات الحالية*\n\n"
        f"💵 الإيداع: {'✅ مفعّل' if dep == '1' else '❌ موقوف'}\n"
        f"💸 السحب: {'✅ مفعّل' if wit == '1' else '❌ موقوف'}\n"
        f"🎟 البرومو: {'✅ مفعّل' if promo == '1' else '❌ موقوف'}\n"
        f"🔧 الصيانة: {'✅ مفعّلة' if maint == '1' else '❌ موقوفة'}\n"
        f"🔜 Soon: {'✅ مفعّل' if soon == '1' else '❌ موقوف'}\n"
        f"🔗 رابط Soon: {soon_url or 'غير محدد'}\n"
    )
    await callback.message.edit_text(text, reply_markup=settings_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "set_soon_url")
async def set_soon_url_start(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("غير مصرح!")
        return
    await callback.message.answer("🔗 أرسل رابط Soon:\n(اكتب /cancel للإلغاء)")
    await state.set_state(AdminStates.waiting_soon_url)
    await callback.answer()


@router.message(AdminStates.waiting_soon_url)
async def set_soon_url_save(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("تم الإلغاء.", reply_markup=admin_menu_keyboard())
        return
    await set_setting("soon_url", message.text.strip())
    await state.clear()
    await message.answer("✅ تم تعيين رابط Soon!", reply_markup=admin_menu_keyboard())


# ── إدارة الأزرار ─────────────────────────────────────────

@router.message(F.text == "🔘 إدارة الأزرار")
async def manage_buttons(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    dep = await get_button_label("deposit")
    wit = await get_button_label("withdraw")
    promo = await get_button_label("promo")
    soon = await get_button_label("soon")
    custom = await get_custom_buttons()
    custom_text = "\n".join([f"  • {b[1]} → {b[2]}" for b in custom]) if custom else "  لا توجد"

    text = (
        f"🔘 *إدارة الأزرار*\n\n"
        f"أسماء الأزرار الحالية:\n"
        f"• إيداع: {dep}\n"
        f"• سحب: {wit}\n"
        f"• برومو: {promo}\n"
        f"• Soon: {soon}\n\n"
        f"أزرار اللينك المخصصة:\n{custom_text}"
    )
    await message.answer(text, reply_markup=buttons_manage_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data.startswith("btn_label:"))
async def btn_label_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("غير مصرح!")
        return
    key = callback.data.split(":")[1]
    current = await get_button_label(key)
    await state.update_data(btn_label_key=key)
    await state.set_state(AdminStates.waiting_button_label)
    await callback.message.answer(
        f"✏️ الاسم الحالي: *{current}*\n\nأرسل الاسم الجديد:\n(اكتب /cancel للإلغاء)",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AdminStates.waiting_button_label)
async def btn_label_save(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("تم الإلغاء.", reply_markup=admin_menu_keyboard())
        return
    data = await state.get_data()
    key = data.get("btn_label_key")
    await set_button_label(key, message.text.strip())
    await state.clear()
    await message.answer(f"✅ تم تغيير الاسم إلى: {message.text.strip()}", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "btn_add_custom")
async def btn_add_custom_start(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("غير مصرح!")
        return
    await callback.message.answer("➕ أرسل اسم الزرار الجديد:\n(اكتب /cancel للإلغاء)")
    await state.set_state(AdminStates.waiting_custom_btn_label)
    await callback.answer()


@router.message(AdminStates.waiting_custom_btn_label)
async def btn_custom_label(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("تم الإلغاء.", reply_markup=admin_menu_keyboard())
        return
    await state.update_data(new_btn_label=message.text.strip())
    await state.set_state(AdminStates.waiting_custom_btn_url)
    await message.answer("🔗 الآن أرسل الرابط:")


@router.message(AdminStates.waiting_custom_btn_url)
async def btn_custom_url(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("تم الإلغاء.", reply_markup=admin_menu_keyboard())
        return
    data = await state.get_data()
    label = data.get("new_btn_label")
    await add_custom_button(label, message.text.strip())
    await state.clear()
    await message.answer(f"✅ تم إضافة الزرار: {label}", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "btn_del_custom")
async def btn_del_custom_list(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("غير مصرح!")
        return
    custom = await get_custom_buttons()
    if not custom:
        await callback.message.answer("لا توجد أزرار مخصصة للحذف.")
        await callback.answer()
        return
    btns = [
        [InlineKeyboardButton(text=f"🗑 {b[1]}", callback_data=f"del_custom_btn:{b[0]}")]
        for b in custom
    ]
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=btns)
    await callback.message.answer("اختر الزرار الذي تريد حذفه:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("del_custom_btn:"))
async def btn_del_confirm(callback: types.CallbackQuery):
    btn_id = int(callback.data.split(":")[1])
    await delete_custom_button(btn_id)
    await callback.message.edit_text("✅ تم حذف الزرار.")
    await callback.answer()


# ── إدارة الأدمنز ─────────────────────────────────────────

@router.callback_query(F.data == "admin_add")
async def admin_add_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("غير مصرح!")
        return
    await callback.message.answer(
        "➕ أرسل الـ Telegram ID للمستخدم:\n(اكتب /cancel للإلغاء)"
    )
    await state.set_state(AdminStates.waiting_add_admin)
    await callback.answer()


@router.message(AdminStates.waiting_add_admin)
async def admin_add_save(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("تم الإلغاء.", reply_markup=admin_menu_keyboard())
        return

    if not message.text.strip().isdigit():
        await message.answer("⚠️ الرجاء إدخال Telegram ID صحيح (أرقام فقط).")
        return

    new_admin_id = int(message.text.strip())
    await add_admin(new_admin_id, "")
    await state.clear()
    await message.answer(
        f"✅ تمت إضافة `{new_admin_id}` كأدمن.",
        parse_mode="Markdown",
        reply_markup=admin_menu_keyboard()
    )
    await log_action("add_admin", message.from_user.id, new_admin_id)


@router.callback_query(F.data == "admin_remove")
async def admin_remove_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("غير مصرح!")
        return
    await callback.message.answer(
        "➖ أرسل الـ Telegram ID للأدمن الذي تريد حذفه:\n(اكتب /cancel للإلغاء)"
    )
    await state.set_state(AdminStates.waiting_add_admin)
    await callback.answer()


# ── قبول الإيداع ──────────────────────────────────────────

@router.message(AdminStates.waiting_deposit_amount)
async def deposit_amount_received(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("تم الإلغاء.", reply_markup=admin_menu_keyboard())
        return

    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ الرجاء إدخال مبلغ صحيح (أرقام فقط).")
        return

    amount = message.text.strip()
    data = await state.get_data()
    order_id = data.get("pending_order_id")

    order = await get_deposit_order(order_id)
    if not order:
        await message.answer("⚠️ الطلب غير موجود!")
        await state.clear()
        return

    user_id = order[1]
    account_id = order[3]
    now = datetime.now()

    template = await get_message("deposit_accepted")
    user_text = template.format(
        account_id=account_id,
        amount=amount,
        date=now.strftime('%d/%m/%Y'),
        time=now.strftime('%I:%M %p')
    )

    try:
        await bot.send_message(user_id, user_text)
    except Exception:
        pass

    await update_deposit_status(order_id, "accepted", amount)
    await state.clear()
    await message.answer(
        f"✅ تم قبول طلب الإيداع Order #{order_id} وإرسال الإشعار للعميل.",
        reply_markup=admin_menu_keyboard()
    )
    await log_action("deposit_accepted", message.from_user.id, order_id, f"amount={amount}")


# ── الرد على العميل ───────────────────────────────────────

@router.message(AdminStates.waiting_reply_message)
async def send_reply(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("تم الإلغاء.", reply_markup=admin_menu_keyboard())
        return

    data = await state.get_data()
    user_id = data.get("reply_to_user_id")

    try:
        await bot.send_message(user_id, f"📨 *رسالة من الإدارة:*\n\n{message.text}", parse_mode="Markdown")
        await message.answer("✅ تم إرسال الرسالة للعميل.", reply_markup=admin_menu_keyboard())
    except Exception:
        await message.answer("⚠️ لم يتمكن البوت من إرسال الرسالة.")

    await state.clear()


# ── طلبات الإيداع والسحب ─────────────────────────────────

@router.message(F.text == "📥 طلبات الإيداع")
async def list_deposit_orders(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    async with aiosqlite.connect("data/bot.db") as db:
        async with db.execute(
            "SELECT id, username, account_id, amount, status FROM deposit_orders ORDER BY id DESC LIMIT 10"
        ) as cur:
            rows = await cur.fetchall()

    if not rows:
        await message.answer("📭 لا توجد طلبات إيداع.")
        return

    text = "📥 *آخر طلبات الإيداع:*\n\n"
    for row in rows:
        status_icon = {"pending": "🟡", "accepted": "🟢", "rejected": "🔴"}.get(row[4], "⚪")
        text += f"{status_icon} Order #{row[0]} | {row[1]} | ID: {row[2]} | {row[3] or '?'} جنيه\n"

    await message.answer(text, parse_mode="Markdown")


@router.message(F.text == "📤 طلبات السحب")
async def list_withdraw_orders(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    async with aiosqlite.connect("data/bot.db") as db:
        async with db.execute(
            "SELECT id, username, account_id, amount, method, status FROM withdraw_orders ORDER BY id DESC LIMIT 10"
        ) as cur:
            rows = await cur.fetchall()

    if not rows:
        await message.answer("📭 لا توجد طلبات سحب.")
        return

    text = "📤 *آخر طلبات السحب:*\n\n"
    for row in rows:
        status_icon = {"pending": "🟡", "accepted": "🟢", "rejected": "🔴"}.get(row[5], "⚪")
        text += f"{status_icon} Order #{row[0]} | {row[1]} | {row[3]} جنيه | {row[4]}\n"

    await message.answer(text, parse_mode="Markdown")


# ── المحادثات ─────────────────────────────────────────────

@router.message(F.text == "💬 المحادثات")
async def list_chats(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    from database.db import get_pending_chats, get_active_chats
    pending = await get_pending_chats()
    active = await get_active_chats()

    text = "💬 *المحادثات*\n\n"
    text += f"⏳ منتظرة: {len(pending)}\n"
    text += f"🟢 نشطة: {len(active)}\n"

    if active:
        text += "\n*المحادثات النشطة:*\n"
        for chat in active:
            text += f"• User ID: `{chat[0]}`\n"

    await message.answer(text, parse_mode="Markdown")


# ── السجلات ───────────────────────────────────────────────

@router.message(F.text == "📜 السجلات")
async def show_logs(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    async with aiosqlite.connect("data/bot.db") as db:
        async with db.execute(
            "SELECT action, admin_id, target_id, details, created_at FROM logs ORDER BY id DESC LIMIT 10"
        ) as cur:
            rows = await cur.fetchall()

    if not rows:
        await message.answer("📭 لا توجد سجلات.")
        return

    text = "📜 *آخر السجلات:*\n\n"
    for row in rows:
        text += f"• `{row[0]}` | admin:{row[1]} | {row[3]} | {row[4][:16]}\n"

    await message.answer(text, parse_mode="Markdown")
