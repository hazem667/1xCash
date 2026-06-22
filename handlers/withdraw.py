import os
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from database.db import (
    get_message, get_setting, create_withdraw_order,
    get_withdraw_order, update_withdraw_status,
    get_all_admins, set_live_chat, delete_live_chat, log_action
)
from handlers.keyboards import (
    cancel_keyboard, main_menu_keyboard,
    withdraw_code_keyboard, withdraw_admin_keyboard,
    help_request_keyboard, withdraw_help_result_keyboard
)
from states.states import WithdrawStates
from datetime import datetime

router = Router()


@router.message(F.text == "💸 سحب")
async def withdraw_start(message: types.Message, state: FSMContext):
    await state.clear()
    enabled = await get_setting("withdraw_enabled")
    if enabled == "0":
        await message.answer("⚠️ خدمة السحب غير متاحة حالياً.\nجاري التحديث والصيانة.")
        return

    intro = await get_message("withdraw_intro")
    await message.answer(intro, reply_markup=cancel_keyboard("🔙 القائمة الرئيسية"), parse_mode="Markdown")
    ask_id = await get_message("withdraw_ask_id")
    await message.answer(ask_id, reply_markup=cancel_keyboard())
    await state.set_state(WithdrawStates.waiting_id)


@router.message(WithdrawStates.waiting_id)
async def withdraw_get_id(message: types.Message, state: FSMContext):
    if message.text == "❌ إلغاء":
        await state.clear()
        welcome = await get_message("welcome")
        await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return

    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ الرجاء إدخال أرقام فقط.")
        return

    await state.update_data(account_id=message.text.strip())
    ask_code = await get_message("withdraw_ask_code")
    await message.answer(ask_code, reply_markup=withdraw_code_keyboard(), parse_mode="Markdown")
    await state.set_state(WithdrawStates.waiting_code_step)


@router.message(WithdrawStates.waiting_code_step)
async def withdraw_code_step(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "🔙 القائمة الرئيسية":
        await state.clear()
        welcome = await get_message("welcome")
        await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return

    if message.text == "🆘 طلب مساعدة":
        user = message.from_user
        username = f"@{user.username}" if user.username else user.full_name
        data = await state.get_data()
        account_id = data.get("account_id", "غير محدد")

        # إشعار الأدمن
        admin_text = (
            f"🆘 *طلب مساعدة في السحب*\n\n"
            f"👤 المستخدم: {username}\n"
            f"🆔 Telegram ID: `{user.id}`\n"
            f"💠 ID الحساب: `{account_id}`"
        )
        admins = await get_all_admins()
        for admin_id in admins:
            try:
                await bot.send_message(
                    admin_id,
                    admin_text,
                    reply_markup=help_request_keyboard(user.id),
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        await set_live_chat(user.id, "pending", "withdraw_help")
        help_msg = await get_message("help_requested")
        await message.answer(help_msg, reply_markup=cancel_keyboard("❌ إلغاء"))
        await state.clear()
        return

    if message.text == "✅ تم الحصول على الكود":
        ask_code_val = await get_message("withdraw_ask_code_value")
        await message.answer(ask_code_val, reply_markup=cancel_keyboard())
        await state.set_state(WithdrawStates.waiting_code_value)
        return

    await message.answer("⚠️ الرجاء اختيار أحد الأزرار.")


@router.message(WithdrawStates.waiting_code_value)
async def withdraw_get_code(message: types.Message, state: FSMContext):
    if message.text == "❌ إلغاء":
        await state.clear()
        welcome = await get_message("welcome")
        await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return

    if not message.text or not message.text.strip():
        await message.answer("⚠️ الرجاء إدخال الكود.")
        return

    await state.update_data(code=message.text.strip())
    ask_amount = await get_message("withdraw_ask_amount")
    await message.answer(ask_amount, reply_markup=cancel_keyboard())
    await state.set_state(WithdrawStates.waiting_amount)


@router.message(WithdrawStates.waiting_amount)
async def withdraw_get_amount(message: types.Message, state: FSMContext):
    if message.text == "❌ إلغاء":
        await state.clear()
        welcome = await get_message("welcome")
        await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return

    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ الرجاء إدخال أرقام فقط.")
        return

    await state.update_data(amount=message.text.strip())
    ask_method = await get_message("withdraw_ask_method")
    await message.answer(ask_method, reply_markup=cancel_keyboard())
    await state.set_state(WithdrawStates.waiting_method)


@router.message(WithdrawStates.waiting_method)
async def withdraw_get_method(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "❌ إلغاء":
        await state.clear()
        welcome = await get_message("welcome")
        await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return

    if not message.text or not message.text.strip():
        await message.answer("⚠️ الرجاء إدخال طريقة الاستلام.")
        return

    data = await state.get_data()
    user = message.from_user
    username = f"@{user.username}" if user.username else user.full_name

    order_id = await create_withdraw_order(
        user_id=user.id,
        username=username,
        account_id=data["account_id"],
        code=data["code"],
        amount=data["amount"],
        method=message.text.strip()
    )

    now = datetime.now()
    admin_text = (
        f"💸 *طلب سحب جديد*\n\n"
        f"Order #{order_id}\n\n"
        f"👤 المستخدم: {username}\n"
        f"🆔 Telegram ID: `{user.id}`\n"
        f"💠 ID الحساب: `{data['account_id']}`\n"
        f"🔑 كود السحب: `{data['code']}`\n"
        f"💰 المبلغ: {data['amount']} جنيه\n"
        f"💳 طريقة الاستلام: {message.text.strip()}\n"
        f"🕒 الوقت: {now.strftime('%Y/%m/%d - %I:%M %p')}"
    )

    admins = await get_all_admins()
    for admin_id in admins:
        try:
            await bot.send_message(
                admin_id,
                admin_text,
                reply_markup=withdraw_admin_keyboard(order_id),
                parse_mode="Markdown"
            )
        except Exception:
            pass

    sent_msg = await get_message("withdraw_sent")
    await message.answer(sent_msg, reply_markup=main_menu_keyboard())
    await state.clear()
    await log_action("withdraw_created", user.id, order_id, f"order#{order_id}")


# ── Callbacks للأدمن: السحب العادي ───────────────────────

@router.callback_query(F.data.startswith("wit_success:"))
async def wit_success(callback: types.CallbackQuery, bot: Bot):
    order_id = int(callback.data.split(":")[1])
    order = await get_withdraw_order(order_id)
    if not order:
        await callback.answer("الطلب غير موجود!")
        return

    # order: id, user_id, username, account_id, code, amount, method, status, ...
    user_id = order[1]
    account_id = order[3]
    amount = order[5]
    method = order[6]
    now = datetime.now()

    template = await get_message("withdraw_success")
    user_text = template.format(
        account_id=account_id,
        amount=amount,
        method=method,
        date=now.strftime('%d/%m/%Y'),
        time=now.strftime('%I:%M %p')
    )

    try:
        await bot.send_message(user_id, user_text)
    except Exception:
        pass

    await update_withdraw_status(order_id, "accepted")
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ *تمت الموافقة*",
        parse_mode="Markdown"
    )
    await callback.answer("تمت الموافقة")


@router.callback_query(F.data.startswith("wit_reject:"))
async def wit_reject(callback: types.CallbackQuery, bot: Bot):
    order_id = int(callback.data.split(":")[1])
    order = await get_withdraw_order(order_id)
    if not order:
        await callback.answer("الطلب غير موجود!")
        return

    user_id = order[1]
    account_id = order[3]
    now = datetime.now()

    template = await get_message("withdraw_rejected")
    user_text = template.format(
        account_id=account_id,
        date=now.strftime('%d/%m/%Y'),
        time=now.strftime('%I:%M %p')
    )

    try:
        await bot.send_message(user_id, user_text)
    except Exception:
        pass

    await update_withdraw_status(order_id, "rejected")
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ *تم الرفض*",
        parse_mode="Markdown"
    )
    await callback.answer("تم الرفض")


@router.callback_query(F.data.startswith("wit_reply:"))
async def wit_reply(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split(":")[1])
    order = await get_withdraw_order(order_id)
    if not order:
        await callback.answer("الطلب غير موجود!")
        return

    user_id = order[1]
    await state.update_data(reply_to_user_id=user_id)
    from states.states import AdminStates
    await state.set_state(AdminStates.waiting_reply_message)
    await callback.message.answer("💬 اكتب رسالتك للعميل:")
    await callback.answer()


# ── Callbacks: طلب مساعدة في السحب ──────────────────────

@router.callback_query(F.data.startswith("chat_start:"))
async def chat_start(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    await set_live_chat(user_id, "active", "withdraw_help")

    connected_msg = await get_message("admin_connected")
    try:
        await bot.send_message(user_id, connected_msg)
    except Exception:
        pass

    await state.update_data(chatting_with=user_id)
    from states.states import AdminStates
    await state.set_state(AdminStates.chatting_with_user)

    await callback.message.edit_reply_markup(
        reply_markup=withdraw_help_result_keyboard(user_id)
    )
    await callback.message.answer(
        f"💬 أنت الآن متصل بالعميل `{user_id}`\nكل ما تكتبه سيصله مباشرة.",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("chat_ignore:"))
async def chat_ignore(callback: types.CallbackQuery, bot: Bot):
    user_id = int(callback.data.split(":")[1])
    await delete_live_chat(user_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("تم التجاهل")


@router.callback_query(F.data.startswith("wit_help_success:"))
async def wit_help_success(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    now = datetime.now()

    data = await state.get_data()
    await state.clear()
    await delete_live_chat(user_id)

    try:
        await bot.send_message(
            user_id,
            f"✅ تمت عملية السحب بنجاح!\n"
            f"🕒 التاريخ: {now.strftime('%d/%m/%Y')}\n"
            f"⏰ الوقت: {now.strftime('%I:%M %p')}\n\n"
            f"نشكر ثقتك بنا 💙"
        )
    except Exception:
        pass

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("✅ تم إرسال رسالة النجاح للعميل وإنهاء المحادثة.")
    await callback.answer()


@router.callback_query(F.data.startswith("wit_help_reject:"))
async def wit_help_reject(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    now = datetime.now()

    await state.clear()
    await delete_live_chat(user_id)

    try:
        await bot.send_message(
            user_id,
            f"❌ عذرًا، تم رفض عملية السحب.\n"
            f"🕒 التاريخ: {now.strftime('%d/%m/%Y')}\n\n"
            f"للاستفسار تواصل مع الإدارة: @z7yzf"
        )
    except Exception:
        pass

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("❌ تم إرسال رسالة الرفض للعميل وإنهاء المحادثة.")
    await callback.answer()
